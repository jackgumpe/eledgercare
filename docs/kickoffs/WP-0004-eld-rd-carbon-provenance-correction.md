# WP-0004 / 007: Correct the renderer wheel checksum

Status: PREPARED / HELD until the current /004 turn ends and the actual completed publication is bound below. No concurrent turn in the author worktree.

- Owner: eld-rd-carbon, agy.exe gemini-4-carbon-high / high; continue author conversation 993d4f08-72d0-479c-9e6c-047280cedf95 after it ends. This remains authorship, not independent review.
- Repository: https://github.com/jackgumpe/eledgercare, private.
- Branch/worktree: research/wp-0004-carbon-recovery; C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-rd-carbon-recovery.
- Full execution base: UNBOUND completed /004 publication.
- Prior frozen candidate: fca8f16e51359d6895dca27a05fe76af82f58ff4; prior evidence: 1ef33dcddf324a6a48285a6e302af5d1528b3c34.
- Reservation: INDEX.md WP-0004 /007 at the supplied release.
- Exact report: docs/agent-reports/eld-rd-carbon/WP-0004/007_2026-11-14_research_eld-rd-carbon.md.
- Next reviewer: uninvolved Opus, eld-rd-reviewer /005, on the final corrected candidate/publication.

Read the authoritative reservation and docs/coordination/WP-0004-provenance-preflight.md from the supplied coordinator release, using git show rather than merging coordinator files. Rehash all three own immutable wheel archives and correct the truncated 55-character pypdfium2 SHA-256 in evaluation/manifests/tooling-provenance.json to the value actually measured from its 4,187,589 bytes. The coordinator measured 74d1bace34fb01c660d0b64344d5a4b7d276942b7c6623c88ab59ea21c5acfbd; verify independently before using it.

Allowed tracked effects: change only that erroneous manifest hash, add compact new evaluation/manifests/provenance-correction-verification.json, and add the exact /007 report. Keep all corpus PDFs, sources, expectations, generation scripts, backlog, prior evidence and published reports identical. Do not rewrite /004. No INDEX/CURRENT, other worktrees, product code, services, package/global setup, model/GPU work or additional agents.

Commit the one-field metadata correction first. Verify three actual wheel sizes and full SHA-256 values against the corrected candidate; record commands, values, exact candidate/base and a Git comparison proving all corpus/backlog files and historical reports unchanged. Then commit new evidence and the short canonical /007 report separately. Do not regenerate or visually recheck forty unchanged pages for this metadata-only correction; attribute unchanged prior runs honestly. Normal push only the owned branch, verify exact origin, and return candidate/evidence/report SHAs and the three-path inventory. A new independent R&D acceptance has not yet occurred.
