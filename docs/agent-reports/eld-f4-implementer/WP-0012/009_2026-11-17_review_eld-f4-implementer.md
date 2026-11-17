# WP-0012 / 009: Independent acceptance of reviewer v6 ownership correction

- Report path: `docs/agent-reports/eld-f4-implementer/WP-0012/009_2026-11-17_review_eld-f4-implementer.md`
- Sequence reservation: coordinator authority `bdd717446bdfac536537187716f7e647b1e2a430`, `docs/kickoffs/WP-0012-eld-f4-implementer-reviewer-v6-review.md` and its INDEX reservation, read through Git.
- Category: review
- Author / agent ID: `eld-f4-implementer`
- Actual model / effort: native Codex `/root/product_author_continuation`; requested xhigh; actual backend and applied effort not exposed.
- Execution environment: Windows PowerShell/native Codex tools, standard-library Python; exact owned branch/worktree below.
- Published by: `eld-f4-implementer`, native continuation
- Timestamp: 2026-11-17T17:36:00Z
- Repository / branch: `https://github.com/jackgumpe/eledgercare.git` / `rehearsal/wp-0012-product`; worktree `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-f4-implementer`.
- Base revision: `bd21e07eb322ea64dee59ba5562ee6b03087d079`
- Deliverable revision: independent final check freeze `c34d4d89e5353a2baf436e81aa50fae5702d8098`; completed evidence `13de509b5681c279fc71f707023a9c3f15e06127`; inventory `b7245cc8b70fa2d94490b5092612a8600e6eb796`.
- Previous report: [Author /003](003_2026-11-17_verification_eld-f4-implementer.md), publication `bd21e07eb322ea64dee59ba5562ee6b03087d079`.
- Reviewed report: [Reviewer implementation /008](https://github.com/jackgumpe/eledgercare/blob/ae71a7362718f36e351e3fd442d9751d875146fe/docs/agent-reports/eld-f4-reviewer/WP-0012/008_2026-11-17_implementation_eld-f4-reviewer.md), exact publication `ae71a7362718f36e351e3fd442d9751d875146fe`.
- Status: accepted
- Next owner: `eld-coordinator`; any new reviewer /004 runtime requires its separate exact release.

## Summary

Accept the bounded reviewer-owned ownership correction at source `6fe4a537eb94fb75776f772e3c37fd5a90101fed`. Independent verification passed 51 focused controls, three original-v5 defect reproductions, and one actual read-only collect/evaluate observation. I did not author this reviewer helper. I authored the separate product helper previously; this review covers the reviewer-owned v6 change and does not re-review my own product implementation.

The first v6 candidate's passing CPU evidence and root's failing actual Windows app-alias observation remain preserved. The final source fixes that demonstrated image-binding defect. No unresolved finding remains within this correction. Acceptance grants no model/service invocation or lease.

## Objective and acceptance criteria

Independently verify exact root-accounted idle Ollama PID/creation/executable identity, successful header-only observation and absent GPU row; reject loaded, unknown, changed or reused identities. Verify the exact owned observer and issued query without a broad PowerShell/Python exemption. Failed or malformed observations must stop execution. Preserve original v5/refusal, root failure, source lineage and unrelated release/output/startup/cleanup behavior.

## Change inventory

All 43 source/input/evidence artifacts are enumerated by exact path, bytes, SHA-256 and Git metadata in [the inventory](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v6-independent-check/final-inventory.json). All 3,773 inherited Git rows are unchanged. The inventory itself and this later report are the only two metadata additions outside those 43 entries; no shared ledger, application, other-author source or prior report changed.

Here `P` means `docs/implementation/WP-0012/eld-f4-implementer/reviewer-v6-independent-check`.

| Added paths under P | Purpose |
| --- | --- |
| `.gitattributes`, `control-intent.json`, four `*-identities.json` manifests | Byte preservation, independently prepared controls and exact Git input identities. |
| `helpers/probe_v5_controls.py`, `helpers/check_v6.py`, `helpers/check_v6_forward.py` | Frozen independent original-defect, ownership, collector-fault and Windows alias controls. |
| `inputs/**` | Exact v5 and both v6 source copies, original refusal/root observations, root actual alias failure, interfaces and two source diffs. |
| `evidence/cpu-01/**`, `evidence/cpu-02/**`, `evidence/actual-01/**`, `evidence/author-evidence-audit.json` | Every independent outcome, commands/PIDs/exits, original streams, actual observation and author artifact audit. |
| `final-inventory.json` | Complete base-to-evidence inventory and preservation proof. |

External effects were read-only GPU/process/Ollama queries and their short-lived owned subprocesses. The actual PowerShell observer PID 37680 and Python PID 13784 completed with exit 0. No services, models, renderer, inference, browser workflow, database operation, dependency install or other-owner process termination occurred.

## Decisions and rationale

The final module requires an explicit idle record matching the same coordinator blob's actual process row, successful header-only Ollama output and successful GPU observation excluding that PID. Current identity and queried executable must match. Independent controls accept `2026-11-12T11:09:34.549904-05:00` and its equivalent UTC instant, while rejecting a changed instant, reused PID, changed executable, new PID, loaded model or GPU row.

Observer collection binds creation time and actual image from the retained Windows handle to CIM, preserves the issued app alias separately, and verifies the exact encoded query. Controls reject observer identity/query mismatches, unrelated PowerShell/Python workers, unknown model/GPU processes, and failed/malformed/stale observations. The retained-image query failure also reaps the owned fake child; no permissive fallback is introduced.

The [v5-to-v6 runner diff](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v6-independent-check/inputs/v5-to-v6-runner.diff) and AST comparison show only ownership collection/evaluation and `main` changed among functions. Manual inspection confirms `main` changes its description, repository-parent index and byte-binding list; the new output-protected prefix and module import support the deeper namespace. Release-contract, startup, output-validation and cleanup functions remain identical. The forward alias fix leaves the runner byte-identical.

## Verification

Commands below use P as defined above. Exact absolute argument vectors, process IDs, timestamps, original stdout/stderr and actual exits are retained beside each result. Candidate copies were checked against exact Git objects before execution; no combined root branch was merged.

| Executed check | Frozen source / actual result | Evidence |
| --- | --- | --- |
| `python -B P/helpers/check_v6.py --output P/evidence/cpu-01` | Check `d8a1d48018d3448fba083a68ba373c57cd6c6b5a`, candidate `651146fa704fe0df262057540587399277ff6a23`; 47/47 controls plus three v5 reproductions pass, exit 0, tool `79df66`, 17:27:39.600351–17:27:39.808742Z. | [Original controls](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v6-independent-check/evidence/cpu-01/controls.json) |
| `python -B P/helpers/check_v6_forward.py --output P/evidence/cpu-02` | Check `c34d4d89e5353a2baf436e81aa50fae5702d8098`, final candidate `6fe4a537eb94fb75776f772e3c37fd5a90101fed`; 41 evaluator + six collector + four alias controls pass, plus three v5 reproductions; exit 0, tool `9bf118`, 17:31:56.370426–17:31:56.857754Z. | [Final controls](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v6-independent-check/evidence/cpu-02/controls.json) |
| `python -B P/helpers/check_v6_forward.py --observe --output P/evidence/actual-01` | Same frozen helper bytes, executing HEAD `95d6c73c75b06b7740be2eb0c2ee8a5959c6c9c3`; final candidate; exit 0, tool `648fea`, 17:32:23.731239–17:32:24.410011Z. | [Actual observation](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v6-independent-check/evidence/actual-01/actual-observation.json), [original observer output](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v6-independent-check/evidence/actual-01/observer.stdout.log) |
| Git object/hash and inherited-tree comparison, tool `55accc` | Author inventory `62b4e2e357b4e4301b671dec4d35b1c890c09f6d`: 29 artifacts, 11 source bindings and 3,801 inherited rows independently verified; final helper bytes unchanged. | [Author evidence audit](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v6-independent-check/evidence/author-evidence-audit.json) |
| Own committed-byte/tree inventory, tool `36bafc` | 43 artifacts, 1,791,131 bytes, 3,773 inherited rows unchanged; additions confined to P. | [Inventory](../../../implementation/WP-0012/eld-f4-implementer/reviewer-v6-independent-check/final-inventory.json) |

The actual probe ran after the reviewer's probe completed. It observed the exact idle Ollama PID 3892 and UTC-normalized creation time, header-only `ollama ps`, no Ollama GPU row, and 24 desktop GPU rows. It matched the actual PowerShell image despite the differing issued app alias. The trace wrapper forwarded real subprocess calls and retained original streams; actual collection/evaluation used no simulated observations. Its baseline is an explicitly labelled CPU-only adaptation of root's original observation with root's authorized idle record, not a runtime release.

The reviewed /008 report accurately binds final source `6fe4a537...`, evidence `787891426846c1fde62fb82d6b32547fa009ed2b`, and inventory `62b4e2e...`. Publication `ae71a736...` adds only that report. Its own 48 passing controls and actual probe are supporting author evidence; the decisive independent results above were separately authored and executed.

## Risks, disagreements, and unfinished work

Original v5 rejects idle Ollama and its own observer; an injected failed process observation also reproduces its fail-open behavior. These are retained CPU reproductions against original source, not further live v5 attempts. First v6 passed the initial independent 47 controls, but root's actual probe failed on the Windows alias/image distinction at `5f8ffa59494accc63f49af53de34d83a1e438049`, tool `c4f9d9`, exit 1. That failure and its exact frozen check are retained under `inputs/root-alias-failure/`. The final four alias controls reproduce the old failure, accept the corrected image binding, and reject image mismatch/query failure. No failure was overwritten.

These are bounded process observations, not continuing hardware isolation or OCR correctness evidence. Desktop/WDDM sharing remains explicit. Unchanged product suites and actual reviewer workflow were not rerun. Original first-/004 refusal and root's separate lease closure remain historical facts; no original return receipt is invented. Any fresh /004 needs new observations, output paths and exact coordinator runtime authority.

## Handoff

Accept /008 only on exact source `6fe4a537eb94fb75776f772e3c37fd5a90101fed` and report publication `ae71a7362718f36e351e3fd442d9751d875146fe`. Root should audit this /009, integrate the metadata as needed, and alone decide the next reviewer /004 lease. No runtime authority follows automatically from this report.

Independent deliverable/inventory `b7245cc8b70fa2d94490b5092612a8600e6eb796` was pushed to the exact origin and remote branch SHA verified before this report. The report-only publication SHA and final clean-origin confirmation follow in the handoff; this immutable report does not claim its own SHA. Root alone updates shared routing.
