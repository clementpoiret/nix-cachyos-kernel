"""Check that a module in a NixOS module tree has a valid kmodigest signature and certificate.

Usage: python3 -I verify.py <lib/modules/version directory> <module path relative to it>
Requires openssl in PATH.
"""

import struct
import subprocess
import sys
import tempfile
from pathlib import Path

MAGIC = b"~Module signature appended~\n"
PKEY_ID_PKCS7 = 2


def fail(message: str):
    sys.exit(f"error: {message}")


def verify(content: bytes, signature: bytes, cert: bytes) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "content").write_bytes(content)
        (tmp / "signature").write_bytes(signature)
        (tmp / "cert").write_bytes(cert)
        subprocess.run(
            ["openssl", "x509", "-inform", "DER", "-in", tmp / "cert", "-out", tmp / "cert.pem"],
            check=True,
        )
        result = subprocess.run(
            ["openssl", "cms", "-verify", "-binary", "-noverify", "-inform", "DER",
             "-in", tmp / "signature", "-content", tmp / "content",
             "-certfile", tmp / "cert.pem", "-out", "/dev/null"],
            capture_output=True,
        )
        return result.returncode == 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        fail("usage: python3 -I verify.py <modules directory> <module>")
    modules, module = Path(sys.argv[1]), sys.argv[2]

    data = (modules / module).read_bytes()
    if not data.endswith(MAGIC):
        fail(f"{module}: not signed")
    # struct module_signature, then the magic string, are appended after the PKCS#7 signature
    info = data[: -len(MAGIC)]
    *_, id_type, _, _, sig_len = struct.unpack(">BBBBB3xI", info[-12:])
    if id_type != PKEY_ID_PKCS7:
        fail(f"{module}: unexpected signature type {id_type}")
    content, signature = info[: -12 - sig_len], info[-12 - sig_len : -12]

    cert_path = modules / f"{module}.cer"
    if not cert_path.exists():
        fail(f"{module}: no certificate")
    cert = cert_path.read_bytes()
    if cert not in (modules / "modules.cer").read_bytes():
        fail(f"{module}: certificate missing from modules.cer")

    if not verify(content, signature, cert):
        fail(f"{module}: signature does not verify")
    # Make sure the check can fail: a single changed byte must break the signature
    tampered = bytearray(content)
    tampered[len(tampered) // 2] ^= 0xFF
    if verify(bytes(tampered), signature, cert):
        fail(f"{module}: signature verifies a modified module")

    print(f"{module}: signature and certificate OK")
