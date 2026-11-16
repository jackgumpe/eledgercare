# Retained Reviewer-Helper Failures — WP-0008 / 007 (`eld-f3-reviewer`)

Per `AGENTS.md` and `docs/kickoffs/WP-0008-eld-f3-presentation-reconciliation.md`, every failed execution of a frozen reviewer helper is preserved byte-for-byte and distinguished from later prose notes:

| Frozen Reviewer Helper Commit | Failure Type | Preserved Byte-Exact Original Logs | Bytes / SHA-256 | Root Cause & Reviewer-Helper Fix |
| --- | --- | --- | --- | --- |
| `04ecf60114bf279d0104d8e7421683a8c68ed6b4` | Reviewer helper SQL column projection typo (not a product defect) | [`04ecf601-task-573.log`](04ecf601-task-573.log)<br>[`04ecf601-01-pg-cluster-start.log`](04ecf601-01-pg-cluster-start.log) | `1654` B (`85d12b743aace47342e9897191e108396cfdfd10af2c89a5c3617527486600ba`)<br>`384` B (`d7c094088eb21de191a3b306ae10dd46f710dc0244486c1567a367ed84193a68`) | `query_seed_db_complete_snapshot` in `run_f3_presentation_reconciliation.py` queried non-existent columns (`previous_revision_id`, `value_text`, `machine_status`, `machine_value_text`, `consulted_source_quote`) instead of the actual `AddWorkOrderReview` migration columns (`previous_revision_number`, `human_value`, `consulted_quote`, `input_sha256`, `raw_output_sha256`, `machine_snapshot_json`, `field_ordinal`). `finally:` cleanly stopped PostgreSQL `55437` (`postmaster PID 5100`). Fixed SQL column list in the next frozen helper commit with zero product edits and zero database mutation. |

> Note: `04ecf601-task-573.log` and `04ecf601-01-pg-cluster-start.log` are exact byte-for-byte copies of the original task/step logs (protected by `.gitattributes` `* -text -whitespace`); this `README.md` is a post-failure explanatory ledger.
