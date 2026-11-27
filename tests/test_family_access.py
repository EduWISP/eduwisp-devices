# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
from datetime import date, timedelta

import pytest
from django.utils import timezone
from eduwisp_audit.models import Action, AuditEvent
from eduwisp_protocol import validate
from eduwisp_school.models import (
    SchoolClass,
    SchoolLevel,
    SchoolYear,
    Section,
    Site,
    Student,
    StudentEnrollment,
)

from eduwisp_devices.models import Device, DeviceAssignment

pytestmark = pytest.mark.django_db

POLICY = "/api/protocol/v0/policy"
STATUS = "/api/protocol/v0/status"


@pytest.fixture
def tablet(api, scuola, crea_token, richiesta):
    """Tablet registrato e affidato a uno studente di quinta."""
    _, raw = crea_token(scuola)
    dati = api.post("/api/protocol/v0/enroll", richiesta(raw), format="json").json()
    api.credentials(HTTP_AUTHORIZATION="Bearer " + dati["device_token"])
    anno = SchoolYear.objects.create(
        organization=scuola,
        label="2026/2027",
        start_date=date(2026, 9, 1),
        end_date=date(2027, 8, 31),
        is_current=True,
    )
    sede = Site.objects.create(organization=scuola, name="Sede", level=SchoolLevel.SECONDARIA_2)
    sez = Section.objects.create(organization=scuola, site=sede, name="A")
    classe = SchoolClass.objects.create(
        organization=scuola, school_year=anno, section=sez, year_number=5
    )
    studente = Student.objects.create(organization=scuola, display_name="Rossi Anna")
    StudentEnrollment.objects.create(organization=scuola, student=studente, school_class=classe)
    device = Device.objects.get(pk=dati["device_id"])
    DeviceAssignment.objects.create(
        organization=scuola, device=device, school_class=classe, student=studente
    )
    return device, studente


def stato(**extra):
    s = {"protocol_version": "0", "policy_version_applied": 1, "compliant": True, **extra}
    validate("status-report", s)
    return s


def test_minorenne_nessuna_domanda(api, tablet):
    assert "family_access" not in api.get(POLICY).json()


def test_maggiorenne_sceglie_dal_tablet(api, tablet):
    _, studente = tablet
    studente.birth_date = timezone.localdate().replace(
        year=timezone.localdate().year - 18
    ) - timedelta(days=1)
    studente.save()
    policy = api.get(POLICY).json()
    validate("policy", policy)
    assert policy["family_access"] == {"choice_requested": True, "granted": None}

    quando = timezone.now().isoformat()
    scelta = {"granted": True, "decided_at": quando}
    assert api.post(STATUS, stato(family_access_choice=scelta), format="json").status_code == 204
    studente.refresh_from_db()
    assert studente.family_access_granted is True
    assert api.get(POLICY).json()["family_access"]["granted"] is True
    ev = AuditEvent.objects.get(action=Action.FAMILY_ACCESS_CHOICE)
    assert ev.details["granted"] is True and ev.actor is None

    # Una scelta più vecchia (rapporto arrivato in ritardo) non sovrascrive quella nuova
    vecchia = {"granted": False, "decided_at": (timezone.now() - timedelta(hours=1)).isoformat()}
    api.post(STATUS, stato(family_access_choice=vecchia), format="json")
    studente.refresh_from_db()
    assert studente.family_access_granted is True

    # Lo studente cambia idea
    nuova = {"granted": False, "decided_at": (timezone.now() + timedelta(seconds=1)).isoformat()}
    api.post(STATUS, stato(family_access_choice=nuova), format="json")
    studente.refresh_from_db()
    assert studente.family_access_granted is False
    assert AuditEvent.objects.filter(action=Action.FAMILY_ACCESS_CHOICE).count() == 2


def test_scelta_ignorata_se_non_richiesta(api, tablet):
    _, studente = tablet  # minorenne
    scelta = {"granted": True, "decided_at": timezone.now().isoformat()}
    assert api.post(STATUS, stato(family_access_choice=scelta), format="json").status_code == 204
    studente.refresh_from_db()
    assert studente.family_access_granted is None
    assert not AuditEvent.objects.exists()


def test_data_non_valida(api, tablet):
    _, studente = tablet
    studente.birth_date = date(1982, 1, 1)
    studente.save()
    scelta = {"granted": True, "decided_at": "ieri"}
    assert api.post(STATUS, stato(family_access_choice=scelta), format="json").status_code == 400


def test_dispositivo_condiviso_non_chiede(api, tablet):
    device, studente = tablet
    studente.birth_date = date(1982, 1, 1)
    studente.save()
    a = DeviceAssignment.objects.get(device=device)
    a.ended_at = timezone.now()
    a.save()
    DeviceAssignment.objects.create(
        organization=device.organization, device=device, school_class=a.school_class
    )
    assert "family_access" not in api.get(POLICY).json()
