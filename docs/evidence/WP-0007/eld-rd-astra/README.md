# WP-0007 /002 CPU author evidence

Final reviewed candidate offered to /003: `a998b765f7734453d27ec4a189a2156778f0913d`; base `c08d50e204395e60a88ce25f70e25bd29b97b8c6`.

- `a998b765/checks.json`: final 25-test run, dev checks, exact process argv/exit codes, audit of actual corpus file opens and output hashes. All checks passed. The audit observed 18 distinct synthetic files, all authorized dev paths, with zero holdout/unexpected paths.
- `a998b765/dev/`: 13-document dev reference inventory plus prediction/reference/score records for only the two existing Q0 F01/F07 clean outputs. `audit-dev/` is the same CPU exercise with an audit hook; no new model output.
- `4461eac2/`: preceding successful frozen-candidate check/evidence, preserved before explicit mapping-coverage refinement.
- `8cd389e9/dev/`: first frozen candidate's retrospective dev output, preserved. Its initial 25-test pass was observed in tool output; no transcript file is claimed for that initial run.
- `publication-inventory.json`: complete candidate/evidence path inventory and identities, excluding itself to avoid self-reference. Canonical /002 report is committed separately afterward.

F01 retrospective exact fields 15/15, cells 18/19; F07 fields 13/15, cells 72/180. F07 maps only 72/180 cells because later native table headers differ from the frozen exact-header rule; 12 expected rows remain unmapped and all 180 cells stay in the denominator. Per-document mapping coverage/reasons/unclassified content distinguish this mapper limitation from raw lexical text errors. These are CPU scorer diagnostics on accepted Q0 dev outputs, **not the new 26-document baseline or a character-accuracy claim**. Document text alignment uses the documented spatial reference and SequenceMatcher token alignment; native column-order differences count as sequence errors.

The CPU Windows job test launched and terminated only its owned sleeping Python child, without runtime/model imports. No baseline runtime root was created, GPU lease requested, model loaded, package installed, customer data accessed or holdout content read. Tests of timeout/storage/release logic are CPU boundary checks, not observed CUDA execution. Model/GPU behavior and the unexecuted runner need independent /003 acceptance and a later exact coordinator release.

Evidence bytes are preserved with local `-text -whitespace` attributes, so original subprocess CRLF output and hashes survive Git publication. Original Q0 core/evidence, admitted corpus, product and shared routing remain unchanged. Source diff check passed; candidate inventory consists only of 13 new `qualification/baseline/**` paths.
