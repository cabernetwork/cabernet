"""
MIT License

Copyright (C) 2021 ROCKY4546
https://github.com/rocky4546

This file is part of Cabernet

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the “Software”), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.
"""

import logging
import platform
import os

try:
    import cryptography
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.fernet import Fernet

    CRYPTO_LOADED = True
except ImportError:
    CRYPTO_LOADED = False

ENCRYPT_STRING = 'ENC::'

LOGGER = logging.getLogger(__name__)


def set_fernet_key():
    opersystem = platform.system()
    # is there a key already generated
    if opersystem in ['Windows']:
        key_file = os.getenv('LOCALAPPDATA') + '/.cabernet/key.txt'
    else:  # linux
        key_file = os.getenv('HOME') + '/.cabernet/key.txt'
    try:
        with open(key_file, 'rb') as f:
            key = f.read()
    except FileNotFoundError:
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        with open(key_file, 'wb') as f:
            f.write(key)
    return key


def encrypt(clearstr, encrypt_key):
    if clearstr.startswith(ENCRYPT_STRING):
        # already encrypted_pwd
        return clearstr
    else:
        f = Fernet(encrypt_key)
        token = f.encrypt(clearstr.encode())
        return ENCRYPT_STRING + token.decode()


def decrypt(enc_str, encrypt_key):
    if enc_str.startswith(ENCRYPT_STRING):
        f = Fernet(encrypt_key)
        try:
            token = f.decrypt(enc_str[len(ENCRYPT_STRING):].encode())
        except cryptography.fernet.InvalidToken:
            # occurs when multiple users are running the app.
            # need to signal the caller that we have issues
            LOGGER.warning("Unable to decrypt string.")
            return None

        return token.decode()
    else:
        return enc_str
