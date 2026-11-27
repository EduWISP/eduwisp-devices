# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from eduwisp_school.models import (
    SchoolClass,
    SchoolLevel,
    SchoolYear,
    Section,
    Site,
    Student,
    StudentEnrollment,
    TeachingAssignment,
)

from eduwisp_devices.models import Device, DeviceAssignment
from eduwisp_devices.queries import devices_for_teacher

pytestmark = pytest.mark.django_db


@pytest.fixture
def struttura(scuola):
    anno = SchoolYear.objects.create(
        organization=scuola,
        label="2026/2027",
        start_date=date(2026, 9, 1),
        end_date=date(2027, 8, 31),
        is_current=True,
    )
    media = Site.objects.create(organization=scuola, name="Centro", level=SchoolLevel.SECONDARIA_1)
    a = Section.objects.create(organization=scuola, site=media, name="A")
    b = Section.objects.create(organization=scuola, site=media, name="B")
    classi = {
        nome: SchoolClass.objects.create(
            organization=scuola, school_year=anno, section=sez, year_number=n
        )
        for nome, sez, n in [("1A", a, 1), ("2A", a, 2), ("1B", b, 1)]
    }
    return anno, a, b, classi


def nuovo_dispositivo(organizzazione):
    d = Device(
        organization=organizzazione, platform="android", agent_version="0.1", os_version="15"
    )
    d.issue_token()
    d.save()
    return d


def test_dispositivo_assegnato_a_studente_della_classe(scuola, struttura):
    _, _, _, classi = struttura
    studente = Student.objects.create(organization=scuola, display_name="Studente Fittizio")
    StudentEnrollment.objects.create(
        organization=scuola, student=studente, school_class=classi["1A"]
    )
    assegnazione = DeviceAssignment(
        organization=scuola,
        device=nuovo_dispositivo(scuola),
        school_class=classi["1A"],
        student=studente,
    )
    assegnazione.full_clean()
    assegnazione.save()


def test_studente_non_iscritto_alla_classe(scuola, struttura):
    _, _, _, classi = struttura
    studente = Student.objects.create(organization=scuola, display_name="Studente Fittizio")
    StudentEnrollment.objects.create(
        organization=scuola, student=studente, school_class=classi["1B"]
    )
    assegnazione = DeviceAssignment(
        organization=scuola,
        device=nuovo_dispositivo(scuola),
        school_class=classi["1A"],
        student=studente,
    )
    with pytest.raises(ValidationError):
        assegnazione.full_clean()


def test_dispositivo_condiviso_della_classe(scuola, struttura):
    _, _, _, classi = struttura
    a = DeviceAssignment(
        organization=scuola, device=nuovo_dispositivo(scuola), school_class=classi["2A"]
    )
    a.full_clean()
    a.save()
    assert "uso condiviso" in str(a)


def test_una_sola_assegnazione_attiva(scuola, struttura):
    _, _, _, classi = struttura
    d = nuovo_dispositivo(scuola)
    DeviceAssignment.objects.create(organization=scuola, device=d, school_class=classi["1A"])
    with pytest.raises(IntegrityError):
        DeviceAssignment.objects.create(organization=scuola, device=d, school_class=classi["1B"])


def test_riassegnazione_conserva_lo_storico(scuola, struttura):
    _, _, _, classi = struttura
    d = nuovo_dispositivo(scuola)
    vecchia = DeviceAssignment.objects.create(
        organization=scuola, device=d, school_class=classi["1A"]
    )
    vecchia.ended_at = timezone.now()
    vecchia.save()
    DeviceAssignment.objects.create(organization=scuola, device=d, school_class=classi["1B"])
    assert d.assignments.count() == 2


def test_classe_di_un_altro_istituto(scuola, altra_scuola, struttura):
    _, _, _, classi = struttura
    a = DeviceAssignment(
        organization=altra_scuola, device=nuovo_dispositivo(altra_scuola), school_class=classi["1A"]
    )
    with pytest.raises(ValidationError):
        a.full_clean()


def test_il_docente_vede_solo_i_dispositivi_delle_sue_classi(scuola, struttura):
    anno, a, _, classi = struttura
    tablet = {nome: nuovo_dispositivo(scuola) for nome in classi}
    for nome, d in tablet.items():
        DeviceAssignment.objects.create(organization=scuola, device=d, school_class=classi[nome])
    docente = get_user_model().objects.create_user("prof.a")
    # Incarico su tutta la sezione A: 1ª A e 2ª A, non 1ª B.
    TeachingAssignment.objects.create(
        organization=scuola, teacher=docente, school_year=anno, section=a
    )
    assert set(devices_for_teacher(docente)) == {tablet["1A"], tablet["2A"]}


def test_assegnazione_chiusa_non_conta(scuola, struttura):
    anno, a, _, classi = struttura
    d = nuovo_dispositivo(scuola)
    DeviceAssignment.objects.create(
        organization=scuola, device=d, school_class=classi["1A"], ended_at=timezone.now()
    )
    docente = get_user_model().objects.create_user("prof.a")
    TeachingAssignment.objects.create(
        organization=scuola, teacher=docente, school_year=anno, section=a
    )
    assert not devices_for_teacher(docente).exists()
