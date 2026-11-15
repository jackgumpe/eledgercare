# WP-0004 /008 coordinator preflight: distinguish rounding sources

Observed at 2026-11-15T00:07Z while the author correction was still unpublished. This is a factual RV-03 clarification, not a new experiment or a corpus change. The draft correctly records the measured dimensions but describes both extra pixel rows as "float32 scale rounding". That wording conflates the page-extent and Python-scale arithmetic.

The already verified pypdfium2 5.15.2 Windows wheel (SHA-256 74d1bace34fb01c660d0b64344d5a4b7d276942b7c6623c88ab59ea21c5acfbd) supplies the inspected source:

- pypdfium2/_helpers/page.py lines 58/65: get_width/get_height call FPDF_GetPageWidthF / FPDF_GetPageHeightF; lines 458/459 compute math.ceil(self.get_width() * scale) and math.ceil(self.get_height() * scale).
- pypdfium2_raw/bindings.py lines 647/657: those two C functions have restype c_float. Their returned extents are converted to Python float; the scale argument 300.0 / 72.0 is Python binary64 arithmetic.
- Actual Python 3.12.10 calculation: scale repr = 4.166666666666667; the exactly representable height 792.0 multiplied by that scale is 3300.0000000000005, whose ceil is 3301. No float32 rounding of 792.0 is needed for this case.
- The decimal height 823.44 represented as float32 is 823.4400024414062; multiplied by that Python scale it is 3431.0000101725263, whose ceil is 3432. Here page-extent quantization is also relevant.

Executed read-only checks: rg of the installed wheel's two source files, followed by a Python stdlib math/struct calculation using struct.unpack("f", struct.pack("f", 823.44)). No author file, environment, or candidate was changed by this preflight.

Responsible author /008: verify this against your own pinned package and use precise causal wording, or simply state the measured dimensions and the documented ceil-based sizing rule. Keep fixture/source/expected bytes unchanged and preserve both genuine renderer resampling and stored-versus-rendered distinctions. Include the correction in the existing RV-03 response before final publication. The independent /009 closure should assess the final text against actual package source; no extra review cycle or human approval is requested here.
