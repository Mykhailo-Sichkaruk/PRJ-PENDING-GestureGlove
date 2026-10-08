# Archived tooling proof of concept

These are editable examples, not final course deliverables or fabrication files.

From the repository root:

```sh
nix run .#freecad -- examples/poc/cad/glove-poc.FCStd
nix run .#eeschema -- examples/poc/electronics/glove/gesture-glove-v2.kicad_sch
nix run .#fritzing -- examples/poc/electronics/fritzing/gesture-glove.fzz
```

The v2 KiCad schematic is the preferred electrical example. Original drafts remain here for reference.
Do not order a PCB or connect a battery from these conceptual examples.
Generators require an explicit `--replace-generated` option before overwriting examples.
