# Nix packages for CachyOS Kernel

This repo contains Linux kernels with both [CachyOS patches](https://github.com/CachyOS/kernel-patches) and [CachyOS tunings](https://github.com/CachyOS/linux-cachyos), as well as [CachyOS-patched ZFS module](https://github.com/CachyOS/zfs).

It is an independently maintained fork of [xddxdd/nix-cachyos-kernel](https://github.com/xddxdd/nix-cachyos-kernel), with its own update automation and binary cache.

## Which kernel versions are provided?

This repo provides the following kernel variants, consistent with the [upstream definitions](https://github.com/CachyOS/linux-cachyos?tab=readme-ov-file#kernel-variants--schedulers):

```bash
└───packages
    └───x86_64-linux
        # Latest kernel, provides all LTO/CPU arch variants
        ├───linux-cachyos-latest
        ├───linux-cachyos-latest-x86_64-v2
        ├───linux-cachyos-latest-x86_64-v3
        ├───linux-cachyos-latest-x86_64-v4
        ├───linux-cachyos-latest-zen4
        ├───linux-cachyos-latest-lto
        ├───linux-cachyos-latest-lto-x86_64-v2
        ├───linux-cachyos-latest-lto-x86_64-v3
        ├───linux-cachyos-latest-lto-x86_64-v4
        ├───linux-cachyos-latest-lto-zen4
        # LTS kernel, provides all LTO/CPU arch variants
        ├───linux-cachyos-lts
        ├───linux-cachyos-lts-x86_64-v2
        ├───linux-cachyos-lts-x86_64-v3
        ├───linux-cachyos-lts-x86_64-v4
        ├───linux-cachyos-lts-zen4
        ├───linux-cachyos-lts-lto
        ├───linux-cachyos-lts-lto-x86_64-v2
        ├───linux-cachyos-lts-lto-x86_64-v3
        ├───linux-cachyos-lts-lto-x86_64-v4
        ├───linux-cachyos-lts-lto-zen4
        # Latest kernel with BORE scheduler, all LTO/CPU arch variants
        ├───linux-cachyos-bore
        ├───linux-cachyos-bore-x86_64-v2
        ├───linux-cachyos-bore-x86_64-v3
        ├───linux-cachyos-bore-x86_64-v4
        ├───linux-cachyos-bore-zen4
        ├───linux-cachyos-bore-lto
        ├───linux-cachyos-bore-lto-x86_64-v2
        ├───linux-cachyos-bore-lto-x86_64-v3
        ├───linux-cachyos-bore-lto-x86_64-v4
        ├───linux-cachyos-bore-lto-zen4
        # Additional CachyOS kernel variants
        ├───linux-cachyos-bmq
        ├───linux-cachyos-bmq-lto
        ├───linux-cachyos-deckify
        ├───linux-cachyos-deckify-lto
        ├───linux-cachyos-eevdf
        ├───linux-cachyos-eevdf-lto
        ├───linux-cachyos-hardened
        ├───linux-cachyos-hardened-lto
        ├───linux-cachyos-rc
        ├───linux-cachyos-rc-lto
        ├───linux-cachyos-rt-bore
        ├───linux-cachyos-rt-bore-lto
        ├───linux-cachyos-server
        ├───linux-cachyos-server-lto
        # ZFS module matching CachyOS kernels
        ├───zfs-cachyos
        ├───zfs-cachyos-lto
        ├───zfs-cachyos-lts
        ├───zfs-cachyos-lts-lto
        ├───zfs-cachyos-hardened
        ├───zfs-cachyos-hardened-lto
        ├───zfs-cachyos-rc
        └───zfs-cachyos-rc-lto
```

Only some of them are in the binary cache, see [Binary cache](#binary-cache).

The kernel versions are automatically kept in sync with upstream CachyOS releases via a daily GitHub Action (see [update.py](update.py)), so once CachyOS updates their kernels, this repo will automatically catch up. Flake inputs (nixpkgs) are updated along with each new `linux-cachyos` release, or after a week without one.

Use `nix flake show github:clementpoiret/nix-cachyos-kernel/release` to see the current effective versions.

The kernels ending in `-lto` have Clang+ThinLTO enabled.

For each linux kernel entry under `packages`, we have a corresponding `linuxPackages` entry under `legacyPackages` for easier use in your NixOS configuration, e.g.:

- `linux-cachyos-latest` -> `inputs.nix-cachyos-kernel.legacyPackages.x86_64-linux.linuxPackages-cachyos-latest`
- `linux-cachyos-lts-lto` -> `inputs.nix-cachyos-kernel.legacyPackages.x86_64-linux.linuxPackages-cachyos-lts-lto`

## How to use kernels

#### Flakes

Add the `release` branch of this repo to the inputs section of your `flake.nix`:

```nix
{
  inputs = {
    nix-cachyos-kernel.url = "github:clementpoiret/nix-cachyos-kernel/release";
    # Do not override its nixpkgs input, otherwise there can be mismatch between patches and kernel version
  }
}
```

The `release` branch only moves once [GitHub Actions](.github/workflows/auto-update.yml) has built every cached kernel and pushed it to the binary cache. Its commits are snapshots of `master` without the `.github/` CI files, which GitHub doesn't let the workflow publish; each commit message names the `master` commit it was taken from.

> If you want the absolute latest version with or without binary cache, use the `master` branch (default branch) instead:
>
> ```nix
> {
>   inputs = {
>     nix-cachyos-kernel.url = "github:clementpoiret/nix-cachyos-kernel";
>   }
> }
> ```

Add the repo's overlay in your NixOS configuration, this will expose the packages in this flake as `pkgs.cachyosKernels.*`.

```nix
{
  outputs = { nix-cachyos-kernel, ... }: {
    nixosConfigurations.example = inputs.nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        (
          { pkgs, ... }:
          {
            nixpkgs.overlays = [
              # Use the exact nixpkgs revision as defined in this repo to ensure binary cache hits.
              nix-cachyos-kernel.overlays.pinned

              # Alternatively, use nixpkgs from your environment, nixpkgs.config will apply.
              # Note: may not hit binary cache; kernel will need to be built locally.
              # nix-cachyos-kernel.overlays.default

              # Only use one of the two overlays!
            ];

            # ... your other configs
          }
        )
      ];
    };
  };
}
```

Then specify `pkgs.cachyosKernels.linuxPackages-cachyos-latest` (or other variants you'd like) in your `boot.kernelPackages` option.

> **`pinned` overlay is recommended** to ensure binary cache hits. The `pinned` overlay uses the exact nixpkgs revision defined in this flake, matching what was used to build the cached kernels. With the `default` overlay, a different nixpkgs revision may cause cache misses and trigger local kernel compilation even if a cached kernel is available.
>
> Use `pinned` if:
>
> - You want to ensure that you can fetch kernel from binary cache.
> - You want to make sure that the kernel can be built successfully.
>
> Use `default` if:
>
> - You want to avoid initializing multiple instances of nixpkgs.
> - You want to use latest kernel modules that are just merged/updated within nixpkgs.
> - You want to customize `nixpkgs.config` options.
> - You need a kernel module that nixpkgs marks as insecure (such as `broadcom_sta`). The `pinned` overlay refuses those, while `default` lets you allow them with `nixpkgs.config.permittedInsecurePackages`.

#### Non-Flakes

This flake is usable in non-flakes nix configuration using npins and the following snippet:

Npins commands:
```bash
npins init
npins add github clementpoiret nix-cachyos-kernel -b release
```

```nix
let
  sources = import ./npins/default.nix;
  cachy-source = import sources.nix-cachyos-kernel;
  cachy-kernel =
    cachy-source.outputs.legacyPackages.x86_64-linux.linuxPackages-cachyos-bore-lto-x86_64-v3;
in
{
  boot.kernelPackages = cachy-kernel;
}
```

You may also fetch the flakes directly using fetchFromGitHub,
but note that you will have to manually update the revision and hash to update your kernel, which is tedious.


### Binary cache

Kernels are built by [GitHub Actions](.github/workflows/auto-update.yml) and pushed to the [`nixos-cachyos-kernels`](https://nixos-cachyos-kernels.cachix.org) Cachix cache. Running `nix` commands directly on this flake will prompt you to accept it through [`nixConfig`](flake.nix), but `nixConfig` is ignored when this flake is an input of your configuration, so add it to your NixOS configuration instead:

```nix
{
  nix.settings.substituters = [ "https://nixos-cachyos-kernels.cachix.org" ];
  nix.settings.trusted-public-keys = [ "nixos-cachyos-kernels.cachix.org-1:ccFqQ2GZOeTAPrZaDDsCY5Rk1Ndg/+NnM2s6UwIDTS0=" ];
}
```

The cache lives on a free Cachix plan, so only these packages are cached, from the `release` branch with the `pinned` overlay:

- `linux-cachyos-latest`, `linux-cachyos-latest-lto`, `linux-cachyos-lts` and `linux-cachyos-bore`, for any x86-64 CPU
- `linux-cachyos-latest-lto-x86_64-v3`, for x86-64-v3 CPUs (Intel Haswell and later, all AMD Zen)
- `linux-cachyos-latest-lto-zen4`, for AMD Zen 4 and Zen 5
- `linux-cachyos-hardened`, with CachyOS's hardened patch (based on [linux-hardened](https://github.com/anthraxx/linux-hardened)), for any x86-64 CPU. It can be on an older kernel series than `linux-cachyos-latest`. It is built with GCC: with Clang (`-lto`), the GCC plugins of its config are unavailable and latent entropy is lost
- their ZFS modules (`zfs_cachyos` in the matching `linuxPackages-cachyos-*`)

Other variants are built locally. If you were going to use an `-x86_64-v2` or `-x86_64-v4` kernel, use the cached generic or `-x86_64-v3` one instead: the kernel is compiled with SIMD disabled, so x86-64-v4 (which only adds AVX-512) produces the same code as x86-64-v3, and x86-64-v2 adds almost nothing over generic (the kernel already switches to POPCNT at boot when the CPU has it). Out-of-tree modules such as NVIDIA or VirtualBox are always built locally, against the cached kernel's `dev` output. CI checks that nixpkgs' `latest` and `stable` NVIDIA drivers, open and proprietary modules, build against every cached kernel. It also checks that modules installing their `.ko` without Kbuild's `modules_install` (`acpi_call` and others in nixpkgs) get the signature and certificate NixOS needs, see `kernelModuleSignOverride` in [helpers.nix](helpers.nix).

**Important:** As with all binary caches, after adding binary cache to your NixOS configuration, please apply your settings once before enabling CachyOS kernel, so that the binary cache settings can take effect.

### Example configuration

```nix
{
  outputs = { nix-cachyos-kernel, ... }: {
    nixosConfigurations.example = inputs.nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        (
          { pkgs, ... }:
          {
            nixpkgs.overlays = [ nix-cachyos-kernel.overlays.pinned ];
            boot.kernelPackages = pkgs.cachyosKernels.linuxPackages-cachyos-latest;

            # Binary cache, see "Binary cache" above
            nix.settings.substituters = [ "https://nixos-cachyos-kernels.cachix.org" ];
            nix.settings.trusted-public-keys = [ "nixos-cachyos-kernels.cachix.org-1:ccFqQ2GZOeTAPrZaDDsCY5Rk1Ndg/+NnM2s6UwIDTS0=" ];

            # ... your other configs
          }
        )
      ];
    };
  };
}
```

### Help! My kernel is failing to build!

In most cases, failing to build a kernel is caused by version mismatch between CachyOS patches and nixpkgs kernel version. (e.g. hardened 6.18 kernel as of 2025-12-12)

Common symptoms are:

- "File not found" error, which indicates that CachyOS patches for given kernel version/variant are unavailable.
- Failures/conflicts when applying patches, which indicates that CachyOS patches are for an older kernel version.

If this is the case, the build will be automatically fixed once versions are in sync again.

## How to use ZFS modules

> Note: CachyOS-patched ZFS module may fail to compile from time to time. Most compilation failures are caused by incompatibilities between kernel and ZFS. Please check [ZFS upstream issues](https://github.com/openzfs/zfs/issues) for any compatibility reports, and try switching between `zfs_2_3`, `zfs_unstable` and `zfs_cachyos`.

To use ZFS module with `linuxPackages-cachyos-*` provided by this flake, point `boot.zfs.package` to `config.boot.kernelPackages.zfs_cachyos`.

```nix
{
  outputs = { nix-cachyos-kernel, ... }: {
    nixosConfigurations.example = inputs.nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        (
          { pkgs, ... }:
          {
            nixpkgs.overlays = [ nix-cachyos-kernel.overlays.pinned ];
            boot.kernelPackages = pkgs.cachyosKernels.linuxPackages-cachyos-latest;

            # ZFS config
            boot.supportedFilesystems.zfs = true;
            boot.zfs.package = config.boot.kernelPackages.zfs_cachyos;

            # ... your other configs
          }
        )
      ];
    };
  };
}
```

If you want to construct your own `linuxPackages` attrset with `linuxKernel.packagesFor (path to your kernel)`, such as for customizing your kernel, you can directly reference the `zfs-cachyos` attribute in this flake's `packages` / `legacyPackages` output, or the `cachyosKernels` overlay:

```nix
{
  outputs = { nix-cachyos-kernel, ... }: {
    nixosConfigurations.example = inputs.nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        (
          { pkgs, ... }:
          let
            kernel = pkgs.cachyosKernels.linux-cachyos-latest.override {
              # Your own customizations
            };
          in
          {
            nixpkgs.overlays = [ nix-cachyos-kernel.overlays.pinned ];
            boot.kernelPackages = (pkgs.linuxKernel.packagesFor kernel).extend (final: prev: {
              zfs_cachyos = pkgs.cachyosKernels.zfs-cachyos.override {
                inherit kernel;
              };
            });

            # ZFS config
            boot.supportedFilesystems.zfs = true;
            boot.zfs.package = config.boot.kernelPackages.zfs_cachyos;

            # ... your other configs
          }
        )
      ];
    };
  };
}
```

> If you are still running into issues, see [this comment](https://github.com/xddxdd/nix-cachyos-kernel/issues/67#issuecomment-4305704829) in the upstream repository for a possible workaround.

### Help! My ZFS module is failing to build!

In most cases, failing to build ZFS module is caused by CachyOS not updating patches for the latest kernel version. The only option is to wait for CachyOS team to update the patches.

## How to customize CachyOS kernel

The kernels provided in this flake can be overridden to use your own kernel source. This is helpful if you want to use a kernel version not available in Nixpkgs, or customize CachyOS optimization settings in [kernel-cachyos/mkCachyKernel.nix](kernel-cachyos/mkCachyKernel.nix).

### Available Arguments

The following arguments can be passed to `mkCachyKernel`:

#### Required Arguments

- **`pname`**: Package name for the kernel
- **`version`**: Kernel version string
- **`src`**: Kernel source derivation
- **`cachyosConfigFile`**: CachyOS kernel config file to use as defconfig. See [CachyOS linux-cachyos repo](https://github.com/CachyOS/linux-cachyos) for available configs.
- **`cachyosPatchesSrc`**: Source of [CachyOS kernel-patches](https://github.com/CachyOS/kernel-patches), rooted at the directory for your kernel's major.minor version.

#### Optional Arguments

**Compiler & Optimization:**

- **`lto`**: Link-Time Optimization setting. Options: `"none"` (default), `"thin"`, or `"full"`. Non-`"none"` values use Clang.
- **`processorOpt`**: Processor optimization level. Options: `"x86_64-v1"` (default), `"x86_64-v2"`, `"x86_64-v3"`, `"x86_64-v4"`, `"zen4"`, or `"native"` (requires impure environment).
- **`autofdo`**: AutoFDO (Automatic Feedback-Directed Optimization) settings. Options:
  - `false` (default): Disable AutoFDO
  - `true`: Enable AutoFDO for profiling performance patterns only
  - `./path/to/autofdo/profile`: Enable AutoFDO with specified profile (requires `lto != "none"`)

> AutoFDO hasn't been fully tested. Please report issue if you encounter any.

**CachyOS Fine Tuning Settings:**

- **`cpusched`**: CPU scheduler. Options: `"eevdf"` (default), `"bore"`, `"bmq"`, `"rt"`, `"rt-bore"` or `null` to disable.
- **`kcfi`**: Enable Kernel Control Flow Integrity. Requires Clang (`lto` other than `"none"`). Default: `false`.
- **`hzTicks`**: Timer frequency. Options: `"1000"` (default), `"100"`, `"250"`, `"300"`, `"500"`, `"600"`, `"750"`, or `null` to disable.
- **`performanceGovernor`**: Enable performance governor. Default: `false`.
- **`tickrate`**: Tick rate. Options: `"full"` (default), `"periodic"`, `"idle"`, or `null` to disable.
- **`preemptType`**: Preemption type. Options: `"full"` (default), `"lazy"`, `"voluntary"`, `"none"`, or `null` to disable.
- **`ccHarder`**: Enable harder compiler optimizations. Default: `true`.
- **`bbr3`**: Enable BBR3 TCP congestion control. Default: `false`.
- **`hugepage`**: Huge page settings. Options: `"always"` (default), `"madvise"`, or `null` to disable.

**CachyOS Additional Patch Settings:**

- **`hardened`**: Apply hardened security patches. Also turns back off what nixpkgs' common kernel config turns on against CachyOS's hardened config (`USERFAULTFD`, `KEXEC_FILE`, `CHECKPOINT_RESTORE`, `VFIO_NOIOMMU`), and back on `BPF_JIT_ALWAYS_ON`. Default: `false`.
- **`rt`**: Apply real-time patches. Default: `false`.
- **`acpiCall`**: Apply ACPI call patches. Default: `false`.
- **`handheld`**: Apply handheld-specific patches. Default: `false`.

**Patch Control:**

- **`prePatch`**: Shell commands to run before applying patches. Default: `""`.
- **`patches`**: List of additional patches to apply. Default: `[ ]`.
- **`postPatch`**: Shell commands to run after applying patches. Default: `""`.

**Module Settings:**

- **`autoModules`**: Build as many components as possible as kernel modules, including disabled ones. Default: `true`.
- **`zfsVariant`**: CachyOS kernel variant whose ZFS module is built into the corresponding `linuxPackages` entry (see `zfs-cachyos/version.json`). Default: `"latest"`.

**Other Options:**

Additional arguments are passed through to `buildLinux` from nixpkgs. See [nixpkgs/pkgs/os-specific/linux/kernel/generic.nix](https://github.com/NixOS/nixpkgs/blob/master/pkgs/os-specific/linux/kernel/generic.nix) for available options.

### Example Usage

```nix
let
  # helpers.nix provides a few utilities for building kernel package sets.
  # I haven't figured out a clean way to expose it in flakes.
  helpers = pkgs.callPackage "${inputs.nix-cachyos-kernel.outPath}/helpers.nix" {};
in
{
  kernel = pkgs.cachyosKernels.linux-cachyos-latest.override {
    pname = "linux-cachyos-with-custom-source";
    version = "6.12.34";
    src = pkgs.fetchurl {
      # ...
    };

    # Customize CachyOS settings
    cpusched = "bore";
    lto = "thin";
    processorOpt = "x86_64-v3";
    hzTicks = "1000";
    bbr3 = true;
    hardened = false;

    # Additional args are available. See kernel-cachyos/mkCachyKernel.nix
  };

  # For non-LTO kernels. helpers.kernelModuleSignOverride adds the certificates (.ko.cer)
  # NixOS needs to out-of-tree modules that install their .ko themselves, such as acpi_call.
  kernelPackages = helpers.kernelModuleSignOverride (pkgs.linuxKernel.packagesFor kernel);

  # For LTO kernels, helpers.kernelModuleLLVMOverride also fixes compilation for some
  # out-of-tree modules in nixpkgs.
  kernelPackagesWithLTOFix = helpers.kernelModuleSignOverride (
    helpers.kernelModuleLLVMOverride (pkgs.linuxKernel.packagesFor kernel)
  );
}
```
