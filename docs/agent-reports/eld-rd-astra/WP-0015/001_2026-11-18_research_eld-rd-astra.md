# WP-0015 / 001 Independent architecture position

| Publication field | Value |
| --- | --- |
| Canonical report | `docs/agent-reports/eld-rd-astra/WP-0015/001_2026-11-18_research_eld-rd-astra.md` |
| Reservation | [Assignment and sequence 001 at the dispatch revision](https://github.com/jackgumpe/eledgercare/blob/c4d7734d0be6302e667d290698bc671631c71ce9/INDEX.md#wp-0015-scanned-packet-ocr-architecture-trial) |
| Author / publisher | eld-rd-astra, fresh native Codex research author in `/root/speed_astra` |
| Model and effort | Requested Codex 6.2 Astra xhigh. Applied backend and effort are not independently exposed to this session. |
| Environment | Local Windows PowerShell and pinned Python 3.12 Q0 interpreter, CPU inspection only |
| Timestamp | 2026-11-18T03:14:06Z |
| Repository / branch | `jackgumpe/eledgercare`, `research/wp-0015-astra`, worktree `speed-astra` |
| Assignment base | `c4d7734d0be6302e667d290698bc671631c71ce9` |
| Deliverable | `7aa1d14c25b9317fd791aa8981816bc78e2d46a6` |
| Prior reports | First report of this author in WP-0015. Prior measurements belong to WP-0014. |
| Status / next owner | Research position ready for comparison with the independently frozen second position. Coordinator owns release, independent reviewer owns final replay. |

## Finding and scope

The first challenger I would measure is a local visual reader with source-linked word geometry and deterministic table reconstruction. Its eliminated serial decode work could close the throughput gap on printed packets. Wrong cell placement could reverse that ranking even with excellent transcription. The position defines the comparator, document-specific predictions, falsifier and thresholds. This report establishes an independent prior. The author did not read a fresh WP-0015 peer position or author either supplied original. [Frozen position](https://github.com/jackgumpe/eledgercare/blob/7aa1d14c25b9317fd791aa8981816bc78e2d46a6/docs/research/WP-0015/astra/position.md)

## Evidence and execution

| Executed check | Observation |
| --- | --- |
| `git status --short --branch` and `git rev-parse HEAD` | Clean assigned worktree and exact assignment base before writing. |
| `Get-ChildItem -File C:/Users/jackg/eLedgerCare-Speed/WP-0015/briefs \| Get-FileHash -Algorithm SHA256` | Original PDF `6c7f5199fb971eff0953f24c6a00b1af8f7c44c407df9c08c4363938c2d6567b`, original Markdown `a6442154f4c65fa0994b7d9b9229cc4d5e1169336dff39f5e17da44f18533099`, controlling brief `5b46d5317c0e8579ea5015d357a38ea4f73cae622f235a92dd3173a4e27c83eb`. All match the assignment. |
| Q0 `pypdfium2.PdfDocument` and page text extraction; `Get-Content` on the three readable inputs | Four original PDF pages. On removing whitespace from the two extractions, 12,835 characters each and two soft glyphs rendered as U+FFFE versus hyphens. The supplied text extraction has digest `e8d51f55ec13e9bc5a945f0629a16bf1f6a03bd1ae146fbbb177d7e6aa288161`. A preliminary console print encountered a CP1252 encoding error; ASCII-escaped inspection completed. |
| Native model `infer`, `infer_multi`, `_uocr_generate`; worker `RealTorchRuntime`; WP-0014 instrument and dense native receipt | Local BF16, greedy cached autoregression, base-mode vision, page-count guard and EOS removal from the returned IDs. Dense observation and prior timings are in the position. |
| Windows PowerShell WinRT `OcrEngine.AvailableRecognizerLanguages`; `Get-Item C:/Windows/System32/Windows.Media.Ocr.dll` | `en-US` recognizer present. DLL version `10.0.26100.9278`. A separate Windows servicing inventory query required elevation; WinRT enumeration succeeded at ordinary privilege. |
| `git diff --check --cached` before commit; `git diff --name-only c4d7734d0be6302e667d290698bc671631c71ce9 HEAD` afterward | Whitespace check passed. Sole deliverable addition was `docs/research/WP-0015/astra/position.md`. This canonical report is the sole subsequent metadata addition. |

No GPU, model inference, sealed input, customer data, product changes or service installation participated. The proposed table reconstruction and full end-to-end gain await actual trials. Handoff is to the coordinator for reconciliation after both position freezes, then exact candidate/lease selection and independent replay. [Position diff](https://github.com/jackgumpe/eledgercare/compare/c4d7734d0be6302e667d290698bc671631c71ce9...7aa1d14c25b9317fd791aa8981816bc78e2d46a6)
