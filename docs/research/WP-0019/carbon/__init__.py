"""WP-0019 persistent local WinRT full-page and in-memory crop OCR worker."""

from .engine import (
    HISTORICAL_WP0015_ASSET_SHA256,
    Worker,
    bmp_to_expected_bgra_bytes,
    inspect_bmp_header,
    rgb_to_opaque_bgra_bytes,
    sha256_hex,
    slice_bgra_rect,
)

__all__ = [
    "HISTORICAL_WP0015_ASSET_SHA256",
    "Worker",
    "bmp_to_expected_bgra_bytes",
    "inspect_bmp_header",
    "rgb_to_opaque_bgra_bytes",
    "sha256_hex",
    "slice_bgra_rect",
]
