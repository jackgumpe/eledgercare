# WP-0002 / 002 primary-source and candidate verification dossier

- Reviewer / stable ID: `eld-reviewer`
- Inspected candidate revision: `e90c71817bc793dfbfc7576006be3cbf0b4310bf`
- Root seed revision: `35f6090a9b2e16c7645b56f34b104eb3126d5c90` (verified 0 parents)
- Seed receipt revision: `287183ceec005195d03e83649a3f91c41ae4fcd1`
- Scope: deterministic read-only inspection of the candidate, seed, and primary upstream sources. **Document, source, and registry metadata inspection only; zero application builds, dependency restores, database launches, PDF parser runs, or OCR executions were performed.**

## 1. Git ancestry, file inventories, and supplied-kit hashes

1. `git rev-list --parents -n 1 35f6090a9b2e16c7645b56f34b104eb3126d5c90` returned only `35f6090a9b2e16c7645b56f34b104eb3126d5c90` (0 parents; root commit confirmed, no fabricated base SHA).
2. Exact tracked path counts and diffs:
   - `35f6090a9b2e16c7645b56f34b104eb3126d5c90`: 20 files, matching `WP-0001 / 001` 1:1.
   - `35f6090..287183c`: `M CURRENT.md`, `M INDEX.md`, `A docs/agent-reports/eld-coordinator/WP-0001/001_2026-11-14_verification_eld-coordinator.md`, `A docs/kickoffs/WP-0004-eld-rd-astra.md`, `A docs/kickoffs/WP-0004-eld-rd-carbon.md`.
   - `287183c..e90c718`: `A docs/design/F1-durable-intake.md`, `A docs/design/dependency-metadata-2026-11-14.json`.
   - `git diff --check 35f6090..e90c718`: clean (0 whitespace errors).
   - Local Markdown link scan across all 19 `.md` files in `e90c71817bc793dfbfc7576006be3cbf0b4310bf`: 0 broken local relative links.
3. Authenticated `gh api repos/jackgumpe/eledgercare`: confirmed `private: true`, `visibility: "private"`, `default_branch: "coordination/bootstrap"`.
4. Bootstrap-kit SHA-256 and byte-length verification against `docs/inputs/bootstrap-kit/manifest.json`:

| File | Manifest bytes | Actual bytes | Actual SHA-256 | Manifest match |
| --- | --- | --- | --- | --- |
| `00-START-COORDINATOR.txt` | 9288 | 9384 | `162cc5c3653b6d277e68087c4d0e3f8d7b4d38089bacced12040c2054989baa1` | No — matches `kit-provenance.md` disclosure |
| `01-REPOSITORY-CONTRACT.md` | 10954 | 10954 | `636a360640d556a8436f641a959c353d2009d4378fafa5e0f2314c6bfcc3ba57` | Yes |
| `02-PRODUCT-BRIEF.md` | 6170 | 6170 | `ecdbfbc1bec0f8a39982e963338fdf95b1bdca1e9fb3d1f93f32b2279bfd5670` | Yes |
| `03-RD-BRIEF.md` | 8056 | 8056 | `61c4dd429e8eeba0fc2b854551b8d4bd84bbfb74c18a10f26894418ea89decca` | Yes |
| `04-ENVIRONMENT-RECEIPT.txt` | 6338 | 6338 | `5a6baf0349f3819c71ebb0fc838d52693cfce1bda84ca4d16057962fbeef380e` | Yes |
| `05-SOURCES-AND-LIMITS.md` | 5159 | 5159 | `66f64fd67867dc9c15f05cebd14f62b2824a13e9cfc0cf6316d05794f776045a` | Yes |
| `06-REPORT-TEMPLATE.md` | 3199 | 3199 | `75f2f2788446fc26b0ddea7647ce9ca1ccf8046e5988ed3df9687d78aa53f8f5` | Yes |

## 2. Primary-source inspection of `UglyToad/PdfPig` `0.1.16`

