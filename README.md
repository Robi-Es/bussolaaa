# Bussola

Sito di pacchetti viaggio. Non vende nulla: unisce voli, alloggio e spostamenti e rimanda ai siti ufficiali.
Funziona su GitHub Pages (gratis) e aggiorna i prezzi dei voli ogni giorno in automatico.

## Cartelle

- `site/` il sito (pagina, dati dei pacchetti, impostazioni recensioni)
- `config/routes.json` città di partenza, destinazioni e rotte. Qui aggiungi o cambi i pacchetti.
- `scripts/build_packages.py` scarica i prezzi da Aviasales e crea i pacchetti
- `.github/workflows/deploy.yml` l'aggiornamento automatico quotidiano

## 1. Carica i file su GitHub

1. Apri il tuo repository `bussola` su github.com.
2. Clicca **Add file → Upload files**.
3. Trascina dentro **il contenuto** della cartella (non la cartella stessa): `site`, `config`, `scripts`, `README.md`, `.gitignore`.
4. In basso clicca **Commit changes**.

La cartella `.github` è nascosta sul Mac e può non essere trascinabile. Creala così:
1. **Add file → Create new file**.
2. Nel campo del nome scrivi `.github/workflows/deploy.yml` (le barre creano le cartelle da sole).
3. Incolla il contenuto del file `deploy.yml` di questo pacchetto e clicca **Commit changes**.

## 2. Attiva la pubblicazione

1. Nel repository apri **Settings → Pages**.
2. Alla voce **Source** scegli **GitHub Actions**. Non scegliere "Deploy from a branch".
3. Apri il tab **Actions**: vedrai partire "Aggiorna prezzi e pubblica il sito". Quando diventa verde, l'indirizzo del sito è in **Settings → Pages**.

Finché non aggiungi il token, il sito mostra i dati dimostrativi (e lo dichiara in un avviso).

## 3. Collega i prezzi veri

1. Apri **Settings → Secrets and variables → Actions → New repository secret**.
2. Crea questi segreti (il nome deve essere identico):
   - `TRAVELPAYOUTS_TOKEN`: il token dal tuo profilo Travelpayouts, scheda **API token**. Obbligatorio.
   - `TP_MARKER`: il tuo marker di affiliazione Travelpayouts. Facoltativo, per guadagnare sulle prenotazioni.
   - `BOOKING_AID`: il tuo ID affiliato Booking.com. Facoltativo.
3. Vai nel tab **Actions**, scegli il workflow, clicca **Run workflow**. Da quel momento va da solo ogni giorno.

I segreti non compaiono mai nel sito né nel codice. Non incollare mai il token in un file del repository.

Come funziona la parte prezzi:
- Il prezzo del volo arriva da Aviasales ed è un prezzo salvato negli ultimi giorni, non in tempo reale.
- Alloggio, transfer e tessere sono stime che modifichi tu in `config/routes.json`. Le voci con `~` e la scritta "stima" lo dicono ai visitatori.
- Se una rotta non ha offerte valide (2–5 notti, partenza tra almeno 7 giorni), quel pacchetto non compare.
- Se l'aggiornamento fallisce del tutto, il sito resta com'era.

Da controllare con il tuo account: il formato del `marker` nei link. La guida di Travelpayouts rimanda al suo modulo di "deep link". Fai una prova con un link e, se serve, cambia la funzione `flight_link` in `scripts/build_packages.py`.

## 4. Attiva le recensioni (Giscus)

Le recensioni sono commenti in una sezione "Discussions" del repository. Chi scrive deve avere un account GitHub gratuito.

1. Nel repository apri **Settings → General**, scorri a **Features** e spunta **Discussions**.
2. Apri il tab **Discussions → ⚙ Categories**, crea una categoria chiamata `Recensioni` di tipo **Announcements**.
3. Installa l'app Giscus sul repository: [github.com/apps/giscus](https://github.com/apps/giscus), scegli solo il repository `bussola`.
4. Vai su [giscus.app/it](https://giscus.app/it), scrivi `tuonome/bussola` come repository, scegli la categoria `Recensioni`. In fondo alla pagina trovi `data-repo-id` e `data-category-id`.
5. Apri `site/data/site.json` su GitHub (icona matita), inserisci i tre valori e conferma:

```json
{
  "giscus": {
    "repo": "tuonome/bussola",
    "repoId": "R_xxxxxxxx",
    "category": "Recensioni",
    "categoryId": "DIC_xxxxxxxx"
  }
}
```

Finché i valori sono vuoti, la sezione dice "Le recensioni saranno disponibili a breve".

## 5. Prima di cercare il Project su Travelpayouts

Quando il sito è online, crea il Project su Travelpayouts con quell'indirizzo. Travelpayouts può rifiutare siti vuoti o con pochi visitatori: tieni il sito curato e aggiornato.

## Prova in locale (facoltativa)

```
python3 scripts/build_packages.py --demo      # dati dimostrativi
cd site && python3 -m http.server 8000        # apri http://localhost:8000
```
