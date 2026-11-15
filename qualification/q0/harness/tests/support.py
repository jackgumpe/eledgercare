"""Shared CPU-test fixtures: isolated .scratch directories, the fake model package,
a fake backend, synthetic final lock/release records. No network, GPU or installs."""

from __future__ import annotations

import copy
import importlib
import json
import shutil
import sys
import uuid
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HARNESS)) if str(HARNESS) not in sys.path else None

from q0harness.environment import build_child_env, layout  # noqa: E402
from q0harness.fixtures import extract_page_rgb_streams  # noqa: E402
from q0harness.hashing import file_digests, sha256_bytes  # noqa: E402
from q0harness.modelfiles import REQUIRED_FILES  # noqa: E402
from q0harness.protocol import MODEL_REVISION, REPO_ROOT, load_protocol  # noqa: E402

FAKE_SRC = Path(__file__).resolve().parent / "fakemodel"
SCRATCH = REPO_ROOT / ".scratch" / "q0-harness-tests"
TRIVIAL_PY = {
    "_sparse_base_impl.py": "# test double\n",
    "deepencoder.py": "# test double\n",
    "sparse_gather_triton.py": "import triton\nSPARSE_BLOCK_SIZE_SENTINEL = 32\n",
    "conversation.py": "# test double\n",
    "packing_patch.py": "def is_packed(x):\n    return False\n",
}


def new_scratch(tag: str) -> Path:
    d = SCRATCH / f"{tag}-{uuid.uuid4().hex[:8]}"
    d.mkdir(parents=True)
    return d


def remove_scratch(d: Path):
    shutil.rmtree(d, ignore_errors=True)


def purge_fake_modules():
    for name in [n for n in sys.modules if n == "transformers_modules" or n.startswith("transformers_modules.")]:
        del sys.modules[name]
    importlib.invalidate_caches()


def write_fake_model_dir(model_dir: Path, *, triton_stub: bool = False) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    for src in FAKE_SRC.glob("*.py"):
        text = src.read_text(encoding="utf-8")
        if triton_stub and src.name == "sparse_gather_e2e_triton.py":
            text = text.replace("import triton  # TRITON_IMPORT_LINE", "TRITON_STUB = True")
        (model_dir / src.name).write_bytes(text.encode("utf-8"))
    for name, text in TRIVIAL_PY.items():
        (model_dir / name).write_bytes(text.encode("utf-8"))
    for name in REQUIRED_FILES:
        p = model_dir / name
        if not p.exists():
            p.write_bytes(f"test double for {name}\n".encode())


NOTICE_BYTES = b"# test double model card (license notice)\n"


def write_notice_dir(notice_dir: Path) -> None:
    notice_dir.mkdir(parents=True, exist_ok=True)
    (notice_dir / "README.md").write_bytes(NOTICE_BYTES)


def manifest_for_dir(model_dir: Path) -> dict:
    files = []
    for name in REQUIRED_FILES:
        d = file_digests(model_dir / name)
        if name.endswith(".safetensors"):
            files.append({"path": name, "size": d["size"], "sha256": d["sha256"], "digest_kind": "lfs_sha256"})
        else:
            files.append({"path": name, "size": d["size"], "git_blob_sha1": d["git_blob_sha1"], "digest_kind": "git_blob_sha1"})
    from q0harness.hashing import git_blob_sha1_bytes
    notices = [{"path": "README.md", "size": len(NOTICE_BYTES), "git_blob_sha1": git_blob_sha1_bytes(NOTICE_BYTES),
                "digest_kind": "git_blob_sha1", "role": "test"}]
    return {"schema": "eldq0-model-files/2", "revision": MODEL_REVISION, "runtime_object_count": len(files),
            "files": files, "notices": notices}


def install_package(cache_root: Path, pkg: str, model_dir: Path, tamper: str | None = None):
    """Mimic the dynamic-module loader: copy every model .py into
    <cache>/transformers_modules/<pkg>/ and import the entry module."""
    base = cache_root / "transformers_modules"
    (base / pkg).mkdir(parents=True, exist_ok=True)
    (base / "__init__.py").write_bytes(b"")
    (base / pkg / "__init__.py").write_bytes(b"")
    for py in model_dir.glob("*.py"):
        data = py.read_bytes()
        if tamper == py.name:
            data += b"\n# modified by loader\n"
        (base / pkg / py.name).write_bytes(data)
    purge_fake_modules()
    sys.path.insert(0, str(cache_root))
    try:
        return importlib.import_module(f"transformers_modules.{pkg}.modeling_unlimitedocr")
    finally:
        sys.path.remove(str(cache_root))