Annotated tag `v0.1.16` (`49ddb62c146d326f90785ed1ca6ca99852768036`) resolves to commit `a7bb35662bbbf405efddad50aedc9bcdcf515afc`, matching `dependency-metadata-2026-11-14.json`. Direct inspection of upstream C# source at `a7bb35662bbbf405efddad50aedc9bcdcf515afc` established five concrete parser behaviors affecting [F1-durable-intake.md](../../../design/F1-durable-intake.md) Step 4:

| Upstream file and lines (`a7bb35662bbbf405efddad50aedc9bcdcf515afc`) | Verified source behavior | Impact on `F1-durable-intake.md` Step 4 |
| --- | --- | --- |
| `src/UglyToad.PdfPig/ParsingOptions.cs` L28-L59 | Exposes `UseLenientParsing` (default `true`), `SkipMissingFonts` (default `false`), `MaxStackDepth` (default `256`), `Password` (default `""`), `Passwords` (default empty list). | Property names and types in `F1-durable-intake.md` match `0.1.16`. |
| `src/UglyToad.PdfPig/Parser/FileStructure/FileHeaderParser.cs` L63-L68, L152-L160 | `GetHeaderVersionAndResetScanner` checks `!comment.Data.StartsWith("PDF-1.") && !comment.Data.StartsWith("FDF-1.")` and delegates to `HandleMissingVersion`, which **throws `PdfDocumentFormatException` whenever `isLenientParsing == false`**. | **Substantive contradiction (`SB-01`)**: Step 4 admits `%PDF-2.0` at the byte-0 header check and also mandates `UseLenientParsing=false`, under which PdfPig `0.1.16` unconditionally rejects every `%PDF-2.0` file with `PdfDocumentFormatException` (`422`). (The byte-0 `%PDF-` pre-check is still essential because `FileHeaderParser` otherwise accepts `%FDF-1.x` and tolerates up to 30 leading junk tokens.) |
| `src/UglyToad.PdfPig/Parser/PdfDocumentFactory.cs` L516-L519; `src/UglyToad.PdfPig/Encryption/EncryptionHandler.cs` L47-L55, L122-L164; `src/UglyToad.PdfPig/PdfDocument.cs` L151 | `PdfDocumentFactory.Open` and `EncryptionHandler` always append `string.Empty` (`""`) to `passwords`. Any PDF with an `/Encrypt` dictionary whose user password is empty (standard owner-password / permissions-locked PDFs) decrypts silently without throwing `PdfDocumentEncryptedException` on `Open` or `GetPage(i)`. `document.IsEncrypted` remains `true` (`encryptionDictionary != null`). | **Substantive gap (`SB-02`)**: Exception-only handling silently accepts owner-password-encrypted PDFs (`201 Created`). Step 4 must explicitly reject `document.IsEncrypted == true` with `422` immediately after `Open`. |
| `src/UglyToad.PdfPig/Parser/PageFactory.cs` L65-L77; `src/UglyToad.PdfPig/Graphics/ContentStreamProcessor.cs` L294, L355-L370; `src/UglyToad.PdfPig.Fonts/SystemFonts/WindowsSystemFontLister.cs` L9-L42 | `document.GetPage(i)` runs `ContentStreamProcessor.Process`, constructing in-memory `Letter` glyph/text objects, and `TrueTypeFontHandler` queries `SystemFontFinder.Instance` -> `WindowsSystemFontLister`, enumerating `C:\Windows\Fonts` when non-embedded TrueType fonts are referenced. | **Substantive precision item (`SB-02`)**: Step 4 must check `document.NumberOfPages` in `1..MaxPages` *before* visiting `1..NumberOfPages`, clarify that "do not extract/persist text" forbids *application* consumption/return/persistence of `Page.Text`/`Letters` (while acknowledging PdfPig's internal glyph parsing and local OS font lookup), and require synthetic product fixtures to embed or use standard-14 PDF fonts. |
| `src/UglyToad.PdfPig/Filters/FlateFilter.cs` L194-L208; `src/UglyToad.PdfPig/Parser/FileStructure/FirstPassParser.cs` L550-L560 | `FlateFilter.Decode` catches exceptions from `Decompress` (`catch { // ignored. }`) and returns raw compressed `input` bytes without throwing; `FirstPassParser.Parse` falls back to `XrefBruteForcer` even when `UseLenientParsing == false`. | Reinforces `F1-durable-intake.md` L40 warning that PdfPig is not a full conformance validator or decompression-bomb sandbox; `DI-07` corrupted-input fixtures must test verified rejection paths rather than assuming corrupted Flate streams throw by themselves. |

## 3. Primary-source and local environment verification of toolchain/dependencies

| Area | Check performed | Observed result | Implication |
| --- | --- | --- | --- |
| .NET SDK & runtimes | `dotnet --list-sdks`, `dotnet --list-runtimes`, `dotnet test --help` | SDKs `10.0.301`, `10.0.403`; runtimes `10.0.9` and `10.0.14` (`NETCore.App`, `AspNetCore.App`, `WindowsDesktop.App`). `dotnet test --help` in `10.0.403` states default is VSTest unless opted into `Microsoft.Testing.Platform` via `global.json`. | `global.json` must include `"test": { "runner": "Microsoft.Testing.Platform" }` alongside `"sdk": { "version": "10.0.403", "rollForward": "disable", "allowPrerelease": false }`, and test projects must use `<OutputType>Exe</OutputType>` without VSTest packages (`BIC-04`). |
| `dotnet-ef` `10.0.15` vs `10.0.14` host runtime | Read-only in-memory inspection of `dotnet-ef.10.0.15.nupkg` `tools/net8.0/any/dotnet-ef.runtimeconfig.json` | Tool targets `tfm: "net8.0"` with `framework.version: "8.0.0"` and `rollForward: "Major"`. | Compatible with installed `Microsoft.NETCore.App 10.0.14`. Verify clean OOB `Microsoft.Extensions.* 10.0.15` assembly resolution during `WP-0003` scaffold build (`BIC-04`). |
| `xunit.v3` `4.0.3` & `Npgsql` `10.0.3` | Read-only NuGet flatcontainer `.nuspec` checks for `xunit.v3.mtp-v2/4.0.3` and `npgsql/10.0.3` | `xunit.v3.mtp-v2` depends on `xunit.v3.core.mtp-v2 [4.0.3]`, `xunit.v3.assert [4.0.3]`, `xunit.analyzers 2.3.0`; `Npgsql 10.0.3` targets `net10.0` (`d3768398c17877b3a916c3c4d87e8e11698991fc`). | Consistent with `dependency-metadata-2026-11-14.json`; lockfiles remain unexecuted bootstrap work. |
| Angular `22.2.6` npm metadata & host IPv6 behavior | `urllib` / `curl.exe` default dual-stack vs `curl.exe -4` against `registry.npmjs.org` | Default dual-stack (IPv6-preferred) timed out during TLS handshake (`_ssl.c:993` / `curl: (28)`); `curl.exe -4` succeeded, matching exact `sha512` hashes and confirming `zone.js`, `@angular/compiler`, and `@angular/animations` are `optional: true` in `peerDependenciesMeta`. | Metadata pins are coherent; record IPv4 DNS-order fallback (`--dns-result-order=ipv4first`) if `npm` restore stalls over IPv6 in `WP-0003` (`BIC-05`). |
| PostgreSQL `18.7` & local ports/services | Read-only check of `postgresql.org/versions.json`, EDB binaries page, `docker version`, `Get-Command`, `Test-Path`, and `netstat -ano` | `18.7` confirmed current (`relDate: 2026-11-12`). `dockerDesktopLinuxEngine` pipe absent; `postgres`/`pg_ctl`/`psql` absent on `PATH` and `C:\Program Files\PostgreSQL\{17,18}`; ports `5180, 4200, 55432, 5280, 4300, 55433, 5432` had no active listeners at check time. | Vendor binary archive URL/SHA-256 and owned per-worktree `initdb`/`pg_ctl` launch remain unexecuted setup gates (`BIC-06`). |
