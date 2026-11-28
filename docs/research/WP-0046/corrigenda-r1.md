# WP-0046 Stage 0 — Standalone Mathematical and Instruction Corrigenda (`corrigenda-r1`)

| Field | Value |
| --- | --- |
| Document ID | `wp0046-corrigenda-r1` (post-opening Stage-0 revision; **requires fresh independent non-author review**) |
| Author | `eld-owner-probe` (Gemini 4 Neon (XHigh) via local `agy` CLI; `xhigh` requested) |
| Operative Base | Paper I reviewed revision 1 (`paper-I-reviewed.pdf` / `bundle/src/stock.tex`, SHA-256 `023897e11d9e68d9aa30cee500ca0341fb5fb2b0dd55e470aeb02415c32d41c8`); repository pin `e43af2e263f55478d1d551a5a095536b042589c2` |
| Cited Independent Positions | Owner independent freeze `6fa242950ffd4dfd1d19accc9271e88aada2d552` (`first.md`, `M-01`–`M-09`, `S-01`–`S-08`, `I-01`–`I-03`); Peer (`eld-rd-reviewer` / Claude) independent return `1c9690b9eab22dfdf0c943815f5440e6563f2350` (expectation freeze `cffc9101e769bc6f7ab11fdb4137401f8f228490`; `M1`–`M5`, `O1`–`O8`, 49 constructed cases) |
| Companions | [`exchange.md`](exchange.md), [`proposal-r1.md`](proposal-r1.md), [`register-r1.json`](register-r1.json), [`build_register_r1.py`](build_register_r1.py), [`controls_r1.py`](controls_r1.py) |
| Independence Boundary | Consolidates independent discoveries from both first positions with post-opening reconciliations. No co-influenced amendment herein is self-certified; all require non-author verification by `eld-rd-reviewer`. |

---

## 1. Symbol Disambiguation Table (Resolves `M5` & `M-09`)

Paper I reviewed revision 1 overloads `D`, `H`, `P`, `b(·)`, and `A` across facing pages (`stock.tex` L283–329 and throughout). The following unambiguous symbol table governs `proposal-r1.md`, `register-r1.json`, and any successor edition of Paper I:

| Overloaded Symbol in Paper I Rev. 1 | Colliding Meanings in Rev. 1 | Unambiguous `r1` Replacement | Type / Domain |
| --- | --- | --- | --- |
| $D_s$ (Eq. 11) vs $D_j$ (Eq. 12) vs $D_1, D_2$ (T5) | Deferred obligation set vs independent design review Boolean vs repetition/page blocked token masks | $\mathrm{Def}_s$ (deferred set), $\mathrm{Rev}_j$ (stage-$j$ independent review Boolean), $\mathrm{Ban}_1, \mathrm{Ban}_2$ (T5 blocked token sets) | $\mathcal P(\mathcal K)$, $\{0,1\}$, $\mathcal P(V)$ |
| $H$ | Archive scope vs trust class vs witnesses $H_1, H_2$ vs T7 history set vs hypotheses $H_1\text{–}H_3$ | $\mathrm{Arch}$ (archive scope), $\mathcal T_{\rm trust}$ (trust class), $W_1, W_2$ (T1 witnesses), $\mathcal H_{\rm id}$ (T7 history set), $\mathsf{Hyp}_{1a}\text{–}\mathsf{Hyp}_3$ (hypotheses) | Distinct domains |
| $P$ | Pass verdict vs predicate $P_k$ vs T7 truth vs stage-$j$ plan $P_j$ vs Edition A2 page-permitted support | $\PP$ (verdict Pass), $\phi_k$ (atom predicate), $\tau_{\rm id}$ (T7 target truth), $\mathrm{Plan}_j$ (stage-$j$ plan), $\mathrm{Allow}_{\rm page}$ (Edition A2 page-permitted set) | Distinct domains |
| $b(\cdot)$ | Multiset multiplicity (T3a/T8a) vs element byte width (T6) | $\mu(\cdot)$ (multiset multiplicity), $\beta$ (element byte width in bytes, $\beta \in \mathbb Z_{>0}$) | $\mathcal K \to \mathbb N$, $\mathbb Z_{>0}$ |
| $A$ | T5 allowed support set vs T8 due set $A_s$ vs active set $A_m$ | $\mathrm{Allow}$ (T5 allowed token support), $\mathrm{Due}_s$ (T8 due-stage atoms $\{k : d_k \le s\}$), $\mathrm{Act}_m$ (active set) | $\mathcal P(V)$, $\mathcal P(\mathcal K)$, set |
| $N$ (Edition A2 vs T5) | Edition A2 no-repeat permitted support set vs T5 IEEE-754 $-\infty$ word `0xFF800000` | $\mathrm{Allow}_{\rm rep} = V \setminus \mathrm{Ban}_1$ (Edition A2 $N$), $w_{-\infty} = \texttt{0xFF800000}$ (T5 $-\infty$ word); $\mathrm{Allow} = \mathrm{Allow}_{\rm rep} \cap \mathrm{Allow}_{\rm page} = V \setminus (\mathrm{Ban}_1 \cup \mathrm{Ban}_2)$ | $\mathcal P(V)$, `uint32` |

