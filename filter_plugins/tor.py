"""Derive the .onion address of a v3 service from its private key file.

Tor stores the service key expanded, not as a seed:

    [0:32]    b"== ed25519v1-secret: type0 ==" padded with NULs
    [32:64]   the scalar a
    [64:96]   the nonce prefix

pyca/cryptography is no help even though ansible-core already pulls it in:
its Ed25519 API takes a 32-byte seed and the seed cannot be recovered from
the expanded key. libsodium has exactly the right primitive instead --
crypto_scalarmult_ed25519_base_noclamp is a*B with the scalar used verbatim,
which is what tor itself does with an expanded key. libnacl ships no Python
wrapper for it, so it is called through the ctypes handle libnacl already
holds on libsodium.

The address is then, per rend-spec-v3 section 6:

    base32(pubkey || sha3_256(".onion checksum" || pubkey || 0x03)[:2] || 0x03)

lower-cased, unpadded, with ".onion" appended.
"""

import base64
import ctypes
import hashlib

from ansible.errors import AnsibleFilterError

try:
    import libnacl
except (ImportError, OSError):  # libnacl raises OSError with no libsodium
    libnacl = None

SECRET_KEY_HEADER = b"== ed25519v1-secret: type0 =="
SECRET_KEY_LENGTH = 96
PUBLIC_KEY_LENGTH = 32
ONION_VERSION = b"\x03"
CHECKSUM_SALT = b".onion checksum"


def onion_address(keyfile):
    """Return the .onion address for a tor hs_ed25519_secret_key file."""
    if libnacl is None:
        raise AnsibleFilterError(
            "the onion_address filter needs libnacl and libsodium on the "
            "controller: pip install libnacl")

    try:
        with open(keyfile, "rb") as handle:
            blob = handle.read()
    except OSError as exc:
        raise AnsibleFilterError(f"cannot read onion key file {keyfile}: {exc}")

    if not blob.startswith(SECRET_KEY_HEADER):
        raise AnsibleFilterError(
            f"{keyfile} is not a tor v3 secret key (bad header) — an offline or "
            "encrypted key cannot be used here")

    if len(blob) != SECRET_KEY_LENGTH:
        raise AnsibleFilterError(
            f"{keyfile} is {len(blob)} bytes, expected {SECRET_KEY_LENGTH}")

    scalar = blob[32:64]

    # libsodium inherits ref10's precondition that the top bit is clear, and
    # returns a wrong point rather than an error if it is not. Every key tor
    # writes is clamped, so this only ever fires on a corrupt or foreign file.
    if scalar[31] > 127:
        raise AnsibleFilterError(
            f"{keyfile} holds an unclamped scalar (byte 31 is 0x{scalar[31]:02x}) — tor never "
            "writes such a key")

    public_key = ctypes.create_string_buffer(PUBLIC_KEY_LENGTH)
    if libnacl.nacl.crypto_scalarmult_ed25519_base_noclamp(public_key, scalar):
        raise AnsibleFilterError(
            f"{keyfile} holds a scalar that is zero mod L — it has no public key")
    public_key = public_key.raw
    checksum = hashlib.sha3_256(CHECKSUM_SALT + public_key + ONION_VERSION).digest()[:2]
    address = base64.b32encode(public_key + checksum + ONION_VERSION)
    return address.decode("ascii").lower().rstrip("=") + ".onion"


class FilterModule:
    def filters(self):
        return {"onion_address": onion_address}
