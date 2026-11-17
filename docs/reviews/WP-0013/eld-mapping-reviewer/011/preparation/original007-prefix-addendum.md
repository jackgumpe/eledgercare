# Original /007 comparison publication-path compatibility

Root's explicit bounded follow-up identified that authorized author /007 publishes
under `docs/research/WP-0013/eld-mapping-author/007/evidence/attempt-1/run`, while
the original frozen comparison helper allowed only evidence/review prefixes.

The additive `008/compare_published_original007_v2.py` changes exactly one guard
expression: that exact research path is also allowed when owner is `author`.
The original helper remains byte-identical. All source/protocol/corpus pins,
comparison and scoring logic, authentication, inventories and output guards remain
identical. Other research owners, sequences, attempts and descendants are rejected.
This is a publication-path compatibility correction, not an accepted result.

Freeze both helper and test before running `test_original007_prefix.py`. Four test
groups execute the actual helper's parsed `safe`, `require` and prefix statements,
prove the entire remainder byte-identical, demonstrate the original rejection and
new exact-path acceptance, and reject nearby unauthorized or unsafe paths. These
tests intentionally stop at the path boundary; they do not claim an authenticated
actual packet has been read. Root supplies the immutable /007 normalized spec later.

Original /007 must still be compared on the original accepted source before any
corrected runtime merge. Later /012 and sentinel require a separately authorized
additive helper with exact corrected source bindings, preserving original results.

Pre-freeze staging incident: two new preparation files were initially written to
owned worktree `011/preparation` instead of the intended documentation directory.
Tool 6e12b3 reported `pathspec ... did not match any files` and no commit was made
(its final rev-parse returned shell exit 0). Both original file bytes were moved
within the verified owned worktree to the intended paths before freezing or tests.
No reviewed source or prior evidence changed.
