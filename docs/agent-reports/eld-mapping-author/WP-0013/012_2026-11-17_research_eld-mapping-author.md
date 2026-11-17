# WP-0013 /012: Separate vocabulary recovery completed

- Report path: `docs/agent-reports/eld-mapping-author/WP-0013/012_2026-11-17_research_eld-mapping-author.md`
- Reservation: INDEX.md WP-0013 /012; exact live authority `73fbbd7856b61d227b4462c9120ca6d117316a04`, [copied kickoff](../../../research/WP-0013/eld-mapping-author/012/evidence/attempt-1/bindings/recovery-kickoff.md).
- Category / author: research / **eld-mapping-author**, native `/root/mapping_author`; same independent author session.
- Actual model / applied effort: not exposed; requested **xhigh** unchanged.
- Environment: Windows PowerShell; Python 3.12; qualified pinned external model environment, unchanged runtime settings.
- Timestamp: 2026-11-17T19:55:00Z.
- Repository / branch: `jackgumpe/eledgercare`; `research/wp-0013-vocabulary`, owned `eld-vocabulary-author` worktree.
- Base / executing HEAD: `fbc2ab64e9ae1b4ff6655e427d78e69930d40b72`.
- Deliverable: `fb5d65a9078619a87eccc5817dd95fbcc54f7f67`.
- Inventory / verification publication: `04546cfec2820a8d52bfa6d5f9fb6aedd8dfedee`.
- Previous reports: [original007](007_2026-11-17_research_eld-mapping-author.md), [correction013](013_2026-11-17_implementation_eld-mapping-author.md); accepted independent [source011 copy](../../../research/WP-0013/eld-mapping-author/012/evidence/attempt-1/bindings/01-011_2026-11-17_review_eld-mapping-reviewer.md).
- Status: **ready-for-review**, author verification only. Next owners: eld-mapping-reviewer /008, then eld-coordinator /009.

## Summary and criteria

The separately released recovery completed exactly two excluded warmups and
twelve primaries once. Execute/worker/score exits were 0, with no runtime or
finalization failure, retry or source change. The same clean HEAD was held
through execution and the one CPU scoring pass. Original007 remains a distinct
failed trial with all twelve primaries unavailable; recovery is not newly blind.

V2 scored 37/87 printed fields, 48/153 cells, 12/27 rows and 6/12 verified
absences; B0 scored zero in those metrics, and v1 scored one field. All three
scored 12/12 pages. V1→v2 field transitions are **37 gains, one loss, 49 neutral**;
cell transitions are **48 gains, zero losses, 105 neutral**. Equal-family v2
field/cell means are 0.488095/0.5. Normalized counts equal printed counts here.

All255 policy slots are eligible (252 known, three ambiguous, zero unknown or
unavailable). V2 has 91 correct known assignments, zero incorrect/ambiguous
assignments, zero surplus candidates, zero of89 required-abstention violations,
and75 unexpected abstentions. V1's four violations are suppressed, including
the one known duplicate-equal work-order identifier credited by the original
scorer. All four unsupported cases remain in the denominator. F02 remains
uncovered: native `Service / Item` fails the frozen case-sensitive
`Service / item` header match, leaving `missing_profile`. These outcomes do
not authorize retuning. [Dossier and full review map](../../../research/WP-0013/eld-mapping-author/012/README.md)
provide every document, family/case, neutral outcome and limitation.

## Change inventory and exact evidence

The [complete inventory](../../../research/WP-0013/eld-mapping-author/012/inventory.json)
lists all152 additions beneath `docs/research/WP-0013/eld-mapping-author/012/`:
the accounting-only collector, byte-preserving attributes, dossier, full
scores/predictions/analysis, original007 score copy, source/input/proof/run
inventories,140 copied originals and collection receipts. All5,173 base paths
retain their exact mode/type/blob identities. Later metadata consists only of
`inventory.json`, five files under `publication-checks/attempt-1/`
(`execution.json`, `originals.json`, `stderr.txt`, `stdout.txt`, `tool.json`),
and this report. No source, catalog, scorer, corpus or shared routing changed.

External run `C:/Users/jackg/eLedgerCare-Vocabulary/WP-0013/author/runs/author/20261117T192905Z-c72cf92b`
is retained:103 run files published byte-exact,28 cache files retained-only and
fully inventoried. No weights are published. Accepted source remains
`ae790497f3fdd10573e8179757416bc2d1736250`, tree
`8fd68c96bb18ca0177f227ad9a82505090d997b0`; corpus tree
`af22f632c2b69531f61866ca467c6f04f386df7e` is unchanged.

## Verification and return

| Actual operation | Result and immutable receipt |
| --- | --- |
| Accepted `cli.py execute`,19:29:02–19:46:23Z | All14 completed, tool83774/final206d9e, exit0; [original argv/identities](../../../research/WP-0013/eld-mapping-author/012/evidence/attempt-1/launch/launch.json). |
| Same-HEAD `cli.py score-run`,19:46:56–19:47:01Z | Exit0; [exact command/HEAD/streams](../../../research/WP-0013/eld-mapping-author/012/evidence/attempt-1/launch/score-execution.json), full scores retained. |
| Explicit lease return19:47:29Z; root ACK19:47:55Z | Bound PIDs absent; post observers0/0 and model/host/notices verified; [ACK](../../../research/WP-0013/eld-mapping-author/012/evidence/attempt-1/bindings/10-lease-return-ack.json) at `6090281419d54292cf8917b38ae50316eb26f3f9`. |
| Frozen collector `9a2e4c8866c90d78e986bf9ef487cb80683ee21b` | First collection and publication verification both exit0; raw/token/render bindings,140 originals/Git copies,28 caches,50 inputs and310 source entries checked. [Exact verification command](../../../research/WP-0013/eld-mapping-author/012/publication-checks/attempt-1/execution.json). |

No inference/scoring repetition or CPU suite rerun was needed for packaging.
Primary call wall time averaged46.630s; fixed order, shared desktop/WDDM use,
one load, observed dense fallback and observer overhead prevent performance
claims. Rows concern declared known cells; historical quantity normalization
and reference-text limits remain unchanged. Four families do not establish
broad quality or safety. Independent /008 and coordinator /009 remain required.

## Handoff

Deliverable and inventory were pushed normally and exact origin
`04546cfec2820a8d52bfa6d5f9fb6aedd8dfedee` verified before this report. Final
report publication SHA and clean/exact-origin receipt follow in the handoff;
this report does not claim its own hash. The author has returned the sole lease
and has no further inference or tuning release.
