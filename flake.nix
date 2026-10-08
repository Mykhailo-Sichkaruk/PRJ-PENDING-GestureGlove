{
  description = "SMVIT gesture glove: course documentation, CAD, and optional MCP tooling";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    nixgl = {
      url = "github:nix-community/nixGL/b6105297e6f0cd041670c3e8628394d4ee247ed5";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    freecad-mcp-src = {
      url = "github:neka-nat/freecad-mcp/d6bbe4b38be3a622b5981d9d2afa7037ee080534";
      flake = false;
    };
    kicad-mcp-src = {
      url = "github:NiRuLabs/kicad-mcp-server/2fd14d32fb2532071649cf6779b5e97b524e0a1b";
      flake = false;
    };
    kicad-sch-api-src = {
      url = "github:circuit-synth/kicad-sch-api/505bca23e91cf3fa6e3b66976e529e775eada3ba";
      flake = false;
    };
    fritzing-mcp-src = {
      url = "github:fedoragobrowse-design/fritzing-mcp/3a8c7ca9b4b9ec52f356070670c05c651f096c24";
      flake = false;
    };
  };

  outputs =
    {
      nixpkgs,
      nixgl,
      freecad-mcp-src,
      kicad-mcp-src,
      kicad-sch-api-src,
      fritzing-mcp-src,
      ...
    }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      # Host NVIDIA driver discovery is deliberately lazy and opt-in (see gui.sh).
      mesaGL =
        (import nixgl {
          inherit pkgs;
          enable32bits = false;
        }).nixGLIntel;
      gui = pkgs.writeShellApplication {
        name = "smvit-gui";
        runtimeInputs = [
          pkgs.gitMinimal
          pkgs.coreutils
        ];
        text = ''
          export SMVIT_MESA_WRAPPER="${mesaGL}/bin/nixGLIntel"
          exec ${pkgs.bash}/bin/bash ${./scripts/gui.sh} "$@"
        '';
      };
      courseTools = with pkgs; [
        bash
        gitMinimal
        gnumake
        nodejs_22
        python3
        rsync
        coreutils
        gnused
        gawk
      ];
      python = pkgs.python3;
      py = python.pkgs;

      # Upstream freecad-mcp requires a newer MCP SDK than this Nixpkgs pin.
      mcpSdk = py.mcp.overridePythonAttrs (old: {
        version = "1.28.1";
        src = pkgs.fetchPypi {
          pname = "mcp";
          version = "1.28.1";
          hash = "sha256-1R42pfVkT66k+F6mSb//prxsJncNQnmK1qPePSumloM=";
        };
        dependencies = old.dependencies ++ [
          py.typing-extensions
          py.typing-inspection
        ];
        # SDK network/process tests are not part of installing this application.
        # scripts/check_mcp.py exercises the real stdio server and GUI instead.
        doCheck = false;
        meta = old.meta // {
          changelog = "https://github.com/modelcontextprotocol/python-sdk/releases/tag/v1.28.1";
        };
      });

      freecadMcp = py.buildPythonApplication {
        pname = "freecad-mcp";
        version = "0.1.25";
        src = freecad-mcp-src;
        pyproject = true;
        build-system = [ py.hatchling ];
        dependencies = [
          mcpSdk
          py.validators
        ]
        ++ mcpSdk.optional-dependencies.cli;
        pythonImportsCheck = [ "freecad_mcp.server" ];
        meta.mainProgram = "freecad-mcp";
      };

      freecadAddon = pkgs.runCommand "freecad-mcp-addon" { nativeBuildInputs = [ pkgs.patch ]; } ''
        cp -r ${freecad-mcp-src}/addon/FreeCADMCP "$out"
        chmod -R u+w "$out"
        cd "$out"
        patch -p1 < ${./patches/freecad-mcp-screenshot.patch}
      '';

      freecadWithAddon = pkgs.freecad.customize {
        modules = [ "${freecadAddon}" ];
      };

      freecadLauncher = pkgs.writeShellApplication {
        name = "freecad";
        runtimeInputs = [
          pkgs.gitMinimal
          pkgs.coreutils
        ];
        text = ''
          project_root="$(git rev-parse --show-toplevel)"
          export SMVIT_PROJECT_ROOT="$project_root"
          export SMVIT_FREECAD_ADDON="${freecadAddon}"
          # Preserve the native NVIDIA/X11 renderer. Software rendering is opt-in.
          # The add-on uses Offscreen capture to avoid the framebuffer hang here.
          if [[ "''${SMVIT_SOFTWARE_RENDERING:-0}" == "1" ]]; then
            export LIBGL_ALWAYS_SOFTWARE=1
            export __GLX_VENDOR_LIBRARY_NAME=mesa
          fi
          # Isolate FreeCAD preferences/addon state without touching global settings.
          export XDG_CONFIG_HOME="$project_root/.local/freecad/config"
          export XDG_DATA_HOME="$project_root/.local/freecad/data"
          export XDG_CACHE_HOME="$project_root/.local/freecad/cache"
          mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME"
          exec ${gui}/bin/smvit-gui ${freecadWithAddon}/bin/FreeCAD ${./scripts/start_mcp.FCMacro} "$@"
        '';
      };

      mcpLauncher = pkgs.writeShellApplication {
        name = "freecad-mcp";
        text = ''
          exec ${freecadMcp}/bin/freecad-mcp \
            --host 127.0.0.1 \
            --freecadcmd ${freecadWithAddon}/bin/freecadcmd "$@"
        '';
      };

      devPython = python.withPackages (_: [ mcpSdk ]);

      kicadMcp = py.buildPythonApplication {
        pname = "kicad-mcp-server";
        version = "0.1.0";
        src = kicad-mcp-src;
        pyproject = true;
        build-system = [ py.hatchling ];
        dependencies = [
          mcpSdk
          py.protobuf
          py.grpcio
          py.pynng
        ];
        pythonImportsCheck = [ "kicad_mcp.server" ];
      };
      kicadSchematicSrc =
        pkgs.runCommand "kicad-sch-api-library-only" { nativeBuildInputs = [ pkgs.coreutils ]; }
          ''
            cp -r ${kicad-sch-api-src} "$out"
            chmod -R u+w "$out"
            substituteInPlace "$out/pyproject.toml" \
              --replace-fail '"mcp>=1.10.0",' "" \
              --replace-fail '"fastmcp>=0.2.0",' ""
          '';
      kicadSchematicApi = py.buildPythonApplication {
        pname = "kicad-sch-api";
        version = "0.5.6-library-only";
        src = kicadSchematicSrc;
        pyproject = true;
        build-system = [
          py.setuptools
          py.wheel
        ];
        dependencies = [
          py.sexpdata
          py.pydantic
          py.jinja2
        ];
        pythonImportsCheck = [ "kicad_sch_api" ];
      };
      kicadSchematicPython = python.withPackages (_: [
        py.sexpdata
        py.pydantic
        py.jinja2
      ]);
      makeGloveSchematic = pkgs.writeShellApplication {
        name = "make-glove-schematic";
        runtimeInputs = [
          pkgs.gitMinimal
          kicadSchematicApi
          kicadSchematicPython
          pkgs.kicad
        ];
        text = ''
          project_root="$(git rev-parse --show-toplevel)"
          export KICAD_SYMBOL_DIR="${pkgs.kicad.passthru.libraries.symbols}/share/kicad/symbols"
          export PYTHONPATH="${kicadSchematicApi}/${python.sitePackages}''${PYTHONPATH:+:$PYTHONPATH}"
          exec ${kicadSchematicPython}/bin/python "$project_root/scripts/create_glove_schematic.py" "$@"
        '';
      };
      kicadTools = pkgs.symlinkJoin {
        name = "smvit-kicad";
        paths =
          map
            (
              tool:
              pkgs.writeShellApplication {
                name = tool;
                runtimeInputs = [
                  pkgs.gitMinimal
                  pkgs.coreutils
                  python
                ];
                text = ''
                  project_root="$(git rev-parse --show-toplevel)"
                  export KICAD_CONFIG_HOME="$project_root/.local/kicad/config"
                  mkdir -p "$KICAD_CONFIG_HOME"
                  ${python}/bin/python ${./scripts/setup_kicad.py}
                  exec ${if tool == "kicad-cli" then "" else "${gui}/bin/smvit-gui "}${pkgs.kicad}/bin/${tool} "$@"
                '';
              }
            )
            [
              "kicad"
              "pcbnew"
              "eeschema"
              "kicad-cli"
            ];
      };
      fritzingLauncher = pkgs.writeShellApplication {
        name = "fritzing";
        runtimeInputs = [
          pkgs.gitMinimal
          pkgs.coreutils
        ];
        text = ''
          project_root="$(git rev-parse --show-toplevel)"
          export SMVIT_PROJECT_ROOT="$project_root"
          export FRITZING_LOCAL_PARTS="$project_root/.local/fritzing/parts"
          ${python}/bin/python ${./scripts/setup_fritzing.py}
          export XDG_CONFIG_HOME="$project_root/.local/fritzing/config"
          export XDG_DATA_HOME="$project_root/.local/fritzing/data"
          export XDG_CACHE_HOME="$project_root/.local/fritzing/cache"
          mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME"
          exec ${gui}/bin/smvit-gui ${pkgs.fritzing}/bin/Fritzing "$@"
        '';
      };
      fritzingToolkit = pkgs.runCommand "smvit-fritzing-toolkit" { nativeBuildInputs = [ python ]; } ''
        cp -r ${fritzing-mcp-src} "$out"
        chmod -R u+w "$out"
        python ${./scripts/patch_fritzing_toolkit.py} "$out"
        cp ${./scripts/fritzing_support.py} "$out/fzkit/smvit.py"
      '';
      fritzingPython = python.withPackages (p: [ p.fastmcp ]);
      fritzingGeometryPython = python.withPackages (p: [ p.pyside6 ]);
      fritzingEnvironment = ''
        project_root="$(git rev-parse --show-toplevel)"
        export SMVIT_PROJECT_ROOT="$project_root"
        export FRITZING_APP_ROOT="${pkgs.fritzing}/share/fritzing"
        export FRITZING_APP="${fritzingLauncher}/bin/fritzing"
        export FRITZING_LOCAL_PARTS="$project_root/.local/fritzing/parts"
        export PYTHONPATH="${fritzingToolkit}"
        ${python}/bin/python ${./scripts/setup_fritzing.py}
      '';
      fritzingCli = pkgs.writeShellApplication {
        name = "fz";
        runtimeInputs = [
          pkgs.gitMinimal
          pkgs.imagemagick
        ];
        text = fritzingEnvironment + ''
          exec ${fritzingGeometryPython}/bin/python -m fzkit.cli "$@"
        '';
      };
      fritzingMcp = pkgs.writeShellApplication {
        name = "fritzing-mcp";
        runtimeInputs = [ pkgs.gitMinimal ];
        text = fritzingEnvironment + ''
          export FZ_BIN="${fritzingCli}/bin/fz"
          exec ${fritzingPython}/bin/python ${fritzingToolkit}/server.py
        '';
      };
      makeGloveFritzing = pkgs.writeShellApplication {
        name = "make-glove-fritzing";
        runtimeInputs = [ pkgs.gitMinimal ];
        text = fritzingEnvironment + ''
          exec ${fritzingGeometryPython}/bin/python "$project_root/scripts/create_glove_fritzing.py" "$@"
        '';
      };
      teamsMcp = pkgs.writeShellApplication {
        name = "teams-mcp";
        runtimeInputs = [ pkgs.nodejs ];
        text = ''
          # npm caches this pinned release on first use; account tokens stay in
          # the server's user config directory, outside this checkout.
          exec npx --yes @softeria/ms-365-mcp-server@0.157.2 \
            --org-mode --read-only \
            --enabled-tools '^(get-current-user|list-joined-teams|list-team-channels|list-chats|list-chat-messages|list-channel-messages|get-chat|list-channel-message-replies)$' \
            "$@"
        '';
      };
    in
    {
      packages.${system} = {
        default = freecadLauncher;
        freecad = freecadLauncher;
        freecad-mcp = mcpLauncher;
        kicad = kicadTools;
        kicad-mcp = kicadMcp;
        make-glove-schematic = makeGloveSchematic;
        fritzing = fritzingLauncher;
        fritzing-mcp = fritzingMcp;
        fz = fritzingCli;
        make-glove-fritzing = makeGloveFritzing;
        teams-mcp = teamsMcp;
      };

      apps.${system} = {
        teams-mcp = {
          type = "app";
          program = "${teamsMcp}/bin/teams-mcp";
        };
        default = {
          type = "app";
          program = "${freecadLauncher}/bin/freecad";
        };
        freecad = {
          type = "app";
          program = "${freecadLauncher}/bin/freecad";
        };
        freecad-mcp = {
          type = "app";
          program = "${mcpLauncher}/bin/freecad-mcp";
        };
        kicad = {
          type = "app";
          program = "${kicadTools}/bin/kicad";
        };
        pcbnew = {
          type = "app";
          program = "${kicadTools}/bin/pcbnew";
        };
        kicad-mcp = {
          type = "app";
          program = "${kicadMcp}/bin/kicad-mcp";
        };
        eeschema = {
          type = "app";
          program = "${kicadTools}/bin/eeschema";
        };
        fritzing = {
          type = "app";
          program = "${fritzingLauncher}/bin/fritzing";
        };
        fritzing-mcp = {
          type = "app";
          program = "${fritzingMcp}/bin/fritzing-mcp";
        };
        fz = {
          type = "app";
          program = "${fritzingCli}/bin/fz";
        };
      };

      devShells.${system} = {
        docs = pkgs.mkShell { packages = courseTools; };
        default = pkgs.mkShell {
          packages = courseTools ++ [
            freecadLauncher
            (pkgs.lib.lowPrio freecadWithAddon)
            mcpLauncher
            devPython
            pkgs.gitMinimal
            pkgs.nixfmt
            pkgs.poppler-utils
            kicadTools
            kicadMcp
            kicadSchematicApi
            makeGloveSchematic
            fritzingLauncher
            fritzingMcp
            fritzingCli
            makeGloveFritzing
            teamsMcp
          ];
        };

      };

      formatter.${system} = pkgs.nixfmt;
    };
}
