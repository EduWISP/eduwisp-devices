# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
"""Interrogazioni riutilizzabili: per esempio i dispositivi su cui un docente può agire."""

from eduwisp_school.queries import classes_for_teacher

from .models import Device


def devices_for_teacher(user, school_year=None):
    """Dispositivi con un'assegnazione attiva a una classe del docente (RF-010)."""
    classes = classes_for_teacher(user, school_year)
    return Device.objects.filter(
        assignments__school_class__in=classes,
        assignments__ended_at__isnull=True,
        is_retired=False,
    ).distinct()
