# Gesture Glove — SMVIT 2026–2027

Team: **Mykhailo Sichkaruk (ST033)** and **[Yaroslav Marochok](https://github.com/ymarochok) (ST029)**.
Our goal is to complete the SMVIT semester project. The assigned team PRJ number is pending.
This is an independent repository created from the teacher's KNIFE/STHDF template.

## Start here

- [Team project and course structure](content/docs/sk/sthdf/PRJ-PENDING-GestureGlove/index.md)
- Individual work: [Mykhailo](content/docs/sk/sthdf/ST-033-SichkarukMykhailo/index.md), [Yaroslav](content/docs/sk/sthdf/ST-029-MarochokYaroslav/index.md)
- [Development setup, Arch graphics and MCP](docs/development.md)
- [Project decisions and AI handoff](docs/project-context.md)
- [Template provenance and submission questions](docs/template-provenance.md)
- [Original idea](hardware/reference/glove_smvit.pdf)
- [Existing CAD examples](examples/poc/README.md) — tooling PoCs, not validated device designs

## Development

Install Nix with flakes enabled. From this checkout:

```sh
nix develop
# Optional automatic shell entry, if direnv is installed and hooked into your shell:
direnv allow
```

Open the editable examples:

```sh
nix run .#freecad -- examples/poc/cad/glove-poc.FCStd
nix run .#eeschema -- examples/poc/electronics/glove/gesture-glove-v2.kicad_sch
nix run .#fritzing -- examples/poc/electronics/fritzing/gesture-glove.fzz
```

Documentation only (no CAD downloads):

```sh
nix develop .#docs
npm ci --prefix publishing/docusaurus
make build
make serve
```

Write course material in `content/docs/`; the copy under `publishing/docusaurus/docs/` is generated.
CI builds the site and saves an artifact; it does not publish or submit it to the teacher.
The inherited npm dependency lock currently reports audit findings; see [validation notes](docs/validation.md).

## Team workflow

Use a short feature branch, commit source files, and review through a pull request.
Agree who edits a binary `.FCStd` or `.fzz` before starting: Git cannot reliably merge simultaneous edits.
Keep one person editing a KiCad sheet at a time; text-based storage does not guarantee a safe merge.
Record each student's contribution in their own ST section, with links to commits/results.
Keep course rosters, meeting access details, tokens, machine-specific settings and CAD caches in ignored `.local/`.

The toolchain targets x86_64 Linux on NixOS or another distribution with Nix.
Actual Arch GUI acceptance remains a teammate check; there is no dependency on Codex for manual development.
