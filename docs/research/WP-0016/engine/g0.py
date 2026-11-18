"""Isolated WP-0016 Gate G0 launcher wrapper over unchanged WP-0015 Carbon control.

Loads docs/research/WP-0015/carbon/launch.py in process with:
- PACKET redirected to C:/Users/jackg/eLedgerCare-Speed/WP-0016
- MODES restricted to G0 arms ('native', 'carbon_bf16')
- SCOPES extended with 'docs/research/WP-0016/engine/g0.py' so this wrapper is
  git-blob and clean-worktree verified alongside all five WP-0015 scopes.

Inherits exact CLI argv (--owner review|carbon --source --plan --sha256 --run
--lease --seconds [--min-vram-mib]) and leaves the child interpreter command
(python.exe -I -B .../docs/research/WP-0015/carbon/trial.py <seg_dir>), inference
code, and model weights completely unchanged. No CUDA/GPU calls occur on import.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ORIG_LAUNCH = ROOT / "docs/research/WP-0015/carbon/launch.py"
WP0016_PACKET = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0016")
G0_MODES = ("native", "carbon_bf16")
G0_WRAPPER_SCOPE = "docs/research/WP-0016/engine/g0.py"


def load_g0_launcher() -> ModuleType:
    spec = importlib.util.spec_from_file_location("wp0015_carbon_launch", ORIG_LAUNCH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load original launcher from {ORIG_LAUNCH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.PACKET = WP0016_PACKET
    mod.MODES = G0_MODES
    if G0_WRAPPER_SCOPE not in mod.SCOPES:
        mod.SCOPES = (*mod.SCOPES, G0_WRAPPER_SCOPE)
    return mod


def main(argv: list[str] | None = None) -> int:
    launcher = load_g0_launcher()
    if argv is None:
        return int(launcher.main())
    saved_argv = sys.argv
    try:
        sys.argv = [str(Path(__file__).resolve()), *argv]
        return int(launcher.main())
    finally:
        sys.argv = saved_argv


if __name__ == "__main__":
    sys.exit(main())
