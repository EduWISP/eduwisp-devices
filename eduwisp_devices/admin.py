# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
from datetime import timedelta

import segno
from django.conf import settings
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from eduwisp_users.models import Role
from eduwisp_users.tenancy import OrganizationScopedAdminMixin

from .models import Device, DeviceAssignment, DevicePolicy, EnrollmentToken
from .platforms import provisioning_payload

MANAGER_ROLES = [Role.SCHOOL_ADMIN, Role.IT_ADMIN]
SESSION_KEY = "eduwisp_enrollment_token_{}"


@admin.register(EnrollmentToken)
class EnrollmentTokenAdmin(OrganizationScopedAdminMixin, admin.ModelAdmin):
    organization_roles = MANAGER_ROLES
    list_display = [
        "label",
        "organization",
        "platform",
        "uses",
        "max_uses",
        "expires_at",
        "revoked",
    ]
    list_filter = ["platform", "revoked"]
    readonly_fields = ["uses", "created_by", "created_at"]

    def get_changeform_initial_data(self, request):
        return {"expires_at": timezone.now() + timedelta(days=7), "max_uses": 1}

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            fields += ["organization", "platform"]
        return fields

    def save_model(self, request, obj, form, change):
        if not change:
            raw = obj.generate()
            obj.created_by = request.user
            super().save_model(request, obj, form, change)
            # Il token in chiaro resta solo nella sessione, per mostrare il QR code una volta.
            request.session[SESSION_KEY.format(obj.pk)] = raw
        else:
            super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        return redirect(reverse("admin:eduwisp_devices_enrollmenttoken_qr", args=[obj.pk]))

    def get_urls(self):
        return [
            path(
                "<int:pk>/qr/",
                self.admin_site.admin_view(self.qr_view),
                name="eduwisp_devices_enrollmenttoken_qr",
            )
        ] + super().get_urls()

    def qr_view(self, request, pk):
        token = get_object_or_404(self.get_queryset(request), pk=pk)
        raw = request.session.pop(SESSION_KEY.format(token.pk), None)
        context = {
            **self.admin_site.each_context(request),
            "title": f"QR code di registrazione — {token}",
            "token": token,
            "opts": self.model._meta,
        }
        if raw is None:
            messages.warning(
                request,
                "Il QR code si può mostrare una sola volta. Per registrare altri dispositivi "
                "crea un nuovo token.",
            )
        else:
            payload = provisioning_payload(token.platform, settings.EDUWISP_SERVER_URL, raw)
            context["qr_svg"] = segno.make(payload, error="m").svg_inline(scale=5)
        return TemplateResponse(request, "eduwisp_devices/enrollment_qr.html", context)


class DeviceAssignmentInline(OrganizationScopedAdminMixin, admin.TabularInline):
    model = DeviceAssignment
    organization_roles = MANAGER_ROLES
    extra = 0
    fields = ["organization", "school_class", "student", "assigned_at", "ended_at"]


@admin.register(Device)
class DeviceAdmin(OrganizationScopedAdminMixin, admin.ModelAdmin):
    inlines = [DeviceAssignmentInline]
    list_display = [
        "__str__",
        "organization",
        "platform",
        "os_version",
        "compliant",
        "policy_version_applied",
        "last_seen_at",
        "is_retired",
    ]
    list_filter = ["platform", "compliant", "is_retired"]
    search_fields = ["display_name", "model"]
    readonly_fields = [
        "id",
        "organization",
        "platform",
        "agent_version",
        "os_version",
        "model",
        "capabilities",
        "enrolled_with",
        "enrolled_at",
        "last_seen_at",
        "policy_version_applied",
        "compliant",
        "non_compliance",
    ]

    def has_add_permission(self, request):
        # I dispositivi si aggiungono solo tramite la registrazione con QR code.
        return False


@admin.register(DevicePolicy)
class DevicePolicyAdmin(OrganizationScopedAdminMixin, admin.ModelAdmin):
    organization_roles = MANAGER_ROLES
    list_display = ["organization", "version", "camera_disabled", "screen_capture_disabled"]
    readonly_fields = ["version", "updated_at"]


@admin.register(DeviceAssignment)
class DeviceAssignmentAdmin(OrganizationScopedAdminMixin, admin.ModelAdmin):
    organization_roles = MANAGER_ROLES
    list_display = ["device", "school_class", "student", "assigned_at", "ended_at"]
    list_filter = ["school_class__school_year", "school_class__section__site"]
