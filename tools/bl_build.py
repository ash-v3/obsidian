#!/usr/bin/env python

"""
bl_build.py --initial-firmware <binary_path>

This tool is responsible for setting up the firmware location and compiling C source code to generate a bootloader binary file.
"""

import argparse
import os
import pathlib
import shutil

from pwn import *
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Signature import eddsa
from Crypto.PublicKey import ECC

from subprocess import run

TOOL_DIRECTORY = pathlib.Path(__file__).parent.absolute()

SECRET_ERROR = -1
FIRMWARE_ERROR = -2

def compile_bootloader() -> bool:
    # Navigate to bootloader directory
    bootloader = TOOL_DIRECTORY / '..' / 'bootloader'
    os.chdir(bootloader)

    # Delete any previous executables and compile
    run('make clean', shell=True)

    # Did our compilation succeed
    if run(["make", "-s"]) == 0:
        print(f"Compiled binary located at {bootloader}")
    else:
        print("Failed to compile, check output for errors.")

def copy_firmware(firmware_path: str) -> None:
    # Navigate to our tool directory
    os.chdir(TOOL_DIRECTORY)

    # Copy generated firmware to build directory
    bootloader = TOOL_DIRECTORY / '..' / 'bootloader'
    try:
        shutil.copy(firmware_path, bootloader / 'src' / 'firmware.bin')
    except Exception as excep:
        print(f"{excep}")
        exit(FIRMWARE_ERROR)

def generate_secrets():
    try:
        # Get the directory to store generated files
        bootloader = TOOL_DIRECTORY / '..' / 'bootloader' / 'src'

        # Generate our random symmetric AES key & initalization vector
        aes = get_random_bytes(32)
        iv  = get_random_bytes(16)

        # ECC key pair generation
        ecc_private = ECC.generate(curve="ed25519")
        ecc_public  = ecc_private.public_key()

        # Write our AES and ECC private key and close for safety
        with open(bootloader / 'secret_build_output.txt', mode='wb') as file:
            file.write(aes + b'\n')
            file.write(ecc_private.export_key(format='DER'))
            print(f"secret_build_output.txt written to {bootloader}")

        # Create a .der file to store our ECC public key
        with open(bootloader / 'ecc_public.der', mode='wb') as file:
            file.write(ecc_public.export_key(format='DER') + b'\n')
            print(f"ecc_public.der written to {bootloader}")

        # Lastly, store our IV
        with open(bootloader / 'iv.txt', mode='wb') as file:
            file.write(iv + b'\n')
            print(f"iv.txt written to {bootloader}")

    # No point of trying to compile if we don't have any secret
    except Exception as excep:
        print(f"ERROR: There was an error while attempting to generate build secrets and keys.\n{excep}")
        exit(SECRET_ERROR)
    else:
        print(f"All build secrets and information were generated succesfully.")


    
if __name__ == '__main__':

    # Setup arguments for our application
    parser = argparse.ArgumentParser(description='Obsidian Build Tool')
    parser.add_argument("--initial-firmware", help="A path to the compiled firmware binary", default=None)
    args = parser.parse_args()

    # Build and use default firmware if none is provided, otherwise look for the binary at the path specificed
    if args.initial_firmware is None:
        firmware_path = TOOL_DIRECTORY / '..' / 'firmware' / 'firmware'
        binary_path = TOOL_DIRECTORY / '..' / 'firmware' / 'firmware' / 'gcc' / 'main.bin'
        os.chdir(firmware_path)

        run('make clean', shell=True)
        run("make")
    else:
        binary_path = os.path.abspath(pathlib.Path(args.initial_firmware))

    # File doesn't exist/cannot be found
    if not os.path.isfile(binary_path):
        raise FileNotFoundError(
            "ERROR: {} does not exist or is not a file. You may have to call \"make\" in the firmware directory."
            .format(binary_path)
        )

    generate_secrets()
    copy_firmware(binary_path)
    compile_bootloader()
    


