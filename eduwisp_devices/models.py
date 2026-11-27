# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Michele Salerno e i contributori di EduWISP
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from eduwisp_school.models import SchoolClass, Student, StudentEnrollment
from eduwisp_users.models import OrganizationOwned

from .secrets import hash_secret, new_secret


class EnrollmentToken(OrganizationOwned):
    """Token per registrare dispositivi in un'organizzazione. Si conserva solo l'hash."""

    label = models.CharField("descrizione", max_length=200)
    platform = models.CharField("piattaforma", max_length=32, default="android")
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    expires_at = models.DateTimeField("scade il")
    max_uses = models.PositiveIntegerField("utilizzi massimi", default=1)
    uses = models.PositiveIntegerField("utilizzi", default=0, editable=False)
    revoked = models.BooleanField("revocato", default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        verbose_name="creato da",
    )
    created_at = models.DateTimeField("creato il", auto_now_add=True)

    class Meta:
        verbose_name = "token di registrazione"
        verbose_name_plural = "token di registrazione"
        ordering = ["-created_at"]

    def __str__(self):
        return self.label

    def generate(self) -> str:
        """Genera un nuovo token, ne salva l'hash e restituisce il valore in chiaro (una volta)."""
        raw = new_secret()
        self.token_hash = hash_secret(raw)
        return raw

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_exhausted(self) -> bool:
        return self.uses >= self.max_uses


class Device(OrganizationOwned):
    """Dispositivo gestito. Contiene solo i dati tecnici minimi (RC-002)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    display_name = models.CharField("nome", max_length=100, blank=True)
    platform = models.CharField("piattaforma", max_length=32)
    agent_version = models.CharField("versione agente", max_length=32)
    os_version = models.CharField("versione sistema", max_length=32)
    model = models.CharField("modello", max_length=64, blank=True)
    capabilities = models.JSONField("capacità", default=list, blank=True)
    secret_hash = models.CharField(max_length=64, editable=False)
    enrolled_with = models.ForeignKey(
        EnrollmentToken, on_delete=models.SET_NULL, null=True, blank=True, editable=False
    )
    enrolled_at = models.DateTimeField("registrato il", auto_now_add=True)
    last_seen_at = models.DateTimeField("ultimo contatto", null=True, blank=True)
    policy_version_applied = models.PositiveIntegerField("versione policy applicata", default=0)
    compliant = models.BooleanField("conforme", null=True)
    non_compliance = models.JSONField("non conformità", default=list, blank=True)
    is_retired = models.BooleanField("dismesso", default=False)

    class Meta:
        verbose_name = "dispositivo"
        verbose_name_plural = "dispositivi"
        ordering = ["-enrolled_at"]

    def __str__(self):
        return self.display_name or f"{self.platform} {str(self.id)[:8]}"

    def issue_token(self) -> str:
        """Crea la credenziale del dispositivo: restituita una volta, si conserva solo l'hash."""
        secret = new_secret()
        self.secret_hash = hash_secret(secret)
        return f"{self.id}.{secret}"


class DevicePolicy(OrganizationOwned):
    """Policy minima per organizzazione.

    Provvisoria: nel prototipo vive qui; la composizione delle policy (scuola, famiglia,
    sicurezza) sarà compito di eduwisp-policy.
    """

    version = models.PositiveIntegerField("versione", default=0, editable=False)
    camera_disabled = models.BooleanField("fotocamera disattivata", default=False)
    screen_capture_disabled = models.BooleanField(
        "acquisizione dello schermo disattivata", default=False
    )
    updated_at = models.DateTimeField("aggiornata il", auto_now=True)

    class Meta:
        verbose_name = "policy dei dispositivi"
        verbose_name_plural = "policy dei dispositivi"
        constraints = [
            models.UniqueConstraint(fields=["organization"], name="una_policy_per_organizzazione")
        ]

    def __str__(self):
        return f"Policy {self.organization} v{self.version}"

    def save(self, *args, **kwargs):
        self.version += 1
        super().save(*args, **kwargs)

    def settings_dict(self) -> dict:
        return {
            "camera_disabled": self.camera_disabled,
            "screen_capture_disabled": self.screen_capture_disabled,
        }


class DeviceAssignment(OrganizationOwned):
    """Assegnazione di un dispositivo a una classe e, se serve, a uno studente (RF-004).

    Un dispositivo può essere di classe (condiviso, per esempio un carrello di tablet) oppure
    affidato a uno studente iscritto a quella classe. Le assegnazioni non si cancellano:
    si chiudono con ``ended_at``, così resta lo storico necessario.
    """

    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="assignments", verbose_name="dispositivo"
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        related_name="device_assignments",
        verbose_name="classe",
    )
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="device_assignments",
        verbose_name="studente",
        help_text="vuoto = dispositivo condiviso della classe",
    )
    assigned_at = models.DateTimeField("assegnato il", default=timezone.now)
    ended_at = models.DateTimeField("terminata il", null=True, blank=True)
    same_organization_fields = ("device", "school_class", "student")

    class Meta:
        verbose_name = "assegnazione"
        verbose_name_plural = "assegnazioni"
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["device"],
                condition=models.Q(ended_at__isnull=True),
                name="una_assegnazione_attiva_per_dispositivo",
            )
        ]

    def __str__(self):
        chi = self.student or "uso condiviso"
        return f"{self.device} → {self.school_class} ({chi})"

    def clean(self):
        super().clean()
        if self.student_id and self.school_class_id:
            iscritto = StudentEnrollment.objects.filter(
                student_id=self.student_id, school_class_id=self.school_class_id
            ).exists()
            if not iscritto:
                raise ValidationError({"student": "Lo studente non è iscritto a questa classe."})
        if self.ended_at and self.ended_at < self.assigned_at:
            raise ValidationError({"ended_at": "Deve essere successiva all'assegnazione."})
