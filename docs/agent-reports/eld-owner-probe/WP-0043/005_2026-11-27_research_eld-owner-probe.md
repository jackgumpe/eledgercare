# WP-0043 / 005. First completed read-only score on the retained stock pair

The native stock run returned both documents and all eight scheduled calls. The corrected scorer reports **M**, with **0/1 qualified public pairs and 0/5 complete field rows**. Its two conflicts concern the Windows executable path recorded in the worker argument vector. The scorer found no difference in the compared public document content, no unsupported token selection and no tensor-byte conflict. Each of the five rows has an unresolved runtime-custody requirement.

## Source, authority and custody

- **Author and publisher** — eld-owner-probe, same Codex CLI session 01a21a88-678f-7ef3-ae76-cc13b78dde43, gpt-6.2-astra with requested xhigh. Windows x64, pinned Q0 venv, CPython 3.12.10. This is author verification. UTC 2026-11-27T02:36:31Z.
- **Reservation** — WP-0043 / 005, research, under docs/agent-reports/eld-owner-probe/WP-0043/005_2026-11-27_research_eld-owner-probe.md. Coordinator commit 6ac5aea379ab5601e5da153a0a041dffb1963d7a assigned one offline scorer correction following the closed lease. [Reservation](https://github.com/jackgumpe/eledgercare/blob/6ac5aea379ab5601e5da153a0a041dffb1963d7a/INDEX.md) · [Closed device receipt](https://github.com/jackgumpe/eledgercare/blob/6ac5aea379ab5601e5da153a0a041dffb1963d7a/docs/coordination/WP-0043/device-return.json)
- **Repository, base and deliverable** — jackgumpe/eledgercare, research/wp-0043-stock in w043-author, base 4e699157a0bd62f60dd145c09394438aa84fe1d5, corrected offline scorer ce72ff81bf7069ccc174b1780dc3a61f88143344. The device capture used the previously reviewed executable at 257bbdacf214285de03089b82a16c31bb27ad106 under release 641f72654257cee1c834461ac972e5ecf82f38f9. The corrected scorer was committed before its post-run entry was invoked or its results opened. [Correction](https://github.com/jackgumpe/eledgercare/commit/ce72ff81bf7069ccc174b1780dc3a61f88143344) · [Original author report /002](002_2026-11-27_research_eld-owner-probe.md)
- **Status** — ready-for-review. Next owner eld-rd-reviewer independently runs the corrected scorer for /003. The coordinator owns /004 and the disposition. The previous report remains an immutable account of its pre-device CPU evidence.

## Why the original invocation crashed

A finished archive enters timing validation for each arm. In score_native, assignment to a local expected-event list named timeline made that name local throughout the function. The completed-arm path attempted to call it before the assignment, producing UnboundLocalError. The absent-archive CPU control in /002 returned before exercising that condition. The only change in the deliverable is two lines in docs/research/WP-0043/native_score.py, giving the imported timing function the distinct name validate_timing and invoking it under that name. All scoring predicates, bounds, evidence requirements and the stored archive remained in force. No further mechanical blocker occurred. The subsequent publication adds only this report.

## What the score measured

The coordinator reported two completed cold loads, eight returns and zero remaining calls under lease wp0043-f07-stock-pair-02, closed and released after supervisor exit. Both target F07 documents stopped with 2,558 non-EOS IDs, 7,617 UTF-8 bytes and markers at positions 0, 1145 and 1896. The closed receipt records 81 pre-outcome files and a completed supervisor manifest. This author performed zero device calls for /005. The corrected offline entry hashed the retained inventory, replayed timing and append chronology, checked native state, tensors and guard captures, and compared the two public returns and their archive anchors. Its conflict list contains only the two argv findings.

| Row | Consumed generated index | Single maximizing ID | Selected ID | Allowed IDs | Row result |
|---:|---:|---:|---:|---:|---|
| 0 | 618 | 6 | 6 | 129279 | U |
| 1 | 619 | 1449 | 1449 | 129279 | U |
| 2 | 620 | 16 | 16 | 129279 | U |
| 3 | 621 | 1328 | 1328 | 129279 | U |
| 4 | 622 | 128822 | 128822 | 129279 | U |

All five observed rows have empty repetition bans and a singleton maximal-ID list. The prior archived public selections alone could not establish the actual winners. Here the read-only scorer computed each maximal-ID list from a full final vector in the captured artifact. The remaining missing key in each row is native_custody_unqualified at B. The scorer emitted no conflict on support, mask composition, first maximum, digest, source cut, global append order or public ID/text/stop. These are observations about this single retained pair and this version of the verifier.

The first conflicting phase is public_document, with key runtime_contract and field argv for each arm. The frozen plan requires the worker command to start with the venv launcher. Each recorded sys.orig_argv starts with the Windows base Python interpreter. Interpreter flags, script path, _worker subcommand and the individual arm name match exactly. The two paths are given in the machine result below. The supervisor constructs its launcher argv from the fixed plan. The worker writes sys.orig_argv at runtime, while child admission separately checks sys.executable against the venv path. The earlier harmless Windows Job test in /002 witnessed two processes, a venv launcher and the actual interpreter, inside the same Job. These are different observable quantities. The failed equality is an actual recorded audit discrepancy. It does not by itself identify a numerical output difference or establish that the run bypassed the venv. The captured data cannot turn a failed frozen equality into a pass.

The scorer aggregates the runtime checks with the public checks and propagates an unqualified custody marker to all five dependent rows. Accordingly the content comparison produced no conflict while the qualified public verdict is M. The overall M is decisive for the specified contract. No new source changes were made in response to these values.

## Verification and retained outputs

From the author's owned worktree, the parent used the following exact argument vector. The command ran from 2026-11-27T02:34:36.738036Z through 02:34:44.049937Z, exited 0 and returned one JSON object. The reported process exit denotes successful completion of scoring, independently of the scientific verdict M.

~~~~text
C:\Users\jackg\eLedgerCare-Q0\WP-0005\venv\Scripts\python.exe
-B
-u
C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\w043-author\docs\research\WP-0043\stock.py
score-native
~~~~

- Standard output measured 2,054 bytes, SHA-256 aef1b94fb102c860409159176ff4ebaacd398cea96866e5d23c290e3130b8b18. Standard error measured zero bytes, SHA-256 e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855.
- Outcome SHA-256 before and after the invocation was 606aaf5719f762bc326d4fd88be72388921cd7c9aa663e99949f26c12b226961. Output files, receipt and verification script are in role-owned scratch under C:/Users/jackg/eLedgerCare-Speed/WP-0043/author. The receipt at closed-score-ce72ff81/receipt.json has SHA-256 52eb10df1d720a43931b74ac3814f0ba2d223289ede05f531f1aa3d8c906d009.
- Only the scorer and the report were committed. The CLI read the private archive in its original location. Standard streams were redirected to a fresh sibling scratch directory. No raw native tensor, logit vector or private memory address is published here. Device admission, model load, capture, restoration, private arms and a second paired run were outside this correction.

The complete returned JSON follows. The original byte hash above includes its Windows line ending.

~~~~json
{"verdict":"M","first_divergent_phase":"public_document","conflict_keys":["runtime_contract"],"missing_keys":["native_custody_unqualified"],"conflicts":[{"row":null,"phase":"public_document","key":"runtime_contract","field":"argv","expected":["C:\\Users\\jackg\\eLedgerCare-Q0\\WP-0005\\venv\\Scripts\\python.exe","-B","-u","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\native.py","_worker","untouched"],"observed":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","-u","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\native.py","_worker","untouched"]},{"row":null,"phase":"public_document","key":"runtime_contract","field":"argv","expected":["C:\\Users\\jackg\\eLedgerCare-Q0\\WP-0005\\venv\\Scripts\\python.exe","-B","-u","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\native.py","_worker","observed"],"observed":["C:\\Users\\jackg\\AppData\\Local\\Programs\\Python\\Python312\\python.exe","-B","-u","C:\\Users\\jackg\\Asp.net Projects\\eledgercare-worktrees\\w043-author\\docs\\research\\WP-0043\\native.py","_worker","observed"]}],"missing":[{"row":0,"phase":"B","key":"native_custody_unqualified"},{"row":1,"phase":"B","key":"native_custody_unqualified"},{"row":2,"phase":"B","key":"native_custody_unqualified"},{"row":3,"phase":"B","key":"native_custody_unqualified"},{"row":4,"phase":"B","key":"native_custody_unqualified"}],"rows":[{"row":0,"banned":[],"ties":[6],"y":6,"support_size":129279,"verdict":"U"},{"row":1,"banned":[],"ties":[1449],"y":1449,"support_size":129279,"verdict":"U"},{"row":2,"banned":[],"ties":[16],"y":16,"support_size":129279,"verdict":"U"},{"row":3,"banned":[],"ties":[1328],"y":1328,"support_size":129279,"verdict":"U"},{"row":4,"banned":[],"ties":[128822],"y":128822,"support_size":129279,"verdict":"U"}],"domain":"native_stock","scheduled_rows":5,"complete_rows":0,"scheduled_pairs":1,"public_pairs_matched":0,"public_verdict":"M"}
~~~~
