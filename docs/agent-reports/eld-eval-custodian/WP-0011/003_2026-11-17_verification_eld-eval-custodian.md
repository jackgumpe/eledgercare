# WP-0011 /003: Sealed matched diagnostic corpus reservation

- Report path: `docs/agent-reports/eld-eval-custodian/WP-0011/003_2026-11-17_verification_eld-eval-custodian.md`
- Sequence reservation: [INDEX.md](../../../../INDEX.md) at exact authority `8d23d755a35be26ff29c319c527bd770abdcae4b`
- Category: verification
- Author / agent ID: `eld-eval-custodian`
- Actual model / effort: continuing native Codex session originally requested `xhigh`; backend model identity is not exposed here
- Execution environment: Windows PowerShell; existing Python 3.12.10, pypdfium2 5.15.2, Pillow 13.0.0, pypdf 7.1.0 CPU environment
- Published by: author
- Timestamp: 2026-11-17T08:46:59Z
- Repository / branch: private `jackgumpe/eledgercare`; `evaluation/wp-0011-diagnostic-families`
- Owned worktree: `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-coverage-custodian`
- Accepted initial base: `956c056be2ec970340074871ecdd7e1a9855d944`
- Exact starting authority HEAD: `8d23d755a35be26ff29c319c527bd770abdcae4b`, clean and exact origin observed
- Public reservation deliverable: `98a3a3f73df0e578ae98ebf3923db7ba4882d018`
- Public preservation evidence: `048719ca3f403d37fbe715ac53fa98288d92b2bd`
- Previous packet report for this role: none; earlier WP9 reports/custody/materials preserved
- Independent admission: /004 accepted at `021dc265790c90ae83f1afa24fc3f2a71eae41e1`
- Finalization release: `4f599cbf9e3deb6ca39473c4c080e17771ed2b78`; root acceptance audit `6ddb3756c9a696916c9657ee4a7bc09665ac7973`, read by exact Git object without merging unrelated changes
- Separate admission metadata revision: `8fff08dbdf456c54f5aa780b5e3dcccfa62c322f`
- Status: ready-for-review — preparation complete and exact corpus independently admitted; source acceptance and unseal remain separate
- Next owner: root for exact protocol/source acceptance and unseal; later reserved custodian /008 publication

## Summary

Exactly three fresh independent content families are frozen, each with four matched one-page PDFs: control, layout, vocabulary and degraded. The twelve documents are three independent samples with paired conditions. Coarse task coverage is work order, service invoice and inspection/service checklist. Public output contains fixed IDs, counts, schema/condition names, hashes, custody and author-check status. Identifying facts, labels/headers, arrangements, images, expected values, references and ideal-native witnesses remain sealed.

The first generation and first validation passed all fourteen author check groups. Both unchanged B0 and mapping-v1 recovered every intended control field, cell, row and explicit absence from ideal-native witnesses without surplus candidates. These witnesses establish source support, not actual OCR success. Both complete regenerations reproduced all 70 core files byte-for-byte. All twelve rendered pages were visually inspected in three matched contact sheets. Independent /004 accepted this exact unchanged corpus; this author report records that non-author acceptance without self-accepting ground truth.

## Objective and acceptance criteria

Follow the exact [WP-0011 kickoff](../../../kickoffs/WP-0011-eld-eval-custodian.md) and [WP-0010-0011 authority](../../../coordination/WP-0010-0011-authority.md). Prepare three fresh matched families before diagnostic source/scoring freeze; maintain facts, canonical identities, types, units and absence meanings across conditions. Prove known control support from frozen source and preserve one-factor restrictions, fixed degradation provenance, deterministic artifacts, complete reading order and exact immutable custody. Public schema coordination may not disclose private examples. Independent reviewer inspects actual visible content and proposes any correction; custodian cannot self-accept.

## Change inventory and immutable custody

Public author delta from exact authority:

| Added path | Purpose |
| --- | --- |
| `docs/evaluation/WP-0011/reservation/README.md` | Early frozen reservation, boundaries, verification scope and next admission |
| `docs/evaluation/WP-0011/reservation/reservation.json` | Twelve fixed IDs, 48 role/path/hash descriptors, condition/schema/counts and exact sealed bindings |
| `docs/evaluation/WP-0011/reservation/sealed-inventory.json` | Exact 108-entry complete sealed tracked-file inventory copy, paths/sizes/hashes only |
| `docs/evaluation/WP-0011/reservation/verification.json` | Public hash parity, metadata-only scope and preservation of all 2,704 authority input objects |
| `docs/evaluation/WP-0011/reservation/admission.json` | Separate exact non-author acceptance and root finalization binding; early reservation files unchanged |
| This later report | Canonical reservation verification after independent admission disposition |

New external custody: `C:/Users/jackg/eLedgerCare-Coverage/WP-0011/sealed`, resolved and confirmed absent before creation; local branch `sealed/wp-0011`, no remote. No old WP9 root or worktree was changed.