class FakeImage:
    def __init__(self, w, h, rgb):
        self.width, self.height, self._rgb, self.mode = w, h, rgb, "RGB"

    def convert(self, mode):
        assert mode == "RGB"
        return self

    def to_pil(self):
        return self

    def tobytes(self):
        return self._rgb


class FakePdfium:
    """Returns, for a verified v0-clean fixture, the RGB pages stored in its dev v1 child."""

    class version:
        PYPDFIUM_INFO = "5.15.2"
        PDFIUM_INFO = "159.0.8149.0@sourcebuild-toolchained"

    def __init__(self, protocol, corrupt: bool = False):
        self.by_sha = {}
        for f in protocol["fixtures"]:
            v1 = (REPO_ROOT / f["raster_derivation"]["v1_raster300_path"]).read_bytes()
            self.by_sha[f["sha256"]] = extract_page_rgb_streams(v1)
        self.corrupt = corrupt
        outer = self

        class _Page:
            def __init__(self, p):
                self.p = p

            def render(self, scale):
                assert scale == 300.0 / 72.0
                rgb = self.p["rgb"]
                if outer.corrupt:
                    rgb = bytes([rgb[0] ^ 1]) + rgb[1:]
                return FakeImage(self.p["width"], self.p["height"], rgb)

            def close(self):
                pass

        class _Doc:
            def __init__(self, data):
                self.pages = outer.by_sha[sha256_bytes(data)]

            def __len__(self):
                return len(self.pages)

            def __getitem__(self, i):
                return _Page(self.pages[i])

            def close(self):
                pass

        self.PdfDocument = _Doc


LOCK_PATH = HARNESS / "locks" / "dependency-lock.json"
TV_LOCAL_SHA = "5ae0ff50fcb43a189250a5fdb36a7dc780ea5caff469653cab1e3f32ed5d385c"  # from the bound receipt


def committed_lock() -> dict:
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def git_reader():
    from q0harness.locks import git_blob_reader
    return git_blob_reader(REPO_ROOT)


def without_local_records(lock: dict) -> dict:
    """In-memory TEST copy of the lock with the torchvision receipt binding removed (gap state)."""
    lock = copy.deepcopy(lock)
    lock["local_hash_records"] = []
    return lock


def final_lock() -> dict:
    return committed_lock()


def lock_pkgs(lock: dict) -> dict:
    from q0harness.locks import validate_lock
    return validate_lock(lock, git_reader())


FAKE_CODE = {"head": "c" * 40, "harness_clean": True, "dirty": []}


def fake_release(protocol, p_sha, lock_sha, root, *, stage="execute", owner="author", exceptions=("torchvision-local-sha256-TOFU",)):
    rel = {"schema": "eldq0-release/2", "packet": "WP-0005", "stage": stage, "released_by": "eld-coordinator",
           "release_commit": "f" * 40, "harness_commit": FAKE_CODE["head"], "protocol_sha256": p_sha,
           "lock_sha256": lock_sha, "storage_root": str(root),
           "accepted_review": {"reviewer": "eld-q0-reviewer", "report_commit": "a" * 40, "evidence_commit": "b" * 40},
           "accepted_provenance_exceptions": list(exceptions)}
    if stage == "execute":
        rel.update(sequence={"author": "004", "reviewer": "005"}[owner], gpu_uuid=protocol["gpu"]["uuid"],
                   lease_id="test-lease")
    return rel


def fake_platform(protocol) -> dict:
    return {"os": "Windows", "machine": "AMD64", "python": "3.12.10", "torch": "2.13.0+cu130",
            "torch_cuda_version": "13.0", "cuda_available": True, "device_count": 1,
            "device_name": "NVIDIA GeForce RTX 5070 Ti", "device_capability": [12, 0],
            "arch_list": ["sm_90", "sm_120"], "device_uuid": protocol["gpu"]["uuid"]}


