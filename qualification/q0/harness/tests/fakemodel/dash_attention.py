# CPU test double mirroring the native import-only Triton fallback of DashAttention._forward_triton.
class DashAttention:
    def _forward_triton(self, cache):
        try:
            from .sparse_gather_e2e_triton import triton_gather_attention_e2e
        except Exception:
            return None
        return triton_gather_attention_e2e(cache)

    def _forward_dense(self, cache):
        return "dense"
