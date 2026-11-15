# CPU test double: DASH inference switch, prefill/decode routing and the fp32 decode attend.
from .dash_attention import DashAttention

_INFER = {"on": False}


class DeepseekV2Model:
    def __init__(self, config):
        self.config = config
        self.layer = _Layer()


def _orig_forward(self, *args, **kwargs):
    return None


def configure_dash_inference(decoder, on, topm=16, page_scope_prefill=True, state=None):
    _INFER["on"] = bool(on)
    return {"on": on} if on else None


def _infer_prefill_attend(router, cache):
    out = router._forward_triton(cache)
    if out is not None:
        return out
    return router._forward_dense(cache)


def _decode_attend(cache):
    return len(cache.key_cache)


def _dash_decode_forward(cache):
    return _decode_attend(cache)


class _Layer:
    def __init__(self):
        self.router = DashAttention()

    def prefill(self, cache):
        cache._dash_idx_k = {0: cache.key_cache[0]}
        return _infer_prefill_attend(self.router, cache)

    def decode(self, cache):
        return _dash_decode_forward(cache)
