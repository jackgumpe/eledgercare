"""Installation-stage CPU preflight (no torch import, no model import, no GPU).

Run with the task venv interpreter after the locked offline install and the verified model
download, BEFORE any GPU lease: proves the installed set equals the bound lock, absence of
optional backends (find_spec('triton') is None), the real renderer identity and the exact
predicted raster bytes, the 18 runtime objects, the separate notice, and the static
save-path facts. Any mismatch blocks the GPU stage.
"""

from __future__ import annotations

from pathlib import Path

from .fixtures import read_verified_fixture, verify_rendered_pages
from .locks import verify_installed
from .modelfiles import load_manifest, normalize_model_dir, verify_model_dir, verify_notices
from .protocol import REPO_ROOT
from .render import check_renderer, raster_tuples, render_pdf_bytes, renderer_identity
from .sourcecheck import MODEL_DIR_NAMES, analyze_model_sources


def cpu_preflight(*, protocol: dict, lock: dict, pkgs: dict, pdfium, installed: dict, importable, dist_version,
                  model_dir: Path | None, notice_dir: Path | None, manifest_path: Path,
                  repo_root: Path = REPO_ROOT) -> dict:
    report = {"installed": verify_installed(pkgs, lock, installed, importable)}
    ident = renderer_identity(pdfium, dist_version)
    check_renderer(ident, protocol)
    report["renderer"] = ident
    report["rasters"] = {}
    for fx in protocol["fixtures"]:
        images = render_pdf_bytes(pdfium, read_verified_fixture(fx, repo_root))
        report["rasters"][fx["fixture_id"]] = verify_rendered_pages(fx, raster_tuples(images))
    if model_dir is not None:
        manifest = load_manifest(manifest_path)
        md = normalize_model_dir(model_dir, model_dir)
        rep = verify_model_dir(md, manifest)
        report["model_runtime_objects_verified"] = rep["runtime_objects"]
        report["notices"] = verify_notices(Path(notice_dir), manifest)["notices"] if notice_dir else None
        report["static_safety"] = analyze_model_sources(md, MODEL_DIR_NAMES)
    report["status"] = "pass"
    return report
