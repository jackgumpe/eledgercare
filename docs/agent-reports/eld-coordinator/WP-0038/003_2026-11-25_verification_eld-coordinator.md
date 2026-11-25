# WP-0038 /003 · D5.3 synthetic arithmetic ambiguity disposition

**Accepted for the released exact-cent synthetic comparison.** Both independently implemented routes returned the same complete signed explanation set for every grid and named observation. Of 288 grid cases, 212 admitted more than one explanation. Seven admitted infinitely many. The result supports preserving ambiguity when diagnosing a ledger. It provides no estimate of physical-ledger fault incidence, OCR repair accuracy or the benefit of applying a correction.

- Author and publisher: eld-coordinator, local Codex thread 01a20a53-eec1-72c1-864c-9f8be8f4aff5. Accepted root launch gpt-6.2-astra/xhigh.
- Category and report: verification, docs/agent-reports/eld-coordinator/WP-0038/003_2026-11-25_verification_eld-coordinator.md
- UTC: 2026-11-25T07:44:02.361964+00:00. Repository jackgumpe/eledgercare, coordination/bootstrap, primary eledgercare worktree.
- Accepted predecessor 40fc3f97f6558123fe9b537583a79c27bb315266, assignment and reservation 0e31fd950c48a6548d19595b2cec326ce79021fe. Evaluator and fixture publication bd1ce0964e510c14ff7398ac452dbe48639962d8. Scored results 843fe0aad3a04025c8a18553c8e9b9f3d5abf19d. Inspected integrated revision 86e1f7576a0dfdf464050c9e2cd7d8a5228af640.
- Related records: [Route 1 author /001](../../eld-owner-probe/WP-0038/001_2026-11-25_research_eld-owner-probe.md) and [independent reviewer /002](../../eld-rd-reviewer/WP-0038/002_2026-11-25_review_eld-rd-reviewer.md). Previous disposition WP-0036 /003. Status accepted and closed. Final action by eld-coordinator is the public byte receipt.

## Decision and population

I verified all six pages of advisory edition 03, November 25, SHA-256 fcdf926d8474b4e67fd9266d0083b43cad967b3671eda5427ba9d47b348e204d. Jack requested a local release decision under the standing synthetic research authority. I released the finite D5.3/D5.4 packet under WP-0038. WP-0037 retains the GPU roadmap designation. The confidence, training, directory-metric and reread proposals on page six stay deferred. [Release contract](../../../coordination/WP-0038/assignment.md)

Each route processed **6 clean controls, 33 single-cell injections and 249 two-cell injections** across six grid strata. All injected explanations and clean controls appeared in the returned sets. The two routes also processed **11 named assertions as 20 domain-specific calls**. Eighteen were admitted and two failed the external anchor guard. Eleven of those 20 observations also occur in the grid. The two denominators remain separate. [Every grid observation, truth, signed support/family and time](../../../coordination/WP-0038/results/grid.jsonl) · [Every named result and grid overlap](../../../coordination/WP-0038/results/named.jsonl)

| Body rows | Opening domain | Grid size | Unique | Multiple finite | Infinite family present |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | OCR-read | 23 | 0 | 16 | 7 |
| 1 | Trusted | 13 | 1 | 12 | 0 |
| 2 | OCR-read | 52 | 4 | 48 | 0 |
| 2 | Trusted | 36 | 9 | 27 | 0 |
| 3 | OCR-read | 93 | 33 | 60 | 0 |
| 3 | Trusted | 71 | 29 | 42 | 0 |
| **All** | | **288** | **76** | **205** | **7** |

## One-row oracle and named regressions

All five one-row oracle regimes occurred in both opening domains. The 23 OCR-read grid cases had counts 2, 5, 3, 3 and 10 for (r,D) both zero, row-only, total-only, opposite nonzero, and generic respectively. The 13 trusted cases had counts 1, 2, 2, 2 and 6. Every oracle check compared the empty-support flag, all signed finite supports, and the exact integer parameter family with its exclusions. Neither route applied a repair. Across the grid the returns held 661 nonempty finite hypotheses, seven clean hypotheses and seven symbolic families. One genuinely injected common shift also admits clean. Of the 288 generating explanations, 6 matched clean, 279 matched a listed finite hypothesis and 3 were represented only through affine-family membership.

- C1's OCR-read observation admits both clean and (B0,B1)=(c,c) for every nonzero integer c, including the injected +6. A consistent trusted opening and zero residual admit clean alone. C1's actual 106 reading against external 100 is rejected before solving, with null discrepancies and zero candidates.
- At C2 with r=6 and D=0, the OCR-read alternatives include B0=−6, B1=+6, (A1,T)=(−6,−6), and (B0,B1)=(c−6,c) for every integer c except 0 and 6. The trusted regime retains B1=+6 and the (A1,T) pair.
- At C9a, (r,D)=(−16,+6) gives (A1,B0)=(6,10), (A1,B1)=(6,−10), (A1,T)=(16,10), (B0,T)=(16,−6) and (B1,T)=(−16,−6). C9b, outside the grid, retains the three pairs without B0. C9c rejects observed opening 110 against trusted 100 before residual calculation, also with zero candidates. Where the two implementations returned a rejection, both set solve_skipped and returned no clean, finite or affine explanation.
- All C3–C8 support identities and signed coefficients agreed with the table in the brief in both domains. Each record in the [named results](../../../coordination/WP-0038/results/named.jsonl) retains the observed inputs, residual fields, exact hypotheses, injected truth, grid membership and per-route elapsed nanoseconds.

