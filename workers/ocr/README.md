# OCR worker boundary (not implemented)

This directory reserves the boundary for a future, separately qualified local OCR worker (feature F2).
It intentionally contains **no code, no mock and no dependency set**.

- F1 (durable intake) never runs OCR. Every admitted document's processing job stays
  `awaiting_extraction`; nothing in the product fabricates extracted fields or progress.
- A worker will be added only after a separate assignment selects and qualifies an actual local runtime,
  model/data storage and resource ownership. GPU use, model downloads and Python environments are not
  part of F1.
- Product projects do not reference research or evaluation code, and no OCR stand-in exists in the
  production path.
