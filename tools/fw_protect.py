#!/usr/bin/env python
"""
Firmware Bundle-and-Protect Tool
"""

import argparse
import pathlib
import struct

from Crypto.Cipher import AES
from Crypto.PublicKey import ECC
from Crypto.Signature import DSS
from Crypto.Hash import SHA256

# crypto directory, where keys generated by bl_build are stored
CRYPTO_DIR = (
    pathlib.Path(__file__).parent.parent.joinpath("bootloader/crypto").absolute()
)

MAX_VERSION = 65535
MAX_MESSAGE_SIZE = 1024
MAX_FIRMWARE_SIZE = 32768

AES_KEY_LENGTH = 32

def protect_firmware(infile, outfile, version, message):
    # Load firmware binary from infile
    with open(infile, "rb") as infile:
        firmware = infile.read()

    # ensure that the firmware and message are not too large and that the version is in range
    assert version <= MAX_VERSION
    assert len(message) <= MAX_MESSAGE_SIZE
    assert len(firmware) <= MAX_FIRMWARE_SIZE

    # Extract keys from secret build output [AES | ECC priv]
    # Public key not needed for signing so not loaded
    with open(CRYPTO_DIR / "secret_build_output.txt", mode="rb") as secfile:
        aes_key = secfile.read(AES_KEY_LENGTH)
        priv_key = secfile.read()
        priv_key = ECC.import_key(priv_key)

    # Extract automatically generated initalization vector (IV) / nonce
    with open(CRYPTO_DIR / "iv.txt", mode="rb") as ivfile:
        nonce = ivfile.read()

    # Pack version and size into two little-endian shorts
    metadata = struct.pack("<HHH", version, len(firmware), len(message))

    aes = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
    signer = DSS.new(priv_key, mode="fips-186-3")

    blob = metadata + aes.encrypt(firmware + message.encode() + b"\x00")
    h = SHA256.new(blob)
    blob = signer.sign(h) + blob

    with open(outfile, "wb+") as outfile:
        outfile.write(blob)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Firmware Update Tool")
    parser.add_argument(
        "--infile", help="Path to the firmware image to protect.", required=True
    )
    parser.add_argument(
        "--outfile", help="Filename for the output firmware.", required=True
    )
    parser.add_argument(
        "--version", help="Version number of this firmware.", required=True
    )
    parser.add_argument(
        "--message", help="Release message for this firmware.", required=True
    )
    args = parser.parse_args()
    protect_firmware(
        infile=args.infile,
        outfile=args.outfile,
        version=int(args.version),
        message=args.message,
    )
    print("!")
