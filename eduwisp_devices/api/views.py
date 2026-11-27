# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
"""API del protocollo EduWISP v0 (vedi eduwisp-protocol, docs/developer/protocollo-v0.md)."""

import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string
from eduwisp_protocol import PROTOCOL_VERSION, ProtocolError, validate
from rest_framework import status
from rest_framework.exceptions import ParseError, UnsupportedMediaType
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from ..family import apply_choice, policy_section
from ..models import Device, DevicePolicy, EnrollmentToken
from ..secrets import check_secret, hash_secret

logger = logging.getLogger("eduwisp.devices")


def poll_interval() -> int:
    return getattr(settings, "EDUWISP_POLL_INTERVAL_SECONDS", 900)


def error(code: str, message: str, http_status: int, details: list[str] | None = None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details[:50]
    return Response(body, status=http_status)


class ProtocolView(APIView):
    """Base: niente autenticazione di sessione, solo JSON, errori nel formato del protocollo."""

    authentication_classes = []
    permission_classes = []
    parser_classes = [JSONParser]
    renderer_classes = [JSONRenderer]

    def validated(self, message_name: str, data):
        validate(message_name, data)
        return data

    def handle_exception(self, exc):
        if isinstance(exc, ProtocolError):
            return error("invalid_request", "Messaggio non conforme.", 400, exc.errors)
        if isinstance(exc, ParseError | UnsupportedMediaType):
            return error("invalid_request", "Corpo JSON non valido.", 400)
        return super().handle_exception(exc)

    def authenticated_device(self, request) -> tuple[Device | None, Response | None]:
        header = request.headers.get("Authorization", "")
        scheme, _, credential = header.partition(" ")
        device_id, _, secret = credential.partition(".")
        if scheme != "Bearer" or not device_id or not secret:
            return None, error("unauthorized", "Credenziale mancante o non valida.", 401)
        try:
            device = Device.objects.select_related("organization").get(pk=uuid.UUID(device_id))
        except (ValueError, Device.DoesNotExist):
            return None, error("unauthorized", "Credenziale mancante o non valida.", 401)
        if not check_secret(secret, device.secret_hash):
            return None, error("unauthorized", "Credenziale mancante o non valida.", 401)
        if device.is_retired or not device.organization.is_active:
            return None, error("device_retired", "Dispositivo dismesso.", 403)
        return device, None


class EnrollView(ProtocolView):
    def post(self, request):
        data = self.validated("enrollment-request", request.data)
        with transaction.atomic():
            token = (
                EnrollmentToken.objects.select_for_update()
                .filter(token_hash=hash_secret(data["enrollment_token"]))
                .first()
            )
            if token is None or token.revoked:
                return error("invalid_token", "Token di registrazione non valido.", 403)
            if token.is_expired:
                return error("token_expired", "Il token di registrazione è scaduto.", 403)
            if token.is_exhausted:
                return error("token_exhausted", "Il token di registrazione è esaurito.", 403)
            agent = data["agent"]
            if agent["platform"] != token.platform:
                return error("invalid_token", "Token non valido per questa piattaforma.", 403)
            device = Device(
                organization=token.organization,
                platform=agent["platform"],
                agent_version=agent["agent_version"],
                os_version=agent["os_version"],
                model=agent.get("model", ""),
                capabilities=data["capabilities"],
                enrolled_with=token,
                last_seen_at=timezone.now(),
            )
            device_token = device.issue_token()
            device.save()
            token.uses += 1
            token.save(update_fields=["uses"])
        logger.info("Dispositivo %s registrato in %s", device.pk, device.organization_id)
        return Response(
            {
                "protocol_version": PROTOCOL_VERSION,
                "device_id": str(device.pk),
                "device_token": device_token,
                "poll_interval_seconds": poll_interval(),
            },
            status=status.HTTP_201_CREATED,
        )


class PolicyView(ProtocolView):
    def get(self, request):
        device, err = self.authenticated_device(request)
        if err:
            return err
        policy = DevicePolicy.objects.filter(organization=device.organization).first()
        if policy is None:
            policy = DevicePolicy(organization=device.organization)
            policy.save()
        Device.objects.filter(pk=device.pk).update(last_seen_at=timezone.now())
        body = {
            "protocol_version": PROTOCOL_VERSION,
            "policy_version": policy.version,
            "poll_interval_seconds": poll_interval(),
            "settings": policy.settings_dict(),
        }
        # Contributi degli altri moduli (per esempio eduwisp-apps, ADR-0019): ciascuno
        # aggiunge chiavi alla policy e una parte della versione, che resta crescente.
        for percorso in getattr(settings, "EDUWISP_POLICY_PROVIDERS", []):
            contributo = import_string(percorso)(device)
            if contributo:
                body.update(contributo["policy"])
                body["policy_version"] += contributo.get("version", 0)
        famiglia = policy_section(device)
        if famiglia is not None:
            body["family_access"] = famiglia
        return Response(body)


class StatusView(ProtocolView):
    def post(self, request):
        device, err = self.authenticated_device(request)
        if err:
            return err
        data = self.validated("status-report", request.data)
        if "family_access_choice" in data:
            try:
                apply_choice(device, data["family_access_choice"])
            except ValueError:
                return error("invalid_request", "Data della scelta non valida.", 400)
        device.policy_version_applied = data["policy_version_applied"]
        device.compliant = data["compliant"]
        device.non_compliance = data.get("non_compliance", [])
        device.agent_version = data.get("agent_version", device.agent_version)
        device.os_version = data.get("os_version", device.os_version)
        device.last_seen_at = timezone.now()
        device.save(
            update_fields=[
                "policy_version_applied",
                "compliant",
                "non_compliance",
                "agent_version",
                "os_version",
                "last_seen_at",
            ]
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
