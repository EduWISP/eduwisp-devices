# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
"""Profilo Android: contenuto del QR code per il provisioning Fully Managed del DPC EduWISP.

Riferimento: costanti EXTRA_PROVISIONING_* di android.app.admin.DevicePolicyManager.
Configurazione in settings.EDUWISP_ANDROID_DPC con le chiavi:
``component_name``, ``download_url``, ``signature_checksum`` e, facoltative, ``locale`` e
``time_zone``.
"""

import json

from django.conf import settings

PREFIX = "android.app.extra."
EXTRA_SERVER_URL = "org.eduwisp.SERVER_URL"
EXTRA_ENROLLMENT_TOKEN = "org.eduwisp.ENROLLMENT_TOKEN"


def provisioning_payload(server_url: str, raw_token: str) -> str:
    dpc = settings.EDUWISP_ANDROID_DPC
    payload = {
        PREFIX + "PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME": dpc["component_name"],
        PREFIX + "PROVISIONING_DEVICE_ADMIN_PACKAGE_DOWNLOAD_LOCATION": dpc["download_url"],
        PREFIX + "PROVISIONING_DEVICE_ADMIN_SIGNATURE_CHECKSUM": dpc["signature_checksum"],
        # Le app di sistema restano: decide l'elenco di app consentite (ADR-0019), non il
        # provisioning, che altrimenti disattiverebbe fotocamera, galleria e simili.
        PREFIX + "PROVISIONING_LEAVE_ALL_SYSTEM_APPS_ENABLED": True,
        PREFIX + "PROVISIONING_LOCALE": dpc.get("locale", "it_IT"),
        PREFIX + "PROVISIONING_TIME_ZONE": dpc.get("time_zone", "Europe/Rome"),
        PREFIX + "PROVISIONING_ADMIN_EXTRAS_BUNDLE": {
            EXTRA_SERVER_URL: server_url,
            EXTRA_ENROLLMENT_TOKEN: raw_token,
        },
    }
    return json.dumps(payload, separators=(",", ":"))
