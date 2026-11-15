"""WP-0005 Q0 unmodified-model qualification harness (research only).

This package is a separate research qualification runner. It is not production
OCR integration and must never be referenced by product projects. Every module
is importable with the Python standard library alone; torch, transformers,
pypdfium2 and the model's remote code are imported lazily and only inside the
released GPU execution stage (WP-0005 /004), never by the CPU checks.
"""

HARNESS_ID = "eld-q0-harness/WP-0005-002"
SCHEMA_VERSION = "eldq0/1"
