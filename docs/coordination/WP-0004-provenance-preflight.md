# R&D publication preflight: truncated renderer wheel checksum

Coordinator observation, 2026-11-14. This is a mechanical publication check, not the required uninvolved R&D review. Carbon's original /004 continuation is still active; no concurrent turn or edit in its owned worktree is authorized by this note.

At frozen candidate fca8f16e51359d6895dca27a05fe76af82f58ff4, `evaluation/manifests/tooling-provenance.json` records the pypdfium2 wheel SHA-256 as the following **55-character** value:

`74d1bace34fb01c660d0b64344d5a4b7c6623c88ab59ea21c5acfbd`

The coordinator read the actual immutable wheel at `eledgercare-worktrees/eld-rd-carbon-recovery/.scratch/wheels/pypdfium2-5.15.2-py3-none-win_amd64.whl` and independently ran `Get-FileHash -Algorithm SHA256`: **4,187,589 bytes**, correct full SHA-256:

`74d1bace34fb01c660d0b64344d5a4b7d276942b7c6623c88ab59ea21c5acfbd`

The original checkpoint 8fb7e3ca537b1710fe231dad0cf5d177c6e5d733 has the complete value; the truncation was introduced in the fresh author continuation. The other two wheel hashes were also recomputed and match their recorded 64-character values:

| Wheel | Bytes | SHA-256 |
| --- | --- | --- |
| pillow-13.0.0-cp312-cp312-win_amd64.whl | 7,272,166 | ff3fe9eb621fbb9db4c4be33ab946f6bac5f98ab50ca8d3260503653656c961b |
| pypdf-7.1.0-py3-none-any.whl | 418,698 | 47cca6b24bdcf4c4d65b5f7b8b972535c61710a061261e737688777cfd9a7bfb |

Next action after the current author turn ends: bind a short responsible-author correction to its actual completed base, fix the manifest from observed bytes, publish focused evidence for all three hashes, and verify no corpus/source/generator/backlog content changes. Preserve any already published /004 report and reserve a new sequence if needed. Do not repeat the forty-page visual run merely for a checksum transcription correction. Bind Opus /005 to the final corrected candidate and report lineage, then perform the full independent corpus/backlog review.
