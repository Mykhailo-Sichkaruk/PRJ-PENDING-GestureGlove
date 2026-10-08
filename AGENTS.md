# Project instructions

The purpose of this repository is to complete the SMVIT semester course as a team.
Read README.md and docs/project-context.md before changing project direction.

- Use the pinned Nix shell. On the original NixOS host, missing diagnostic CLIs can be run with `, toolname`.
- Keep all shared tooling portable: no personal absolute paths, credentials or account settings.
- Course source is `content/docs/`; `publishing/docusaurus/docs/` is generated.
- `examples/poc/` proves tool integration; it is not a validated wearable design.
- Preserve the teacher template structure and licenses, including per-file license notices.
- Do not invent PRJ/ST identifiers, measurements, student contributions or completed deliverables.
- Test native CAD files by reopening them in the actual app when changing their content.
- Coordinate binary CAD edits: one editor per file at a time; use branches/PRs for code and prose.
- Keep private course PDFs and account data under ignored `.local/`, never in Git.
