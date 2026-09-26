"""Derive the .b32.i2p address of a destination from its private key file.

An I2P private key file starts with the Destination it belongs to:

    [0:256]      public encryption key
    [256:384]    signing public key (padded)
    [384]        certificate type
    [385:387]    certificate payload length (big endian)
    [387:387+n]  certificate payload

The base32 address is the SHA-256 of those bytes, base32 encoded,
lower-cased and stripped of padding.
"""

from __future__ import absolute_import, division, print_function

import base64
import hashlib

from ansible.errors import AnsibleFilterError

__metaclass__ = type

DESTINATION_HEADER = 387


def i2p_b32(keyfile):
    """Return the .b32.i2p address for an i2pd destination key file."""
    try:
        with open(keyfile, "rb") as handle:
            blob = handle.read()
    except OSError as exc:
        raise AnsibleFilterError("cannot read I2P key file %s: %s" % (keyfile, exc))

    if len(blob) < DESTINATION_HEADER:
        raise AnsibleFilterError("%s is too short to be an I2P key file" % keyfile)

    certificate_length = int.from_bytes(blob[385:DESTINATION_HEADER], "big")
    destination = blob[: DESTINATION_HEADER + certificate_length]

    if len(destination) < DESTINATION_HEADER + certificate_length:
        raise AnsibleFilterError("%s is truncated: incomplete destination" % keyfile)

    digest = hashlib.sha256(destination).digest()
    return base64.b32encode(digest).decode("ascii").lower().rstrip("=") + ".b32.i2p"


class FilterModule:
    def filters(self):
        return {"i2p_b32": i2p_b32}
