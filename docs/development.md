# Development setup

## Nix on NixOS and Arch Linux

Use the same committed `flake.lock` on both systems. Enable flakes in the user's Nix config if needed:

```ini
experimental-features = nix-command flakes
```

No NixOS module or system-wide CAD installation is required. Supported architecture: x86_64 Linux.
`nix develop` includes CAD, MCP servers and documentation tools. `nix develop .#docs` is the smaller documentation environment.
The optional `.envrc` uses direnv; install/hook direnv separately or just use `nix develop`.
Do not commit `.direnv`, `.local`, personal credentials or `.envrc.local`.

## Graphics on Yaroslav's Intel/NVIDIA Arch laptop

The display server and working GPU drivers belong to the host OS. Nix supplies the applications.
All three GUI launchers use the same `SMVIT_GL` switch:

| Mode | Behavior |
| --- | --- |
| `auto` | Native on NixOS; NVIDIA if its kernel driver is present elsewhere, Mesa otherwise |
| `native` | Use host/NixOS graphics environment directly |
| `mesa` | Pinned nixGL Mesa wrapper (Intel/AMD); try the integrated Intel GPU first |
| `nvidia` | Build nixGL for the running host NVIDIA driver, then launch the app |
| `software` | Mesa software rendering for diagnostics |

First Arch test, from the repository root:

```sh
SMVIT_GL=mesa nix run .#freecad -- examples/poc/cad/glove-poc.FCStd
SMVIT_GL=mesa nix run .#eeschema -- examples/poc/electronics/glove/gesture-glove-v2.kicad_sch
SMVIT_GL=mesa nix run .#fritzing -- examples/poc/electronics/fritzing/gesture-glove.fzz
```

To retain that preference with direnv, put `export SMVIT_GL=mesa` in ignored `.envrc.local`, then run `direnv allow`.
If the desktop is wired to NVIDIA, try `SMVIT_GL=nvidia`. This opt-in path uses impure evaluation to read the host driver version and may download the matching proprietary driver libraries. The normal flake remains pure. On hybrid systems the active display/PRIME configuration matters; neither mode is claimed validated on Arch yet.
The nixGL source and application packages share the pinned nixpkgs input. See [nixGL](https://github.com/nix-community/nixGL).

Acceptance on Arch: open each example, rotate/zoom FreeCAD, pan KiCad, move a Fritzing part in a disposable copy, close and reopen. Record OS/GPU/driver/mode and errors in `docs/validation.md`.

## Optional Codex integration

The shared `.codex/config.toml` only adds MCP servers. It contains no absolute checkout path, account, model or permissions settings.
Each command finds the Git root, then runs its server through the pinned flake. It works from the root or a nested directory.
Codex loads project configuration for trusted projects; personal/global settings remain user-local. See [official OpenAI documentation](https://developers.openai.com/codex/mcp/).
Prebuild once before launching Codex so downloads do not consume its startup timeout:

```sh
nix build .#freecad .#freecad-mcp .#kicad .#kicad-mcp .#fritzing .#fritzing-mcp --no-link
```

FreeCAD must be opened using the project launcher to start its local RPC add-on (127.0.0.1:9875).
KiCad MCP operates the PCB Editor through its IPC API; it is not a complete schematic editor. The launcher enables the API in isolated local preferences.
Fritzing MCP edits native sketch files and can open/render them with the application.
Launch one project FreeCAD/PCB Editor instance at a time when running integration checks.

```sh
nix develop -c python scripts/check_mcp_servers.py
nix develop -c python scripts/check_glove_connections.py
# With project FreeCAD running:
nix develop -c python scripts/check_mcp.py
# Native sketch edit / undo-to-original check and render in .local/:
nix develop -c python scripts/check_fritzing_mcp.py
```

Teams MCP stays disabled until STU consents to its Microsoft application. The optional wrapper pins the Softeria npm release but fetches its dependency tree through npx on first use; it is not a fully Nix-locked npm closure. No teammate needs it for CAD or docs.

## Course documentation

```sh
nix develop .#docs
npm ci --prefix publishing/docusaurus
make build
make serve
```

The site is local by default. CI uploads its static build as an artifact. GitHub Pages publishing and the teacher's actual hand-in route are separate steps, still to be configured/confirmed.
Use `make S31-sthdf-new STHDF_NAME=... STHDF_TITLE=... LOCALE=sk` for another teacher-template instance.
When the teacher assigns a PRJ number, rename the provisional project directory/repository and update its ID and incoming links together. Keep ST033/ST029 as the roster identities; directory names follow the teacher's hyphenated style.

For the live KiCad edit check, copy the disposable fixtures first, open the PCB, wait for the editor to finish loading, then run the check from another shell:

```sh
mkdir -p .local/kicad/smoke-test
cp scripts/fixtures/integration-test.kicad_* .local/kicad/smoke-test/
nix run .#pcbnew -- .local/kicad/smoke-test/integration-test.kicad_pcb
# In another terminal, from the repository root:
nix develop -c python scripts/check_kicad_mcp.py
```
