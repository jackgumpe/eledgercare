# WP-0012 / 008: Exact idle-model and observer ownership correction

- Report path: `docs/agent-reports/eld-f4-reviewer/WP-0012/008_2026-11-17_implementation_eld-f4-reviewer.md`
- Sequence reservation: `INDEX.md` at correction authority `8b6224a44ddbf4658abc5ae1fe3ac0cd2bb96938`; kickoff `docs/kickoffs/WP-0012-eld-f4-reviewer-correction-008.md` at `5ea833f`.
- Category: implementation
- Author / agent ID: `eld-f4-reviewer`
- Actual model / effort: native Codex `/root/product_reviewer_continuation`, requested xhigh; actual backend/applied effort unexposed.
- Execution environment: Windows PowerShell/native Codex tools; standard-library Python CPU controls and read-only Windows process, GPU and Ollama observations.
- Published by: `eld-f4-reviewer`, native continuation
- Timestamp: 2026-11-17T17:32:22Z
- Repository / branch: `https://github.com/jackgumpe/eledgercare.git` / `review/wp-0012-product-rehearsal`
- Base revision: `36580948f4efe28e35f08762e6bcc1cc4368bb55`
- Deliverable revision: final source and focused alias controls `6fe4a537eb94fb75776f772e3c37fd5a90101fed`; evidence and frozen inventory helper `787891426846c1fde62fb82d6b32547fa009ed2b`; final inventory/resource metadata `62b4e2e357b4e4301b671dec4d35b1c890c09f6d`.
- Previous report: [Independent /007](007_2026-11-17_review_eld-f4-reviewer.md), unchanged acceptance of author /006 preparation.
- Related reports: [Author /003](../../eld-f4-implementer/WP-0012/003_2026-11-17_verification_eld-f4-implementer.md). Independent /009 is separately assigned; actual workflow /004 remains unfinished.
- Status: ready-for-review
- Next owner: `eld-f4-implementer` as independent /009 reviewer of this reviewer-authored helper, then `eld-coordinator` for disposition and any new exact runtime lease.

## Summary

The reviewer ownership guard now accepts only an explicitly root-accounted idle Ollama identity and excludes only its exact owned process observer. PID, creation instant, executable, exact observer query, successful fresh idle observation and absent GPU workload remain required. Failed or malformed observations refuse execution. Own verification passed 48 focused CPU controls and an actual read-only host observation. This is implementation verification, not independent acceptance or live OCR evidence.

The first actual /004 invocation refused before Q0, services or model execution. V5 classified existing idle Ollama PID 3892 and its own PowerShell observer PID 37576 as competing workloads. Original validation exit 0, live helper exit 2, wrapper exit 2 and outer tool exit 1 are preserved. It produced no summary or return receipt and consumed zero model attempts. Root separately verified resource absence and explicitly closed that lease; this report does not invent an original return receipt.

## Objective and acceptance criteria

Repair only the two demonstrated ownership-classification defects, preserving prior v5, /007, accepted application/author source, original failure and attribution. Exercise idle/observer positives and loaded/unknown model, PID reuse, observer mismatch and malformed/failed-observation refusals. Bind and execute the source before reporting it. Independent /009 and root acceptance must precede any new model/service invocation.

## Change inventory

All additions are under `docs/reviews/WP-0012/eld-f4-reviewer/live-004/preflight-correction/`, plus this reserved report. [The exact inventory](../../../reviews/WP-0012/eld-f4-reviewer/live-004/preflight-correction/final-inventory.json) enumerates every artifact, byte length and SHA256, verifies 15 original/root copies and 11 source/evidence bindings, and proves all 3,801 inherited Git paths unchanged. Inventory/report metadata committed afterward is listed separately there. Shared routing and root's combined branch were not merged or edited.

| Added paths within the owned prefix | Purpose |
| --- | --- |
| `helpers/run_wp0012_reviewer_rehearsal_v6.py`, `helpers/ownership_v6.py` | New runtime wrapper and bounded process observer/evaluator; preserve v5. |
| `helpers/check_ownership_v6_cpu.py`, `helpers/check_ownership_v6_cpu_v2.py`, `helpers/build_008_inventory.py` | Frozen focused controls, separate alias controls, exact inventory/resource audit. |
| `first-refusal/**`, `root-alias-failure/**` | Byte-identical original /004 refusal and root's first-v6 Windows alias failure, with copy provenance. |
| `evidence/**`, `INTERFACE.md`, `.gitattributes` | Actual executions, explicit tool receipts, process/resource reconciliation and coordinator schema; preserve evidence bytes. |

Final runtime-wrapper SHA256: `7fafe34da2f46ce9508a54748c275d272147655285c209c2fcf68ed34240f5df`. Final ownership-module SHA256: `ff01e70c09c1e7b69cbed3c660f9f6cb777d381a920a51af7e1204d24eee6d9f`. Both are bound by runtime source validation alongside the unchanged browser helper.

## Decisions and rationale

The hashed coordinator ownership blob must explicitly list `accounted_idle_ollama` with matching PID, creation instant, name and executable from that same blob's actual process rows. Its successful `ollama ps` must contain only a recognized header, and its successful GPU process observation must omit that PID. The current observation must independently satisfy those conditions, query the same Ollama executable and remain fresh. UTC normalization accepts equivalent offset serialization, while PID reuse fails. GPU model processes remain forbidden. Known desktop sharing is disclosed without claiming hardware exclusivity.

