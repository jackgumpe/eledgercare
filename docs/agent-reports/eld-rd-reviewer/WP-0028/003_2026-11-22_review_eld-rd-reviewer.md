# WP-0028 /003 Independent review of the owner-only twin binders

| Field | Recorded value |
| --- | --- |
| Report path | `docs/agent-reports/eld-rd-reviewer/WP-0028/003_2026-11-22_review_eld-rd-reviewer.md` |
| Reservation | [WP-0028 /003](https://github.com/jackgumpe/eledgercare/blob/c000c0299619345c887859b95c45befbb0c68987/INDEX.md#wp-0028-owner-only-matched-binders) |
| Category and status | Review, accepted for the CPU diagnostic. Both controlled pairs are blocked at feature admission. |
| Author and publisher | eld-rd-reviewer, fresh non-author native Codex collaboration session `/root/w28_review`; no involvement in the two reviewed implementations, historical probe, fixtures, or coordinator proposal |
| Model and environment | Codex based on GPT-6. Exact backend variant and effective effort are unexposed. Requested xhigh. Windows PowerShell, Q0 Python 3.12.10, Torch 2.13.0+cu130, deterministic single-thread CPU, offline and CUDA hidden |
| Timestamp | 2026-11-22T07:51:57Z |
| Repository and branch | Private `jackgumpe/eledgercare`, `review/wp-0028-owner-only`, `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/w028-review` |
| Base revision | `c000c0299619345c887859b95c45befbb0c68987` |
| Final reviewer source | `bf0ff7af0d8da893beb0dae742c133dbb1880aa1` |
| Reviewer deliverable with evidence | `28be00df3b48aee0a3016a0d6eef63876c7a629a` |
| Reports reviewed | [Fixture /001](https://github.com/jackgumpe/eledgercare/blob/98702b5583d27b654b52507673985e9d307e7a54/docs/agent-reports/eld-owner-fixture/WP-0028/001_2026-11-22_research_eld-owner-fixture.md) and [probe /002](https://github.com/jackgumpe/eledgercare/blob/b4cd4a6492b9405c729ee7f7bb78b998daa34e78/docs/agent-reports/eld-owner-probe/WP-0028/002_2026-11-22_research_eld-owner-probe.md) |
| Previous report and next owner | First independent review in this packet. eld-coordinator owns /004. |

## Disposition

The 12- and 30-page trials lack the same authenticated Cedar opening. Independent source rendering and a search of the eligible archives reproduced both authors' admission decision. The available data cannot determine how either frozen probe responds to changing the active owner alone, whether a response persists, or whether the correct winner changes. Historical pairs did vary in other cues. The historical replay passed all three checkpoints.

| Arm and horizon | Pair planned / admitted / completed | Alder windows covered | Cedar windows covered | Controlled owner ranking, typed posting and retention |
| --- | --- | --- | --- | --- |
| M1, 12 pages | 1 / 0 / 0 | 4/4 | 3/4 | Unobserved |
| M3, 12 pages | 1 / 0 / 0 | 4/4 | 3/4 | Unobserved |
| M1, 30 pages | 1 / 0 / 0 | 10/10 | 9/10 | Unobserved |
| M3, 30 pages | 1 / 0 / 0 | 10/10 | 9/10 | Unobserved |

## Fixture, archive and eligibility

I reconstructed both pairs directly from their preregistered development v2 PDFs. The original directory order, unit, schema, interruptions, page order, Courier-Bold text operation, and final unheaded posting stayed identical within each pair. The only source edit exchanged the five-byte owner literal in the opening parent declaration. Among 84 complete page appearances, both edited openings changed exactly 4,331 RGB pixel locations. The half-open difference box was [583, 1616, 804, 1677), within the preregistered [575, 1566, 875, 1705) pixel region at 300 dpi. The 40 untreated page pairs matched both canonical PNG and RGB bytes. All 38 regenerated files matched the fixture deliverable byte for byte, including the four PDFs and 31 distinct PNGs. [Independent per-page digests and routes](../../../reviews/WP-0028/physical.json)

I inspected every issued receipt in the four W0-qualified WP-0026 development archives. H0 contributes 8 hooked and 8 stock calls across two loads, development training-split C1 contributes 28 hooked calls, its completion archive contributes 11, and calibration contributes 29. The 76 hooked records span 61 distinct ordered RGB triples. The eight stock records lack pooled activations. Older unconditioned acquisitions lack the required W0 provenance. Blind records and sealed material were outside the search. The training-split check used published source and capture receipts. The only external answer-key access in this review was v2 development calibration, SHA-256 `a227da1293bcd6f8b0f636ce3349abd12d02a52361a46b47dbf34969cc773ff1`.

I checked the releases, plans, model/worker/sensor identities, order, matching W0 load and receipt, complete input triples, actual metadata, pooled float32 bytes and through-EOS bytes. Ten of eleven target input triples are cached, covering 26/28 uses. The only missing RGB key is `33362fbbeb37e805a64acbf3afdc3ec04315a4706820ed634a8fe0fb865ce2d5`, used at window one of each Cedar member. The three source pages had 0, 8 and 6 same-position feature-record matches individually and zero complete matches. Both final posting windows are physically shared with their source templates. All controlled checkpoint, query, field, typed and paired-effect observations remained null. I checked 24 member checkpoint rows, 48 null owner-score slots and 12 fully null derived rows. [Checked outputs](../../../reviews/WP-0028/comparisons.json)

The fixture author disclosed an exploratory read of one superseded development calibration label. The coordinator's reservation had already fixed the exact template IDs and target mapping. I inspected the executable source, which binds the v2 receipt and truth digest, and reproduced the full fixture and feature manifest from those inputs. I did not access superseded truth or find a dependency on it.

## Independent scoring

I loaded the exact WP-0024 scorer `7db67283a4ffd3e7a20bb8d80499572cc7118c71` and both WP-0026 weight objects from `6d79c24364ba10a1d9bfa4c72c837e2f216cf4bc`. An independently written observer took t₁ from the parent write's returned matrices, t₂ after the last first-window span completed and t₃ at entry to the native attempt before its target write. Each read used the original final query, actual depth and native eligible anchors. Each arm/pair had identical target query digests across twins and checkpoints. All checkpoint pointer, matrix, read, query, owner and unit/column results matched the frozen candidate. For T1, t₁ was (1,1,7), t₂ (1,3,15), and t₃ (4,2,3) or (10,2,3).

Across 8 historical pairs × 2 arms × 3 checkpoints I independently recomputed 48 paired trajectories from 96 member readouts. I compared 224 native field logits across 32 actual attempts, including subtotal status when eligible. With the recorder enabled and disabled, native results and final states matched, and an identical repeat reproduced all score, query and state bytes. The signed Alder-minus-Cedar margins, μ, δ, δ change from t₁, signed guarded ratio, swaps and strict win equivalence agreed. I checked ties in a nonzero equal-logit native decision and a zero-state native read, negative initial effects, and null division for zero, absent, below-floor and exactly-at-floor denominators. [Independent per-binder results](../../../reviews/WP-0028/historical.json)

| Historical result, out of eight pairs per arm | M1 t₁ / t₂ / t₃ | M3 t₁ / t₂ / t₃ |
| --- | --- | --- |
| Positive directed δ | 0 / 8 / 8 | 4 / 8 / 8 |
| Both owner rankings strictly correct | 0 / 0 / 0 | 0 / 0 / 0 |

The PDF's M3 pair `03fe821e0efada96bdc61e31` reproduced target margins +0.10301829874515533 and +0.1028849147260189, μ +0.10295160673558712, and δ +0.00013338401913642883. Both inputs favored Alder. At the frozen gates, all 16 answerable historical binders in each arm abstained on the owner threshold. At the historical permissive cell, each arm posted 8/16 correct owners and 0/16 complete correct postings. The historical pairs do not enter the matched intervention denominator.

## Verification and inventory

From the owned worktree I used `C:/Users/jackg/eLedgerCare-Q0/WP-0005/venv/Scripts/python.exe -I -B` with each invocation below. The review-only entry points set offline caches and single-thread CPU execution in `C:/Users/jackg/eLedgerCare-Speed/WP-0028/review`. Commands shown use paths relative to `docs/reviews/WP-0028`.

| Script and arguments | Result |
| --- | --- |
| `physical.py physical-1.json`, repeated as `physical-2.json` | Identical independent source/feature output SHA-256 `1388837051412467894c772137e1f71fb4e4150b414b17a1c6772b76bb99b7e9`. Timed repeat 12.49 s wall, 11.59 s CPU. |
| `historical.py historical-3.json`, repeated as `historical-4.json` | Identical independent complete output SHA-256 `b13c60b54ba5ab414cc7d6f84d3b0932bbdc194c544b1869ef991bb9c01cf636`. Timed repeat 6.42 s wall, 4.88 s CPU. |
| `author_run.py fixtures 083564a96b015384de091f3578a76b41883ab1f0 fixture-author-2` | Exact fixture deliverable `ee8e96afcbd7a3c1f3eaa8125c05e68003c4a893` reproduced. Fixture process 22.37 s wall, 20.42 s CPU. |
| `author_run.py historical 9cb018cecab739097abb9e1554e8c61768b257b0 historical-author-2` | Author result SHA-256 `0db140d33dcfedba8787316ad4ef51b6ef2574db3dd15310d867212d74789d89`. 8.05 s process CPU. |
| `author_run.py controlled 9cb018cecab739097abb9e1554e8c61768b257b0 controlled-author-1 ee8e96afcbd7a3c1f3eaa8125c05e68003c4a893` | Author result SHA-256 `080fe21cc127cc36f86620ff28306bc154320617cfece01bb911958ea5f715f5`. 5.31 s process CPU. |
| `proposal.py proposal-1.json observed-coordinator-1.json physical-1.json` | Coordinator constructor `9377977d43042a78dd14d018878f714bb8b763e6` reproduced the published scope `eb814e399d50fc9b28738751fbbf92ca3c732214` byte for byte. |
| `compare.py comparisons.json` | Exact output comparison against both candidate publications, including probe evidence `fcaf30465f0ce120c8077369155e4b624044baad`, passed. |

The review-only scratch launcher initially wrote a Windows CRLF to Git's alternate-object path. Git reported that the object directory did not exist and both author launches stopped before measurement. I corrected the review launcher to write LF, froze it, and ran both frozen author sources in fresh directories. No author's source changed.

Base-to-deliverable changes under `docs/reviews/WP-0028` added `common.py` for pinned inputs and CPU isolation, `physical.py` for rendering and admission, `historical.py` for native replay, `proposal.py` for costs, `author_run.py` for scratch execution, and `compare.py` for evidence comparison. Outputs are `physical.json`, `historical.json`, `proposal.json` and `comparisons.json`. The following report commit adds only this report. Effects outside Git were temporary caches, copied frozen Git objects, copied development windows, renders and these results in owned scratch. No device lease, native inference, training or additional data acquisition occurred. Both authors' report heads were verified against the private remote with `git ls-remote --heads origin` before publication.

## Follow-up and handoff

One separately authorized native B=1 hooked BF16 capture could supply both missing uses, after one excluded W0 on the same fresh load. The proposed budget is one load, two native calls total, zero retries and 180 seconds supervised. The closest historical Alder opening, calibration k0007, took 38.7288812 s. Its primary cold-load and W0 receipts recorded 20.5959215 and 24.7535243 s, yielding an 84.078327 s comparator. A non-author operator on one verified exclusive lease and independent receipt verification are specified, with abort on identity, EOS, source alignment, feature integrity, VRAM or time failures. Ten eligible triples stay cached. The coordinator's document records the proposal as unreleased. [Cost verification](../../../reviews/WP-0028/proposal.json)

eld-coordinator may close /004 on these exact revisions. The independent review accepts the fixtures, historical replay, reason-coded missing results and cost proposal. Controlled owner accuracy, retention, and winner changes remain unmeasured.
