<p align="center"><img src="https://raw.githubusercontent.com/EduWISP/.github/main/branding/eduwisp-mark.svg" alt="EduWISP" height="72"></p>

# eduwisp-devices

**Gestione dispositivi (MDM)** · *Device management (MDM)*

Inventario, ciclo di vita, provisioning e comandi remoti dei dispositivi gestiti, **indipendente dalla piattaforma**: le funzioni specifiche (oggi Android) arrivano dagli agenti tramite `eduwisp-protocol`.

> 🧪 **Stato: prototipo v0.** Registrazione dei dispositivi con QR code, protocollo v0 e policy minima. La progettazione è nella [documentazione EduWISP](https://eduwisp.org/docs/moduli/mdm/).

🇬🇧 *Inventory, lifecycle, provisioning and remote commands for managed devices, **platform-independent**: platform-specific features (Android first) come from agents via `eduwisp-protocol`. **Status: design phase**, no code yet. See the [design docs](https://eduwisp.org/docs/en/modules/mdm/).*

## Documentazione / Documentation

- Progettazione / Design: <https://eduwisp.org/docs/moduli/mdm/>
- Mappa dei repository / Repository map: <https://eduwisp.org/docs/architettura/repository/>
- Documentazione del modulo / Module docs: [`docs/user/`](docs/user/) · [`docs/developer/`](docs/developer/)

## Cosa contiene il prototipo / What the prototype contains

- **Token di registrazione** per organizzazione: scadenza, utilizzi massimi, revoca. Il server ne conserva solo l'hash; il **QR code** si vede **una sola volta**, subito dopo la creazione.
- **API del protocollo v0** (`/api/protocol/v0/enroll`, `/policy`, `/status`), con i messaggi validati dagli schemi di [eduwisp-protocol](https://github.com/EduWISP/eduwisp-protocol).
- **Dispositivi** con solo i dati tecnici minimi; credenziale per dispositivo conservata come hash.
- **Assegnazioni**: ogni dispositivo si assegna a una **classe** e, se serve, a uno **studente** iscritto a quella classe (oppure resta condiviso della classe). Le assegnazioni si chiudono, non si cancellano.
- `queries.devices_for_teacher()`: i dispositivi delle classi del docente nell'anno in corso (RF-010).
- **Policy minima** per organizzazione (fotocamera, acquisizione dello schermo). È provvisoria: la composizione delle policy sarà compito di `eduwisp-policy`.
- **Profili di piattaforma** (`eduwisp_devices/platforms/`): il core non conosce Android; il profilo Android genera solo il contenuto del QR code di provisioning.
- Ogni tecnico vede **solo i dati del proprio istituto** (`OrganizationScopedAdminMixin` di eduwisp-users).

### Provarlo in locale / Try it locally

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e ../eduwisp-protocol -e ../eduwisp-users -e ../eduwisp-school -e ".[test]"
pytest
python -m django migrate --settings=tests.settings --pythonpath=.
python -m django createsuperuser --settings=tests.settings --pythonpath=.
python -m django runserver --settings=tests.settings --pythonpath=.
```

Poi apri <http://127.0.0.1:8000/admin/>, crea un'organizzazione e un token di registrazione: comparirà il QR code. Le impostazioni in `tests/` sono **solo per sviluppo**.

## Dipendenze / Dependencies

[`eduwisp-utils`](https://github.com/EduWISP/eduwisp-utils), [`eduwisp-users`](https://github.com/EduWISP/eduwisp-users), [`eduwisp-audit`](https://github.com/EduWISP/eduwisp-audit), [`eduwisp-school`](https://github.com/EduWISP/eduwisp-school), [`eduwisp-protocol`](https://github.com/EduWISP/eduwisp-protocol)

## Privacy

Dati personali previsti e regole: [PRIVACY.md](PRIVACY.md). Il rispetto della normativa su privacy e minori è un vincolo bloccante ([ADR-0008](https://eduwisp.org/docs/decisioni/0008-conformita-normativa/)).

## Responsabile del modulo / Module owner

Cerchiamo persone che vogliano prendere in carico questo modulo! Proponiti in [Discussions](https://github.com/EduWISP/docs/discussions). / *Want to own this module? Say hi in Discussions.*

## Contribuire / Contributing

Vedi [CONTRIBUTING](https://github.com/EduWISP/.github/blob/main/CONTRIBUTING.md) e il [Codice di condotta](https://github.com/EduWISP/.github/blob/main/CODE_OF_CONDUCT.md). **Mai dati personali reali** di studenti, famiglie o personale.

## Licenza / License

**AGPL-3.0-or-later**, con termini aggiuntivi di attribuzione e tutela del nome (sezione 7): vedi [LICENSE](LICENSE) e [NOTICE.md](NOTICE.md). Chi usa o modifica EduWISP deve sempre indicare «Basato su EduWISP» e non può usare il nome e il logo per versioni modificate. Licenza scelta secondo le [linee guida AgID](https://eduwisp.org/docs/decisioni/0006-licenza/) per il software usato via rete.

*AGPL-3.0-or-later with additional attribution and trademark terms (section 7): see LICENSE and NOTICE.md.*

I contributi richiedono il [DCO](https://github.com/EduWISP/.github/blob/main/CONTRIBUTING.md#dco) (`git commit -s`).
