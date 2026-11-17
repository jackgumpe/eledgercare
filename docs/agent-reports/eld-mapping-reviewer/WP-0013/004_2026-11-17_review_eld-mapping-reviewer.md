# WP-0013 /004: independent admission of the sealed finite corpus

- Report path: `docs/agent-reports/eld-mapping-reviewer/WP-0013/004_2026-11-17_review_eld-mapping-reviewer.md`.
- Sequence reservation: `47fbc7612e4a08cf1960ad7ac01bd2843ae645e5:INDEX.md`.
- Category: review.
- Author / agent ID: eld-mapping-reviewer, stable native `/root/mapping_reviewer`; independent of the corpus and mapping authors; no subagents.
- Actual model / effort: not exposed; continuing the user-requested xhigh session.
- Execution environment: Windows PowerShell; existing Python environment, pypdf 7.1.0, pypdfium2 5.15.2, Pillow 13.0.0; CPU only.
- Published by: reviewer.
- Timestamp: 2026-11-17T15:07:00Z.
- Repository / branch: `https://github.com/jackgumpe/eledgercare.git`, `review/wp-0013-vocabulary`.
- Owned worktree: `C:/Users/jackg/Asp.net Projects/eledgercare-worktrees/eld-vocabulary-reviewer`.
- Initial clean reviewer revision: `bb66c7261339a1e5b36a826e949b1eb6f8d62cd8`.
- Actual clean admission start: `bddb01f715b1f76745acdcd2a64cdc070fd41f43`, 2026-11-17T14:50:51.9214018Z.
- Final authority / public deliverable base: `ad7309f2079ed11bc4a63e52567e6a1e5fba1868`.
- Accepted protocol source: `6207daf1dc9cbdd141d083ca2d8d1e7507c63b09`; tree `e424945507bb1d7ebf70e18e6d26bf808270bb66`.
- Reviewed public reservation: `b50b2a3bc22927890c8f391943f2a3fe9168d0da`; SHA256 `533f4be35fb89efd9e288c0470201457b5ab32373eab3112ae283b42febcfea5`.
- Core manifest SHA256: `91c4a38adeef4ceb2c3fb399eac525e141e4821e9a7dcdf0fb82803e89b86319`.
- Final custody inventory SHA256: `bfb7b818ced3992a28bff3dd7968ac5003b3c47367589817b99c5c2d74039ea0`.
- Independent private evidence inventory SHA256: `7b6fec8e91cd5b3ee2b7d8ddf13cd47f6edab7746a47dfd567741b802830c180`; exact private revisions and locations delivered only to root/custodian.
- Public deliverable / inventory helper freeze: `efbe182ae403b57cd2a790165681ab59a6bc8a69`.
- Public inventory metadata revision: `98afd35966d00942af6a2d0ad198ed2b127c7901`.
- Public inventory SHA256: `99daeefa1507ff6d4664ca71dbcc7df78e14e5105da73acbf866d4fcf3f5529e`.
- Previous report: [independent protocol /002](002_2026-11-17_review_eld-mapping-reviewer.md).
- Related input: [complete public reservation](../../../evaluation/WP-0013/reservation/reservation.json); custodian canonical /003 remains subsequent.
- Status: accepted, exact corpus admission only.
- Next owner: root for binding this independent disposition, then custodian for canonical /003.

## Summary

Accept the exact sealed reservation for the finite WP-0013 evaluation.
Independent execution passed all 50 CPU check groups; the reviewer actually
inspected all 12 full-size rendered pages. The separate final custody audit
verified 120 files / 5,270,705 bytes, all 48 public descriptors and preservation
of all 116 earlier private objects. No corpus blocker was established.

This report publishes hashes, counts and disposition only. Detailed specimens,
truth, private source bindings, helpers and observations stay sealed. The
[dossier](../../../reviews/WP-0013/eld-mapping-reviewer/admission/README.md) and
[public receipt](../../../reviews/WP-0013/eld-mapping-reviewer/admission/receipt.json)
bind the independently preserved evidence without disclosing those contents.

## Objective and acceptance criteria

The [admission kickoff](../../../kickoffs/WP-0013-eld-mapping-reviewer-corpus-admission.md)
requires independent inspection of every original, exact accepted-contract
validation, grounded truth/reference/policy records, family relationships and
custody preservation. The [final root release](../../../coordination/WP-0013/final-reservation-release.json)
released canonical /004 after the complete reservation was bound.

The reviewer inspected actual source and evidence, independently extracted PDF
text/geometry and rendered original bytes, and checked the accepted public
contract. Custodian generation, verification and regeneration claims remain
attributed to the custodian; they are not substituted for these independent checks.

## Change inventory

All 3,720 paths at the final public base are unchanged. The
[complete public inventory](../../../reviews/WP-0013/eld-mapping-reviewer/admission/deliverable-inventory.json)
accounts for four additions under
`docs/reviews/WP-0013/eld-mapping-reviewer/admission/`:

