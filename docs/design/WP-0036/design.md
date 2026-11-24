# WP-0036 `/004` Design Memorandum: Constructive Specifications, Counterexamples, and Anti-False-Positive Gates
**Author:** `eld-pgda-neon` (Gemini Neon) | **Base:** `7643bb9b26d15c9d435234e9d3a5d11b742dc771`

## 1. Component E: Byte Digest Contract, No-Write `t_post`, and E4 Revision

**Canonical Digest Layout.** Each frame `f∈{0..7}` owns 50 independent slots (`[0..1]` owner/unit, `[2..33]` column, `[34..49]` summary). Serialize slot `s` as little-endian bytes: `[u16 slot_idx, u8 vec_valid, u8 decl_valid, u32[128] vec_bits, u32 conf_bits, u32 text_len, u8[text_len] text_utf8]`. Reject non-finite binary32 (`NaN`, `±Inf`); hash raw `u32` bits so `-0.0/+0.0` flips fail equality. Force `conf_bits=0, text_len=0` when `decl_valid=0`; require `conf∈[0,1]` and valid UTF-8 when `1`. Zero all 50 slots on frame push/pop so reused depths cannot leak stale `vec_valid=1` (replacing first-write `gain=1` with sigmoid) or stale text. Emit per-frame hashes:
`D_decl(f)=SHA256("E_DECL_V1"||u8(f)||rec(f,0..33))`, `D_sum(f)=SHA256("E_SUM_V1"||u8(f)||rec(f,34..49))`, `D_frame(f)=SHA256("E_FRM_V1"||D_decl(f)||D_sum(f))`.

**No-Write `t_post` (E3).** Snapshot `t_pre` pre-push and `t_post` post-pop/summary with zero root declaration writes. Require: `D_decl(0,t_post)==D_decl(0,t_pre)` unconditionally (even when pop writes `frame[0].summary`), `D_frame(0,t_post)==D_frame(0,t_pre)` when pop writes no root summary (or targets parent `f≥1`), and `D_frame(f,t+1)==D_frame(f,t)` for all `f` across any no-write step (catching shallow aliasing, closed-gate drift, or decay).

**E4 Counterexample.** Set `c_min=0.7`. Frame 0 commits `s=("Unit 104",0.95)`. Push Frame 1; low-confidence write `("Unit 109",0.30)` unconditionally sets `F1[s].validity=1` and updates `vec` (`gain=1`), leaving `text=""`, `conf=0`. Push Frame 2; commit `("Unit 202",0.92)`, then pop to Frame 1. Scoped read ("nearest valid ancestor") stops at `F1[s]`, returning uncommitted `("",0)` and shadowing `"Unit 104"` instead of restoring it. (In-frame low-confidence writes also mutate `vec` via sigmoid while keeping old `text/conf`, desynchronizing vector and declaration.)

**Minimal Revision.** Split `validity` into `vec_valid` (first-write gain) and `decl_valid` (set iff `c≥c_min` atomically with `text,conf`). Bind scoped declaration reads (E4, G1) to nearest `decl_valid==1`, zero popped frames, and scope E4 to committed `(text,conf)` (or gate `vec` on `c≥c_min` for vector/text parity).

## 2. Component F: Scope, Directory, Perturbation, and Typed vs. Rank Gates

**Metric & F3 Preconditions.** Pin `ν`: NFKC → casefold → strip Unicode `P*` and pinned whitespace; reject empty keys or directory collisions (`ν(A)=ν(B) ⇒ g=0 ⇒` abstain). Assert pairwise-disjoint optical classes programmatically. At `η=0.5` (same-class sub `0.5`, cross-class sub/ins/del `1.0`), disjointness ensures symmetry and triangle inequality, validating F3: for fixed `A`-vs-`B` margins `s_A=d(x_A,B)-d(x_A,A)∈[g-2e_A,g]` and `s_B=d(x_B,B)-d(x_B,A)∈[-g,-g+2e_B]`, `|μ|≤max(e_A,e_B)` and `δ=s_A-s_B≥2g-2(e_A+e_B)`. At `η=0`, `d_0` is only a pseudometric (`g=0` across optically equivalent distinct IDs).

**Scope & Directory.** G1 binds nearest `decl_valid==1` ancestor's own raw text (abstaining if sibling owner/unit slots `[0],[1]` conflict at that depth; never reading labels) against the binder's own directory `D` (never cross-binder pools or label-pruned pairs). Define `g=min_{u≠v∈D} d_η(u,v)` (`|D|≥2` for G3); unconstrained pairwise `d(y_(1),y_(2))` false-accepts out-of-directory targets when `y_(2)` is distant.

