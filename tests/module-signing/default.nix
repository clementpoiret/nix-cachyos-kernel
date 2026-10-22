# Checks helpers.kernelModuleSignOverride against nixpkgs' module signing: a module that copies
# its .ko itself must make it into a NixOS module tree (system.modulesTree), with a certificate
# and a signature that verifies, so it was signed after stripping.
{
  lib,
  pkgs,
  runCommand,
  openssl,
  python3,
  kernelPackages,
}:
let
  helpers = pkgs.callPackage ../../helpers.nix { };
  packages = helpers.kernelModuleSignOverride (
    kernelPackages.extend (final: _: { module-signing-test = final.callPackage ./module.nix { }; })
  );
  inherit (packages.kernel) modDirVersion;

  # Same as NixOS' system.modulesTree, which fails without the certificate
  modulesTree = pkgs.aggregateModules [
    (lib.getOutput "modules" packages.kernel)
    packages.module-signing-test
  ];
in
runCommand "module-signing-test-${modDirVersion}" { nativeBuildInputs = [ openssl ]; } ''
  ${lib.getExe python3} -I ${./verify.py} ${modulesTree}/lib/modules/${modDirVersion} misc/signing_test.ko
  touch $out
''
