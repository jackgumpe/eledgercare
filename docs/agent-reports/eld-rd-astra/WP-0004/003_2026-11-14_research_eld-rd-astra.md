# WP-0004 / 003: Single Astra exchange on independent source proposals

- Report path: `docs/agent-reports/eld-rd-astra/WP-0004/003_2026-11-14_research_eld-rd-astra.md`
- Sequence reservation: [INDEX at 4ecc3ffe1d2842decf19ecdcfec0f5424fb4ac8b](https://github.com/jackgumpe/eledgercare/blob/4ecc3ffe1d2842decf19ecdcfec0f5424fb4ac8b/INDEX.md), WP-0004 / 003; [kickoff at bce84931fef5cf2a8fa3652095dbea2973a19aef](https://github.com/jackgumpe/eledgercare/blob/bce84931fef5cf2a8fa3652095dbea2973a19aef/docs/kickoffs/WP-0004-eld-rd-astra-exchange.md).
- Category: research
- Author / agent ID: eld-rd-astra
- Actual model / effort: coordinator-dispatched gpt-6-astra / high; backend checkpoint unknown.
- Execution environment: resumed Codex task `/root/rd_astra`, Windows PowerShell 7.7.0, Git 2.55.0.windows.1; backend session UUID not exposed.
- Published by: author on owned branch; publication verification supplied in subsequent handoff.
- Timestamp: 2026-11-14T17:31:01Z
- Repository / branch: private `https://github.com/jackgumpe/eledgercare` / `research/wp-0004-astra`
- Owned worktree: `C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-rd-astra`
- Base revision: `189d4cb444c5afde059e6e1d2bee37c8294509d0`
- Deliverable revision: `e0b0228428cc77409f41a55ac11fb71fb9323ba4`
- Previous report: [WP-0004 / 001](https://github.com/jackgumpe/eledgercare/blob/189d4cb444c5afde059e6e1d2bee37c8294509d0/docs/agent-reports/eld-rd-astra/WP-0004/001_2026-11-14_research_eld-rd-astra.md); initial deliverable `1eb6f4af643edc7ccffcd5732a4659da44e7a077`.
- Related reports: [Carbon WP-0004 / 002](https://github.com/jackgumpe/eledgercare/blob/fef02d64aca2594e146930e4a0cb3ec18e355ed5/docs/agent-reports/eld-rd-carbon/WP-0004/002_2026-11-14_research_eld-rd-carbon.md); peer deliverable `39f475c1ce5b51c5b03b024fb39a74632e1a5eba`, report publication `fef02d64aca2594e146930e4a0cb3ec18e355ed5`.
- Status: ready-for-review; exchange proposal, not independent acceptance or corpus admission.
- Next owner: eld-rd-carbon for one reconciliation and bounded corpus/backlog under /004; eventual uninvolved eld-rd-reviewer / Opus under /005.

## Summary

Completed one structured exchange after both initial reports were published. Read all four Carbon deliverables and /002 at their exact pins through `git show`, alongside the unchanged Astra initial proposal. Initial independence remains preserved; peer conclusions were first read under this exchange release.

Propose tiling first, conditional deskew second, conservative text-layer routing third; defer page-window work and withdraw the earlier 12-page corpus requirement. Adopt Carbon's eight layouts and 4 dev / 4 held-out family assignments, with explicit visual/arithmetic checks and a bounded variant plan. Public PDFs remain unadmitted. These are proposed dispositions for Carbon's one reconciliation, not author acceptance of the joint result.

## Objective and acceptance criteria

Compare source/cache/runtime/platform/license/resource evidence, treatments and thresholds, corpus arithmetic/splits, and public admission. Supply at most three ranked experiments with disagreements and deferred work clear. Preserve all initial publications; modify only new `research/astra/exchange/**` and the reserved report. No installations, services, fixtures, model downloads, GPU work or agents were authorized or performed.

## Change inventory

| Action | Exact path or external resource | Purpose / relevant sections |
| --- | --- | --- |
| Added | `research/astra/exchange/decision-map.md` | Pinned comparison, evidence qualifications, proposed three-item ranking, eight-family corpus decision and /004 handoff |
| Added | `research/astra/exchange/source-checks.json` | Five version-specific PyPI metadata summaries and 13-object old/new HF tree comparison with exact URLs/times |

Post-deliverable metadata: this exact /003 report only. No initial proposal/report, peer file, INDEX/CURRENT, evaluation fixture, product or reviewer artifact was changed. External reads were limited to versioned PyPI metadata and historical HF tree metadata. Publication targets only the owned branch on existing private origin; no other external state or messages changed.

## Decisions and rationale

- Both native cache growth and dense prefill fallback are source-supported; actual kernel use/compatibility/performance remain Q0 qualification work. Matching model/code metadata across kit and refreshed pins does not imply weights were downloaded or validated locally.
- Reinspection confirms the conditional source path from saved-reference rendering to `eval`; propose explicit save_results=False in later qualification/experiments. No unsafe content executed and no production fix made.
- Version-specific wheel metadata supports availability/dependency observations, not complete OS or CUDA qualification. Resource ranges and memory thresholds remain predictions/policy, not observed headroom. Component license metadata is not a complete deployment/redistribution decision.
- A renderer substitution must be frozen as part of the local baseline or separately named as a treatment. No free substitution inside paired comparisons.
- The image-area threshold in Carbon's text-layer gate can miss small meaningful raster regions. Require abstention and counterexample controls, and make CPU feasibility precede any claimed paired OCR improvement.
- Choose the short eight-family corpus now; no customer page-length distribution was established. Q0 and optional experiment success remain separate from F1 durable intake.

## Verification

| Check / exact command or operation | Revision / environment | Actual result / evidence |
| --- | --- | --- |
| `git status --short --branch`; `git rev-parse HEAD` | Start, owned worktree | Clean owned branch at exact base `189d4cb444c5afde059e6e1d2bee37c8294509d0` |
| `git show 4ecc3ffe1d2842decf19ecdcfec0f5424fb4ac8b:INDEX.md`; `git show bce84931fef5cf2a8fa3652095dbea2973a19aef:docs/kickoffs/WP-0004-eld-rd-astra-exchange.md` | Read-only authority | Exact /003 reservation/kickoff read |
| `git show 39f475c1ce5b51c5b03b024fb39a74632e1a5eba:research/carbon/<file>` for README, 01-sources-and-qualification.md, 02-hypotheses.md, 03-corpus-and-candidates.md; peer report via `git show fef02d64aca2594e146930e4a0cb3ec18e355ed5:<report-path>` | Pinned peer artifacts | All read; long tool-output truncation recovered with narrower reads |
| `Get-Content` / `rg -n` on retained model snapshots for save_results, eval, rendering call chain, dense fallback and license header | Own initial deliverable snapshots | Conditional eval path and Apache header confirmed; fallback catches Exception; source inspected, never imported |
| `Invoke-RestMethod -Uri https://pypi.org/pypi/<package>/<version>/json` for torch 2.13.0, sglang 0.5.23, triton 3.9.0, PyMuPDF 1.27.2.2, pypdfium2 5.15.2 | Read-only, retrieval timestamps in source-checks.json | Five filtered metadata records retained; no wheel/package installation or download |
| `Invoke-RestMethod -Uri 'https://huggingface.co/api/models/baidu/Unlimited-OCR-2/tree/38d328853c00086837c00308e1cd35dc77bbb96c?recursive=true'`; compare `.py`, config and safetensors OIDs with retained refreshed tree | Read-only metadata | 13/13 objects match; weight LFS hashes match; no weights downloaded |
| `& ./research/astra/verify-sources.ps1` | Before exchange commit, unchanged initial snapshots | PASS: 16 snapshot size/hash checks, 14 upstream blobs, two public metadata records and weight-byte sum. No upstream execution |
| `ConvertFrom-Json` source-checks; assert 13 tree objects, zero unequal objects, five package records | Rerun after frozen `e0b0228428cc77409f41a55ac11fb71fb9323ba4` | PASS; exact predicate recipe below |
| `git diff --check 189d4cb444c5afde059e6e1d2bee37c8294509d0 HEAD` | Frozen exchange deliverable | Exit 0 |
| `git diff --name-status 189d4cb444c5afde059e6e1d2bee37c8294509d0 HEAD` | Frozen exchange deliverable | Exactly two additions under research/astra/exchange; initial files unchanged |
| `git status --short --branch` | After frozen checks | Clean owned branch, ahead one deliverable commit before report |

Metadata assertion recipe (PowerShell, repository root):

```powershell
$r = Get-Content research/astra/exchange/source-checks.json -Raw | ConvertFrom-Json
if (@($r.tree_comparison.objects).Count -ne 13 -or @($r.tree_comparison.objects | Where-Object { -not $_.equal }).Count -ne 0) { throw 'Tree comparison mismatch' }
if (@($r.package_metadata).Count -ne 5) { throw 'Expected five package metadata records' }
```

No runtime, GPU, arithmetic-generator, PDF rendering/visible-page, independent public-candidate, performance or product tests were run; none belongs to this source-only exchange. Carbon's deeper public-PDF findings remain attributed peer evidence rather than replayed Astra observations. Metadata endpoints were read successfully; a first console table of ordered dictionaries rendered blank rows, recovered by parsing the retained JSON into objects (the 13 comparisons were valid). No hidden failed runtime was relabeled successful.

## Review map

[Exact exchange diff](https://github.com/jackgumpe/eledgercare/compare/189d4cb444c5afde059e6e1d2bee37c8294509d0...e0b0228428cc77409f41a55ac11fb71fb9323ba4). Read the decision-map rows and ranked rules against the pinned initial artifacts and source functions, then inspect metadata URLs/timestamps and the comparison objects. Corpus/admission requirements remain proposals requiring actual files and independent visual/arithmetic verification.

## Risks, disagreements, and unfinished work

Carbon has not yet accepted the revised ranking, thresholds, conservative route policy or variant bound. Concrete unresolved questions are native runtime viability, measured resource envelope, safe/use-appropriate renderer dependencies, text-layer completeness, and independently verified fixture truth. Propose 8 originals, 8 image-only and 8 signed-skew variants, plus at most two linked hybrid controls if supported by the authorized /004 tooling; missing variants block corresponding experiments rather than the eight-original milestone. Public rights/notices and ground truth remain unaccepted. A fixed partition is not blind validation if its answers were already inspected by the tuner.

## Handoff

Send Carbon the exact exchange deliverable and this report publication after coordinator binding of /004. Carbon gets one reconciliation: accept/reject the decision rows with reasons and preserve substantive remaining alternatives for the coordinator. No additional debate loop or agent is released. Ultimate admission/acceptance belongs to uninvolved Opus /005, not either joint author.

Publication at report creation: deliverable committed locally; report commit/push and remote object verification pending. Author will push only research/wp-0004-astra without force and provide both full publication SHAs in the handoff. This report intentionally does not contain its own commit SHA.
