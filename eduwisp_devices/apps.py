# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
from django.apps import AppConfig


class EduwispDevicesConfig(AppConfig):
    name = "eduwisp_devices"
    verbose_name = "EduWISP — dispositivi"
    default_auto_field = "django.db.models.BigAutoField"