class FakeBackend:
    def __init__(self, protocol, *, pkg: str, model_dir: Path, modules_cache: Path, installed: dict, opts: dict | None = None):
        self.protocol, self.pkg, self.model_dir, self.cache = protocol, pkg, model_dir, Path(modules_cache)
        self._installed, self.opts = installed, opts or {}
        self.load_called = False
        self.invocations = 0
        self.probes = 0

    def platform(self):
        plat = fake_platform(self.protocol)
        plat.update(self.opts.get("platform_override", {}))
        return plat

    def installed(self):
        return dict(self._installed) | {"pip": "25.0.1"} | self.opts.get("extra_installed", {})

    def memory_probe(self):
        self.probes += 1
        return {"max_allocated": 1000 + self.probes, "max_reserved": 2000}

    def importable(self, name):
        return name in self.opts.get("importable", ())

    def dist_version(self, name):
        return "5.15.2"

    def pdfium(self):
        return FakePdfium(self.protocol, corrupt=self.opts.get("corrupt_render", False))

    def load(self, model_dir, protocol):
        self.load_called = True
        mod = install_package(self.cache, self.pkg, model_dir, tamper=self.opts.get("tamper_cache"))
        model = mod.UnlimitedOCRForCausalLM(mod.UnlimitedOCRConfig())
        model.flaky = self.opts.get("flaky", False)
        model.force_length = self.opts.get("force_length", False)
        return mod.FakeTokenizer(), model, {"fake_load_s": 0.0}

    def sync(self):
        pass

    def reset_peak(self):
        pass

    def cuda_memory(self):
        return {"provenance": "fake", "max_allocated": 0, "max_reserved": 0}

    def invoke(self, model, tok, prompt, images, kwargs):
        self.invocations += 1
        if self.opts.get("oom_on_invocation") == self.invocations:
            raise MemoryError("simulated out of memory")
        if self.opts.get("enter_save_path_on_invocation") == self.invocations:
            model._uocr_save_results("x", images, "somewhere")
        return model.infer_multi(tok, prompt=prompt, image_files=list(images), **kwargs)

    def is_oom(self, exc):
        return isinstance(exc, MemoryError)


def session_kit(tag: str, *, owner: str = "author", lock: dict | None = None, release_mutation=None,
                triton_stub: bool = False, opts: dict | None = None, repo_root: Path = REPO_ROOT,
                model_tamper: bool = False, code: dict | None = None, disk_usage=None, no_notice: bool = False):
    """Build an isolated root under .scratch and every Session constructor argument."""
    import shutil as _sh
    from q0harness.session import Session
    protocol, p_sha = load_protocol()
    scratch = new_scratch(tag)
    root = scratch / "q0root"
    paths = layout(root, owner)
    run_dir = paths["run_owner"] / "run-1"
    for sub in ("tmp", "home", "hf-modules", "evidence"):
        (run_dir / sub).mkdir(parents=True)
    model_dir = root / protocol["storage"]["subdirs"]["models"]
    write_fake_model_dir(model_dir, triton_stub=triton_stub)
    if not no_notice:
        write_notice_dir(root / protocol["storage"]["subdirs"]["notices"])
    manifest_path = scratch / "model-files.json"
    manifest_path.write_text(json.dumps(manifest_for_dir(model_dir)), encoding="utf-8")
    if model_tamper:
        p = model_dir / "dash_attention.py"
        p.write_bytes(p.read_bytes() + b"# tampered\n")
    lock = copy.deepcopy(final_lock() if lock is None else lock)
    lock_raw = json.dumps(lock, sort_keys=True).encode()
    try:
        installed = {a["name"]: a["version"] for a in lock_pkgs(lock).values()}
    except Exception:
        installed = {}
    release = fake_release(protocol, p_sha, sha256_bytes(lock_raw), root, owner=owner)
    if release_mutation:
        release = release_mutation(release)
    env = build_child_env({"SystemRoot": r"C:\Windows", "HF_TOKEN": "x"}, root=root, owner=owner, run_dir=run_dir,
                          gpu_uuid=protocol["gpu"]["uuid"])
    pkg = f"fake_{uuid.uuid4().hex[:8]}"
    backend = FakeBackend(protocol, pkg=pkg, model_dir=model_dir, modules_cache=Path(env["HF_MODULES_CACHE"]),
                          installed=installed, opts=opts)
    session = Session(protocol=protocol, protocol_sha256=p_sha, lock=lock, lock_sha256=sha256_bytes(lock_raw),
                      release=release, root=root, owner=owner, run_dir=run_dir, backend=backend, repo_root=repo_root,
                      expected_root=str(root), forbidden_parents=[], code=code or FAKE_CODE, lock_reader=git_reader(),
                      manifest_path=manifest_path, environ=env, disk_usage=disk_usage or _sh.disk_usage)
    return session, backend, scratch, run_dir
