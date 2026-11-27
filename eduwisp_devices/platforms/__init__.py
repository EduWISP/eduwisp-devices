# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
"""Profili di piattaforma (ADR-0011).

Il core non conosce le singole piattaforme: ogni profilo sa solo come trasformare
un token di registrazione nel contenuto del QR code di provisioning.
"""

from . import android

PROFILES = {"android": android}


def provisioning_payload(platform: str, server_url: str, raw_token: str) -> str:
    try:
        profile = PROFILES[platform]
    except KeyError as exc:
        raise ValueError(f"Piattaforma non supportata: {platform}") from exc
    return profile.provisioning_payload(server_url, raw_token)
