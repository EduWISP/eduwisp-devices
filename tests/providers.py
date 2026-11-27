# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
"""Contributo di prova alla policy, come farebbe eduwisp-apps."""


def app_di_prova(device):
    return {
        "policy": {"apps": {"mode": "allowlist", "allowed": [{"id": "org.example"}]}},
        "version": 5,
    }


def nessun_contributo(device):
    return None
