"""Plan bounded D2H byte spans; no torch operation copies, reshapes or casts device values."""
import ctypes
import itertools
import math
import hashlib
import struct
import threading
from pathlib import Path


def spans(shape,strides,element_size,offset,storage_bytes,limit):
    """Yield (source byte offset, logical byte count) from initialized logical elements."""
    if len(shape)!=len(strides) or element_size<=0 or offset<0 or min([0,*shape,*strides])<0:
        raise ValueError("unsupported tensor metadata")
    if not math.prod(shape):
        return
    last=offset+sum((width-1)*stride for width,stride in zip(shape,strides))
    if (last+1)*element_size>storage_bytes:
        raise ValueError("address outside source storage")
    inline=1
    rank=len(shape)
    while rank and (shape[rank-1]==1 or strides[rank-1]==inline):
        rank-=1
        inline*=shape[rank]
    if math.prod(shape[:rank])>limit:
        raise ValueError("source requires too many strided transfers")
    for index in itertools.product(*(range(n) for n in shape[:rank])):
        start=offset+sum(i*s for i,s in zip(index,strides))
        yield start*element_size,inline*element_size


class PinnedTransport:
    def __init__(self,torch,capacity):
        self.torch=torch
        self.capacity=capacity
        self.host=torch.empty(capacity,dtype=torch.uint8,pin_memory=True)
        self.destination=self.host.data_ptr()
        self.origin=threading.get_native_id()
        self.stream=torch.cuda.current_stream(0)
        if self.stream.cuda_stream!=torch.cuda.default_stream(0).cuda_stream or not self.host.is_pinned():
            raise RuntimeError("requires single source thread on default stream and pinned host space")
        lib=Path(torch.__file__).resolve().parent/"lib/cudart64_13.dll"
        self.runtime=ctypes.WinDLL(str(lib))
        self.memcpy=self.runtime.cudaMemcpyAsync
        self.memcpy.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int,ctypes.c_void_p]
        self.memcpy.restype=ctypes.c_int
        self.done=torch.cuda.Event()
        self.done.record(self.stream)
        self.done.synchronize()
        self.serial=0
        self.origin_event=None

    def stream_record(self):
        stream=self.torch.cuda.current_stream(0)
        if threading.get_native_id()!=self.origin or stream.cuda_stream!=self.stream.cuda_stream:
            raise RuntimeError("producer thread or CUDA stream changed")
        return {"thread":self.origin,"stream":stream.cuda_stream,"device":0}

    def allocations(self):
        stats=self.torch.cuda.memory_stats(0)
        keys=("allocation.all.allocated","allocated_bytes.all.allocated","reserved_bytes.all.allocated")
        return {k:stats[k] for k in keys}

    def read(self,t):
        if self.origin_event is None:
            raise RuntimeError("native producer instruction unavailable")
        current=self.stream_record()
        if self.origin_event["stream"]!=current["stream"] or self.origin_event["thread"]!=current["thread"]:
            raise RuntimeError("unknown cross-stream/cross-thread producer")
        if t.layout!=self.torch.strided or t.is_conj() or t.is_neg() or t.is_cuda and t.device.index!=0:
            raise ValueError("unsupported tensor view or device")
        base=t.untyped_storage().data_ptr()
        size=t.numel()*t.element_size()
        if size>192*(1<<20):
            raise ValueError("individual tensor exceeds qualified range")
        segments=spans(t.shape,t.stride(),t.element_size(),t.storage_offset(),t.untyped_storage().nbytes(),65536)
        baseline=self.allocations()
        parts=[]
        receipts=[]
        used=0
        copies=0
        address_hash=hashlib.sha256()
        def finish():
            nonlocal used,copies,address_hash
            if t.is_cuda:
                self.done.record(self.stream)
                self.done.synchronize()
                if not self.done.query():
                    raise RuntimeError("copy event incomplete")
            self.serial+=1
            parts.append(ctypes.string_at(self.destination,used))
            receipts.append({"transport":"cuda-fenced-pinned" if t.is_cuda else "host-fenced",
                    "producer_stream":self.origin_event["stream"],"producer":self.origin_event,
                    "copy_stream":current["stream"],"copy_thread":current["thread"],"source_storage":base,
                    "dest_storage":self.destination,"completion":True,"complete_before_return":True,
                    "fence_serial":self.serial,"pinned":self.host.is_pinned(),"bytes":used,"byte_runs":copies,
                    "source_shape":list(t.shape),"source_strides":list(t.stride()),"element_size":t.element_size(),
                    "source_offset":t.storage_offset(),"allocation_bytes":t.untyped_storage().nbytes(),
                    "address_map_sha256":address_hash.hexdigest(),"native_event":self.done.cuda_event,"api":"cudaMemcpyAsync(D2H)" if t.is_cuda else "memmove"})
            used=copies=0
            address_hash=hashlib.sha256()
        for start,n in segments:
            while n:
                piece=min(n,self.capacity-used)
                if t.is_cuda:
                    rc=self.memcpy(self.destination+used,base+start,piece,2,self.stream.cuda_stream)
                    if rc:
                        raise RuntimeError(f"cudaMemcpyAsync D2H returned {rc}")
                else:
                    ctypes.memmove(self.destination+used,base+start,piece)
                address_hash.update(struct.pack("<QQQ",start,used,piece))
                copies+=1
                used+=piece
                start+=piece
                n-=piece
                if used==self.capacity:
                    finish()
        if used or not receipts:
            finish()
        if sum(len(part) for part in parts)!=size:
            raise RuntimeError("logical transfer length")
        final=self.allocations()
        if baseline!=final:
            raise RuntimeError(f"observer CUDA allocator changed during D2H {baseline} -> {final}")
        for receipt in receipts:
            receipt.update(allocator_before=baseline,allocator_after=final)
        return b"".join(parts),receipts