**Perturbation (`k=0..floor(g)`).** Edit along a verified minimal normalized alignment `ν(A)→ν(B)` (never raw edits collapsed off-geodesic by `ν`). Never assert unattainable steps (`g=0.5 ⇒ floor(g)=0`); test only prefixes verifying `d_η(x,A)=k̃` and `d_η(x,B)=g-k̃`. Assert exact zones: `k̃<g/2 ∧ g-2k̃≥0.5 ⇒ RESOLVE(A)`; `min(k̃,g-k̃)≥g/2 ∨ |g-2k̃|<0.5 ⇒ WITHHOLD` (e.g., `g=2, k̃=1`); `k̃>g/2 ∧ 2k̃-g≥0.5 ⇒ RESOLVE(B)` (never `A`).

**Typed vs. Rank Gates.** Rank-only metrics mask no-target false accepts. Score typed outcomes `{RESOLVE(id),WITHHOLD(reason)}` deduplicated to 20 independent calibration binders (not 224 duplicated M1/M3 views): 16 answerable require exact `RESOLVE(true_id)`; 4 no-target require `WITHHOLD` (any `RESOLVE(*)` fails). Native calibrated M2 sets the parity floor (`20/20`, `4/4` withholds).

## 3. Component D: Arithmetic Matrix & Non-Identifiability

**Parser & Invariants.** Parse monetary strings to exact signed `int64` minor units at one pinned scale (no floats); normalize `-`, `U+2212`, `(x)`, trailing `-`, pinned `CR/DR`, and split Debit/Credit columns (`PARSE_ABSTAIN` on contradictory/malformed tokens). Require **measured** running balances `b̂_0..b̂_n` (reconstructed balances force `ρ_i≡0`). With `â_i=a_i+ε_i, b̂_i=b_i+β_i, T̂=T+τ`: `D=∑â_i-T̂=∑ε_i-τ`, `ρ_i=b̂_i-b̂_{i-1}-â_i=β_i-β_{i-1}-ε_i`, and boundary invariant `B=(∑ρ_i)+D=(b̂_n-b̂_0)-T̂=β_n-β_0-τ`.

|Signature|Preconditions|Disposition / Gate|
|---|---|---|
|`D=0, ∀ρ_i=0`|`B=0`|`OK` (uniform shift of all `b̂_i` unobservable)|
|`D≠0, ∀ρ_i=0`|`B=D≠0`|Total-only fault (`τ=-D`); **never edit `a_i`**|
|`D≠0, B=0`, unique `ρ_k=-D`|`a*_k=â_k-D`; same sign, base-10 Hamming-1 on `abs(a*_k)` vs `abs(â_k)`|`D1–D4` decimal sub (`abs(D)=d·10^p` alone falsely matches `-100→+700`)|
|`D≠0, B=0`, unique `ρ_k=-D`|`D` even, `â_k≠0`, `D=2â_k=-ρ_k`|`D4.1` sign flip (`a*_k=-â_k`, `+↔-`; separates `â_k=±5·10^p` from D1–D4)|
|`D=0, B≠0`, `ρ_1=-Δ` or `ρ_n=+Δ`|Boundary residual|`BOUNDARY_ABSTAIN`: `β_0`/`β_n` confounded with `(ε_1,τ)`/`(ε_n,τ)`|
|`D=0, B=0`, `ρ_j=+Δ, ρ_k=-Δ` (`j<k`)|Never gate on `D≠0`|**`NON_IDENTIFIABLE`** (D5 vs. interior balance)|
|Other / `B≠0` + interior `ρ_i`|Compound/missing/tax|`STRUCTURAL_ABSTAIN`|

**Non-Identifiability Proof.** For adjacent `k=j+1`, single interior balance corruption `β_j=+Δ` (`ε≡0`) yields `(D=0, ρ_j=+Δ, ρ_{j+1}=-Δ)`, algebraically identical to opposed amount errors `ε_j=-Δ, ε_{j+1}=+Δ` (`β≡0`). For `k>j+1`, opposed errors `(ε_j=-Δ, ε_k=+Δ)` match balance-block shift `β_j=…=β_{k-1}=+Δ`. Emit `NON_IDENTIFIABLE` (never auto-apply D5) absent independent OCR/logit evidence. (Without measured `b̂_i`, D1–D4/D4.1 require a singleton row match else abstain.)

## 4. Component A Guards, Tokenizer/Logit Gates, Guarantees, and C Conditioning

