# WP-0002 / 004: bounded independent correction closure

Status: released for the existing product-review Carbon session. This is the one routine correction exchange / evidence reconciliation after /002, not a fresh full-project review. Product implementation remains held until a non-author verdict and coordinator disposition.

- Owner: eld-reviewer.
- Requested model/effort: gemini-4-carbon-high / high, exposed by the existing agy models command. Continue Antigravity conversation 780ff7d0-276e-490c-b280-f6df87c57404 if available; report actual selected model/session and do not infer a backend checkpoint.
- Repository: https://github.com/jackgumpe/eledgercare (PRIVATE).
- Owned branch/worktree: review/wp-0002-contract; C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-reviewer.
- Full own-branch base: 266a80bf7a123496ef0d0c848fbd521b117f4543.
- Prior frozen design: e90c71817bc793dfbfc7576006be3cbf0b4310bf.
- Corrected frozen design candidate: bce84931fef5cf2a8fa3652095dbea2973a19aef.
- Own previous evidence/report: b279d28879316939b308cf50b8f5cc792a235775 / 266a80bf7a123496ef0d0c848fbd521b117f4543.
- Reservation: coordinator INDEX.md at 4ecc3ffe1d2842decf19ecdcfec0f5424fb4ac8b, WP-0002 / 004.
- Exact report: docs/agent-reports/eld-reviewer/WP-0002/004_2026-11-14_review_eld-reviewer.md.
- Next owner: eld-coordinator, WP-0002 / 005 for final design disposition and the held Opus release.

Keep your worktree on your owned review branch. Inspect the corrected candidate via git show/git diff on the exact SHAs; disposable gitignored .scratch materialization is allowed. Do not change the candidate, switch the coordinator's branch, merge new design files into your review branch, edit /002 or touch INDEX.md/CURRENT.md. Your report base is your own branch base above; your reviewed candidate is the separately pinned bce8493 revision.

Verify closure of SB-01, SB-02 and SB-03 in docs/design/F1-durable-intake.md: PDF 1.0..1.7-only strict admission with explicit 2.0/FDF rejection; immediate IsEncrypted and pre-loop NumberOfPages checks including empty-user-password owner encryption; acknowledged internal glyph/font/fallback behavior without application text extraction; 5xx uncertainty and 429 same-key retention. Check that BIC-01..06 are carried forward as bootstrap obligations, without being misreported as executed. The design adopted optional pageCount-internal and consistent GET UUID validation; browser digest caching stays deferred.

For BIC-03, the correction targets processing_jobs and requires evidence of the owned statement/locks. It also prohibits claiming completed earlier insertion from lock mode/timing alone; decide whether that is a faithful precise implementation obligation. Preserve all unknown server/runtime/lockfile/parser-test qualifications and local-only synthetic scope. No architectural redesign is requested.

Allowed edits: new docs/reviews/WP-0002/eld-reviewer/correction-closure/** evidence and your exact /004 report only. Existing tools/read-only source checks and scratch inspection are permitted. No package installs, application builds, parser execution, databases, services, GPU, models, production code, other agents or research branches. Avoid first-run dotnet commands; record any incidental effects honestly.

Return accepted or changes-requested on the exact corrected design, naming each SB disposition and remaining implementation checks. If a substantive issue is still unresolved after this exchange/reconciliation, identify its practical impact and alternatives for the coordinator instead of silently extending review cycles. You must not self-author design fixes.

Commit any review evidence first, then your immutable report as a separate metadata commit with full base/deliverable/reviewed SHAs, full inventory, UTC timestamp and actual checks. If the report is the only artifact, clearly identify the inspected candidate as the review deliverable and report publication as metadata. Push only your branch, verify remote report/branch objects and send full publication/deliverable SHAs and verdict to the coordinator. File creation or a branch push does not itself start Opus.
