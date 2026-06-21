"""Srun campus portal crypto helpers for HTTP authentication."""

import hashlib
import hmac
import json
import math
import random
import re
import time

_SRUN_BASE64_PAD = "="
_SRUN_BASE64_ALPHABET = "LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA"
_UINT32_MASK = 0xFFFFFFFF


def _ordat(msg: str, index: int) -> int:
    if len(msg) > index:
        return ord(msg[index])
    return 0


def _sencode(msg: str, include_length: bool) -> list[int]:
    length = len(msg)
    result = []
    for i in range(0, length, 4):
        result.append(
            _ordat(msg, i)
            | _ordat(msg, i + 1) << 8
            | _ordat(msg, i + 2) << 16
            | _ordat(msg, i + 3) << 24
        )
    if include_length:
        result.append(length)
    return result


def _lencode(msg: list[int], use_length: bool) -> str | None:
    length = len(msg)
    last_length = (length - 1) << 2
    if use_length:
        message_length = msg[length - 1]
        if message_length < last_length - 3 or message_length > last_length:
            return None
        last_length = message_length
    encoded = "".join(
        chr(value & 0xFF)
        + chr(value >> 8 & 0xFF)
        + chr(value >> 16 & 0xFF)
        + chr(value >> 24 & 0xFF)
        for value in msg
    )
    if use_length:
        return encoded[0:last_length]
    return encoded


def srun_xencode(msg: str, key: str) -> str:
    """Return Srun's XXTEA-like encrypted string for *msg* and *key*."""
    if msg == "":
        return ""

    pwd = _sencode(msg, True)
    pwd_key = _sencode(key, False)
    if len(pwd_key) < 4:
        pwd_key = pwd_key + [0] * (4 - len(pwd_key))

    # This is the portal JavaScript xEncode routine translated directly.
    n = len(pwd) - 1
    z = pwd[n]
    y = pwd[0]
    c = 0x86014019 | 0x183639A0
    q = math.floor(6 + 52 / (n + 1))
    d = 0
    while 0 < q:
        d = (d + c) & _UINT32_MASK
        e = d >> 2 & 3
        p = 0
        while p < n:
            y = pwd[p + 1]
            m = z >> 5 ^ y << 2
            m = m + ((y >> 3 ^ z << 4) ^ (d ^ y))
            m = m + (pwd_key[(p & 3) ^ e] ^ z)
            pwd[p] = (pwd[p] + m) & _UINT32_MASK
            z = pwd[p]
            p = p + 1
        y = pwd[0]
        m = z >> 5 ^ y << 2
        m = m + ((y >> 3 ^ z << 4) ^ (d ^ y))
        m = m + (pwd_key[(p & 3) ^ e] ^ z)
        pwd[n] = (pwd[n] + m) & _UINT32_MASK
        z = pwd[n]
        q = q - 1

    encoded = _lencode(pwd, False)
    return encoded if encoded is not None else ""


def _getbyte(data: str, index: int) -> int:
    value = ord(data[index])
    if value > 255:
        raise ValueError("INVALID_CHARACTER_ERR: DOM Exception 5")
    return value


def srun_base64(data: str) -> str:
    """Return Srun's custom-alphabet base64 encoding for *data*."""
    if len(data) == 0:
        return data

    # Srun uses normal base64 bit packing with a portal-specific alphabet.
    encoded = []
    imax = len(data) - len(data) % 3
    for i in range(0, imax, 3):
        b10 = (_getbyte(data, i) << 16) | (_getbyte(data, i + 1) << 8) | _getbyte(
            data, i + 2
        )
        encoded.append(_SRUN_BASE64_ALPHABET[b10 >> 18])
        encoded.append(_SRUN_BASE64_ALPHABET[(b10 >> 12) & 63])
        encoded.append(_SRUN_BASE64_ALPHABET[(b10 >> 6) & 63])
        encoded.append(_SRUN_BASE64_ALPHABET[b10 & 63])

    if len(data) - imax == 1:
        b10 = _getbyte(data, imax) << 16
        encoded.append(
            _SRUN_BASE64_ALPHABET[b10 >> 18]
            + _SRUN_BASE64_ALPHABET[(b10 >> 12) & 63]
            + _SRUN_BASE64_PAD
            + _SRUN_BASE64_PAD
        )
    elif len(data) - imax == 2:
        b10 = (_getbyte(data, imax) << 16) | (_getbyte(data, imax + 1) << 8)
        encoded.append(
            _SRUN_BASE64_ALPHABET[b10 >> 18]
            + _SRUN_BASE64_ALPHABET[(b10 >> 12) & 63]
            + _SRUN_BASE64_ALPHABET[(b10 >> 6) & 63]
            + _SRUN_BASE64_PAD
        )

    return "".join(encoded)


def srun_hmac_md5(password: str, token: str) -> str:
    """Return the Srun HMAC-MD5 password digest."""
    return hmac.new(token.encode(), password.encode(), hashlib.md5).hexdigest()


def srun_sha1(value: str) -> str:
    """Return a SHA-1 hex digest for *value*."""
    return hashlib.sha1(value.encode()).hexdigest()


def generate_callback() -> str:
    """Return a random jQuery-style JSONP callback name."""
    digits = "".join(str(random.randint(0, 9)) for _ in range(21))
    return "jQuery" + digits + "_" + str(int(time.time() * 1000))


def parse_jsonp(text: str) -> dict | None:
    """Parse a JSONP object response into a dictionary, or return None."""
    match = re.search(r"\((\{.*\})\)", text)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None
