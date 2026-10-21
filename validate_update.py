"""Validate the output of the auto-update job, then copy it into the working tree.

The update job executes CachyOS PKGBUILDs (see update.py), so its output is untrusted. Only
pinned revisions, versions and hashes may change, and every source must keep pointing at the
expected CachyOS / flake input location.

Usage: python3 -I validate_update.py <artifact-dir>
Prints a summary of the changes, one per line.
"""

import json
import re
import stat
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
LOCK_FILE = "flake.lock"
KERNEL_FILE = "kernel-cachyos/version.json"
ZFS_FILE = "zfs-cachyos/version.json"
MAX_SIZE = 1024 * 1024

SRI_SHA256 = re.compile(r"sha256-[A-Za-z0-9+/]{43}=")
GIT_REV = re.compile(r"[0-9a-f]{40}")
VARIANT = re.compile(r"linux-cachyos(-[a-z0-9]+)*")
KERNEL_VERSION = re.compile(r"([0-9]+)\.([0-9]+)(\.[0-9]+)?(-rc[0-9]+)?")
ZFS_VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")

KERNEL_KEYS = {
    "configHash",
    "configUrl",
    "hash",
    "patchHash",
    "patchRev",
    "patchVersion",
    "url",
    "version",
}
ZFS_KEYS = {"commit", "hash", "url", "version"}
# Only these fields of a locked flake input may change
LOCK_UPDATABLE = {"lastModified", "narHash", "rev"}


def fail(message: str):
    sys.exit(f"error: {message}")


def check(name: str, value, pattern: re.Pattern):
    if not isinstance(value, str) or not pattern.fullmatch(value):
        fail(f"{name}: unexpected value {value!r}")


def check_keys(name: str, value, keys: set[str]):
    if not isinstance(value, dict) or set(value) != keys:
        fail(f"{name}: expected keys {sorted(keys)}")


def read_json(root: Path, rel: str):
    path = root / rel
    if not path.resolve().is_relative_to(root.resolve()):
        fail(f"{rel}: escapes {root}")
    try:
        st = path.lstat()
    except FileNotFoundError:
        fail(f"{rel}: missing")
    if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_SIZE:
        fail(f"{rel}: not a regular file of at most {MAX_SIZE} bytes")
    data = path.read_bytes()
    if not data.isascii():
        fail(f"{rel}: contains non-ASCII bytes")
    try:
        return data, json.loads(data)
    except json.JSONDecodeError as error:
        fail(f"{rel}: {error}")


def check_kernels(new, old) -> list[str]:
    if not isinstance(new, dict):
        fail(f"{KERNEL_FILE}: expected an object")
    removed = sorted(set(old) - set(new))
    if removed:
        fail(f"{KERNEL_FILE}: variants disappeared upstream: {removed}, update kernel-cachyos/ by hand")

    changes = []
    for variant, v in sorted(new.items()):
        name = f"{KERNEL_FILE}: {variant}"
        check(name, variant, VARIANT)
        check_keys(name, v, KERNEL_KEYS)
        check(f"{name}.version", v["version"], KERNEL_VERSION)
        version = KERNEL_VERSION.fullmatch(v["version"])
        check(
            f"{name}.url",
            v["url"],
            re.compile(
                r"https://github\.com/CachyOS/linux/releases/download/"
                rf"(cachyos-{re.escape(v['version'])}-[0-9]+)/\1\.tar\.gz"
            ),
        )
        check(
            f"{name}.configUrl",
            v["configUrl"],
            re.compile(
                r"https://raw\.githubusercontent\.com/CachyOS/linux-cachyos/"
                rf"[0-9a-f]{{40}}/{re.escape(variant)}/config"
            ),
        )
        check(f"{name}.patchRev", v["patchRev"], GIT_REV)
        if v["patchVersion"] != f"{version[1]}.{version[2]}":
            fail(f"{name}.patchVersion: {v['patchVersion']!r} does not match {v['version']!r}")
        for key in ("hash", "configHash", "patchHash"):
            check(f"{name}.{key}", v[key], SRI_SHA256)

        previous = old.get(variant, {}).get("version")
        if previous != v["version"]:
            changes.append(f"{variant}: {previous} -> {v['version']}")
    return changes


