# Prototipo Enterprise Agentic Banking

## Avvio Parte A

Installa le dipendenze:

```bash
python3 -m pip install -r requirements.txt
```

Oppure:

```bash
make setup
```

Avvia il prototipo:

```bash
make run
```

Apri:

```text
http://127.0.0.1:8000
```

Il prototipo usa SQLite come system of record locale (`src/bank_data/banking.db`)
e dati JSON come seed/policy iniziali. Non richiede login, autenticazione reale
o database vettoriale. La dashboard, i guardrail e il flow di trasferimento
funzionano senza servizi esterni; la chat agentica con tool calling richiede
`GROQ_API_KEY` in `.env` o nell'ambiente.

I documenti di consegna sono in `docs/`:

- `part_B-architecture_system_design.md`
- `part_B-architecture_system_design.html`
- `part_C-process_decision.md`
- `part_C-process_decision.html`

## Comandi utili

```bash
make help
make dev
make stop
make restart
make smoke
make reset-audit
make reset-data
make clean
```

Se la porta `8000` e gia in uso, probabilmente l'app e gia in esecuzione.
Apri `http://127.0.0.1:8000`, oppure esegui `make stop` prima di riavviarla.

`make reset-data` ricrea il database SQLite dal seed `ledger.json`.

## Cosa provare

- Approva il trasferimento predefinito da EUR 300 verso `Emergency_Fund`.
- Cambia l'importo a EUR 500 e visualizza/approva l'anteprima.
- Cambia l'importo a EUR 750 e osserva il blocco deterministico con MFA.
- Apri il pannello di grounding per vedere policy attive e obsolete.
- Chiedi in chat: `Quanto ho speso in sport di recente?`
- Chiedi in chat: `Puoi dirmi il rischio del mio mutuo?`