**Numerical Guards.** Run on full pre-softmax Pass-1 logits `z∈ℝ^{|V|}` in FP64. Reject `NaN/+Inf` (`ABSTAIN`); filter masked `-Inf` *before* empty-rival checks (preventing `(-Inf)-(-Inf)=NaN`). Define distinct confusable rivals `R(v*)={v'∈V_fin : ν(v')≠ε ∧ ν(v')≠ν(v*) ∧ d_η(ν(v*),ν(v'))≤1-η}`. Pin `η=0.5` (`1-η=0.5` selects optical confusables only; `η=0` sets `1-η=1`, sweeping all 1-char and empty-normalized punctuation tokens into `R(v*)` for 1-char `v*`). Exclude same-normalized variants (`"0"` vs `"▁0"`) from `R(v*)` and distinct runner-up `v_ru`, giving `m=z_{v*}-z_{v_ru}`. If `R(v*)=∅`, set `m_conf=+∞, σ=m`; else compute shift-invariant FP64 `logsumexp` via `log1p` over `R(v*)` (including `v_ru` iff `v_ru∈R(v*)`), `m_conf=z_{v*}-L_conf`, `σ=min(m,m_conf)`. Do **not** clamp `σ≥0` (`|R|≥2` yields `m_conf<0`; track BPE multiplicity penalty `-ln|R|`). On `n` independent error-docs (doc `max` or one sampled error `σ`, ascending): `k=⌈(n+1)(1-α)⌉`, `τ̂=S_(k)` if `k≤n` else `+∞`; flag via **inclusive** `σ≤τ̂` (strict `<` breaks tie coverage).

**Tokenizer/Logit Gates & Guarantees.** Frozen captures (markup/spans/pooled vectors/tokens) cannot execute A; A requires pinned Pass-1 vocabulary (single-token `EV(v)` misses multi-token splits like `"10"` vs `"I"+"O"`), unpruned Pass-1 logits, and true error-doc labels. Calibration guarantees **only** exchangeable error-conditional recall `≥1-α` (`max` ⇒ all-error doc recall; sampled ⇒ single-error recall)—zero bound on clean-doc false alarms, precision, subtype coverage, or shift. At `α=0.05`, finite `τ̂` requires `n_err≥19` independent error-docs; on 20 binders (0 M2 errors), `k>n_err ⇒ τ̂=+∞`. Pooling 224 duplicated M1/M3 rows violates exchangeability.

**Revised C Conditioning (Sufficient vs. Generic).** `∇_{e_ℓ}L = J_{y,e_ℓ}^⊤ g_y`. *Generic* nonzeroness (random `g_y` misses `ker(J^⊤)` when `J≠0`) fails for structured task/LayerNorm/softmax gradients; deterministic *sufficiency* (`g_y≠0 ⇒ J^⊤g_y≠0`) requires `ker(J^⊤)={0}` (full row rank—impossible when `dim(e_ℓ)<dim(y)`, broken by zero-init/saturated gates). B's adaptive routing invalidates both: hard routing zeroes `J_{y,e_ℓ}` when `e_ℓ`-blocks are skipped; soft input-dependent gating adds `∑_b f_b(∂m_b/∂e_ℓ)`, breaking fixed-graph identity and enabling cancellation.

## 5. Promotion Support vs. Hard Stop Gates

**May Support Promotion** (at `7643bb9b26d15c9d435234e9d3a5d11b742dc771`):
- Standalone CPU contracts passing adversarial suites: revised E (`D_decl/D_frame`, no-write `t_post`, 3-level E4 shadow), F (disjoint classes, F3, attainable geodesics, own-scope binding), D (signed `int64` matrix, `NON_IDENTIFIABLE` D5/balance gate), and A numerical kernels.
- Full v3/A promotion **only** with provenance-pinned `W_V, g, c_t`, exact Pass-1 tokenizer + full logits, and independent error-doc labels (`n_err≥⌈1/α⌉-1`, disjoint from 4 dev binders), achieving `≥20/20` typed binders (`4/4` withholds) plus clean-doc false-alarm reporting.

**Hard Stop Gates (Any Breach Blocks Promotion):**
1. Missing `W_V, g, c_t`, full Pass-1 logits, or error labels (halts neural-E, A-calibration, and C).
2. Label-populated slots, M2 decisions substituted as v3 outputs, or reconstructed balances used as measured `b̂_i`.
3. Inflating `n` via 224 duplicated M1/M3 rows, suppressing `τ̂=+∞` when `k>n`, or rank-only/answerable-only scoring.
4. Any no-target false resolve, unrevised E4, auto-applying D5 over balance corruption, unattainable perturbation assertions, or citing unexecuted C as proof under B.
