# Local OCR Worker Runtime Manifest Provenance

These self-contained JSON manifests pin the exact unmodified model files and Python runtime
distribution lock used by `workers/local_ocr/` so that production execution never imports,
reads, or invokes `qualification/`, `research/`, `evaluation/`, or runtime `git.exe` (`F2-BIC-01`).

1. [`model-files.json`](model-files.json) (`eledgercare.local-ocr-model-manifest/1`):
   - Model: `baidu/Unlimited-OCR-2` at commit `0480966938291445591f69f08a13b041c073a96a`.
   - Runtime directory leaf: `Unlimited_OCR_2_04809669` (valid Python identifier for `transformers_modules`).
   - Exact 18 runtime objects (`16` non-LFS files verified by Git-blob SHA-1 and byte size; `2` safetensors shards verified by LFS SHA-256 and byte size; `6,699,195,181` total bytes) plus separate model-card notice `README.md` (`14,107` bytes, Git-blob SHA-1 `c79e1e3362c8fd2f9193d79c1db80fbf7f041c45`) in `notices\Unlimited-OCR-2_0480966938291445591f69f08a13b041c073a96a\README.md`.
   - Resolved from accepted WP-0005 Q0 manifest at core commit `41d6204648e4115ab197507d1a22f6d5c7f3e784`.

2. [`dependency-lock.json`](dependency-lock.json) (`eledgercare.local-ocr-dependency-lock/1`):
   - Interpreter/platform: CPython `3.12.10` on `Windows` `AMD64`; CUDA `13.0`, capability `[12, 0]` (`sm_120`).
   - Exact 32 locked runtime distributions (`torch==2.13.0+cu130`, `torchvision==0.28.0+cu130`, `transformers==4.52.1`, `pypdfium2==5.15.2` / PDFium `159.0.8149.0`, etc.), resolved from accepted WP-0005 metadata graph blob `ec8c650ed5fbeb0a754e4daee53aad53753a57a3`.
   - Retains explicit disclosure of `torchvision==0.28.0+cu130` (`hash_kind: "local-sha256-TOFU"`, SHA-256 `5ae0ff50fcb43a189250a5fdb36a7dc780ea5caff469653cab1e3f32ed5d385c`, independent acquisition receipt blob `877d822099e7b3628d36f6b4a709d76ecad6de00`), requiring `"torchvision-local-sha256-TOFU"` in `accepted_provenance_exceptions`.
   - Enforces `triton`, `flash_attn`, and `xformers` non-importability (`find_spec(...) is None`).
