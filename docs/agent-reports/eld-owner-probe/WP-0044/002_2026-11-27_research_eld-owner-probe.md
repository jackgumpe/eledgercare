# WP-0044 / 002 — Windows observed both Python images and two protected outputs

| Report field | Value |
| --- | --- |
| Reserved path | docs/agent-reports/eld-owner-probe/WP-0044/002_2026-11-27_research_eld-owner-probe.md |
| Reservation and base | eb2b09c176cf3793ea9e9f930b913b9769d516e8, WP-0044 / 002 in INDEX.md |
| Category and author | Research, eld-owner-probe |
| Actual session | Native Codex collaboration worker /root/provenance_author, thread 01a21d7c-eca3-7131-86e7-9612211371c8. The assignment requested gpt-6.2-astra at xhigh. The worker's environment disclosed its thread and did not independently expose a model identifier or effort setting. |
| Environment | Windows x64 10.0.26300.0, CPython 3.12.10 final, AMD64, MSC v.1943, standard library, ordinary current user |
| Repository and branch | jackgumpe/eledgercare, research/wp-0044-provenance, worktree w044-author |
| Deliverable | 8e78cc23abbc796b846ce59284ff46f66fde866b |
| Decisive release | a472267c05d678e63af4d01db7dcd823cc31d04c |
| Blind evidence | f3c59b478d4b6ce19dc7dd32ae68ad663a8ee29c |
| Timestamp and status | 2026-11-27T15:11:31Z, ready-for-review |
| Related report | WP-0043 / 004, coordinator's historical disposition at 82952ad1f75509131228ef19d8d4fcd771ef4c8e |
| Next owner | eld-rd-reviewer for independent source and evidence inspection, then eld-coordinator for disposition |

## Decision and observations

