{
  inputs,
  callPackage,
  kernel ? null,
  variant ? "latest",
  lib,
  fetchurl,
}:
let
  versionJson = lib.importJSON ./version.json;
  metadata = versionJson."${variant}";
  zfsGeneric = callPackage "${inputs.nixpkgs.outPath}/pkgs/os-specific/linux/zfs/generic.nix" {
    inherit kernel;
  };

  # generic.nix passes the kernel's make flags both to configure (as KERNEL_*) and to make.
  # Their CC, LD and LLVM select the kernel's own toolchain (an unwrapped GCC for GCC
  # kernels), which can't find userland headers such as blkid.h. Since this builds both
  # userland and the kernel module, leave those three to ZFS's module build, which gets
  # them from KERNEL_CC, KERNEL_LD and KERNEL_LLVM.
  isKernelToolchainFlag = flag: lib.any (name: lib.hasPrefix "${name}=" flag) [ "CC" "LD" "LLVM" ];
in
# https://github.com/chaotic-cx/nyx/blob/aacb796ccd42be1555196c20013b9b674b71df75/pkgs/linux-cachyos/packages-for.nix#L99
(zfsGeneric {
  kernelModuleAttribute = "zfs_cachyos";
  kernelMinSupportedMajorMinor = "1.0";
  kernelMaxSupportedMajorMinor = "99.99";
  enableUnsupportedExperimentalKernel = true;
  version = metadata.version;
  tests = { };
  maintainers = with lib.maintainers; [
    pedrohlc
  ];
  hash = "";
  extraPatches = [ ];
}).overrideAttrs
  (prevAttrs: {
    src = fetchurl {
      inherit (metadata) url hash;
    };
    postPatch = builtins.replaceStrings [ "grep --quiet '^Linux-M" ] [ "# " ] prevAttrs.postPatch;
    makeFlags = lib.filter (flag: !isKernelToolchainFlag flag) prevAttrs.makeFlags;
    passthru = prevAttrs.passthru // {
      cachyosVariant = variant;
    };
  })
