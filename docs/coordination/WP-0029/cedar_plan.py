"""Bind the single released Cedar window to the historical native W0 protocol."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "WP-0026"))
import bind as historical

guard = historical.guard
QPY = historical.QPY
SCOPE = ROOT / "docs/coordination/WP-0028/acquisition-scope.json"
MANIFEST = ROOT / "docs/fixtures/WP-0028/manifest.json"
OLD_RELEASE = HERE.parent / "WP-0026/cal-features-r1-release.json"
OLD_PLAN = HERE.parent / "WP-0026/cal-features-r1-plan.json"
BASE = Path("C:/Users/jackg/eLedgerCare-Speed/WP-0029")
OUTPUT = BASE / "acquisition/runs/cedar-r1"
LEASE = BASE / "coordination/leases/cedar-r1"
RGB_KEY = "33362fbbeb37e805a64acbf3afdc3ec04315a4706820ed634a8fe0fb865ce2d5"
WARM_HASH = "7c509b3514daf75854b2b719cc7a94d44175c5af9fdcbae8ef4df0c68ec812e7"
WARM_TOKENS = "837b21829d99ee47d583039651628cf6c7f6e796bd71ee8b5490c21d0c3a52d4"
DESKTOP = ROOT / "docs/reviews/WP-0024/admission-watch-binding.json"
PINS = {
    SCOPE: "887772656057b4188118adc5b7501bfb592f196ccd6decb496d8dbd3ba9a08b1",
    MANIFEST: "cb058f1931758c516e21e2d791d5b5dffd04646bc773b8e967a11024fdf58cf2",
    OLD_RELEASE: "a6ef16988a6d669e31d254a188f5c9f4ea0d916e467ab7aec480d8237bc84852",
    OLD_PLAN: "000cac60211fe6225ca1ef66ed82e0eb8ecc44e936d9f017b4101db946a11405",
    DESKTOP: "ad311561b81f7d3f86938861726385fa5f7ddd0ffff826d6a205552697b7ab6d",
}
read = historical.read
require = historical.require


def git(*args):
    return subprocess.check_output(["C:/Program Files/Git/cmd/git.exe", "-C", ROOT, *args], text=True).strip()


def execution_fields():
    for path, digest in PINS.items():
        require(guard.sha(path) == digest, f"Changed source {path.name}")
    ref = read(OLD_PLAN)
    scope = read(SCOPE)
    fixture = read(MANIFEST)
    cedar = [next(b for b in pair["members"] if b["owner"] == "Cedar") for pair in fixture["pairs"]]
    require(len(cedar) == 2 and cedar[0]["binder"] == "b1319c493624d146b9905f68"
            and cedar[1]["binder"] == "64ca02ee321c80c200e01a1a", "Cedar binder identity")
    first = cedar[0]["windows"][0]["pages"]
    require(first == cedar[1]["windows"][0]["pages"] and len(first) == 3, "Opening reuse")
    rgb = [p["rgb_sha256"] for p in first]
    key = hashlib.sha256((json.dumps(rgb, indent=2) + "\n").encode("ascii")).hexdigest()
    expected = scope["missing"][0]["ordered_pages"]
    require(key == RGB_KEY and [(p["sha256"], p["rgb_sha256"]) for p in first]
            == [(p["png_sha256"], p["rgb_sha256"]) for p in expected], "Opening differs from proposal")
    pages = [dict(p, image=str(ROOT / p["image"])) for p in first]
    raster = ROOT / "docs/fixtures/WP-0028/rasters"
    for p in pages:
        path = Path(p["image"]).resolve(strict=True)
        require(path.parent == raster and guard.sha(path) == p["sha256"], "Cedar PNG")
        with historical.Image.open(path) as source:
            with source.convert("RGB") as image:
                require(image.size == (2550, 3300) and hashlib.sha256(image.tobytes()).hexdigest()
                        == p["rgb_sha256"], "Cedar RGB")
    member = cedar[0]
    pdf = ROOT / member["source_pdf"]
    require(guard.sha(pdf) == member["source_pdf_sha256"], "Cedar source PDF")
    request = {"pdf":str(pdf), "sha256":member["source_pdf_sha256"], "pages":12,
               "rgb_sha256":[p["rgb_sha256"] for w in member["windows"] for p in w["pages"]]}
    warm = historical.warmup(ROOT)
    require(warm["fixture_sha256"] == WARM_HASH and not set(warm["request"]["rgb_sha256"]).intersection(
            request["rgb_sha256"]) and len(request["rgb_sha256"]) == request["pages"], "W0 disjoint identity")
    call = dict(ordinal=2, tag="k0001", mode="H", binder=member["binder"], window=1,
                hooked=True, retain_hidden=True, pages=pages)
    fields = {k:ref[k] for k in historical.BASE_KEYS}
    return dict(fields, packet="WP-0029", phase="cedar-capture", split="development", process_id="cedar-r1",
                lease="cedar-r1", process_ordinal=1, output=str(OUTPUT), raster_root=str(raster),
                calls=[call], check_groups=[], requests=[warm["request"],request], warmup=warm,
                historical_w0_through_eos=WARM_TOKENS, ordered_rgb_key=key, deadline_seconds=180,
                sensor_tree=ref["sensor_tree"], runner_sha256=ref["runner_sha256"])


def source_pins():
    previous = read(OLD_RELEASE)
    require(previous["review_worktree_head"] == "9c02c9fae465dc1d1322a81c23eb3af45bbb0aff", "Worker revision")
    pins = dict(previous["source_files"])
    pins.update({p.relative_to(ROOT).as_posix(): h for p,h in PINS.items()})
    pins.update({p.relative_to(ROOT).as_posix():guard.sha(p) for p in HERE.glob("*.py")})
    for name, digest in pins.items():
        require(guard.sha(ROOT / name) == digest, f"Changed acquisition source {name}")
    return pins


def bind(destination, candidate):
    require(git("rev-parse","HEAD") == candidate and not git("status","--porcelain","--untracked-files=all"),
            "Clean frozen runtime checkout required")
    require(not OUTPUT.exists() and not LEASE.exists(), "Reconcile prior issuance")
    plan_path = destination / "cedar-r1-plan.json"
    release_path = destination / "cedar-r1-release.json"
    require(not plan_path.exists() and not release_path.exists(), "Existing release")
    stage = BASE / "coordination/preparation"
    stage.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=stage) as temp:
        env = {k:v.replace(str(Path(temp)),str(OUTPUT / "sensor")) for k,v in historical.environment(Path(temp)).items()}
    plan = dict(execution_fields(), candidate=candidate, environment=env)
    pins = source_pins()
    guard.dump(plan_path, plan)
    release = dict(packet="WP-0029", operator="eld-cedar-operator", name="cedar-r1", candidate=candidate,
                   worktree=str(ROOT), gpu_uuid=guard.GPU, free_floor_mib=12000, ceiling_mib=12500,
                   seconds=180, loads=1, excluded_w0=1, scored_calls=1, retries=0, output=str(OUTPUT),
                   plan=str(plan_path), plan_sha256=guard.sha(plan_path), source_files=pins,
                   sensor_revision="1843cdb7b6279b84b539d3ca1ba7bd0affa1f7dd",
                   worker_revision=read(OLD_RELEASE)["review_worktree_head"], prepared_utc=guard.utc())
    guard.dump(release_path, release)
    print(guard.sha(plan_path), guard.sha(release_path))


if __name__ == "__main__":
    bind(Path(sys.argv[1]).resolve(strict=True), sys.argv[2])