| Sealed purpose | Exact revision |
| --- | --- |
| Generator and validator frozen before execution | `d2be63415e2c0dc5e781cdf4bbf3f42505d72317` |
| Complete core candidate | `b5f33a65d463d4b9a5463fdb93353c0c7ac7c7f3` |
| Author evidence and frozen interface/inventory helpers | `f92ee134ead0d086330aaecbdad7a6e73ff6bbdd` |
| Exact offered public interface check evidence | `ae560b3936d1ca599bf027022691d9142fc07736` |
| Complete inventory receipt and clean sealed HEAD | `6583715067d3a027dd2502ed9623cf02c545391d` |

The complete inventory at `inventory/sha256-r1.json` has SHA256 `bd37f4020a4b5b185379d9d7d2e529b39ebc0d3fa0aa37802d2bccc0546c4330`, with 108 entries / 6,292,191 bytes at source commit `ae560b3936d1ca599bf027022691d9142fc07736`. Its subsequent receipt binds the inventory itself as the 109th file. Git internals, ignored byte-identical regeneration scratch and Python caches are excluded. Core manifest is `corpus/r1/manifest.json`; all 70 core files, including manifest, were reproduced exactly twice.

Public reservation JSON SHA256 is `ac58c97459b199232cb541ba2216159cada61db73b8e44abaa4128a22284cddc`. The diagnostic author pinned those metadata bytes and received no identifying contents. Public future paths under `evaluation/coverage_v1/` are reserved, not an unseal or runtime release.

## Condition design and limitations

All families use new fictional facts. Control field labels/header signatures come from unchanged B0 rules, and both unchanged mappers must recover a private ideal-native witness of its actual printed arrangement. Expected objects retain B0 schema 1.0.0, `split=diagnostic_eval`, and condition-valued `variant_kind`. Annotations retain canonical fields, headers, columns, row-key columns and PDF-point regions under `eld-coverage-annotations/1`; references cover all visible text, including furniture.

Layout changes arrangement only, preserving exact wording, multiplicities and typography. Vocabulary changes field/absence labels and table headers only, within identical reserved regions, positions, fonts and one-line/no-wrap layout. Glyph ink widths vary with wording inside those fixed regions; actual ink extents are retained separately. Facts, canonical slots/row identities, values, types, units and explicit absence meanings remain identical within each family.

Degraded references/witnesses use the same-family control. One fixed deterministic composite scan-quality recipe was selected before generation. Its transformed canonical control raster and final model-input render match pixel-for-pixel, preventing hidden container/resampling/clipping effects. Exact private recipe/geometry remain sealed. This is one composite condition at one severity, not independent attribution among its components. No fixture or severity was selected using model outputs.

Explicit empty printed slots use absent_blank; unprinted optional fields have no absence denominator. Quantity/unit literals are printed and retained, while inherited numeric normalization alone is not unit accuracy. Three families cannot establish population performance. No mapper, model or existing scorer was changed. Separate diagnostic metric definitions belong to the assigned author and independent source review.

## Verification

Generation/validation used the existing read-only CPU Python environment at `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-rd-carbon-recovery/.venv/Scripts/python.exe`. Commands below ran inside sealed custody; identifying results remain private.

| Command / check | Actual result | Retained evidence |
| --- | --- | --- |
| `generation/create.py --out corpus/r1` | Exit 0; 3 families, 12 one-page PDFs, 70 core files | `evidence/generation-r1/` |
| `generation/validate.py --candidate corpus/r1 --candidate-commit b5f33a65d463d4b9a5463fdb93353c0c7ac7c7f3 --public-repo <owned public worktree> --run-id verify-r1` | Exit 0; fourteen check groups passed against frozen candidate | `evidence/verify-r1/validation.json` |
| Actual PDF streams, reading order, expected values, annotations, typed values, empty boxes and no overlap/overflow | Passed all twelve; aggregate 92 filled fields, 12 tables, 28 rows, 172 cells, 12 absences, 12 quantity/unit cells | Core operators/reference/annotations and validation |
| Both unchanged mappers on all three ideal control witnesses | Six complete control recoveries; no surplus; explicit absences verified | `evidence/verify-r1/ideal-control-support.json` |
| Matched semantic signatures and one-factor text/style/region restrictions | Passed across three four-condition families | `evidence/verify-r1/matched-condition-checks.json` |
| Fixed degradation recomputation from exact control model-input rasters and final render/container comparison | All three final rendered input rasters exactly match declared transformed targets | Same matched-condition evidence |
| Independent Decimal invoice arithmetic | Passed | Same matched-condition evidence |
| Twelve PDFium previews; local view_image of three matched sheets | All twelve visually inspected; readable intended values; no observed clipping/collision | Previews/contact sheets and `visual-inspection.json` |
| Two full fresh generator invocations in distinct ignored scratch directories | Both exit 0; all 70 files byte-identical to frozen candidate | Retained stdout/stderr and commands in validation JSON |
| `generation/validate_interface.py` | Exact offered public contract checkpoint `63a14cafa1dee7db7cb70aca00cee529c46452fc`: twelve schemas, three paired-family checks and six control-mapper support checks passed | `evidence/interface-r1/result.json` plus byte-exact public interface checkpoint source |
| `generation/inventory.py --out inventory/sha256-r1.json` | 108 committed files verified against local Git bytes and hashed | Complete inventory plus subsequent inventory receipt |
| Public projection audit | All 108 inventory entries and 48 artifact descriptors match; public inventory copy byte-exact; permitted metadata scope | Public `verification.json` |
| Authority versus public candidate Git tree comparison | All 2,704 original paths/modes/types/blobs unchanged; exactly three initial owned reservation additions | Same public audit |
| Git staged whitespace checks and normal owned pushes | Passed; exact origin observed for early reservation and evidence | Tool observations and final handoff |

