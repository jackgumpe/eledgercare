# PostgreSQL 18.7 Windows binaries: acquisition and validation (BIC-06)

Author: eld-implementer, WP-0003 / 001. Executed 2026-11-14 on Windows x64, worktree-owned paths only.

## Source and identity

| Item | Value |
| --- | --- |
| Official route | https://www.postgresql.org/download/windows/ → EDB "Download PostgreSQL Binaries" page (https://www.enterprisedb.com/download-postgresql-binaries), Version 18.7, Windows x86-64 link `getfile.jsp?fileid=1260664` |
| Resolved archive | https://get.enterprisedb.com/postgresql/postgresql-18.7-1-windows-x64-binaries.zip |
| Content-Length | 389,515,503 bytes |
| ETag / Last-Modified | `"8f6c6a2cecbbcb81f373cccf044af2ea-47"` / Thu, 12 Nov 2026 11:20:46 GMT |
| Zip central directory | offset 386,879,447, size 2,636,034, 22,284 entries, SHA-256 `3132ca63b424f7ec371eabe50753ad7cd036278d942a6ea465547b17bf90a149` |
| Extracted subset | `pgsql/bin/`, `pgsql/lib/`, `pgsql/share/` and `pgsql/` root files: 1,597 files, 151,078,582 bytes |
| Subset manifest SHA-256 | `47c3deb9c917f79c353b3683b2c2611ee975285ea06226c8f72444c96ce9051f` (SHA-256 of the `"<sha256>  <path>"` lines, sorted by path) |
| Per-file list | [postgresql-18.7-1-server-subset.sha256](postgresql-18.7-1-server-subset.sha256) |
| Whole-archive SHA-256 | **not computed** — see limitation below |

## Why a verified subset instead of the whole archive

Observed network throughput during this session was ~17–110 KB/s (measured: single connection 17 KB/s
via PowerShell `Invoke-WebRequest`, 41–79 KB/s with curl, ~107 KB/s aggregate across six parallel range
requests; all to the same IPv4 CloudFront edge 13.224.125.24, so not a DNS/IPv6 issue). The central
directory showed `pgsql/pgAdmin 4` occupies 318,396,799 of the 389,515,503 bytes (82 %); the server
needs only bin/lib/share (~54.5 MB compressed). [fetch_server_subset.py](../../../../deploy/dev/postgres/fetch_server_subset.py)
therefore downloads only those entries by HTTP range requests and, for every entry, verifies the local
header name against the central directory, the compressed and uncompressed sizes and the CRC-32 before
writing it, rejecting encrypted/unsupported entries and unsafe paths. No vendor checksum for this archive
was found on the download page, so a whole-archive SHA-256 would also only identify "the bytes this
session received"; the subset manifest provides the same reproducible comparison for the files actually used.

## Validation executed

| Check | Result |
| --- | --- |
| `postgres.exe --version`, `initdb --version`, `pg_ctl --version`, `psql --version` | all `(PostgreSQL) 18.7` |
| Authenticode (`Get-AuthenticodeSignature`, pwsh 7.7) on every `.exe`/`.dll` in the subset | **161 / 161 Valid**, signer `CN=EnterpriseDB Corporation, O=EnterpriseDB Corporation, L=Wilmington, S=Delaware, C=US` |
| `postgres.exe` SHA-256 | `4e67c961ac182a36c44a18fefcb5548d1ad5b40b252abb9cfa1259112d7faf75` |
| `initdb.exe` SHA-256 | `1bb6b320887e52e45d1cdf0e7db57aded35854992cabc31bdba525f774708483` |
| `pg_ctl.exe` SHA-256 | `5083fb9353a569ab00cefb8bee79f2e9b98b96ae527fdae2fb30a2737d11aff4` |
| `psql.exe` SHA-256 | `3b1dc3f517736ea9ecfc0a5609269e8d5661e98262c1f88e0d65d99175dc4b57` |
| `libpq.dll` SHA-256 | `bc55be2d69cd88bb82531595e599240a04940478b5161954a68d7a6737155645` |
| `initdb` (scram-sha-256, UTF8, no locale; data checksums on by PG 18 default) | success |
| Start / query / stop / start | `pg_ctl start` → ready; `SHOW`-equivalent `pg_settings` query; fast stop; restart — see the decisive run and demo receipt |

## Owned cluster configuration

`.local/postgres-data` (ignored), appended settings: `listen_addresses='127.0.0.1'`, `port=55432`,
`unix_socket_directories=''`, `password_encryption='scram-sha-256'`, `fsync=on`, `full_page_writes=on`,
`synchronous_commit=on`, `wal_level=replica`. `pg_hba.conf` contains a single line:
`host all all 127.0.0.1/32 scram-sha-256`. Roles: `eledgercare_admin` (bootstrap superuser, setup and
test harness only), `eledgercare_migrator` (database/schema owner, migrations),
`eledgercare_app` (runtime: `CONNECT`, `USAGE` on schema `eledgercare`, `SELECT, INSERT` on the three F1
tables). Random passwords are generated into `.local/secrets/pg-local.json` and passed to `psql` via
stdin/`PGPASSWORD` in-process only. No Windows service, installer, PATH change, firewall rule or
machine-wide configuration was created.
