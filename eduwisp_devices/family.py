# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
"""Scelta degli studenti maggiorenni sull'accesso dei familiari (ADR-0018)."""

from datetime import timedelta

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from eduwisp_audit.log import record
from eduwisp_audit.models import Action

from .models import DeviceAssignment

TOLLERANZA_OROLOGIO = timedelta(minutes=5)


def adult_student(device):
    """Lo studente maggiorenne a cui il dispositivo è affidato, oppure None.

    Solo dispositivi personali: su quelli condivisi della classe non si chiede nulla.
    """
    a = (
        DeviceAssignment.objects.filter(device=device, ended_at__isnull=True, student__isnull=False)
        .select_related("student")
        .first()
    )
    return a.student if a and a.student.is_adult() else None


def policy_section(device):
    studente = adult_student(device)
    if studente is None:
        return None
    return {"choice_requested": True, "granted": studente.family_access_granted}


def apply_choice(device, choice):
    """Registra la scelta se il server l'aveva chiesta e se è più recente.

    Restituisce True se la scelta è stata registrata. Una data non valida solleva ValueError.
    """
    deciso = parse_datetime(choice["decided_at"])
    if deciso is None:
        raise ValueError("decided_at non valido")
    if timezone.is_naive(deciso):
        deciso = timezone.make_aware(deciso)
    adesso = timezone.now()
    deciso = min(deciso, adesso)  # un orologio avanti non deve bloccare le scelte successive
    studente = adult_student(device)
    if studente is None:
        return False
    if studente.family_access_decided_at and deciso <= studente.family_access_decided_at:
        return False
    studente.family_access_granted = choice["granted"]
    studente.family_access_decided_at = deciso
    studente.save(update_fields=["family_access_granted", "family_access_decided_at"])
    record(
        Action.FAMILY_ACCESS_CHOICE,
        actor=None,
        actor_label=f"dispositivo {device.display_name or device.pk}",
        organization=device.organization,
        granted=choice["granted"],
        student_id=studente.pk,
        device_id=str(device.pk),
    )
    return True