---

## 2. Standalone Mathematical Corrigenda (Paper I T1 through T8a)

### Corrigendum C1 — T1 Corollary Typing and Conflict-Class Preservation
- **Origin:** Corollary typing (`eld-rd-reviewer`, `first.md` §3 T1); conflict-class preservation (`eld-owner-probe`, `first.md` `M-02`).
- **Baseline (Paper I Rev. 1, p. 2, `stock.tex` L65–80):** States Corollary hypothesis *"$\phi_k$ takes both values on $H_T$"*, which is ill-typed when $\phi_k(h_D, h_T)$ depends jointly on $(h_D, h_T)$ (as in relational profile comparisons of T2). Separately, T4 Eq. (7) collapses Eq. (2)'s $\MM_{\rm field}$ (valid receipt showing target failure) and $\MM_{\rm integrity}$ (empty fiber $\Omega(o)=\varnothing$ with witnessed protocol/order/hash contradiction) into bare `M`.
- **Amended Statement:**
  1. *(Independent-Target Corollary, typed)* Let $\Omega(o_D) = \Omega_D(o_D) \times H_T$ with $\Omega_D(o_D) \neq \varnothing$. If there exists $h_D \in \Omega_D(o_D)$ such that $\{\phi_k(h_D, h_T) : h_T \in H_T\} = \{0, 1\}$, then $K_k(o_D) = \{0, 1\}$ and $V_k(o_D) = \UU$.
  2. *(Proof)* Fix $h_D \in \Omega_D(o_D)$ and pick $h_T^{(0)}, h_T^{(1)} \in H_T$ with $\phi_k(h_D, h_T^{(0)}) = 0$ and $\phi_k(h_D, h_T^{(1)}) = 1$. Both $(h_D, h_T^{(0)})$ and $(h_D, h_T^{(1)})$ lie in $\Omega_D(o_D) \times H_T = \Omega(o_D)$, so $\{0, 1\} \subseteq K_k(o_D) \subseteq \{0, 1\}$, yielding $V_k(o_D) = \UU$.
  3. *(Conflict-Class Preservation)* Every return record carrying `verdict = "M"` MUST preserve per-conflict class tags in $\{\MM_{\rm field}, \MM_{\rm integrity}, \MM_{\rm static\_plan}\}$ alongside `conflict_classes` so protocol/integrity contradictions (`order.integrity`, forged duplicates) remain distinguishable from target value/numeric conflicts (`obligations42.md` L55).
- **Worked Boundary:** WP-0045 direct inert CPU passes $4/4$ ($h_D$ fixed) while target stock $h_T$ may either satisfy or violate `PYTHONHASHSEED` effectiveness or `triton` absence $\Rightarrow K_k(o_D) = \{0, 1\} \Rightarrow \UU$ (zero dynamic transfer).

---

