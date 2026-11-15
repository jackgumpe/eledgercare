"""Installation-stage CPU preflight (no torch import, no model import, no GPU).

Run with the task venv interpreter after the locked install and the verified model
download, BEFORE any GPU lease: proves the installed set, absence of forbidden backends,
the real renderer identity and the exact predicted raster bytes, and the model directory
digests plus static save-path facts. Any mismatch blocks the GPU stage.
"""

from __future__ import annotations

from pathlib import Path

from .fixtures import read_verified_fixture, verify_rendered_pages
from .locks import verify_installed
from .modelfiles import load_manifest, verify_model_dir
from .protocol import REPO_ROOT
from .render import check_renderer, raster_tuples, render_pdf_bytes, renderer_identity
from .sourcecheck import MODEL_DIR_NAMES, analyze_model_sources


def cpu_preflight(*, protocol: dict, lock: dict, pdfium, installed: dict, importable, dist_version,
                  model_dir: Path | None, manifest_path: Path, repo_root: Path = REPO_ROOT) -> dict:
    report = {"installed": verify_installed(lock, installed, importable)}
    ident = renderer_identity(pdfium, dist_version)
    check_renderer(ident, protocol)
    report["renderer"] = ident
    report["rasters"] = {}
    for fx in protocol["fixtures"]:
        images = render_pdf_bytes(pdfium, read_verified_fixture(fx, repo_root))
        report["rasters"][fx["fixture_id"]] = verify_rendered_pages(fx, raster_tuples(images))
    if model_dir is not None:
        rep = verify_model_dir(Path(model_dir), load_manifest(manifest_path))
        report["model_files_verified"] = len(rep["files"])
        report["static_safety"] = analyze_model_sources(Path(model_dir), MODEL_DIR_NAMES)
    report["status"] = "pass"
    return report
