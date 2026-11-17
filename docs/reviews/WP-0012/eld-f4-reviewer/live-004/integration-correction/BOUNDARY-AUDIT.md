# Reviewer v7 integration boundary audit

Root authority `bc5b345d812fdd3bdcf6eb7ae6b5a43b895d8113`; source base `ae71a7362718f36e351e3fd442d9751d875146fe`. New /010 implementation only; separate /011 review required. V6, /008, /009 and both failed runtime namespaces remain unchanged. No model retry or live release.

Actual native-02 validated successfully, passed ownership and wrote the real Q0 receipt, then failed on a disk field that Q0 does not return. V7 measures the owned runtime tree's actual file sizes and actual volume free space separately; linked, missing, inaccessible, over-cap and below-floor observations fail closed. The Q0 receipt retains its actual schema, with disk evidence in a distinct `owned_demo_storage` member. Q0 model/dependency guard results are explicitly checked before services and after cleanup. No missing disk value is defaulted or fabricated.

Every `prep_mod` invocation and consumed return value in the complete main:

| Boundary | Actual signature/schema | Consumer and disposition |
| --- | --- | --- |
| Pre-start Q0 | `verify_q0_readonly_pure_stdlib(repo_root)` returns model/notices/dependency metadata, `verified_model_files`, no disk data | Original v6's two disk keys were invalid. V7 calls the same actual verifier, validates its returned conditions and independently measures storage. |
| Pre-start empty DB | `compute_canonical_8table_snapshot(psql_exe, settings, database, cwd)` returns `counts`, `canonical_8table_sha256`, `fencing_seq` | All four positional arguments match; the eight count values are actual table-list lengths. Main requires every count zero and no runtime runs. Unchanged. |
| Final DB accounting | Same function/signature | Main retains actual `counts` and includes them in the return receipt. No synthetic attempt/result count is supplied. Unchanged. |
| Post-cleanup Q0 | Same verifier as pre-start | Main validates actual receipt conditions and compares complete `verified_model_files` lists, including sizes, timestamps and digests. V7 adds explicit condition checks; the real verifier is never replaced in integration. |

Other complete-main boundaries inspected: exact Git release/source/output guards; local settings keys and PostgreSQL executables/data path; `start-cluster.ps1`/`stop-cluster.ps1` arguments and exit checks; `inspect_process` PID/creation fields and owned stop receipt; keyword-only atomic API/UI startup; runtime environment keys; Node/browser CLI pairs; phase-one `woDocument.documentId`/`mpDocument.documentId` consumed by phase two; persisted snapshot; log scrub; `pg_ctl status`; full reviewer-port dictionary; ownership pre/post; Q0 post-check; runtime-run enumeration and truthful return receipt.

Browser flags match the actual unchanged driver: `--mode`, `--ui-port`, `--api-port`, `--output`, `--screenshot-dir`, followed in phase two by `--wo-document-id` and `--mp-document-id`. Actual live phase one writes both document objects with `documentId`; actual phase two asserts `workerEnabled === false`, one attempt per document and no new extraction POST. The CPU adapter must never execute either live mode. It runs the existing read-only `cpu-preflight --target empty-ready-db` mode twice, before/after real restart, preserving zero rows/non-GET requests and browser storage. Explicit synthetic IDs are only argument-plumbing fixtures between these CPU phases; they are not database rows or model evidence.

The isolated integration harness will force every actual API process to `LocalOcr__Enabled=false` and independently reject any enabled API launch at the process boundary. It will reject live browser execution, upload/queue/model commands, use actual Q0 verification/disk/ports/PostgreSQL subset/local dependency checks and actual owned API/UI/PG lifecycle, preserve original logs and process identities, and compare real database state before/after. One complete CPU lifecycle exercises restart; a separate intentional boundary failure exercises final cleanup. Prior databases and empty demo state remain unchanged. Synthetic release adapters and phase receipts are labelled CPU-only and cannot authorize runtime. The production v7 runtime contains no test adapter or alternate CPU mode.

Execution results and limitations are added only after frozen-source execution. Root and independent /011 must inspect actual source and evidence before any later live invocation.
