# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
from datetime import timedelta

import pytest
from django.utils import timezone
from eduwisp_protocol import validate

from eduwisp_devices.models import Device, DevicePolicy, EnrollmentToken

pytestmark = pytest.mark.django_db

ENROLL = "/api/protocol/v0/enroll"
POLICY = "/api/protocol/v0/policy"
STATUS = "/api/protocol/v0/status"


def registra(api, richiesta, raw):
    risposta = api.post(ENROLL, richiesta(raw), format="json")
    assert risposta.status_code == 201, risposta.content
    validate("enrollment-response", risposta.json())
    return risposta.json()


def test_flusso_completo(api, scuola, crea_token, richiesta):
    _, raw = crea_token(scuola)
    DevicePolicy.objects.create(organization=scuola, camera_disabled=True)
    dati = registra(api, richiesta, raw)

    api.credentials(HTTP_AUTHORIZATION="Bearer " + dati["device_token"])
    policy = api.get(POLICY)
    assert policy.status_code == 200
    validate("policy", policy.json())
    assert policy.json()["settings"]["camera_disabled"] is True

    stato = {
        "protocol_version": "0",
        "policy_version_applied": policy.json()["policy_version"],
        "compliant": True,
    }
    validate("status-report", stato)
    assert api.post(STATUS, stato, format="json").status_code == 204

    dispositivo = Device.objects.get(pk=dati["device_id"])
    assert dispositivo.organization == scuola
    assert dispositivo.compliant is True
    assert dispositivo.policy_version_applied == policy.json()["policy_version"]


def test_il_server_non_conserva_segreti_in_chiaro(api, scuola, crea_token, richiesta):
    token, raw = crea_token(scuola)
    dati = registra(api, richiesta, raw)
    segreto = dati["device_token"].split(".", 1)[1]
    dispositivo = Device.objects.get(pk=dati["device_id"])
    assert raw not in token.token_hash
    assert segreto not in dispositivo.secret_hash


@pytest.mark.parametrize(
    ("modifica", "codice"),
    [
        ({"revoked": True}, "invalid_token"),
        ({"expires_at": timezone.now() - timedelta(minutes=1)}, "token_expired"),
    ],
)
def test_token_non_utilizzabile(api, scuola, crea_token, richiesta, modifica, codice):
    _, raw = crea_token(scuola, **modifica)
    risposta = api.post(ENROLL, richiesta(raw), format="json")
    assert risposta.status_code == 403
    validate("error", risposta.json())
    assert risposta.json()["error"]["code"] == codice


def test_token_esaurito(api, scuola, crea_token, richiesta):
    _, raw = crea_token(scuola, max_uses=1)
    registra(api, richiesta, raw)
    risposta = api.post(ENROLL, richiesta(raw), format="json")
    assert risposta.json()["error"]["code"] == "token_exhausted"
    assert EnrollmentToken.objects.get().uses == 1


def test_token_inesistente(api, richiesta, db):
    risposta = api.post(ENROLL, richiesta("token-che-non-esiste-0123456789"), format="json")
    assert risposta.status_code == 403
    assert risposta.json()["error"]["code"] == "invalid_token"


def test_dati_non_previsti_rifiutati(api, scuola, crea_token, richiesta):
    _, raw = crea_token(scuola)
    corpo = richiesta(raw)
    corpo["agent"]["imei"] = "000000000000000"
    risposta = api.post(ENROLL, corpo, format="json")
    assert risposta.status_code == 400
    validate("error", risposta.json())
    assert not Device.objects.exists()


def test_json_malformato(api, db):
    risposta = api.post(ENROLL, "{non json", content_type="application/json")
    assert risposta.status_code == 400
    assert risposta.json()["error"]["code"] == "invalid_request"


@pytest.mark.parametrize(
    "intestazione",
    ["", "Bearer", "Bearer non-un-uuid.segreto", "Basic abc", "Bearer {id}.segreto-sbagliato"],
)
def test_credenziale_non_valida(api, scuola, crea_token, richiesta, intestazione):
    _, raw = crea_token(scuola)
    dati = registra(api, richiesta, raw)
    api.credentials(HTTP_AUTHORIZATION=intestazione.format(id=dati["device_id"]))
    risposta = api.get(POLICY)
    assert risposta.status_code == 401
    validate("error", risposta.json())


def test_dispositivo_dismesso(api, scuola, crea_token, richiesta):
    _, raw = crea_token(scuola)
    dati = registra(api, richiesta, raw)
    Device.objects.filter(pk=dati["device_id"]).update(is_retired=True)
    api.credentials(HTTP_AUTHORIZATION="Bearer " + dati["device_token"])
    assert api.get(POLICY).json()["error"]["code"] == "device_retired"


def test_ogni_dispositivo_riceve_la_policy_della_propria_scuola(
    api, scuola, altra_scuola, crea_token, richiesta
):
    DevicePolicy.objects.create(organization=scuola, camera_disabled=True)
    DevicePolicy.objects.create(organization=altra_scuola, camera_disabled=False)
    _, raw_b = crea_token(altra_scuola)
    dati = registra(api, richiesta, raw_b)
    api.credentials(HTTP_AUTHORIZATION="Bearer " + dati["device_token"])
    assert api.get(POLICY).json()["settings"]["camera_disabled"] is False


def test_la_versione_della_policy_cresce(scuola):
    policy = DevicePolicy.objects.create(organization=scuola)
    assert policy.version == 1
    policy.camera_disabled = True
    policy.save()
    assert policy.version == 2


def test_policy_predefinita(api, scuola, crea_token, richiesta):
    _, raw = crea_token(scuola)
    dati = registra(api, richiesta, raw)
    api.credentials(HTTP_AUTHORIZATION="Bearer " + dati["device_token"])
    policy = api.get(POLICY).json()
    assert policy["policy_version"] == 1
    assert policy["settings"] == {"camera_disabled": False, "screen_capture_disabled": False}


def test_contributi_di_altri_moduli(api, scuola, crea_token, richiesta, settings):
    settings.EDUWISP_POLICY_PROVIDERS = [
        "tests.providers.app_di_prova",
        "tests.providers.nessun_contributo",
    ]
    _, raw = crea_token(scuola)
    dati = registra(api, richiesta, raw)
    api.credentials(HTTP_AUTHORIZATION="Bearer " + dati["device_token"])
    policy = api.get(POLICY).json()
    validate("policy", policy)
    assert policy["apps"]["allowed"] == [{"id": "org.example"}]
    base = DevicePolicy.objects.get(organization=scuola).version
    assert policy["policy_version"] == base + 5
