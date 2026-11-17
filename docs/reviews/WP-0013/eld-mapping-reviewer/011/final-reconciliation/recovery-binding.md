# Recovery /012 additive comparison binding

`008/compare_published_recovery012.py` is copied from the immutable original /007
compatibility helper with exactly four replacements: source revision to
`ae790497f3fdd10573e8179757416bc2d1736250`; source tree to
`8fd68c96bb18ca0177f227ad9a82505090d997b0`; runtime protocol SHA256 to
`ef648a3cd52df16ed6ed352e666ffedf789148100d640e2582cf13f76b6f9783`; and the run-prefix
binding. The latter admits only exact author `/012/evidence/attempt-1/run` and
reviewer `/008/results/attempt-1/run` paths under their own identities. Full paths
are fixed in the helper and control test; general research/evidence/review prefixes
are not accepted by this version.

All remaining bytes, including scoring, comparison, input/proof authentication,
denominators, failure semantics, sentinel and corpus pins, remain identical.
Both earlier helpers and the original failed /007 comparison stay immutable.
Four controls execute the actual parsed path guard and prove the complete byte
delta plus accepted/nearby-invalid paths. No recovery packet or model output has
been read or produced by preparation.

Freeze this helper and controls before testing. Actual /012 and reviewer
comparison require later immutable root specs, new release/unseal proofs and
their own actual execution records. A newly bound `releases/author.json` is read
only from the future exact authority; original authority6558c3d7 remains historical.
This binding does not release inference and does not overwrite the twelve
unavailable original /007 primaries. Final canonical /008 will keep original,
recovery and sentinel evidence separate.