Can the observer show which interpreter issued the write to the scored object? Two genuine Windows runs returned the exact four bytes 46 30 37 0A to distinct original NTFS files. In both, L, I, A and C passed. E and B were unresolved. Each creation event supplied an OS handle to the actual executable file, and its measured digest matched the correct frozen role. The interpreter reported its original argv[0] as @base/python.exe and its effective executable as @venv/Scripts/python.exe. The two genuinely missing atomic witnesses were **E.parent** and **B.writer**. Both custody and joint were U on each genuine arm. The required genuine full passes are 0/2 on this author route. [Blind records](https://github.com/jackgumpe/eledgercare/blob/f3c59b478d4b6ce19dc7dd32ae68ad663a8ee29c/docs/research/WP-0044/blind-results.json)

The held launcher instance, inherited-parent PID from the worker, interpreter self-instance, job membership and creation order all agreed. Windows' CREATE_PROCESS_DEBUG_EVENT identifies the newly created process and its image. This receipt contains no creator-thread identity. The parent created the output endpoint and retained a writable guard, the launcher received a writable stdout alias and the pinned worker inherited it. The worker reported the original NTFS ID on stdout. The supervisor observed the same ID at creation, finalization and direct read. These observations establish the endpoint assignment and continuous protection. They leave attribution of an individual write to one of the writable aliases unresolved. On the nominated implementation, accepting either genuine arm would therefore exceed the observations. [Observer implementation](https://github.com/jackgumpe/eledgercare/blob/8e78cc23abbc796b846ce59284ff46f66fde866b/docs/research/WP-0044/native.py)

| Submission for A | Witness in the decisive run | Joint / content |
| --- | --- | --- |
| Second valid process pair | Its selected launcher instance differed from A's anchor, E.launcher M | M / P |
| Incompatible read-only open on A's venv image | CreateFileW returned sharing violation 32 at 15:09:03.281199Z, with the retained guard ID equal to the OS-supplied loaded-image ID | U / P |
| Protected A | Direct scorer handle joined A's registered NTFS member and authenticated receipt | U / P |
| Protected B | Separate registered NTFS member joined B's authenticated receipt, B.origin M for wrong origin | M / P |
| Detached copy with valid reference | No registered direct object or origin for the supplied equal bytes | U / P |
| Detached copy with altered seal | HMAC verification failed, B.seal M for integrity, with direct acquisition and origin missing | M / P |
| Detached copy with verification unavailable | Seal verification, direct acquisition and origin unresolved | U / P |
| A after closing the guard and reopening | Equal bytes and file ID, with protection, direct acquisition and origin unresolved | U / P |

Six owned processes were observed, counting a Windows console host for each Python pair. Both arm jobs reported limit flag 8192, both Python members were in their assigned job, and the launcher was alive when the interpreter was created. Separate reader handles observed NTFS object IDs [3228420142,76561193665433661] for A and [3228420142,11258999068561478] for B. Each arm ran for approximately 0.188 seconds. The 0.485-second route generated 851,528 bytes across its private evidence directory, including the 303,991-byte public summary. It returned all 33 scheduled rows on the one authorized invocation.

## Score and diagnostic coverage

| Interface | Returned / scheduled | Matched the author's frozen target fields |
| --- | --- | --- |
| Native Windows | 10/10 | 0/10 |
| Constructed scorer input | 16/16 | 15/16 |
| Read-only WP-0043 index | 3/3 | 3/3 |
| Mathematical controls | 4/4 | 4/4 |

The author target measured coordinates, minima, content and complete conflicting/missing key lists for provenance rows; it measured the specified numerical values for the other seven. Its total is 22/33. Official q additionally requires agreement with the independently committed oracle on reason, source and earliest supported event. Its comparison belongs to independent review. The author never opened that oracle during implementation, execution or preparation of this report.

W5.config changed include-system-site-packages and the complete pyvenv.cfg digest. The scorer returned both conflicting atomic keys, C=M and custody=P. The author's expected key list omitted the full-file hash consequence. Its blind return also exposes a timing limitation. The input includes file-digest source sequence 189677 and parsed-setting source sequence 189687. The scorer preserves the source descriptors and treats both keys as earliest in the configuration phase. Its event ordering consumes time_ns for native measurements and otherwise uses phase ordering. Consequently its reported frontier fails to distinguish the supplied sequence order. The source descriptors in the frozen output preserve the distinction for inspection. The candidate and its result were frozen before this reconciliation. [Source and frontier rule](https://github.com/jackgumpe/eledgercare/blob/8e78cc23abbc796b846ce59284ff46f66fde866b/docs/research/WP-0044/scoring.py)

All five archived winning gaps recomputed as 10.875, 15.1875, 13.5625, 15.375 and 13.875. Each archived support comprised 129,279 permitted IDs and excluded only EOS=1. The public WP-0043 index records two literal argv[0] disagreements, one matched target document, five U custody rows, joint M and 0/1 qualified pairs and 0/5 qualified rows. This route reevaluated the public recorded constraints. Its mathematical controls observed unchanged row-0 pair winner under a common +10 shift, ties resolving to the lower ID, distinct little-endian FP32 signed-zero words for equal numerical values, and reset ID 0 versus linked ID 1 after a changed scalar cache. [Archive and arithmetic source](https://github.com/jackgumpe/eledgercare/blob/8e78cc23abbc796b846ce59284ff46f66fde866b/docs/research/WP-0044/controls.py)

## Change inventory and reproduction

| New file under docs/research/WP-0044 | Role |
| --- | --- |
| README.md | Scientific question, assumptions, proof scope, resource limits and invocations |
| manifest.json | Both image digests, script/argv, 70 module-cut identities and configuration |
| expectations.json | Independently transcribed author targets fixed before challenge exposure |
| worker.py | Fixed inert output, module/config cut, process self-key and stdout identity |
| win_observer.py | Win32 handle, NTFS identity, job and creation-event observations |
| native.py | Two real arms, receipt authentication, direct scorer acquisition and native challenge submissions |
| scoring.py | Typed comparisons, minima, diagnostics and event ordering |
| controls.py | Three archival and four mathematical checks |
| probe.py | Ordinary run and offline score subcommands |
| blind-results.json | Subsequent evidence-only commit f3c59b478d4b6ce19dc7dd32ae68ad663a8ee29c |

The report itself is a later metadata-only commit. The following checks were executed.

1. git status --short --branch and git rev-parse HEAD confirmed the clean assigned branch at the reservation and again at the frozen source revision. The coordinator-supplied handoff and mathematical Markdown SHA-256 values matched their source pins. The admission schedule and expected file covered the same 33 case IDs.
2. py -3.12 -I -B -m venv --without-pip prepared runtime-v1 under the private role directory. Developer-only manifest calibration measured the exact fixed worker entry. The manifest SHA-256 was 87a4ded6ceac20c88bd5108b0b912c844c23c690996f9d64ba50fc02dddde7c1, and the author expectation file was 2ed04310a2f8a4d6f6c61878638927ddb7b220a4b0519fdf3eed06cac85b13cd. Python parsed every candidate source. A disjoint constructed smoke retained a B.seal conflict and a missing B.direct in the same return.
3. Isolated native development smoke 01 stopped when Windows created its console host as an auxiliary third process. Smoke 02 identified the auxiliary job member via its creation notification. That pre-freeze diagnostic read the OS-supplied console-host image handle. The frozen candidate closes auxiliary image handles without hashing their bytes. Smokes 03 and 04 verified the interpreter's independent process/NTFS self-observations and the single-arm genuine U. These smoke directories are retained separately in private scratch.
4. Immediately before execution, a SHA-256 verification of all 16 case files in the private staged blind directory matched both blind-digests.json and the coordinator's exact execution freeze. The author ran **py -3.12 -B docs/research/WP-0044/probe.py run**, once from the worktree root. Exit code was 0, with 33 returns and zero harness errors. HMAC material, diagnostic stderr, per-submission input records and original four-byte members stay in decisive-v1 under the private role root. The public results file matched SHA-256 4a407a3c75ac4e1447a8cdc4bd5d2553fef72b3f7f4cec8ad302cfd7f6764502.
5. The owned branch was pushed normally and git ls-remote confirmed both the deliverable and subsequent blind-evidence heads at their publication points. The previous scorer and product received no source changes. The 49+1 prior-scorer regression suite was outside the unchanged-scorer branch of this assignment. No model, accelerator or production route ran.

For an offline constructed record, the normal entry is py -3.12 -B docs/research/WP-0044/probe.py score record.json. The smallest outstanding native observations are the creator identity at interpreter creation and an attributable write with complete alias accounting. The smallest diagnostic reproduction is a same-phase pair with two distinct source sequence values. The independent reviewer can compare these exact candidate and evidence revisions with its separate route. [Pinned candidate diff](https://github.com/jackgumpe/eledgercare/compare/eb2b09c176cf3793ea9e9f930b913b9769d516e8...8e78cc23abbc796b846ce59284ff46f66fde866b)
