# eLedgerCare

An on-premises intranet document application. The first customer feature is to retain a submitted maintenance PDF, its original bytes, and its honest processing status across an application restart. Demonstration target: 26 November 2026.

This is a **provisional coordination seed**. Jack approved the direction; the contract and detailed design have not yet received independent technical acceptance. No application is implemented or released by this seed.

Start with [START_HERE.md](START_HERE.md). Current assignments are in [CURRENT.md](CURRENT.md); packet and report reservations are in [INDEX.md](INDEX.md).

Direction: ASP.NET Core 10, Angular 22, EF Core/Npgsql 10, PostgreSQL, and a later separately qualified local Python OCR worker. Product and research have separate dependency graphs and environments. There will be one production .NET solution.

Source is private unless Jack explicitly changes that decision. Public fixtures do not authorize public source publication. Do not place customer documents, secrets, database contents, uploads, model weights, or large corpora in Git.
