"""Read an i2pd destination key file: its .b32.i2p address, and when its
offline signature expires.

An I2P private key file starts with the Destination it belongs to:

    [0:256]      public encryption key
    [256:384]    signing public key (padded)
    [384]        certificate type
    [385:387]    certificate payload length (big endian)
    [387:387+n]  certificate payload

The base32 address is the SHA-256 of those bytes, base32 encoded,
lower-cased and stripped of padding.

The destination's private keys follow: its encryption key, then its
signing key, each as long as the key certificate's types make it
(payload [0:2] the signing type, [2:4] the encryption type; without a
key certificate, DSA and ElGamal). A key file from i2pd-tools'
offlinekeys has the signing key zeroed, as it stays offline, and after
it what the server signs with instead:

    [0:4]   expiry, seconds since the epoch (big endian)
    [4:6]   transient signing key type
    [6:]    transient public key, the offline key's signature over all of
            the above, and the transient private key

Once that expiry has passed, routers reject the destination's leasesets,
and newer i2pd refuses to load the file.
"""

import base64
import hashlib

from ansible.errors import AnsibleFilterError

DESTINATION_HEADER = 387
CERTIFICATE_TYPE_KEY = 5

# By key type, as i2pd sizes them in a key file. The ECIES-P256 key is
# 32 bytes, but i2pd keeps the 256 of ElGamal's for older files.
ENCRYPTION_PRIVATE_KEY_LENGTH = {0: 256, 1: 256, 4: 32, 5: 32, 6: 32, 7: 32}
SIGNING_PRIVATE_KEY_LENGTH = {0: 20, 1: 32, 2: 48, 3: 66, 7: 32, 9: 32, 10: 64, 11: 32}


def _read_destination(keyfile):
    """Return the key file's bytes and the length of its destination."""
    try:
        with open(keyfile, "rb") as handle:
            blob = handle.read()
    except OSError as exc:
        raise AnsibleFilterError(f"cannot read I2P key file {keyfile}: {exc}")

    if len(blob) < DESTINATION_HEADER:
        raise AnsibleFilterError(f"{keyfile} is too short to be an I2P key file")

    certificate_length = int.from_bytes(blob[385:DESTINATION_HEADER], "big")
    destination_length = DESTINATION_HEADER + certificate_length

    if len(blob) < destination_length:
        raise AnsibleFilterError(f"{keyfile} is truncated: incomplete destination")

    return blob, destination_length


def i2p_b32(keyfile):
    """Return the .b32.i2p address for an i2pd destination key file."""
    blob, destination_length = _read_destination(keyfile)
    digest = hashlib.sha256(blob[:destination_length]).digest()
    return base64.b32encode(digest).decode("ascii").lower().rstrip("=") + ".b32.i2p"


def i2p_offline_expiry(keyfile):
    """Return when the key file's offline signature expires, in seconds
    since the epoch, or None if it holds the destination's own signing key."""
    blob, offset = _read_destination(keyfile)

    signing_type, encryption_type = 0, 0
    if blob[384] == CERTIFICATE_TYPE_KEY:
        payload = blob[DESTINATION_HEADER:offset]
        if len(payload) >= 2:
            signing_type = int.from_bytes(payload[0:2], "big")
        if len(payload) >= 4:
            encryption_type = int.from_bytes(payload[2:4], "big")

    if encryption_type not in ENCRYPTION_PRIVATE_KEY_LENGTH:
        raise AnsibleFilterError(f"{keyfile} has an unknown encryption key type {encryption_type}")
    if signing_type not in SIGNING_PRIVATE_KEY_LENGTH:
        raise AnsibleFilterError(f"{keyfile} has an unknown signing key type {signing_type}")

    offset += ENCRYPTION_PRIVATE_KEY_LENGTH[encryption_type]
    signing_key = blob[offset : offset + SIGNING_PRIVATE_KEY_LENGTH[signing_type]]
    offset += len(signing_key)

    if len(signing_key) < SIGNING_PRIVATE_KEY_LENGTH[signing_type]:
        raise AnsibleFilterError(f"{keyfile} is truncated: incomplete private keys")
    if any(signing_key):
        return None
    if len(blob) < offset + 4:
        raise AnsibleFilterError(f"{keyfile} is truncated: incomplete offline signature")

    return int.from_bytes(blob[offset : offset + 4], "big")


class FilterModule:
    def filters(self):
        return {"i2p_b32": i2p_b32, "i2p_offline_expiry": i2p_offline_expiry}
