# -*- coding: utf-8 -*-
"""Kodek formátu .vlcr

V textovém editoru vypadá soubor jako náhodný šum. Zpráva je uvnitř
zamaskovaná proudovou "šifrou" (SHA-256 keystream + XOR) a zakódovaná
přes Base85. POZOR: je to jen maskování pro zábavu, ne skutečné zabezpečení.
"""
import base64
import hashlib
import os
import zlib

MAGIC = b"VLCR\x01"
_PEPPER = b"vzdelany-lid-cr"


def _keystream(salt, n):
    out = b""
    counter = 0
    while len(out) < n:
        out += hashlib.sha256(salt + _PEPPER + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:n]


def _xor(a, b):
    return bytes(x ^ y for x, y in zip(a, b))


def encode(message):
    """Vrátí text obsahu souboru .vlcr pro danou zprávu."""
    data = MAGIC + message.encode("utf-8")
    data += zlib.crc32(data).to_bytes(4, "big")
    salt = os.urandom(8)
    blob = salt + _xor(data, _keystream(salt, len(data)))
    raw = base64.b85encode(blob).decode("ascii")
    return "\n".join(raw[i:i + 72] for i in range(0, len(raw), 72)) + "\n"


def decode(text):
    """Rozluští obsah souboru .vlcr. Při chybě vyvolá ValueError."""
    raw = "".join(text.split())
    if not raw:
        raise ValueError("Nic k rozluštění – vložte obsah souboru .vlcr.")
    try:
        blob = base64.b85decode(raw)
    except Exception:
        raise ValueError("Tohle nevypadá jako platný soubor .vlcr.")
    if len(blob) < 8 + len(MAGIC) + 4:
        raise ValueError("Soubor .vlcr je příliš krátký nebo poškozený.")
    salt, enc = blob[:8], blob[8:]
    data = _xor(enc, _keystream(salt, len(enc)))
    body, crc = data[:-4], data[-4:]
    if not body.startswith(MAGIC) or zlib.crc32(body).to_bytes(4, "big") != crc:
        raise ValueError("Soubor .vlcr je poškozený nebo upravený.")
    return body[len(MAGIC):].decode("utf-8")
