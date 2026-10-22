"""Short, human-friendly reference codes that are easy to read out over the phone."""

from __future__ import annotations

import secrets

# No 0/O, 1/I/L to avoid confusion when codes are read aloud or typed on a keypad.
ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def new_reference(prefix: str, length: int = 6) -> str:
    return f"{prefix}-" + "".join(secrets.choice(ALPHABET) for _ in range(length))