### Corrigendum C2 — T2a Derived Absolute Comparator for `Q_hash`, Strict Flag Typing, and `e_launch` vs `e_child`
- **Origin:** Derived-vs-observed comparator (`eld-rd-reviewer`, `first.md` §3 T2a); extended 8-flag strict typing, `e_launch`/`e_child` split, and `-I` defeating `PYTHONUTF8` (`eld-owner-probe`, `first.md` `M-01`); closed 31-key env schema (`eld-rd-reviewer`, `O4`, `S4a`/`S4b`/`S6` and `eld-owner-probe`, `S-03`).
- **Baseline (Paper I Rev. 1, p. 4, `stock.tex` L99–124; `amendments.py` L9–13):** T2a writes *"compare the effective flags with their observed stock counterparts"*, checks only 2 flags (`ignore_environment`, `hash_randomization`) with Python `bool` in `amendments.py:startup()`, and leaves the launch vs child environment relation implicit.
- **Problem Witness:** `prior0.json` marks historical `flags` as *"full field absent at historical public observation cut"* and `worker43.py` L362 omits `sys.flags` from `runtime.json`. Comparing against the historical observed stock counterpart therefore passes $y = \unk$ into Eq. (6), forcing `unobserved` (`U`) on every target run! Moreover, CPython 3.12.10 `sys.flags` attributes are `int` (`0`/`1`) except `safe_path` (`bool`), and `worker43.py` L199 sets `PYTHONUTF8="1"` (`utf8_mode == 1`), which `-I` also defeats (`utf8_mode == 0`).
- **Amended Definitions:**
  1. **Derived absolute comparator (explicitly labeled):** $Q_{\rm startup}$ compares the target child's observed 8-tuple of `sys.flags` against a **frozen derived absolute expectation** derived from historical `worker43.py` L86–87 (`-B -u`, neither `-E` nor `-I`) and L199 (`PYTHONHASHSEED="0"`, `PYTHONUTF8="1"`), explicitly labeled `derived_not_historically_observed`:
     $$f^* = \bigl(\texttt{isolated}:0,\; \texttt{ignore\_environment}:0,\; \texttt{hash\_randomization}:0,\; \texttt{no\_site}:0,\; \texttt{no\_user\_site}:1,\; \texttt{dont\_write\_bytecode}:1,\; \texttt{safe\_path}:\mathsf{True},\; \texttt{utf8\_mode}:1\bigr)$$
     compared with strict type-preserving equality (`type(a) is type(b)`, so `0 != False`, `1 != True`).
  2. **Closed typed `e_launch` vs `e_child` schema:** Every environment key takes a tagged value in $\{\mathsf{present}(v), \mathsf{absent}, \mathsf{unobserved}\}$. $Q_{\rm env}$ checks the exact closed 31-key child allowlist $\mathcal E_{31}$ (matching `worker43.py` L189–199, with explicitly declared Stage-1a/1b intentional deltas `CUDA_VISIBLE_DEVICES=""` and `PATH="%SystemRoot%/System32;%SystemRoot%"`), enforces $\forall k \notin \mathcal E_{31}: e_{\rm child}[k] = \mathsf{absent}$ (catching `PYTHONPATH=""` vs `ABSENT`, `S6`, and missing `PYTHONUTF8`, `S4b`), and explicitly models launch-only keys consumed before user code (e.g., under the primary `__PYVENV_LAUNCHER__` hypothesis, $e_{\rm launch}[\texttt{\_\_PYVENV\_LAUNCHER\_\_}] = \mathsf{present}(\texttt{"@venv/Scripts/python.exe"})$ and $e_{\rm child}[\texttt{\_\_PYVENV\_LAUNCHER\_\_}] = \mathsf{absent}$).
- **Worked Counterexamples:** `S1`/`ctrl_02` (`-I` with `PYTHONHASHSEED="0"` $\Rightarrow \MM$ on `ignore_environment`, `hash_randomization`, `utf8_mode`); `S4a` vs `S4b` (6-key register misses absent `PYTHONUTF8`/`utf8_mode=0`, closed schema returns $\MM$ with `minX = {env.PYTHONUTF8}`); `S6` (`PYTHONPATH=""` vs `ABSENT` $\Rightarrow \MM$, `PYTHONCASEOK=?` $\Rightarrow \UU$).

---

