#!/usr/bin/env bash
# One graphics policy for all three CAD applications. No host paths in the flake.
set -euo pipefail
mode="${SMVIT_GL:-auto}"
if [[ "${SMVIT_SOFTWARE_RENDERING:-0}" == 1 ]]; then mode=software; fi
if [[ "${QT_QPA_PLATFORM:-}" == offscreen ]]; then exec "$@"; fi
if [[ "$mode" == auto ]]; then
  if [[ -e /etc/NIXOS ]]; then mode=native
  elif [[ -e /proc/driver/nvidia/version ]]; then mode=nvidia
  else mode=mesa
  fi
fi
case "$mode" in
  native) exec "$@" ;;
  mesa) exec "$SMVIT_MESA_WRAPPER" "$@" ;;
  software)
    export LIBGL_ALWAYS_SOFTWARE=1 __GLX_VENDOR_LIBRARY_NAME=mesa
    if [[ -e /etc/NIXOS ]]; then exec "$@"; fi
    exec "$SMVIT_MESA_WRAPPER" "$@" ;;
  nvidia)
    # Match the running host driver. Only this optional path uses impure evaluation.
    project_root="$(git rev-parse --show-toplevel)"
    wrapper=$(cd "$project_root" && nix build --impure --no-link --print-out-paths --expr '
      let f = builtins.getFlake (toString ./.);
          pkgs = import f.inputs.nixpkgs { system = builtins.currentSystem; config.allowUnfree = true; };
      in (import f.inputs.nixgl { inherit pkgs; enable32bits = false; }).auto.nixGLNvidia')
    exec "$wrapper"/bin/nixGLNvidia-* "$@" ;;
  *) printf 'Unknown SMVIT_GL=%s (auto, native, mesa, software, nvidia)\n' "$mode" >&2; exit 2 ;;
esac
