# CPU test double. Like the pinned file it imports triton unconditionally at module scope;
# tests generate a TRITON_STUB variant (import removed) to exercise the executed-kernel path.
import triton  # TRITON_IMPORT_LINE


def triton_gather_attention_e2e(cache):
    if getattr(cache, "raise_in_kernel", False):
        raise RuntimeError("simulated kernel failure")
    return "triton"
