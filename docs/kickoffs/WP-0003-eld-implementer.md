# WP-0003 / 001: Opus reproducible scaffold and durable intake

Status: FULLY PREPARED, **HELD / NOT STARTED**. Do not execute implementation or dependency setup from this assignment until eld-coordinator records Carbon's acceptance/disposition of the exact WP-0002 design. If the reviewed design changes, the coordinator must refresh this full base and kickoff before release.

- Stable ID: eld-implementer.
- Requested model: Opus via the existing Claude CLI if available. Record actual model/effort/session/provider from exposed execution metadata; a CLI alias does not prove backend identity.
- Repository: https://github.com/jackgumpe/eledgercare, PRIVATE.
- Owned branch: feature/wp-0003-durable-intake.
- Owned worktree: C:\Users\jackg\Asp.net Projects\eledgercare-worktrees\eld-implementer.
- Full prepared base/design candidate: e90c71817bc793dfbfc7576006be3cbf0b4310bf.
- Canonical reservation: coordinator INDEX.md, WP-0003 / 001; this externally delivered kickoff supersedes stale routing at the base.
- Exact report: docs/agent-reports/eld-implementer/WP-0003/001_2026-11-14_implementation_eld-implementer.md.
- Next reviewer: eld-reviewer / Carbon, WP-0003 / 002, in a different worktree/cluster on a subsequently frozen product candidate.

Read AGENTS.md, START_HERE.md, the coordinator's release disposition, docs/design/F1-durable-intake.md, its dependency metadata, kit 01/02 and the report template. Do not begin from an old product checkout or read another team's unrelated sources.

Objective after release: build the one production .NET solution, Angular shell, explicit PostgreSQL setup/migrations and the reviewed F1 behavior. First freeze reproducible dependency/setup choices, then implement durable intake. Fulfil DI-01 through DI-08 author-side evidence; DI-08 independent acceptance belongs to Carbon, never to you.

Allowed product paths: ELedgerCare.slnx, global.json, Directory.Build.props, Directory.Packages.props, NuGet.Config, .editorconfig, .config/dotnet-tools.json, source dependency locks, src/**, web/**, tests/**, deploy/**, contracts/**, workers/ocr/README.md, evaluation/product-smoke/**, docs/product/**, docs/evidence/WP-0003/eld-implementer/**, your exact report, README.md setup guidance and narrowly needed .gitignore entries. No AGENTS.md/START_HERE.md/INDEX.md/CURRENT.md changes, reviewed-design rewrites, research/** edits, R&D evaluation/corpus edits or other authors' reports. Notify the coordinator when scope or a substantive design/pin correction is needed.

Allowed external effects after release: project-local dependency restores/tool environments; scoped Windows PostgreSQL binary acquisition and validation from the official linked route; an owned per-worktree PostgreSQL cluster; local-only API/UI/test processes and disposable owned test databases. Use your worktree .local/ for binaries/data/logs/credentials and .scratch/ for transient evidence; keep these ignored. Candidate ports API 5180, UI 4200, PostgreSQL 55432; check actual bind/ownership before start. Bind to 127.0.0.1. Stop only processes you started and verified by PID/start time. No global installs/configuration, unrelated containers/services/databases, public/intranet deployment, production/customer data, model downloads or GPU use. Do not auto-start Docker Desktop as a workaround.

Pins: .NET SDK 10.0.403 with disabled roll-forward and no previews; Node 24.18.0/npm 11.16.0; Angular framework 22.2.6/tooling 22.2.7; TypeScript 6.0.3; RxJS 7.8.2; tslib 2.8.1; EF/Design/dotnet-ef 10.0.15; Npgsql EF 10.0.3; PdfPig 0.1.16; PostgreSQL 18.7; xunit.v3 4.0.3/MTP v2; Vitest 4.0.18 and Playwright 1.65.1 when used. Freeze actual resulting direct/transitive packages in lockfiles. The design lists what was observed versus unqualified; do not treat version metadata as a passing build. Vendor binary build/hash and actual PostgreSQL launch are still unresolved setup gates. No qualified Python/OCR environment is required for F1.

Implement exactly the accepted raw-PDF/body limit policy, bytea atomic transaction, unique retry identity, stable document/job references and honest awaiting_extraction state. No OCR mock, broad framework, multiple database providers or speculative future classes. Do not weaken acceptance criteria because a dependency/service is unavailable. Use a minimal source-first synthetic fixture independent of the research corpus, documenting bytes/hash and provenance.

Freeze a code candidate before decisive builds, real HTTP/PostgreSQL/restart/retry/failure checks. Record actual counts, source/dependency pins, server settings, process ownership, migrations, fixture/digest and limitations. Do not claim app restart proves power-loss durability. Commit any resulting source fixes as a new candidate and rerun affected checks. Commit compact evidence and the canonical report afterward, inventorying every path and all installation/service effects separately. Push only your owned branch and verify remote publication. Send deliverable, evidence/report SHAs, report path, exact commands/results and remaining limitations to the coordinator for independent Carbon review.
