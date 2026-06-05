# Argo Family Dashboard for Home Assistant

![Argo Family Dashboard](assets/logo.svg)

Dashboard familiare per visualizzare in Home Assistant i dati del registro
elettronico Argo/didUP: medie, voti, materie, compiti, attivita, registro,
bacheca e assenze.

> Progetto non ufficiale e non collegato ad Argo Software S.r.l.

## Stato del progetto

Versione beta nativa: `0.4.0`.

Questa repository e pensata per essere installabile da HACS come una normale
custom integration Home Assistant.

## Esperienza utente prevista

1. Installa da HACS.
2. Riavvia Home Assistant.
3. Vai in **Impostazioni > Dispositivi e servizi > Aggiungi integrazione**.
4. Cerca **Argo Family Dashboard**.
5. Inserisci i dati di un figlio:
   - nome figlio;
   - codice scuola;
   - nome utente;
   - password.
6. Ripeti la procedura per ogni figlio.
7. Home Assistant crea le entita sensore per ogni figlio.

Non e richiesto Docker e non e richiesto MQTT.

## Icona Home Assistant

Home Assistant mostra l'icona ufficiale di una custom integration tramite il
repository `home-assistant/brands`. Gli asset sono gia pronti in:

- `assets/icon.png`
- `assets/logo.png`
- `brands/custom_integrations/argo_family_dashboard/icon.png`
- `brands/custom_integrations/argo_family_dashboard/logo.png`

Quando la repository sara pubblicata su GitHub, questi file potranno essere
usati per aprire una richiesta su `home-assistant/brands`.

## Installazione HACS

Quando la repository sara pubblicata su GitHub:

1. apri HACS;
2. aggiungi questa repository come repository personalizzato;
3. categoria: `Integration`;
4. installa `Argo Family Dashboard`;
5. riavvia Home Assistant.

## Sensori creati

Per ogni figlio vengono creati sensori come:

- stato;
- media generale;
- materie;
- sensori per singola materia;
- voti;
- ultimo voto;
- compiti;
- compiti da fare;
- compiti assegnati;
- prossimi impegni;
- aggiornamenti;
- registro;
- lezioni;
- attivita svolte;
- promemoria;
- assenze;
- bacheca/comunicazioni;
- bacheca alunno;
- note;
- orario.

Gli elenchi completi vengono esposti negli attributi dei sensori.

## Materie dinamiche

Le materie non sono fisse nel codice. L'integrazione legge le materie restituite
da Argo per ogni studente e crea automaticamente i sensori relativi.

Esempi:

- `sensor.argo_edoardo_materia_italiano`
- `sensor.argo_edoardo_materia_matematica`
- `sensor.argo_mario_materia_scienze_naturali`

Se uno studente non ha voti o non ha materie disponibili, non vengono creati
sensori materia inutili. Quando Argo iniziera a restituire nuove materie, queste
appariranno automaticamente dopo il prossimo aggiornamento.

Per questo motivo le plance di esempio usano due approcci:

- riepilogo dinamico da `sensor.<studente>_materie`, consigliato per tutti;
- sensori materia singoli solo dove esistono davvero per quello studente.

## Entita principali

Il prefisso delle entita dipende dal nome inserito per lo studente.

Esempio con nome figlio `Edoardo`:

| Dato | Entita |
|---|---|
| Stato | `sensor.argo_edoardo_stato` |
| Media generale | `sensor.argo_edoardo_media_generale` |
| Materie | `sensor.argo_edoardo_materie` |
| Voti | `sensor.argo_edoardo_voti` |
| Ultimo voto | `sensor.argo_edoardo_ultimo_voto` |
| Compiti | `sensor.argo_edoardo_compiti` |
| Compiti da fare | `sensor.argo_edoardo_compiti_da_fare` |
| Prossimi impegni | `sensor.argo_edoardo_prossimi_impegni` |
| Registro | `sensor.argo_edoardo_registro` |
| Bacheca | `sensor.argo_edoardo_bacheca` |
| Assenze | `sensor.argo_edoardo_assenze` |

## Plance di esempio

La repository include plance Lovelace di esempio per Edoardo e Francesco.
Sono solo esempi: ogni utente puo duplicarle e sostituire il prefisso
`argo_edoardo` con il nome del proprio figlio.

Per una plancia compatibile con qualsiasi studente e consigliato usare il
blocco dinamico delle materie, cosi le materie compaiono solo quando Argo le
restituisce.

## Privacy

Le credenziali Argo restano nel server dell'utente. Non vengono inviate a
servizi terzi da questo progetto.

## Licenza

MIT