### Corrigendum C3 — T3 Sharpening Witness & T3a Conjunct-Wise Three-Valued $B_{\rm arm}$ (Resolves `M3` & `M-03`)
- **Origin:** Independent convergence by both providers (`eld-rd-reviewer` `M3`, `I1`–`I6b`, T3 witness; `eld-owner-probe` `M-03`, `ctrl_05`–`ctrl_07`).
- **Baseline (Paper I Rev. 1, pp. 5–6, `stock.tex` L125–169; `amendments.py` L15–20):** Writes $B_{\rm arm}$ as a single conjunction and implements `amendments.py:inventory()` with an early `if schema is MISSING or sealed is MISSING or read is MISSING: return "U"`, which hides decidable conflicts behind `U`! Also omits key uniqueness $\mu(E_r)(k) \le 1$, physical-object uniqueness, ordered-projection checking, and `auth(q_r)` from the formula.
- **T3 Sharpening Witness (Archive):** `review43` records historical `sys.orig_argv[0] = @base/python.exe` and `sys.executable = @venv/Scripts/python.exe`. A direct-stock launch of `@base/python.exe` reports the same `orig_argv[0]` (and, if `__PYVENV_LAUNCHER__` applies, the same `sys.executable`). Therefore reported image/argv cannot separate $\tau=\texttt{venv}$ from $\tau=\texttt{direct-stock}$; only Eq. (4)'s creation join $J(e, S, i_{\rm base})$ can.
- **Amended T3a Conjunct-Wise Evaluation ($X_{\rm arm}, U_{\rm arm}$):**
  Given schedule authentication $\mathrm{auth}(q_r)$, independent schema sequence $E_r = F_r(q_r)$, sealed inventory $I_r$, scorer read sequence $R_r$, order-sensitivity flag $\mathrm{ord} \in \{0,1\}$, keyed custody map $c(k) \in \{\mathsf{True}, \mathsf{False}, \unk\}$, and physical-object map $\kappa(k)$:
  1. **Schema ($E_r$):** If $E_r = \unk$, add `schema` to $U_{\rm arm}$; else for each $k$ with $\mu(E_r)(k) > 1$, add `schema.duplicate:k` to $X_{\rm arm}$. Also check $\mathrm{auth}(q_r)$ ($\mathsf{False} \Rightarrow X_{\rm arm}$, $\unk \Rightarrow U_{\rm arm}$).
  2. **Sealed Inventory ($I_r$ vs $E_r$):** If $I_r = \unk$, add `inventory` to $U_{\rm arm}$; else if $E_r \neq \unk$, add `omit:k` to $X_{\rm arm}$ for every $k$ with $\mu(E_r)(k) > \mu(I_r)(k)$ and `extra:k` for $\mu(I_r)(k) > \mu(E_r)(k)$.
  3. **Scorer Read ($R_r$ vs $I_r$):** If $R_r = \unk$, add `read` to $U_{\rm arm}$; else if $I_r \neq \unk$, add `read.missing:k` for $\mu(I_r)(k) > \mu(R_r)(k)$, `read.extra:k` for $\mu(R_r)(k) > \mu(I_r)(k)$, and if $\mathrm{ord}=1 \land \mu(I_r)=\mu(R_r) \land R_r \neq I_r$, add `order` to $X_{\rm arm}$.
  4. **Keyed Custody & Physical Uniqueness:** Over $M_{\rm chk} = \{k \in I_r : E_r = \unk \lor k \in E_r\}$ (scoping custody to sealed members so an omitted member produces `omit:k` in $X_{\rm arm}$ without spurious `U` entries for an uncreated file):
     - For each $k \in M_{\rm chk}$: $c(k)=\mathsf{False} \Rightarrow \texttt{custody:}k \in X_{\rm arm}$; $c(k)=\unk \Rightarrow \texttt{custody:}k \in U_{\rm arm}$.
     - For each $k \in M_{\rm chk}$: $\kappa(k)=\unk \Rightarrow \texttt{object:}k \in U_{\rm arm}$; for any distinct keys $K_o = \{k \in M_{\rm chk} : \kappa(k) = o\}$ with $|K_o| > 1$, add `object.shared:` + joined sorted $K_o$ to $X_{\rm arm}$.
  5. **Verdict:** $V_{\rm arm} = V(X_{\rm arm}, U_{\rm arm})$ under Eq. (7) ($\MM < \UU < \PP$).
  6. **Operational NTFS tightening (`continuous(m)`):** Require `FILE_SHARE_READ` **only** (excluding both `FILE_SHARE_WRITE` and `FILE_SHARE_DELETE`) on BOTH writer (`CREATE_NEW`) and scorer fresh (`OPEN_EXISTING`) opens plus `nNumberOfLinks == 1` (tightening WP-0045 `win.py` L107's `SHARE_R | SHARE_W`).
- **Worked Witnesses:**
  - `I3` ($E=\unk, I=(a,b), R=(a)$): $X_{\rm arm} = \{\texttt{read.missing:b}\}, U_{\rm arm} = \{\texttt{schema}\} \Rightarrow \MM$ (whereas `amendments.inventory` wrongly returned `U`).
  - `ctrl_06` ($E=(a,b), I=(a), R=\unk$): $X_{\rm arm} = \{\texttt{omit:b}\}, U_{\rm arm} = \{\texttt{read}\} \Rightarrow \MM$ (whereas `amendments.inventory` wrongly returned `U`).
  - `I5` ($\kappa(a)=\kappa(b)=o_1$): $X_{\rm arm} = \{\texttt{object.shared:a+b}\} \Rightarrow \MM$.
  - `I6a` vs `I6b` ($I=(a,b), R=(b,a)$): $\mathrm{ord}=1 \Rightarrow \MM$ (`order`); $\mathrm{ord}=0 \Rightarrow \PP$.

---

### Corrigendum C4 — T4 First-Matching-Case Eq. (6), Strict Typing, Transitive Closure, and Acyclicity
- **Origin:** Transitive closure `D6` & Eq. (6) wording (`eld-rd-reviewer`, `first.md` §2 & §3 T4); strict `bool != int`, `present(null) != absent`, reflexive/cyclic `order.integrity` (`eld-owner-probe`, `first.md` `M-04`).
- **Amended Rules:**
  1. **Eq. (6) ("first matching case"):** Evaluate `Compare(x, y; k)` strictly in top-down order:
     (1) $J_k = 0 \mapsto \texttt{incomparable}$;
     (2) $J_k = \unk \lor x = \unk \lor y = \unk \mapsto \texttt{unobserved}$;
     (3) type mismatch (`type(x) != type(y)`, including `bool != int` and `present(null) != absent`) $\mapsto \texttt{different}$ (or `schema_mismatch` when comparing against a typed schema);
     (4) $\eta_k(x) = \eta_k(y) \mapsto \texttt{same}$;
     (5) otherwise $\mapsto \texttt{different}$.
  2. **Minimal frontiers (`firstConflict`, `firstFinding`):** Given a direct precedence edge set $E_{\rm ord}$, first validate that $E_{\rm ord}$ is **irreflexive and acyclic** (a valid DAG generating a strict partial order $\prec$). If any reflexive edge $(a,a)$ or cycle exists, emit `order.integrity` with class $\MM_{\rm integrity}$ rather than silently returning an empty frontier! Otherwise form the transitive closure $\prec^+$ (Warshall / DFS) and define:
     $$\fn{firstConflict}(X) = \{x \in X : \nexists a \in X,\; a \prec^+ x\}, \qquad \fn{firstFinding}(X, U) = \{e \in X \cup U : \nexists a \in X \cup U,\; a \prec^+ e\}.$$
- **Worked Witnesses:** `D6` ($a \prec b \prec c$, events $\{a, c\}$ $\Rightarrow$ `{a}`, fixing `amendments.minimal` which returned `{a, c}`); `ctrl_16` (cycle `{(a,b),(b,a)}` $\Rightarrow \MM_{\rm integrity}$ `order.integrity`; `present(0) != present(false)` and `absent != present(null)`).

---

### Corrigendum C5 — T5 Reading B on `P7`, `X_oob` vs Literal `X_choice` (`P3`), Partial Missingness, $D_1$ Archive Scope, and `WP-0043/scorer.py` L304
- **Origin:** `P7` Reading B, $D_1$ bundle scope, A2 notation reconciliation (`eld-rd-reviewer`, `first.md` §3 T5); `X_oob`, partial-phase missingness, and Git-verified `WP-0043/scorer.py` L304 bug (`eld-owner-probe`, `first.md` `M-05`, `S-08`); Git `e43af2e2` $D_1$ derivation (this exchange).
- **Amended Rules & Clarifications:**
  1. **Resolved `P7` (Convergent Reading B):** $y_{\rm obs}$ is ALWAYS a required observation on a retained score row. If $y_{\rm obs} = \unk$, add `emission` to $U$ unconditionally (even when $X_0 \cup X_1 \cup X_2 \cup X_{\rm supp} \neq \varnothing$). Winner optimality $X_{\rm choice}$ is evaluated ONLY when the score phases and support are clean ($X_0 = X_1 = X_2 = X_{\rm supp} = \varnothing$). On `P7` (`z0=[1.0, NaN]`, `emitted="?"`), this gives `verdict="M", X=["0/1"], U=["emission"], winner=None`.
  2. **Explicit Mode Distinction on `P3` ($X_{\rm oob}$ vs Paper I Rev. 1 literal):**
     - *Paper I rev. 1 strict mode* (Claude `P3`): evaluates emission checks only when `clean` ($\mathrm{Allow} \neq \varnothing$ and $X_0=X_1=X_2=\varnothing$), yielding on `P3` (`D1=[0], D2=[1], emitted=0`): `verdict="M", X=["supp"], U=[], winner=None`.
     - *Amended `r1` `X_oob` mode* (Gemini `M-05` / `WP-0043/README.md` L69): defines $X_{\rm oob} = \{\texttt{oob} : y_{\rm obs} \neq \unk \land y_{\rm obs} \notin \mathrm{Allow}\}$ whenever $\mathrm{Allow}$ and $y_{\rm obs}$ are observed, yielding on `P3`: `verdict="M", X=["oob", "supp"], U=[], winner=None` (and catching a banned emission even when `z0` has a raw `NaN` on another coordinate). Both agree on `verdict="M"` and `winner=None`; Stage-2 scorer freeze must explicitly pick one reporting convention (`controls_r1.py` supports both).
  3. **Partial-phase missingness:** If any vector $z^p$ or mask $\mathrm{Ban}_p$ is unobserved, add the missing symbol to $U$ and still evaluate every transition whose endpoints and mask are present (`ctrl_10`).
  4. **Archive Scope of $\mathrm{Ban}_1 = \varnothing$ (Bundle vs Pinned Git `e43af2e2`):**
     - Inside standalone `stock-transfer-source.zip`, $\mathrm{Ban}_1 = \varnothing$ is **NOT derivable** from history because `F07.warm1.token_ids.json` is absent from the ZIP (`c0_identical_c1` is effect-only evidence, forbidden for witnessing by Edition A2).
     - Inside pinned Git commit `e43af2e263f55478d1d551a5a095536b042589c2`, `F07.warm1.token_ids.json` (SHA-256 `532ffea05870c45189f473d1cb16ded1d26c583f07737e1462ac325ecdae5982`, identical across author Q0, author snapshot, and reviewer Q0; 2,558 tokens) and `F07.warm1.observation.json` (`prompt_len=827`, SHA-256 `0550505135cd181dd0e326c3aa4752fab24a63654af6981636339e449d65219e`) ARE archived. Recomputing `support(h, order=35, window=1024)` across `g = 618..622` (`t = 1445..1449`) checks **585 + 586 + 587 + 588 + 589 = 2,935** candidate 34-gram starts, finds longest suffix matches `[2, 0, 0, 1, 2] < 34`, and independently proves $\mathrm{Ban}_1 = \varnothing$ on 5/5 rows from pinned Git history! Paper I should state this scope boundary explicitly or include `F07.warm1.token_ids.json` in a successor bundle.
  5. **Actual Historical Scorer Bug (`S-08`):** `e43af2e2:docs/research/WP-0043/scorer.py` L304 writes `if (j==1 and token in banned) or (j==2 and token not in allowed): expected = NEG_INF` (cumulative mask at `C2_post_page`), violating T5 Theorem 3 on `P1` (`ctrl_08`). Stage-2 scorer MUST use phase-local `j==2 and token not in page_allowed`.

---

### Corrigendum C6 — T6 Determinism Premise (`M4` / `M-06`), Empty-View Extension (`L3`), and Alias Distinction
- **Origin:** Independent convergence by both providers on determinism (`eld-rd-reviewer` `M4`, `L1`–`L3`, `N1`–`N2`; `eld-owner-probe` `M-06`).
- **Amended Statements:**
  1. **Explicit Determinism Premise (`M4`):** Eq. (9) ($\exists g: Y_F = g \circ C \iff (\forall s, s' \in \mathcal S: C(s)=C(s') \Rightarrow Y_F(s)=Y_F(s'))$) and $\mathsf{Hyp}_3$ assume $F$ is a deterministic function of $s$ on $\mathcal S$ (or index the trace by kernel nondeterminism seed/schedule $\omega$: $Y_F(s, \omega)$ and bind deterministic backend settings in the trace schema). Bitwise run-to-run GPU determinism is **unmeasured** (WP-0043 matched 1 content pair only); without this premise, nondeterministic floating-point reductions could be misattributed to capture insufficiency.
  2. **Tensor Layout Bound (`L1`–`L3`):** For nonempty views ($\forall i: n_i \in \mathbb Z_{>0}$, $s_i \in \mathbb Z_{\ge 0}$, $o \in \mathbb Z_{\ge 0}$, $\beta \in \mathbb Z_{>0}$), require $\beta(1 + o + \sum_i (n_i - 1) s_i) \le B_{\rm storage}$ (`L1`: $2 \cdot (1 + 0 + 9\cdot 2048 + 6\cdot 128 + 127) = 38,656 \le 40,960 \Rightarrow \mathsf{True}$; `L2`: $41,216 > 40,960 \Rightarrow \mathsf{False}$). For empty views ($\exists i: n_i = 0$ with all $n_i \ge 0$), Paper I rev. 1 leaves them outside the nonempty domain (`L3` $\Rightarrow$ `outside_domain` in strict rev. 1 mode); the Stage-2/3 validator (`M-06`, fixing `WP-0043/transfer.py` L15–16) adds the empty-view offset bound $0 \le \beta \cdot o \le B_{\rm storage}$ (`L3` $\Rightarrow \mathsf{True}$, while `o = 10^9, cap = 0` $\Rightarrow \mathsf{False}$).
  3. **Read-bound vs writable intra-tensor aliasing:** Nonempty layout containment is necessary for D2H read capture, whereas writable restored Stage-3 views additionally require injective (non-overlapping) strides or explicit alias-class preservation.

---

### Corrigendum C7 — T7 Correlated Source-Group Loss Infeasibility (`K3` & `M-07`)
- **Origin:** Independent convergence (`eld-rd-reviewer` `K1`–`K3` and `check.py` uniqueness verification; `eld-owner-probe` `M-07`).
- **Amended Clarification:** The $1 + f$ hitting-set RHS holds strictly for up to $f$ non-informative arbitrary **coordinate** erasures. When failure domains are **sources** $G_1, \dots, G_r \subseteq M$ carrying multiple coordinates, replace coordinate count with source-failure resilience: for every $F \subseteq \{1,\dots,r\}$ with $|F| \le f$ and every distinguishing pair $(h, h') \in \mathcal P$, require $(S \setminus \bigcup_{i \in F} G_i) \cap S(h, h') \neq \varnothing$.
- **Worked Boundary Witness (`K3`):** On Paper I p. 10's 4-history table (`h0=(0,0,0)` truth 1; `h1=(1,1,0)`, `h2=(0,1,1)`, `h3=(1,0,1)` truth 0), if Source 0 carries $\{u, w\}$ and Source 1 carries $\{v\}$, then $f = 1$ source failure is **infeasible** for every $S \subseteq \{u, v, w\}$ because losing Source 0 leaves only $\{v\}$, on which $h_0$ and $h_3$ both equal $0$. Solvers MUST return explicit `{infeasible: true, min_cost: null, argmin: []}`.

---

### Corrigendum C8 — T8 Scoped Plan $\Pi_s$ and Plan-Wide Static Conflicts (Resolves `M1` & `M-08`)
- **Origin:** Independent convergence (`eld-rd-reviewer` `M1`, `A1`/`A2a`/`A2b`/`S7`/`MIX`; `eld-owner-probe` `M-08`, `ctrl_15`).
- **Baseline Contradiction:** Paper I rev. 1 Eq. (11) restricts $X_T^{(s)}$ and $W_T^{(s)}$ to $k \in A_s$ ($d_k \le s$), contradicting `ASSESS()` and the TF32 regression example (`d_k = 2 > s = 0` returning `M`). Conversely, whole-plan `ASSESS()` puts unbound Stage-3 `private.parity` into `U` at Stage 1 (`A2a`), making `V_preflight = P` impossible and contradicting Eq. (12).
- **Amended Eq. (11):** Let $\Pi_s \subseteq \mathcal K$ be the declared scoped obligation set for stage $s \in \{0, 1a, 1b, 2, 3\}$, let $\mathrm{Due}_s = \{k \in \mathcal K : d_k \le s\}$ and $\mathrm{Def}_s = \{k \in \mathcal K : d_k > s\}$, let $X_{\rm static}(\text{all}) = \{k \in \mathcal K : \bigcap_i L_{k,i} = \varnothing\}$ (checked across ALL stages before deferral), and let $B_T = \{k \in \mathcal K : \text{required static binding missing}\}$:
  $$X_{\rm total}^{(s)} = X_{\rm static}(\text{all}) \cup \{k \in \mathrm{Due}_s \cap \Pi_s : X_{k,\rm due} \neq \varnothing\}$$
  $$U_{\rm total}^{(s)} = (B_T \cap \Pi_s) \cup \{k \in \mathrm{Due}_s \cap \Pi_s : U_{k,\rm due} \neq \varnothing\}$$
  $$\mathrm{DeferredUnbound}^{(s)} = B_T \setminus \Pi_s, \qquad V^{(s)}(\Pi_s) = V\bigl(X_{\rm total}^{(s)},\; U_{\rm total}^{(s)}\bigr)$$
  returning $(V^{(s)}, X_{\rm total}^{(s)}, U_{\rm total}^{(s)}, \mathrm{Def}_s, \mathrm{DeferredUnbound}^{(s)}, \fn{firstConflict}, \fn{firstFinding})$.
- **Worked Witnesses:** `A1`/`S7`/`ctrl_15` (Stage-2/1 static conflict at $s=0 \Rightarrow \MM$); `A2a` (whole-plan at $s=1 \Rightarrow \UU$ on `private.parity`); `A2b` (scoped $\Pi_1$ at $s=1 \Rightarrow \PP$ with `deferred_unbound = ["private.parity"]`).
- **Prose `relation` Audit:** Prose-only `relation` strings lacking typed comparators/locators do NOT satisfy frozen bindings for $B_T$; in the original `bundle/register.json`, `5` `bind_before_review` + `36` prose `relation` entries = `41` unexecutable entries. `register-r1.json` replaces all prose stubs with typed predicates and computes $B_T \cap \Pi_s$ mechanically per stage (`0` in $\Pi_0$, `4` in $\Pi_{1a}$, `5` in $\Pi_{1b}$, `10` in $\Pi_2$, `12` in $\Pi_3$).

---

### Corrigendum C9 — T8a Defined $V_{\rm preflight}$, Stage 1→2 Bridge, and Full-Tuple $J_5$ (Resolves `M2` & `M-09`)
- **Origin:** Independent convergence (`eld-rd-reviewer` `M2`, `G1`/`G2`, `J1`–`J6`; `eld-owner-probe` `M-09`, `ctrl_12`–`ctrl_14`).
- **Amended Eq. (12):** With unambiguous symbols $\mathrm{Plan}_j$ and $\mathrm{Rev}_j$ (from §1):
  $$V_{\rm preflight}(\Pi_1) := V^{(1a)}(\Pi_{1a}) \otimes V^{(1b)}(\Pi_{1b}) \quad\text{(pass iff both Stage 1a and Stage 1b pass } \PP\text{)}$$
  $$\mathsf{eligible}_{1a} = \mathrm{Plan}_{1a} \land \mathrm{Rev}_{1a}, \qquad \mathsf{eligible}_{1b} = \mathrm{Plan}_{1b} \land \mathrm{Rev}_{1b} \land \bigl[V^{(1a)}(\Pi_{1a}) = \PP\bigr] \land \bigl[\mathrm{proj}(\Pi_{1a}) = \mathrm{proj}(\mathrm{Plan}_{1b})\bigr]$$
  $$\mathsf{considerStockCapture} = \mathrm{Plan}_2 \land \mathrm{Rev}_2 \land \bigl[V_{\rm preflight}(\Pi_1) = \PP\bigr] \land \bigl[\mathrm{proj}(\Pi_1) = \mathrm{proj}(\mathrm{Plan}_2)\bigr]$$
  $$\mathsf{considerPrivateReplay} = \mathrm{Plan}_3 \land \mathrm{Rev}_3 \land \exists r : \Bigl(\bigl[V_{\rm stock}(r) = \PP\bigr] \land J_5(r, R_{\rm cand})\Bigr)$$
  $$\mathsf{execute}_j = \mathsf{eligible}_j \land \mathsf{separateLocalRelease}_j$$
  where:
  - $\mathrm{proj}(\cdot)$ projects `(route, env_schema_modulo_reviewed_stage1_deltas, source_pin_or_reviewed_bridge, static_manifest_digest)`, blocking `G1` (environment schema drift) and `G2` (route drift) even when literal `P2 & D2 & V_preflight==P` holds!
  - $J_5(r, R_{\rm cand})$ requires exact multiset bijection $\mu(\{(\mathrm{label}(t), \mathrm{arm}(t), \mathrm{pos}(t)) : t \in R_{\rm cand}\}) = \mu(K)$ over $K = \{(\texttt{F07.warm1}, \texttt{observed}, p) : p \in 1445..1449\}$ AND $\forall t \in R_{\rm cand}: \mathrm{run}(t)=r \land \mathrm{originalBound}(r,t) \land \mathrm{restorable}(t)$, blocking `J1` (cross-run), `J2` (duplicate position), `J3` (`F07.warmup`), `J4` (`untouched` arm), and `J6` ($\mathrm{Plan}_3 = \mathsf{False}$).
  - $V_{\rm stock}(r) = \PP$ covers BOTH cold stock arms (`untouched` and `observed`) through native EOS.

---

## 3. Implementation Instruction Corrigenda (Paper I Physical pp. 15–18)

1. **Role & Provider Table (p. 17):** Replace the superseded five-role table (which included an advisory cloud coordinator and a separate fixture role) with WP-0046's active three-role binding (`docs/coordination/WP-0046/assignment.md`): sole coordinator `eld-coordinator`, sole proposal/register author `eld-owner-probe` (Gemini), and independent reviewer `eld-rd-reviewer` (Claude).
2. **Stage-1 Split Into Stage 1a and Stage 1b (pp. 16–17):** Split Stage 1 into **Stage 1a** (pure-stdlib direct-stock observer stopping strictly before `import torch`; 5 scheduled units = 2 decisive + 3 live controls) and **Stage 1b** (separately gated CPU-only `import torch` + `LOAD_DLL_DEBUG_EVENT` DLL-origin check with `CUDA_VISIBLE_DEVICES=""`). Unchanged `worker43.py` MUST NEVER be run for Stage 1.
3. **Safe Literal vs Prohibited vs Future Commands (pp. 16–18):**
   - *Safe literally now (read-only stdlib, offline):* `python -I check.py` (in extracted bundle), `python -I -B docs/research/WP-0046/build_register_r1.py --verify`, and `python -I -B docs/research/WP-0046/controls_r1.py --cases docs/research/WP-0046/control_cases.json` (or `--claude-cases`).
   - *Prohibited in Stage 0:* `worker43.py`, `docs/research/WP-0043/stock.py`, any `torch`/stock/model/CUDA import or execution, and any host profile probe.
   - *Unimplemented future entries:* `stage1a_*`, `stage1b_*`, Stage-2 direct-stock runner/amended scorer, Stage-3 private replay runner.
4. **Bundle vs Git Archive Scope (p. 18):** Explicitly state that `bundle/sources/plan43.json` adds a trailing `\n` (`6,574` B vs Git `6,573` B), that `02-verify-wheelhouse.json`, `03-pip-check-and-venv-inventory.json`, `05-preflight-cpu.json`, `F07.warm1.token_ids.json`, and the 6 WP-0043 sibling modules (`timing`, `bindings`, `capture`, `transfer`, `native_observer`, `limits`) live in pinned Git `e43af2e2` outside the standalone ZIP, and that historical `exec.backend` booleans (`tf32`, `cudnn_tf32`, `deterministic`, `autocast`) and `@venv/pyvenv.cfg` digest are absent globally from public Git `e43af2e2`.