## Why these routes are independent

The author enumerated exact supports and solved their residual equations over the integers. A unit pivot expresses the first coefficient as an affine function of the second. Remaining rows either determine a single consistent integer parameter, contradict the support, or leave the parameter free. Zero coefficients are removed by exact-support checks. The independent reviewer reconstructed true ledger values by propagating balance differences along edges for the observed cells outside each candidate support. Contradictory paths eliminate a completion. A disconnected component allows a common shift, giving the symbolic endpoint family. For n≥2 the amounts and total form a rim cycle in the reconstruction graph, with a balance-reading spoke from the monetary origin to each rim vertex. Removing two edges cannot disconnect it. Removing both endpoint readings can disconnect the one-row OCR graph. I inspected these conditions against the reviewer’s code and reconciled its outputs to the independent support solver. The only data passed into either solve function were the observed amount, balance and total readings in cents, opening domain and external anchor. The fixture generator, injection coordinates, base truth, oracle and ordering join were withheld from both solvers. The fixture design itself is public.

D5.3 follows from the incidence structure of the residual columns. In the simple graph cases a nonzero circulation supported on at most four edges is confined to a triangle or four-cycle with a single signed multiplier. For one OCR-read row the full zero-residual difference is (t,s,s+t,t) in (A1,B0,B1,T) order. The parallel endpoint columns allow a two-cell common shift and the four-cell kernel can have two independent integer parameters. Fixing B0 removes that freedom. On exact two-cell endpoint support for an observed r, the canonical family has (B0,B1)=(c−r,c), c in the integers excluding 0 and r. D5.4's bijection subtracts a supported signed error from the observation to obtain a balanced true ledger; subtraction in the opposite direction recovers the exact error. Both directions preserve support and the verified external anchor.

## Execution, exceptions and review

| Record | Full revision |
| --- | --- |
| Support equations, independent freeze, author publication | e6cc29548480c8d6c0e364b6cab7e1a39528e6e4 / 5dfb081694470a3d6a681fefe07e6bebcb441f98 / 4dee32e61ef23463f703020de3bf3c9ebd0978a0 |
| Balanced-ledger reconstruction, independent freeze, review publication | 779d0cf4e27e7fafa0b7b4b727b136a2481f90e4 / 5d55b11cd9b26369199a3944e533c108010f2311 / 1d0b2c58498556651d88f781ec45ddf61b2c5f45 |
| Shared driver and pre-unblinding scoring digest | 3494da54b614e0bf6b5ce779c279d4fae457c483 / 246882bfd338487cbfc6d2e4a22621135839c9a4 |

The two original fresh Codex turns recorded an interruption before any source commit or CPU lease. I verified the empty worker evidence directories, preserved the draft driver and input batch, resumed the same thread IDs, and ran each frozen candidate once on a serial lane. The Codex turn metadata for each role records gpt-6.2-astra and xhigh. [Thread IDs, exact argv, source blobs, input digest and nonoverlapping leases](../../../coordination/WP-0038/dispatch.json)

Both runs used isolated Python 3.12.10 with its standard library and measured perf-counter time. Over all 308 calls, summed solver time was **13.7560 ms** for support equations and **31.5212 ms** for reconstruction. Timed batch wall time, including result serialization and writes, was **16.9085 ms** and **34.9268 ms**, respectively. Grid-only median solver calls were 48.50 and 111.95 microseconds. These are single executions on this host. The raw timing files intentionally differ; the canonical signed results agree. [Timing distributions and frozen evidence hashes](../../../coordination/WP-0038/results/summary.json)

There were **zero runtime exceptions, zero incompatible answers on released inputs and zero signed-output disagreements**. The two guard rejections were expected domain results. Outside the declared schema the routes have different validation behavior. In particular the support route checks the domain and balance count, while the reconstruction route assumes a valid domain and shape. The packet defines only integer cents and the two named domains. It defines no literal-input adapter or off-contract coercion. The earlier validator returns discrepancies as (D,rho) and parses printed major-unit strings; the current solver uses named fields and exact cents. No historical outputs or source were changed.

## Publication and preservation

Changes since the predecessor are limited to INDEX.md, CURRENT.md and the WP-0038 role, coordinator, evidence and canonical report paths. Each worker committed the candidate and raw evidence before its own report. The reviewer inspected actual solver, driver and scoring sources and reproduced the keyed scores from the two publicly pinned evidence objects. The coordinator compared the returned signed hypotheses, checked exact affine domains, reconstructed finite candidates, joined the known injections and reconciled every named expectation. [Evaluator](../../../coordination/WP-0038/score.py) · [Inputs and order](../../../coordination/WP-0038/fixtures.py)

The dirty primary web/package.json retains SHA-256 6af72a0583bf4a640633ac17b0cc3e9adc83a5f4df12d09b01ae70dcec0546e0; stash@{0} remains bcc4b085be6b5f2c64bca52443f410398db15aa1. All 108 pre-existing worktree bindings were preserved, and the pre-existing 73 working-file identities matched by path, size, file identity and modification time. The two new worktrees are retained. The final receipt verifies public bytes, branch ancestry and report identities. [Integrity evidence](../../../coordination/WP-0038/integrity.json) · [Public verifier](../../../coordination/WP-0038/verify_publication.py)
