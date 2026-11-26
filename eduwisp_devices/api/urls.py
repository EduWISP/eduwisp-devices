# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
from django.urls import path

from . import views

app_name = "eduwisp_protocol_v0"

urlpatterns = [
    path("enroll", views.EnrollView.as_view(), name="enroll"),
    path("policy", views.PolicyView.as_view(), name="policy"),
    path("status", views.StatusView.as_view(), name="status"),
]
