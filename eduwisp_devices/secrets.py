# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
"""Generazione e verifica dei segreti. Il server conserva solo gli hash."""

import hashlib
import hmac
import secrets


def new_secret(nbytes: int = 32) -> str:
    """Segreto casuale adatto a un URL (almeno 256 bit)."""
    return secrets.token_urlsafe(nbytes)


def hash_secret(value: str) -> str:
    """Hash SHA-256 in esadecimale. Adatto a segreti ad alta entropia, non a password."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def check_secret(value: str, expected_hash: str) -> bool:
    """Confronto in tempo costante."""
    return hmac.compare_digest(hash_secret(value), expected_hash)
