# Argo Family Dashboard for Home Assistant

<p align="center">
  <img src="https://raw.githubusercontent.com/fcaloro-beep/argo-family-dashboard/main/assets/logo.png" alt="Argo Family Dashboard" width="360">
</p>

Integrazione non ufficiale Home Assistant per Argo/didUP pensata per famiglie:
voti, materie, compiti, lezioni, registro, bacheca, assenze e aggiornamenti per
ogni figlio.

> Progetto non ufficiale e non collegato ad Argo Software S.r.l.

## Stato del progetto

Versione beta nativa: `0.4.13`.

La repository e installabile da HACS come custom integration Home Assistant.
Non richiede Docker e non richiede MQTT.

La versione `0.4.9` migliora il calcolo delle medie quando Argo restituisce
voti non numerici, ad esempio `-`, `S` o `NS`: questi valori non vengono
trattati come zero.

La versione `0.4.10` aggiunge il sensore `Ultimo aggiornamento` e riduce gli
attributi troppo grandi nei sensori con molti voti, compiti o registri, evitando
avvisi del database di Home Assistant.

La versione `0.4.11` alleggerisce ulteriormente gli attributi rimuovendo i dati
grezzi interni dagli elenchi esposti ai sensori.

La versione `0.4.12` applica la stessa pulizia anche al sensore `Ultimo voto`.

La versione `0.4.13` ricalcola la media generale dalle medie materia pulite,
quando disponibili, e aggiunge un'opzione per scegliere quanti elementi mostrare
negli attributi dei sensori.

## Screenshot

### Integrazione in Home Assistant

![Integrazione Argo Family Dashboard](https://raw.githubusercontent.com/fcaloro-beep/argo-family-dashboard/main/docs/screenshots/integration-overview.png)

### Configurazione studente

![Configurazione Argo Family Dashboard](https://raw.githubusercontent.com/fcaloro-beep/argo-family-dashboard/main/docs/screenshots/setup-flow.png)

### Opzioni aggiornamento

![Opzioni Argo Family Dashboard](https://raw.githubusercontent.com/fcaloro-beep/argo-family-dashboard/main/docs/screenshots/options-flow.png)

### Plancia di esempio

I dati nello screenshot sono dimostrativi.

![Plancia esempio Argo Family Dashboard](https://raw.githubusercontent.com/fcaloro-beep/argo-family-dashboard/main/docs/screenshots/dashboard-example.png)

## Installazione da HACS

1. Apri HACS.
2. Vai su **Repository personalizzati**.
3. Inserisci questa repository:

   ```text
   https://github.com/fcaloro-beep/argo-family-dashboard
   ```

4. Categoria: **Integrazione**.
5. Installa **Argo Family Dashboard**.
6. Riavvia Home Assistant.

## Configurazione

1. Vai in **Impostazioni > Dispositivi e servizi**.
2. Clicca **Aggiungi integrazione**.
3. Cerca **Argo Family Dashboard**.
4. Inserisci i dati di uno studente:
   - nome figlio;
   - codice scuola;
   - nome utente;
   - password.
5. Ripeti la procedura per ogni figlio.

Home Assistant crea un dispositivo separato per ogni studente.

## Sensori creati

Per ogni figlio vengono creati sensori come:

- stato;
- info studente;
- media generale;
- materie;
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

Gli elenchi completi vengono esposti negli attributi dei sensori, cosi possono
essere usati nelle plance Lovelace.

Il sensore `Info studente` espone anche gli attributi restituiti da Argo per
profilo, codice scuola, eventuale nome scuola, classe e prime informazioni
orario. I campi disponibili possono variare in base alla scuola e al profilo
Argo/didUP.

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

Per una plancia compatibile con qualsiasi studente e consigliato usare il
riepilogo dinamico da `sensor.<studente>_materie`.

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

Per una plancia compatibile con qualsiasi studente, usare il blocco dinamico
delle materie: le materie compaiono solo quando Argo le restituisce.

## Logo e brand

Da Home Assistant 2026.3 le custom integration possono includere direttamente
le proprie immagini brand. Gli asset principali sono in:

- `assets/icon.png`
- `assets/logo.png`
- `custom_components/argo_family_dashboard/brand/icon.png`
- `custom_components/argo_family_dashboard/brand/logo.png`

Non e necessario aprire una richiesta su `home-assistant/brands`.

## Privacy

Le credenziali Argo restano nel server Home Assistant dell'utente. Non vengono
inviate a servizi terzi da questo progetto.

## Licenza

MIT
