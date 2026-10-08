{ pkgs, nixgl }:
let
  # Nixpkgs 26.05 separates the userspace driver from the kernel module.
  # Upstream nixGL still supplies the removed `kernel` override argument.
  compatibleSource = pkgs.applyPatches {
    name = "nixgl-nixpkgs-26.05";
    src = nixgl;
    patches = [ ../patches/nixgl-nvidia-nixpkgs-26.05.patch ];
  };
in
import compatibleSource {
  inherit pkgs;
  enable32bits = false;
}