def check_zfs(new, old, kernels) -> list[str]:
    if not isinstance(new, dict) or set(new) != set(kernels):
        fail(f"{ZFS_FILE}: variants do not match {KERNEL_FILE}")
    for variant, v in new.items():
        name = f"{ZFS_FILE}: {variant}"
        check_keys(name, v, ZFS_KEYS)
        check(f"{name}.commit", v["commit"], GIT_REV)
        if v["url"] != f"https://github.com/CachyOS/zfs/archive/{v['commit']}.tar.gz":
            fail(f"{name}.url: unexpected value {v['url']!r}")
        check(f"{name}.version", v["version"], ZFS_VERSION)
        check(f"{name}.hash", v["hash"], SRI_SHA256)

    versions = sorted({v["version"] for v in new.values()})
    previous = sorted({v.get("version") for v in old.values()})
    return [f"zfs: {', '.join(previous)} -> {', '.join(versions)}"] if versions != previous else []


def check_lock(new, old) -> list[str]:
    if not isinstance(new, dict) or {k: v for k, v in new.items() if k != "nodes"} != {
        k: v for k, v in old.items() if k != "nodes"
    }:
        fail(f"{LOCK_FILE}: unexpected top-level change")
    nodes, old_nodes = new.get("nodes"), old["nodes"]
    if not isinstance(nodes, dict) or set(nodes) != set(old_nodes):
        fail(f"{LOCK_FILE}: set of inputs changed, update it by hand")

    def frozen(node):
        locked = {k: v for k, v in node.get("locked", {}).items() if k not in LOCK_UPDATABLE}
        return {**node, "locked": locked}

    changes = []
    for input_name, node in sorted(nodes.items()):
        previous = old_nodes[input_name]
        if "locked" not in previous:
            if node != previous:
                fail(f"{LOCK_FILE}: {input_name}: unexpected change")
            continue
        if not isinstance(node, dict) or not isinstance(node.get("locked"), dict):
            fail(f"{LOCK_FILE}: {input_name}: malformed")
        if frozen(node) != frozen(previous):
            fail(f"{LOCK_FILE}: {input_name}: only {sorted(LOCK_UPDATABLE)} may change")
        locked = node["locked"]
        check(f"{LOCK_FILE}: {input_name}.rev", locked.get("rev"), GIT_REV)
        check(f"{LOCK_FILE}: {input_name}.narHash", locked.get("narHash"), SRI_SHA256)
        if not isinstance(locked.get("lastModified"), int):
            fail(f"{LOCK_FILE}: {input_name}.lastModified: expected an integer")

        if locked["rev"] != previous["locked"].get("rev"):
            changes.append(f"{input_name}: {previous['locked'].get('rev', '')[:12]} -> {locked['rev'][:12]}")
    return changes


if __name__ == "__main__":
    if len(sys.argv) != 2:
        fail("usage: python3 -I validate_update.py <artifact-dir>")
    artifact = Path(sys.argv[1])

    files = {}
    for rel in (LOCK_FILE, KERNEL_FILE, ZFS_FILE):
        files[rel] = read_json(artifact, rel)
    current = {rel: json.loads((REPO / rel).read_bytes()) for rel in files}

    changes = check_lock(files[LOCK_FILE][1], current[LOCK_FILE])
    changes += check_kernels(files[KERNEL_FILE][1], current[KERNEL_FILE])
    changes += check_zfs(files[ZFS_FILE][1], current[ZFS_FILE], files[KERNEL_FILE][1])

    for rel, (data, _) in files.items():
        (REPO / rel).write_bytes(data)
    print("\n".join(changes))
