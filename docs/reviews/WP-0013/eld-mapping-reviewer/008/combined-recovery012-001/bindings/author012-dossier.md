# WP13 separate recovery012 results

All 14 scheduled calls completed once: two excluded historical warmups and 12
primaries across four families. Execute, worker and CPU score exits were 0;
there were no runtime/finalization failures or retries. The separate original
/007 trial remains immutable with all 12 primaries unavailable. Recovery used
already exposed content and is not a newly blind evaluation.

| Original metric | B0 | Mapping v1 | Mapping v2 |
| --- | ---: | ---: | ---: |
| Printed fields | 0/87 | 1/87 | 37/87 |
| Printed cells | 0/153 | 0/153 | 48/153 |
| Rows, declared known cells | 0/27 | 0/27 | 12/27 |
| Verified absences | 0/12 | 0/12 | 6/12 |
| Page count | 12/12 | 12/12 | 12/12 |

Normalized field/cell counts equal printed counts in this run. Equal-family
mean field and cell rates for v2 are 0.488095 and 0.5; these are distinct from
pooled slot rates. Full predictions, original metrics, policy metrics, family
and case summaries are in [scores.json](evidence/attempt-1/scores.json).
[Analysis](evidence/attempt-1/analysis.json) retains every per-document count and
all three paired comparisons, including neutral and unavailable populations.

V1 to v2 has 37 field gains, one loss and 49 neutral uncredited fields; 48 cell
gains, no losses and 105 neutral uncredited cells; 12 row gains and six verified
absence gains. The one lost exact field is F01-conflict `work_order_id`: v1
emitted the duplicated equal value, while v2's `duplicate_label` guard removed
that candidate. Its known printed truth remains scored as a loss; the separate
required-abstention violation is removed. F02, F03 and F04 conflict cases also
lose three ambiguous assignments, which are not original known-value credits.

Policy accounting keeps all 255 slots eligible: 252 known, three ambiguous,
zero unknown, zero unavailable. V2 has 91 correct known assignments, zero
incorrect/ambiguous/unknown assignments, zero surplus candidates and zero of
89 required-abstention violations. It has 164 abstentions, including 75
unexpected abstentions. V1 has one correct known and three ambiguous
assignments, with four required-abstention violations; B0 has zero assignments
and 166 unexpected abstentions. Required abstention is not value recovery.
The four unsupported cases remain in all denominators: 85 eligible required
abstentions, no assignments. Supported/conflict cases have 47/44 correct
assignments and 38/37 unexpected abstentions, respectively.

F02 supported/conflict remain uncovered. Their retained v2 decisions show
`missing_profile`, with the description column unresolved: native output says
`Service / Item`, while the frozen case-sensitive catalog has `Service / item`.
Without a complete native header match, the table and alias fields are refused.
This is an observed mapping-coverage limitation; the output was available and
parseable. No new experiment, catalog edit or inference follows this finding.

## Exact execution and custody

- Executing HEAD: `fbc2ab64e9ae1b4ff6655e427d78e69930d40b72`, held clean through
  execute and score. Accepted source `ae790497f3fdd10573e8179757416bc2d1736250`,
  mapping tree `8fd68c96bb18ca0177f227ad9a82505090d997b0`.
- Corpus `373106d94b56e619e2210308ca3bf237b45affc0`, tree
  `af22f632c2b69531f61866ca467c6f04f386df7e`; no source/input changes.
- Runtime authority `73fbbd7856b61d227b4462c9120ca6d117316a04`; exact
  [kickoff](evidence/attempt-1/bindings/recovery-kickoff.md) and
  [release](evidence/attempt-1/bindings/00-author.json) are copied from Git.
- Execute 19:29:02.0754462–19:46:23.8644620Z; tool83774/final206d9e.
  Wrapper10620, supervisor28512, launcher26836, worker36624; creation identities
  and original argv are in [launch receipts](evidence/attempt-1/launch/launch.json)
  and [run result](evidence/attempt-1/run/run-result.json).
- CPU score 19:46:56.5433437–19:47:01.7472574Z; tool59b184, exit0.
  [Score receipt](evidence/attempt-1/launch/score-execution.json) records the
  exact command and clean HEAD. Execute/score streams and tool receipts remain
  byte-exact under the same launch directory.
- Explicit return 19:47:29.8978374Z. Root ACK
  `6090281419d54292cf8917b38ae50316eb26f3f9` at 19:47:55Z independently binds
  model/notices/host, owned PID absence and desktop sharing; see
  [ACK](evidence/attempt-1/bindings/10-lease-return-ack.json). No further author
  model job is authorized.

The one-load supervisor elapsed time was 1038.594s. Excluded warmups took
143.976s and 303.041s. Primary synchronized calls totaled 559.555s, mean
46.630s, range 36.106–68.794s. Primary maximum CUDA allocated/reserved bytes
were 7,293,335,040 / 7,480,541,184. Host private/working-set sampled peaks were
10,881,638,400 / 2,388,942,848 bytes (lower bounds); the cold-load private peak
was higher and remains in the load receipt. All 14 observations retain the
`triton_import_failed_dense_fallback` label. Fixed order, one load, shared
desktop/WDDM activity and observer overhead prevent a performance claim.

## Evidence and review map

[Collector](collect_evidence.py) was frozen at
`9a2e4c8866c90d78e986bf9ef487cb80683ee21b` after execute and scoring, before its
first successful collection (19:51:07–18Z). It imports no model, renderer or
scorer. Its [original execution receipts](collection-execution/attempt-1/execution.json)
and tool records are retained. No failed collection attempt exists.

[Collection](evidence/attempt-1/collection.json) binds 140 copied originals,
50 scheduled input artifacts and 310 source paths. The complete
[run-copy manifest](evidence/attempt-1/run-copy-manifest.json) covers 131 files:
103 published under the original run-relative names and 28 retained-only cache
files. Empty cache directories are disclosed. No weights or unrelated files
are published. [Source inventory](evidence/attempt-1/source-inventory.json)
records exact Git mode/type/blob identities; the later publication inventory
checks every base path and every copied Git byte. Original007 scores are copied
separately and never pooled into recovery quality estimates.

Scoring remains unchanged: row credit concerns declared known cells; raw
`extra_cells` does not prove invention for unjudged cells. Historical quantity
normalization tests numeric magnitude after supported-unit validation, not full
unit semantics. Bounded reference text-edit metrics do not establish complete
OCR character accuracy. Four families do not establish broad generalization.
Independent /008 and coordinator /009 remain pending; no retuning or promotion.
