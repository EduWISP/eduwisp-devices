# Changelog — eduwisp-devices

## Non rilasciato / Unreleased

- Creazione del repository (fase di progettazione). / *Repository created (design phase).*
- Licenza AGPL-3.0-or-later con termini aggiuntivi (sezione 7), publiccode.yml e controllo DCO. / *AGPL-3.0-or-later licence with additional terms, publiccode.yml and DCO check.*
- Prototipo v0: token di registrazione con QR code, API del protocollo v0, dispositivi, policy minima, profilo Android, assegnazione dei dispositivi a classi e studenti, isolamento tra istituti. / *v0 prototype: QR enrollment tokens, protocol v0 API, devices, minimal policy, Android profile, device assignment to classes and students, tenant isolation.*
- Studenti maggiorenni (ADR-0018): la policy chiede la scelta sull'accesso dei familiari ai tablet personali; il rapporto di stato la registra (solo se richiesta e più recente) nel registro delle operazioni. Nuova dipendenza: eduwisp-audit. / *Adult students' family-access choice via policy/status, recorded in the audit log.*
- Policy composta con i contributi di altri moduli (`EDUWISP_POLICY_PROVIDERS`), per esempio le app consentite di eduwisp-apps (ADR-0019). / *Policy composed with other modules' contributions.*
- QR code: app di sistema mantenute (decide l'elenco di app consentite), lingua italiana e fuso orario di Roma. / *QR: keep system apps, Italian locale, Rome time zone.*
