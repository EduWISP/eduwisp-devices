# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.utils import timezone
from eduwisp_users.models import Membership, Role

from eduwisp_devices.models import EnrollmentToken
from eduwisp_devices.platforms import android

pytestmark = pytest.mark.django_db
ADD_URL = "/admin/eduwisp_devices/enrollmenttoken/add/"


def tecnico_di(organizzazione):
    utente = get_user_model().objects.create_user("tecnico", password="x", is_staff=True)
    utente.user_permissions.set(
        Permission.objects.filter(content_type__app_label="eduwisp_devices")
    )
    Membership.objects.create(user=utente, organization=organizzazione, role=Role.IT_ADMIN)
    return utente


def dati_form(organizzazione):
    scadenza = timezone.localtime() + timedelta(days=1)
    return {
        "organization": str(organizzazione.pk),
        "label": "Laboratorio 1",
        "platform": "android",
        "expires_at_0": scadenza.strftime("%d/%m/%Y"),
        "expires_at_1": scadenza.strftime("%H:%M:%S"),
        "max_uses": "5",
    }


def test_qr_mostrato_una_sola_volta(client, scuola):
    client.force_login(tecnico_di(scuola))
    risposta = client.post(ADD_URL, dati_form(scuola), follow=True)
    assert risposta.status_code == 200, risposta.content
    assert 'id="eduwisp-qr"' in risposta.content.decode()
    token = EnrollmentToken.objects.get()
    assert token.created_by.username == "tecnico"
    di_nuovo = client.get(f"/admin/eduwisp_devices/enrollmenttoken/{token.pk}/qr/")
    assert 'id="eduwisp-qr"' not in di_nuovo.content.decode()


def test_tecnico_non_vede_i_token_di_altre_scuole(client, scuola, altra_scuola, crea_token):
    crea_token(altra_scuola)
    client.force_login(tecnico_di(scuola))
    elenco = client.get("/admin/eduwisp_devices/enrollmenttoken/")
    assert "Istituto Fittizio B" not in elenco.content.decode()
    altro = EnrollmentToken.objects.get(organization=altra_scuola)
    assert client.get(f"/admin/eduwisp_devices/enrollmenttoken/{altro.pk}/qr/").status_code == 404


def test_tecnico_non_crea_token_per_altre_scuole(client, scuola, altra_scuola):
    client.force_login(tecnico_di(scuola))
    risposta = client.post(ADD_URL, dati_form(altra_scuola))
    assert risposta.status_code == 200  # il form viene rifiutato
    assert not EnrollmentToken.objects.exists()


def test_contenuto_qr_android(settings):
    testo = android.provisioning_payload("https://server.invalid", "token-di-prova")
    dati = json.loads(testo)
    extras = dati["android.app.extra.PROVISIONING_ADMIN_EXTRAS_BUNDLE"]
    assert extras[android.EXTRA_SERVER_URL] == "https://server.invalid"
    assert extras[android.EXTRA_ENROLLMENT_TOKEN] == "token-di-prova"
    componente = dati["android.app.extra.PROVISIONING_DEVICE_ADMIN_COMPONENT_NAME"]
    assert componente == settings.EDUWISP_ANDROID_DPC["component_name"]


def test_qr_mantiene_le_app_di_sistema_e_imposta_lingua_e_fuso():
    from eduwisp_devices.platforms import android

    dati = json.loads(android.provisioning_payload("https://server.invalid", "token-di-prova"))
    assert dati["android.app.extra.PROVISIONING_LEAVE_ALL_SYSTEM_APPS_ENABLED"] is True
    assert dati["android.app.extra.PROVISIONING_LOCALE"] == "it_IT"
    assert dati["android.app.extra.PROVISIONING_TIME_ZONE"] == "Europe/Rome"
