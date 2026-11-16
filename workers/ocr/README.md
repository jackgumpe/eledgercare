# OCR worker directory redirect

Feature F1's unimplemented OCR placeholder at `workers/ocr/` is superseded in WP-0006 (F2) by the
self-contained production local extraction worker under [`../local_ocr/`](../local_ocr/README.md),
governed by [`../../docs/design/F2-local-extraction.md`](../../docs/design/F2-local-extraction.md).

- Production local extraction code and self-contained runtime manifests live solely under
  `workers/local_ocr/`.
- No OCR mock or stand-in exists in `workers/ocr/` or `workers/local_ocr/`.
- Product projects and workers never import, reference, or invoke `qualification/`, `research/`, or
  `evaluation/` tooling.