No generation or validation failure occurred and no corpus correction was made before independent admission. Harmless source-discovery probes for two absent filenames were corrected by listing the actual existing mapping_v1 module paths before implementation; no source or execution was changed by those probes.

Not run: actual OCR/model inference, GPU, service, download/package setup, quality treatments or product integration. No actual diagnostic inference result is claimed. Public contract compatibility is distinct from independently accepting the final diagnostic source/protocol.

## Independent admission and handoff

The [independent /004 report](https://github.com/jackgumpe/eledgercare/blob/021dc265790c90ae83f1afa24fc3f2a71eae41e1/docs/agent-reports/eld-mapping-reviewer/WP-0011/004_2026-11-17_review_eld-mapping-reviewer.md) accepted exact sealed receipt `6583715067d3a027dd2502ed9623cf02c545391d` and core `b5f33a65d463d4b9a5463fdb93353c0c7ac7c7f3`. It independently inspected all twelve actual rendered pages and complete source/expected/reference/annotation records, passed 17/17 audit groups, reproduced all 70 corpus files byte-identically, and passed six control mapper-support checks. No blocking corpus finding or correction remained. Reviewer reference coverage counted 484 text runs.

The reviewer authored its own helpers and evidence and did not author corpus or diagnostic implementation. Its deliverable is `0979750ed48e686cc41854b7f14c1338a356f852`, public inventory `832645cfa2be0069c95fed58d618ede0a45f5008`, final private receipt `a9a7ca6ae1b2d0e8536e00c190accd520b2a75ee`, private inventory SHA256 `e04cc2ef8d006d27b708efd03b7be749851fc85ff980b94c6b227a669da4f3ef` (27 entries plus inventory). Its initial image-display and public CRLF inventory-packaging failures are retained in the independent record; neither changed corpus facts or admission findings. The custodian did not copy identifying reviewer evidence into public files.

Root's [exact acceptance audit](https://github.com/jackgumpe/eledgercare/blob/4f599cbf9e3deb6ca39473c4c080e17771ed2b78/docs/coordination/WP-0011/admission-acceptance-audit.json) verified ten public artifacts in both Git and working bytes, 27 private entries plus inventory, 2,724 preserved reviewer base paths, exact-origin/report-only publication and unchanged sealed receipt. Root released this final /003 under `4f599cbf9e3deb6ca39473c4c080e17771ed2b78`. That identity audit is separate from the independent reviewer's semantic/render checks.

The [separate admission binding](../../../evaluation/WP-0011/reservation/admission.json) records the immutable disposition without replacing the original [reservation](../../../evaluation/WP-0011/reservation/reservation.json), [inventory](../../../evaluation/WP-0011/reservation/sealed-inventory.json) or early status. The [public verification receipt](../../../evaluation/WP-0011/reservation/verification.json) retains the exact protected-file/hash audit. From original authority through this report, all six author additions are the five reservation files enumerated above plus canonical /003.

The author later froze a public diagnostic source candidate with stricter quantity_unit presence/value and absence label/state checks. The admitted metadata is compatible with those stated constraints; custodian execution evidence accurately remains bound to offered interface checkpoint `63a14cafa1dee7db7cb70aca00cee529c46452fc`. Final source/protocol acceptance belongs to separate independent /002. No final diagnostic source acceptance or fresh inference is claimed by this corpus report.

Procedural sealing remains in force. Root must bind accepted diagnostic source/scoring/protocol and exact unseal before content access or reserved /008 unchanged corpus publication. Later finite runtime requires separate exact input/source/protocol/sole-lease authority. Earlier reservation files and sealed receipts remain immutable; later publication is documented separately.

This report cannot contain its own commit SHA. Normal owned push, exact-origin confirmation, report-only delta and final clean states are supplied to root in the handoff after publication.
