# Migration validation — 2026-10-08

Verified on the original x86_64 NixOS host using the staged checkout at a different path:

- `nix flake check --no-build`: all outputs evaluate in pure mode.
- Built FreeCAD, KiCad, Fritzing and their MCP launchers with the pinned dependencies and graphics wrapper.
- `nix develop .#docs`: independent documentation toolchain; Node 22.23.3.
- `npm ci --prefix publishing/docusaurus` and `make build`: Slovak and English static sites build, including broken-link checks.
- All three CAD MCP servers initialize and list tools from both the checkout root and a nested directory: FreeCAD 17, KiCad 19, Fritzing 14 tools.
- FreeCAD GUI reopened the moved FCStd; RPC reported healthy and a rendered isometric screenshot showed the glove.
- KiCad GUI opened a disposable fixture; MCP created, read back and deleted a track. The first request arrived before KiCad was ready; retry after startup passed.
- Fritzing MCP searched parts, created/placed/wired/removed components, moved and restored a part in a copy, validated it and rendered SVG/PNG using native Fritzing.
- All 16 example KiCad/Fritzing nets still match.

The examples themselves were moved, not redesigned. These checks do not validate an electrical design or wearable safety.
Actual Arch Intel/NVIDIA GUI behavior remains to be checked by Yaroslav. The graphics bridge is configured, not claimed tested on his machine.

The teacher's original npm lockfile reports 81 audit findings (6 low, 16 moderate, 40 high, 19 critical) at installation time. It was preserved for this migration; no automatic breaking dependency upgrade was applied. Treat dependency updates as a separate follow-up before exposing a development server. Current CI produces static artifacts and does not publish a server.

The optional Teams wrapper is not part of these checks; university consent remains pending.

A clean Git clone at an unrelated `/tmp` path also passed pure flake evaluation, all six MCP initialization checks, the 16-net comparison and the complete Fritzing edit/render check. Its local Fritzing part cache was created from the committed part bundles.
