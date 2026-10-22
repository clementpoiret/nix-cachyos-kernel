# Built like acpi_call was before nixpkgs switched it to modules_install: the .ko is copied by
# hand, so it has no signature or certificate unless helpers.kernelModuleSignOverride adds them.
{
  stdenv,
  kernel,
  kernelModuleMakeFlags,
}:
stdenv.mkDerivation {
  name = "module-signing-test-${kernel.modDirVersion}";
  src = ./src;

  hardeningDisable = [ "pic" ];

  nativeBuildInputs = kernel.moduleBuildDependencies;

  makeFlags = kernelModuleMakeFlags ++ [
    "KDIR=${kernel.dev}/lib/modules/${kernel.modDirVersion}/build"
  ];

  installPhase = ''
    install -D signing_test.ko $out/lib/modules/${kernel.modDirVersion}/misc/signing_test.ko
  '';
}
