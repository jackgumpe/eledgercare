# Preserved reviewer publication attempt

The first inventory command was executed as a Python stdin script at public HEAD `7aa66058c79e19a677b1d0e719a7f48813f97ec6`. Its exact Python text is retained as `inventory-attempt-1.py`; the file was saved after execution for preservation, not represented as a pre-execution freeze. The observed tool chunk `1c355b` returned:

```text
Traceback (most recent call last):
  File "<stdin>", line 11, in <module>
AssertionError
fatal: pathspec 'docs/reviews/WP-0011/eld-mapping-reviewer/admission/public-inventory.json' did not match any files
On branch review/wp-0011-coverage
Your branch is ahead of 'origin/review/wp-0011-coverage' by 13 commits.
  (use "git push" to publish your local commits)

nothing to commit, working tree clean
7aa66058c79e19a677b1d0e719a7f48813f97ec6
```

The shell's final command returned zero although the Python assertion failed; this is recorded as a failed inventory attempt. No inventory file or commit was created. This block transcribes observed tool output and does not claim that an original failure stdout file existed.

Inspection in tool chunk `b6116c` established the exact cause: `verification-attempt-1.log` had two CRLF sequences on disk while its committed Git blob had LF. The other four files were byte-identical. All five working files matched their Git-filter blob identities. This is normal repository text conversion, not altered verification content. `verification-attempt-1-original.log` preserves the original on-disk log bytes under a narrowly scoped `-text` attribute; the original tracked log stays unchanged.

The corrected helper `inventory_v2.py` is frozen before its affected publication check. It inventories committed bytes as the publication authority and separately records working-file size/SHA and Git-filter parity. It rejects uncommitted content differences. This correction changes only reviewer packaging; the frozen source/corpus and all completed semantic/visual checks remain unchanged. No inference or scoring was rerun. Private evidence already used byte-preserving attributes and is unaffected.
