# WP-0018 / 003 reviewer evidence (first phase)

Reviewer: eld-rd-reviewer. Source freeze `e531eef74156f325b2747307adecc09ecd7890ee`, with the C4.2r correction at `ecbeb8b858f6086027ae767b421465e1c8608b3b`; see [PREREGISTRATION.md](../PREREGISTRATION.md). All runs read the reviewer copies at `wp0018-data/review/inputs` and wrote to the scratch directory `wp0018-data/review/out/`. No OCR, WinRT, GPU, rasterization or network was used. **No H/A `tables=[]` result has been produced.**

| Committed file | SHA-256 | Produced by |
|---|---|---|
| `phase1-e531eef/phase1.json` | `eadc6f713d2af1ee79e493e419aaa9add5edf64381cb9b811f3af8d9325d3915` | first decisive `phase1` at `e531eef`: 1158/1162 passed. Retained failure: the preregistered C4.2 checks for H and A, caused by the historical `comparison` block |
| `phase1-ecbeb8b/phase1.json` | `b4dcaf53fc163384cf73b401ab9dd4d70519b2939208cc6a427183869dca97cf` | `phase1` at `ecbeb8b`: **1166/1166 passed** |
| `witnesses-ecbeb8b/witnesses.json` | `57ef2a688be0cb84ea4ac14890808e7503ecd053daa2ee006c27aa87acb4cb9d` | `witnesses` at `ecbeb8b` (index, environment and baseline commands) |
| `witnesses-ecbeb8b/witness-W1.json` | `552b242e5b8c95444df9b34206831e4f770957a0ad66ce08745c8381fe3b0fd6` | H p2 t1 r2c1 |
| `witnesses-ecbeb8b/witness-W2.json` | `b1a1495bfddc00c22b5bcb89f3252b89dc8262ff6bf9d17bfd98f0ec0a2e4da9` | A p60 t1 r2c2 |
| `witnesses-ecbeb8b/witness-W3.json` | `26dbe446917b83095bcd5f3d76a2ea365333af88abf07bf34bbe90f92d75d686` | H p1 line 2 |
| `witnesses-ecbeb8b/witness-W4.json` | `c307cffec229baf5456731b1e060e306217324bf187f02aff52b77ed37c18c33` | H p2 line 2 |

The following stay in scratch only. The full per-cell scorer outputs embed unpublished H/A truth, which is kept out of Git as it was in WP-0015.

| Scratch file (`wp0018-data/review/out/…`) | SHA-256 |
|---|---|
| `phase1-*/baseline-H-run{1,2}.json`, `witnesses-ecbeb8b/baseline-H.json` | `0e59f3ca5d90f1d80839b91e90a4d0599a787538aa0688c33e08668b077a8c56` (all identical) |
| `phase1-*/baseline-A-run{1,2}.json`, `witnesses-ecbeb8b/baseline-A.json` | `0db04b1debea6843e29251abffa10273ddb4bdccf150f191b085aad41e40705d` (all identical) |
| `prefreeze-smoke-control/paired.json` (constructed control only, pre-freeze) | `f1eff52d46aeb64e8b67dcf2a755ad22ce413125783431e03bd4881eefa16bdf` |
| `prefreeze-smoke-control-2/paired.json` (constructed control only, pre-freeze) | `c9738d59a481ce121071f3f8f08d4ff1b297a2cbbf2b3c126d8ae29a8b8c42ab` |

Reproduce from the worktree:

```
python docs/reviews/WP-0018/review_checks.py phase1 --out <new dir>
python docs/reviews/WP-0018/review_checks.py witnesses --out <new dir>
```

# Second phase (released paired run, attribution and reconciliation)