The observer uses its retained Windows process handle to obtain creation time and executed image, then requires exact agreement with CIM and its issued encoded query. Other PowerShell/Python workers retain the usual refusal checks. The wrapper otherwise preserves v5 release, startup, output and cleanup behavior; its deeper path requires the adjusted repository-root index and new protected output prefix.

The first v6 source `651146fa704fe0df262057540587399277ff6a23` passed 46 synthetic controls, but root's actual observation failed because the issued Windows app alias differed from the installed executable path. [That failure](../../../reviews/WP-0012/eld-f4-reviewer/live-004/preflight-correction/root-alias-failure/actual-alias-finding.json) remains bound to root publication `5f8ffa59494accc63f49af53de34d83a1e438049`, frozen root check `69ccb4897f32ece3e5030aa57e28c3d29471b826`, tool `c4f9d9`, exit 1. The forward correction uses `QueryFullProcessImageNameW` on the retained handle and records the issued alias separately. It adds no basename/path bypass. Original controls and first-candidate evidence remain unchanged.

## Verification

Commands use `P = docs/reviews/WP-0012/eld-f4-reviewer/live-004/preflight-correction`.

| Exact command | Frozen/executing revision | Actual result |
| --- | --- | --- |
| `python -B P/helpers/check_ownership_v6_cpu.py --mode cpu --output-dir P/evidence/cpu-01` | Source `651146fa704fe0df262057540587399277ff6a23`; harness/execution `6c5bcd61efca70b5217a47a46a5d36baa3690bab` | 46/46 passed, 17:27:40.669466–17:27:40.742544Z; retained [result](../../../reviews/WP-0012/eld-f4-reviewer/live-004/preflight-correction/evidence/cpu-01/result.json). Synthetic v5 replay reproduces both original refusal causes; it is not another live v5 invocation. |
| `python -B P/helpers/check_ownership_v6_cpu_v2.py --mode cpu --source-commit 6fe4a537eb94fb75776f772e3c37fd5a90101fed --output-dir P/evidence/cpu-02` | Exact final source `6fe4a537eb94fb75776f772e3c37fd5a90101fed` | Exit 0, 48/48 passed, 17:30:01.150925–17:30:01.213336Z, tool `318ec0`; [result](../../../reviews/WP-0012/eld-f4-reviewer/live-004/preflight-correction/evidence/cpu-02/result.json). Adds app-alias acceptance and retained-image/CIM mismatch refusal. |
| `python -B P/helpers/check_ownership_v6_cpu_v2.py --mode read-only --source-commit 6fe4a537eb94fb75776f772e3c37fd5a90101fed --output-dir P/evidence/read-only-01` | Exact final source `6fe4a537eb94fb75776f772e3c37fd5a90101fed` | Exit 0, 17:30:10.113463–17:30:10.895454Z, tool `5d3b37`; [actual observation](../../../reviews/WP-0012/eld-f4-reviewer/live-004/preflight-correction/evidence/read-only-01/result.json). Idle Ollama PID 3892, exact observer PID 26276 and 24 desktop GPU rows; no competing model workload. |
| `python -B P/helpers/build_008_inventory.py` | Frozen/executing `787891426846c1fde62fb82d6b32547fa009ed2b` | Exit 0, tool `a8e3bd`: 29 artifacts, 15 copies, 11 source bindings, 3,801 preserved paths. Resource audit at 17:31:52.242063Z confirms both actual probe processes absent, reviewer ports empty, PostgreSQL status 3 and reviewer runs empty. |

The actual probe's baseline is an explicitly labelled CPU-only fixture derived from root's original ownership blob plus its authorized exact idle identity. It is not a runtime release. Unrelated command arguments are omitted from published observations; command hashes, classification tokens and exact observer command remain. The probe verifies that this public projection produces the same classification as the in-memory observation.

No services, models, renderers, inference, browser workflow or database writes occurred in this correction. Unchanged application suites were not rerun. Original first-refusal files, empty outputs and missing receipts remain preserved.

## Review map, risks and handoff

Inspect [the complete diff](https://github.com/jackgumpe/eledgercare/compare/36580948f4efe28e35f08762e6bcc1cc4368bb55...6fe4a537eb94fb75776f772e3c37fd5a90101fed), [interface](../../../reviews/WP-0012/eld-f4-reviewer/live-004/preflight-correction/INTERFACE.md), actual source and evidence. Root and independent /009 must disposition this reviewer-authored implementation. No self-acceptance is claimed. Original Carbon-derived v3/v4/v5 attribution and prior publications remain intact.

Actual /004 remains unfinished. Root must bind the accepted forward helper, clean executing HEAD, fresh host observations, exact sole lease and new external output paths before any service/model invocation. The prior lease is closed and its outputs cannot be reused. This report grants no runtime authority.

Branch `review/wp-0012-product-rehearsal`; source `6fe4a537eb94fb75776f772e3c37fd5a90101fed`, evidence `787891426846c1fde62fb82d6b32547fa009ed2b`, inventory metadata `62b4e2e357b4e4301b671dec4d35b1c890c09f6d`. Exact publication SHA and origin receipt follow separately after the report-only commit.