| Added path | Purpose |
| --- | --- |
| `.gitattributes` | Preserve the dossier's exact bytes. |
| `README.md` | Bounded independent disposition and evidence limits. |
| `receipt.json` | Nonrevealing hashes, counts and actual execution status. |
| `inventory_public.py` | Frozen public identity/preservation verifier; no private access. |

The inventory and its tool receipt are two subsequent metadata additions at
98afd35966d00942af6a2d0ad198ed2b127c7901. This canonical report follows them.

The owned private local/no-remote evidence repository contains 35 inventoried
deliverable files plus its inventory and execution receipt: 37 total files /
3,708,890 bytes. It preserves independent helpers, all twelve renders, all
per-document observations, actual receipts and the visual inspection record.
Original corpus/source files were read only. No shared routing, prior report,
model/service resource or reviewed source changed.

## Verification and decisions

| Actual check | Result | Immutable evidence binding |
| --- | --- | --- |
| Frozen private `admit.py --out attempt-1`, existing Python with `-I -B` | Exit 0; all 50 groups passed on the first semantic execution. | Receipt SHA256 `83833b038d6e264858cf5314017b45b02cff82dfb133e3e8a41b399120a3c9f5`. |
| Frozen private `custody_audit.py final --out final-custody-audit-1.json` | Exit 0; all 120 final files and 48 public descriptors verified. | Audit SHA256 `358f7166d230ac91cc3f673b4fd1092703fb2de8cd9a8bca4b870c233bfb87f1`. |
| `view_image` on all twelve independently rendered original pages | All twelve actually inspected; admission passes. | Visual record SHA256 `ccdf3af1b4197acd0aa45ff0131cd7cb4c8d9d25420cb6c2506726cf178bae2c`. |
| Frozen private `custody_audit.py inventory` on the clean private deliverable | Exit 0; 35 files / 3,698,029 bytes, exact Git/working bytes. | Private inventory SHA256 above; two later metadata files separately bound in the public receipt. |
| Frozen public `inventory_public.py --candidate efbe182ae403b57cd2a790165681ab59a6bc8a69 --out .../deliverable-inventory.json` | Exit 0; four additions, 3,720 unchanged prior paths, exact public reservation/counts/protocol tree. | [Actual inventory tool receipt](../../../reviews/WP-0013/eld-mapping-reviewer/admission/inventory-receipt.json). |
| `git diff --cached --check` | Passed before owned commits. | Private/public commit sequences. |

Semantic execution was 2026-11-17T14:57:40.980464Z–14:57:58.540802Z at the
privately bound final helper freeze. The receipt retains 77 public source
identities and complete actual private input identities. Full commands, launch
session and observed tool outputs remain in private tool receipts, SHA256
`83eb49be18fe1d3c0845b284baab509f1115ee997f77729f56ad9ddda7c5b089`.
Private helper/source revisions were fixed before decisive checks.

All original-render, reference/policy and paired-family admission criteria pass.
Unknown or ambiguous truth remains unjudged under the accepted contract, and
known-cell row-score limitations remain unchanged. Detailed opportunity counts
and case findings remain private; no fresh-example treatment advice was given.

## Failures, limitations and unfinished work

No semantic or custody check failed. Preserved reviewer preparation incidents
comprise a corrected initial repository-location setup, a failed read-only
path lookup, and a pre-execution helper refinement. The initial helper was
never executed; the corrected helper was frozen before the first decisive
checks. No input mutation or discarded semantic attempt resulted.

The independent direct render used the same pinned PDFium version; this is
not a different-renderer test. Automated geometry establishes text-baseline
containment, supplemented by actual visual inspection for clipping/legibility.
It is not a proof about every glyph pixel or every possible renderer.

There are four factual/template families with three paired conditions each,
not twelve independent families. The finite one-page corpus cannot establish
general accuracy or exhaustive guard coverage. No mapper, model inference,
live process/GPU observer, service, dependency installation or download ran.
The reviewer did not regenerate custodian files.

## Review map and handoff

[Public base-to-deliverable diff](https://github.com/jackgumpe/eledgercare/compare/ad7309f2079ed11bc4a63e52567e6a1e5fba1868...efbe182ae403b57cd2a790165681ab59a6bc8a69)
contains only the four inventoried public admission artifacts. Root/custodian
have the exact private evidence mapping and can audit it against the opaque
hashes above.

Root may bind this corpus admission and release custodian /003 final reporting.
Implementation /005 and independent source /006 remain separate work. Explicit
root unseal and exact finite runtime/sole-lease gates still apply; product keeps
first GPU priority. The preselected sentinel is unchanged. Admission does not
establish implemented guard enforcement, OCR quality or product promotion.

Publication receipt: the public deliverable and inventory precede this report.
Normal owned push, final report-only diff and exact-origin/clean checks follow.
The resulting publication SHA is sent to root without rewriting this report.
