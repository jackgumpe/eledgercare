# WP13 guarded vocabulary proposal

Current phase: public protocol /001 only. No mapping_v2 extractor or runtime
exists. Implementation /005 requires root's exact binding of accepted /002 plus
fresh final reserved bytes. Independent /006 must accept implementation before
unseal and any later finite model release. Historical code and data remain intact.

The proposed treatment is defined by [policy](protocol/POLICY.md), finite
[catalog](protocol/catalog.json) and [machine protocol](protocol/protocol.json).
The [reference interface](protocol/INTERFACE.md) and `contract.py` separate known
original ground truth from ambiguous/unknown full policy opportunities.
`scoring.py` invokes unchanged B0/v1 scoring and counts actual output candidates
independently. It does not extract values or alter aliases in native output.

Run the CPU checks only after committing the exact source/helpers:

```
python -I -B qualification/mapping_v2/protocol/run_checks.py --out docs/research/WP-0013/eld-mapping-author/001/evidence/attempt-N
```

The runner blocks model/renderer imports, requires a clean worktree, retains each
attempt in a new directory, checks the finite catalog/protocol/reference/scoring
counterexamples, and reproduces unchanged predictions/full scores on all twelve
exposed WP11 outputs. Later implementation must additionally exercise actual
native association/suppression guards and full historical regression; passing
these protocol tests is not evidence that an unimplemented mapper works.

`protocol/cli.py validate` validates authorized reference-side objects.
`score-policy` accepts an independently supplied prediction and cannot call a
model or v2 mapper. A custodian/reviewer may use it on their separately authorized
sealed material; the author must not access that material before root unseal.

No fresh evaluation results, expected gains or product promotion are claimed.
Guarded v2 may lose original first-candidate credits to reduce unsafe assignments.
Same-output gains, losses, neutral results and unavailable cases all remain.
