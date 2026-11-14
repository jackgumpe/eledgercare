# WP-NNNN / SSS: Short descriptive title

- Report path: `docs/agent-reports/<agent-id>/WP-NNNN/SSS_YYYY-MM-DD_category_agent-id.md`
- Sequence reservation: pinned INDEX.md link or coordinator reservation reference
- Category: research | design | implementation | review | verification | incident
- Author / agent ID:
- Actual model / effort: (use "not exposed" if unknown)
- Execution environment: CLI | API | web | other; relevant versions when exposed
- Published by: (if the coordinator publishes on behalf of the author)
- Timestamp: YYYY-MM-DDTHH:MM:SSZ
- Repository / branch:
- Base revision: full commit SHA before the reported work
- Deliverable revision: full commit SHA inspected or produced
- Previous report:
- Related or reviewed reports: pinned links; report identities WP-NNNN / SSS
- Status: in-progress | blocked | ready-for-review | changes-requested | accepted
- Next owner:

## Summary

Brief outcome, unfinished work, and whether this is author verification or independent review.
For a newly authored report, the directory owner, filename agent ID, and author metadata must agree. Use a packet-wide reserved sequence, even when this is your first report in that packet. Review another agent's work from your own directory. User-authorized historical moves and link repairs use the migration guide; they do not change original authorship or findings.

## Objective and acceptance criteria

State the authorized packet scope and observable completion conditions.

## Change inventory

| Action | Exact path or external resource | What changed and why | Relevant symbols |
| --- | --- | --- | --- |
| Added / modified / deleted / renamed | | | |

Account for every path in the base-to-deliverable diff. List report/index metadata committed afterward separately. For external changes, record target identity, result, and persistence status.

## Decisions and rationale

Explain necessary logic, alternatives, rejected complexity, assumptions, and any evidence limitations.

## Verification

| Check / exact command or tool operation | Environment and revision | Actual result | Evidence location |
| --- | --- | --- | --- |
| | | | |

Separate executed checks from proposed checks. List checks not run and why.
Do not include secrets in commands or logs.

## Review map

Link the pinned diff, relevant files and symbols, and supporting evidence.
A reviewer must inspect actual changes, not just this summary.

## Risks, disagreements, and unfinished work

Include failures and uncertainty. For escalation, state the decision needed, both positions and evidence, attempted reconciliation, and consequences.

## Handoff

Specify next action, next owner, required revision, and outstanding acceptance checks. Give the coordinator the branch, report path, report publication SHA (in the handoff message after publication), and deliverable SHA so the index can be updated. Only the designated index writer edits INDEX.md.
Publication receipt: confirm the remote contains the report and deliverable revision, or explicitly state that remote confirmation is pending. The receiving agent can record that confirmation in its review; do not rewrite a published historical report to add it.
