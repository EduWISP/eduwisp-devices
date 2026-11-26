# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
"""Profilo Android: contenuto del QR code per il provisioning Fully Managed del DPC EduWISP.

Riferimento: costanti EXTRA_PROVISIONING_* di android.app.admin.DevicePolicyManager.
Configurazione in settings.EDUWISP_ANDROID_DPC con le chiavi:
``component_name``, ``download_url``, ``signature_checksum``.
"""

import json

from django.conf import settings

PREFIX = "android.app.extra."
EXTRA_SERVER_URL = "io.github.eduwisp.SERVER_URL"
EXTRA_ENROLLMENT_TOKEN = "io.github.eduwisp.ENROLLMENT_TOKEN"


def provisioning_payload(server_url: str, raw_token: str) -> str:
    dpc = settings.EDUWISP_ANDROID_DPC
    payload = {
        PREFIX + "PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME": dpc["component_name"],
        PREFIX + "PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION": dpc["download_url"],
        PREFIX + "PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM": dpc["signature_checksum"],
        PREFIX + "PROVISIONING_ADMIN_EXTRAS_BUNDLE": {
            EXTRA_SERVER_URL: server_url,
            EXTRA_ENROLLMENT_TOKEN: raw_token,
        },
    }
    return json.dumps(payload, separators=(",", ":"))
