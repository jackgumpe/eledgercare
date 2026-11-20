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
