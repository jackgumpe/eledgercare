# WP-0041 / 002 — Layer 11 source feasibility and mathematical verification

| Report metadata | Value |
| --- | --- |
| Path and category | `docs/agent-reports/eld-owner-probe/WP-0041/002_2026-11-26_research_eld-owner-probe.md`, research |
| Reservation | [WP-0041 /002 in INDEX](https://github.com/jackgumpe/eledgercare/blob/5f73e671ccd2fc12eb0f2d85b2effae713dc867c/INDEX.md#wp-0041-layer-11-one-field-feasibility-and-handoff-rule-review) |
| Author and publisher | eld-owner-probe, native Codex session `01a21654-e733-7d43-a35a-4ef7951c75d3`, team path `/root/layer_author` |
| Model and effort disclosure | Dispatched as a full-history native child inheriting the coordinator's gpt-6.2-astra/xhigh configuration. The child environment exposes the session ID; an independent per-call model/effort meter was unavailable. |
| Time and environment | 2026-11-26T05:39:24Z, Windows PowerShell, local CPython 3.12.10, SHA-256 `4d6f5f81a4bca11191c4c7c6b43632694d0a4ce74e068619d8fdc161d469859a` |
| Repository, branch and worktree | jackgumpe/eledgercare, `research/wp-0041-layer11`, `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w041-author` |
| Product base / checkout reservation | `a0bf6122d082675d483ffd9aeb7f4dbedbfb174c` / `5f73e671ccd2fc12eb0f2d85b2effae713dc867c` |
| Frozen deliverable candidate | `71ad1a2cb2324c2c89485085dedb4e2c3083aac6` |
| Executed evidence commit | `da275f4f036c2f6fb1af28a231157ada70fc1430` |
| Predecessor | [WP-0040 /004, coordinator disposition](https://github.com/jackgumpe/eledgercare/blob/a0bf6122d082675d483ffd9aeb7f4dbedbfb174c/docs/agent-reports/eld-coordinator/WP-0040/004_2026-11-25_verification_eld-coordinator.md) |
| Status and next owner | Ready for review by eld-rd-reviewer /003. eld-coordinator owns final disposition. This is the author's first report in WP-0041. |

## Summary and objective

The pinned stock reader ends its language decoder with block 11, final RMSNorm and an untied, bias-free language head. The three mathematical propositions hold with the stated assumptions. A private one-token evaluation advances the layer once; a processed-score rival needs differential gain exceeding its original deficit for a strict overtake; and the loop saves mean wall time only above the derived trigger threshold when crop cost exceeds loop cost. These checks do not measure a device, read accuracy or timing. Full hypotheses, proofs, worked examples, edge conditions and an observation contract are in the frozen analysis. [Mathematical analysis and source map](https://github.com/jackgumpe/eledgercare/blob/71ad1a2cb2324c2c89485085dedb4e2c3083aac6/docs/research/WP-0041/analysis.md)

The assignment required a source and provenance examination plus an independent author derivation from the nine-page amendment. I read all nine pages of the 215,820-byte supplied PDF (SHA-256 `3f4451dd3a1bd2dc37d50c5ddb720dfd37005f62c1da68a6b2958aa86db14264`). I did not inspect the current reviewer's work or select a competing field. Development field tracing is reserved to /001. Page 6 proposes a local governance decision owned by eld-coordinator; external Workspace Ledger was outside the assignment.

## Change inventory

All five research paths are under `docs/research/WP-0041/`. [Frozen candidate diff](https://github.com/jackgumpe/eledgercare/compare/5f73e671ccd2fc12eb0f2d85b2effae713dc867c...71ad1a2cb2324c2c89485085dedb4e2c3083aac6)

| Phase | Added path | Purpose |
| --- | --- | --- |
| Candidate | `analysis.md` | Derivations, decision boundaries, model/processor state map and prior-probe limits |
| Candidate | `math_check.py` | Stdlib exact arithmetic, bounded enumerations, mutable-state and signed-zero witnesses, archived C9b reconstruction |
| Candidate | `source_check.py` | Static source locations/signatures, SHA-256, Git blob/LFS and package-version checks, optional public revision comparison |
| Evidence | `math.json` | Constructed arithmetic and archive-reconstruction results |
| Evidence | `source.json` | Local model, tokenizer, historical imported files, distribution versions, callable signatures and upstream comparison |
| Publication metadata | This canonical /002 report only | Separate publication after committing candidate and evidence |

External effects were read-only access to the named PDF, model files, earlier Q0 author module copies, installed metadata and public HF revision metadata. Both safetensors files were streamed into SHA-256 as raw bytes. The packet's author scratch directory was created. The assigned Git branch was pushed normally. Model/runtime, packages, product services and hardware were unchanged.

## Verification

| Executed check | Observed result |
| --- | --- |
| `git status --short --branch`, `git rev-parse HEAD`, `git remote -v`, `git sparse-checkout list` | Clean owned checkout at reservation, public eLedgerCare origin. Prior records were read by explicit Git object path. |
| CPython/pypdf PdfReader, extraction of pages 1 through 9; stdlib SHA-256 and byte length | 9 pages and exact supplied file identity. |
| `python -B docs/research/WP-0041/source_check.py --online --out docs/research/WP-0041/source.json` on frozen candidate | Exit 0. All 18 runtime objects verified; eight historical imported Python module copies matched source and Q0's original author receipt. All 32 installed locked distributions had their prescribed versions. The permitted extra package was pip. The installed versions included torch 2.13.0+cu130, transformers 4.52.1, tokenizers 0.21.4 and torchvision 0.28.0+cu130. Checked 23 callable signatures and location spans. |
| HF commit page, patch, recursive trees and `git ls-remote https://huggingface.co/baidu/Unlimited-OCR-2.git refs/heads/main` | Commit `cb16b920ec2249c4b280f3aa67942e00b5099122` had sole parent `0480966938291445591f69f08a13b041c073a96a`; it was the observed main. Both trees had 26 files and README.md was the sole changed file. |
| `python -B docs/research/WP-0041/math_check.py --out docs/research/WP-0041/math.json` on frozen candidate | Exit 0. 22,500 strict-overtake/equality comparisons, 480 protected-winner cases, 729 geometric checks, 512 Hamming triples and 1,375 cost cases. Four-position alignment, nine transition contributions, boundary lengths and C9b amounts matched. |
| `git show a0bf6122d082675d483ffd9aeb7f4dbedbfb174c:docs/research/WP-0017/engine/span_probe.py` | Existing cache-copy and readout helpers inspected at source. Last branch reuses the original reconstructed state; final normalized hidden and teacher-forced identifier-score summaries do not supply a full native layer-11 trace. |
| `git diff --cached --check` at candidate/evidence staging, packet `coordination/push.ps1 -ExpectedHead 71ad1a2cb2324c2c89485085dedb4e2c3083aac6` and remote head comparison | Clean staged diff. Remote owned branch was the exact frozen candidate after its first normal push. Final report publication SHA will be sent in the coordinator receipt. |

The three tokenizer file SHA-256 values are `c55c165e32c5a67830362a53e1f548c8930dcc8469efa30ff3252a982799c589` (tokenizer.json), `ceba7d221f265cca4c98b5e0a1d48c10107270b7b29c12396610d6d0fd64b126` (tokenizer_config.json) and `9e89493d7938e7710c524dbaff613c3648f0a018262417af78505128004e5cb4` (special_tokens_map.json). The full evidence records the SHA-256 and upstream Git object or LFS digest for every runtime file. [Source evidence](https://github.com/jackgumpe/eledgercare/blob/da275f4f036c2f6fb1af28a231157ada70fc1430/docs/research/WP-0041/source.json) · [HF revision](https://huggingface.co/baidu/Unlimited-OCR-2/commit/cb16b920ec2249c4b280f3aa67942e00b5099122)

The decimal worked example gives a +0.45 relative gain and 0.05 revised lead. C9b gives (0,1,1) against its three candidate amounts. Illustrative R=3,G=1,N=10 gives +20 percentage points, with conditional one-sided binomial tail 5/16 when the independent-family null applies. At zero paired fields the accuracy change is undefined. The cost example gives a tie at p=25%, a 1.2 ms/page increase at 10% and a 2 ms/page saving at 50%. No physical rows contributed to these constructed checks. [Arithmetic evidence](https://github.com/jackgumpe/eledgercare/blob/da275f4f036c2f6fb1af28a231157ada70fc1430/docs/research/WP-0041/math.json)

## Limitations and handoff

Initial inspection encountered a missing worktree-relative push-helper path (the helper is in the assigned packet scratch's coordination directory), a sparse checkout omitting older packet directories, and a console `UnicodeEncodeError: 'charmap' codec can't encode character '\uff5c'` while displaying preliminary tokenizer metadata. Using the packet helper, immutable Git-object reads and escaped JSON gave the complete audits above. Both decisive commands succeeded on the first frozen candidate.

Greedy parity requires the actual inputs, per-layer K/V, router/page and rotary state, layer-10 exit h0, positions, full raw and processed scores, masks/ties, emitted IDs, post-state and unchanged native branch through the complete closing token. The raw head geometry is an exact-arithmetic claim. A finite-precision deployment needs observed logits or explicit rounding allowances. Source parity of historical imports cannot demonstrate current per-position device parity. Stock/P1/P2/L2, fresh observations, crop, timing, training and physical inference were not executed. The original WP-0040 physical denominator remains zero; development source material cannot substitute for a future independently sampled paired physical trial.

The next owner can inspect the [frozen checks](https://github.com/jackgumpe/eledgercare/tree/71ad1a2cb2324c2c89485085dedb4e2c3083aac6/docs/research/WP-0041) and [executed evidence](https://github.com/jackgumpe/eledgercare/tree/da275f4f036c2f6fb1af28a231157ada70fc1430/docs/research/WP-0041), independently verify the claims and reconcile /001's single-field binding with the required custody and trace. eld-coordinator alone decides any subsequent finite resource release and records the local policy disposition.
