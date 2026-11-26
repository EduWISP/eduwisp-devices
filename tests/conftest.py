# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
from datetime import timedelta

import pytest
from django.utils import timezone
from eduwisp_users.models import Organization
from rest_framework.test import APIClient

from eduwisp_devices.models import EnrollmentToken


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def scuola(db):
    return Organization.objects.create(name="Istituto Fittizio A", slug="istituto-a")


@pytest.fixture
def altra_scuola(db):
    return Organization.objects.create(name="Istituto Fittizio B", slug="istituto-b")


@pytest.fixture
def crea_token():
    def _crea(organizzazione, **kwargs):
        kwargs.setdefault("expires_at", timezone.now() + timedelta(days=1))
        token = EnrollmentToken(organization=organizzazione, label="Laboratorio", **kwargs)
        raw = token.generate()
        token.save()
        return token, raw

    return _crea


@pytest.fixture
def richiesta():
    def _richiesta(raw, **agent):
        return {
            "protocol_version": "0",
            "enrollment_token": raw,
            "agent": {"platform": "android", "agent_version": "0.1.0", "os_version": "15", **agent},
            "capabilities": ["setting:camera_disabled"],
        }

    return _richiesta