| Committed file (`second-phase/`) | SHA-256 | Produced by |
|---|---|---|
| `phase1-pre-paired.json` | `c51e550787e2db90d0365114697d92172001614d5904fe0142a3de39c04d2051` | `phase1` re-run at `94eba5b` (source unchanged since `ecbeb8b`): 1166/1166 passed |
| `paired.json` | `640ea4f05fca0438642a21fe100b5a8dfd45f5333c36afd20232d478a5b7ae4f` | `paired --execute-held-paired` at `94eba5b`: 18/18 passed; all 320 per-cell rows |
| `attribution.json` | `609ad712a912d5c82eab945a856cbe03dbe587811ddef0c0e27374cfd6e734ee` | `review_attribution.py` at `d9c5e7f` (committed before any author object was opened); all 320 cells and 304 lines |
| `receipt.json` | `6ee310d82b9efaed93d6c45cc5bb89f12b3471ae88c449cc7020d848b0adc845` | truth-free receipt committed at `199662d` before author inspection: scratch file hashes, checks, tallies |
| `compare.json` | `5b9610db42a6758cfcbf70aabb6f415baf208b66e7b72c1933aefd319e1d797b` | `review_compare.py` at `bacdaaf`: 104/104 passed, 0 row disagreements; also the supplementary reproduction |

The following stay in scratch only (`wp0018-data/review/out/`). The hashes are bound in `second-phase/receipt.json`.

| Scratch file | SHA-256 |
|---|---|
| `paired-94eba5b/paired-H-before.json` | `0e59f3ca5d90f1d80839b91e90a4d0599a787538aa0688c33e08668b077a8c56` |
| `paired-94eba5b/paired-H-after.json` | `c8dd1951cab6495d2585e668c08557cee37cec48547d0bfddb13a5b69b38a062` |
| `paired-94eba5b/paired-A-before.json` | `0db04b1debea6843e29251abffa10273ddb4bdccf150f191b085aad41e40705d` |
| `paired-94eba5b/paired-A-after.json` | `6c945ebfb8d3e0b0c011ccf9b0f34c3219e71bfe35ad04a5a54a970400ef6409` |
| `paired-94eba5b/H-prediction-tables-empty.json` | `35ea28b4b60dd3b32014780a6a5ccf0e3219e74309e2111a455901b047f78b6c` |
| `paired-94eba5b/A-prediction-tables-empty.json` | `ad3f0dc4963a1a6e6ccb1632f91779ee34d16044b7a595ea3c0e6a5b6cae9596` |
| `compare-6fd3e5d/` | empty; the first compare run failed at serialization (PREREGISTRATION Addendum 3) |

## Executable reproduction

Run these from the worktree root with CPython 3.12 and no third-party packages. Each `--out` must be a new directory. `DATA` defaults to the sibling `wp0018-data/review`, which holds `inputs/` and `admission.json`; pass `--data` to use another admitted copy. Author objects are read from local Git.

```
python docs/reviews/WP-0018/review_checks.py phase1    --out <scratch>/phase1
python docs/reviews/WP-0018/review_checks.py witnesses --out <scratch>/witnesses
python docs/reviews/WP-0018/review_checks.py paired --execute-held-paired --out <scratch>/paired-94eba5b
python docs/reviews/WP-0018/review_attribution.py --paired-dir <scratch>/paired-94eba5b --out <scratch>/attribution-d9c5e7f
python docs/reviews/WP-0018/review_compare.py --scratch <scratch> --out <scratch>/compare --fresh
```

`review_compare.py` re-checks the paired and attribution outputs against `second-phase/receipt.json`. To use a new scratch root, keep the directory names `paired-94eba5b` and `attribution-d9c5e7f`.

Without `--fresh`, every scratch file must match the receipt byte for byte, which is how the recorded run at `bacdaaf` was checked. With `--fresh`, the frozen-scorer outputs and stripped predictions must still match byte for byte. `paired.json` and `attribution.json` must equal the committed `second-phase/` copies once the run-environment, timestamp and path fields are removed. The `environment` and `*_utc` fields record the actual run.

## Fresh end-to-end reproduction at `0e31c99`

| Committed file (`second-phase/`) | SHA-256 | Produced by |
|---|---|---|
| `reproduction-receipt.json` | `3f5f0ceb8a6d684de50d10ca3448b19f61f29b60275249176fc15aa48988c11e` | full pipeline rerun into `out/repro-0e31c99`. All five commands exited 0, and all 21 output hashes are recorded |
| `compare-fresh-0e31c99.json` | `e248433ab09504deb1a7cc98351a2fc5920e4b06a1f0942cf8e9648c2ce72645` | `review_compare.py --fresh` over that rerun: 104/104 passed, 0 disagreements |
