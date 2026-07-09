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
un provider LLM configurato in `.env` o nell'ambiente.

Esempi `.env` supportati:

```bash
# OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Groq
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# Gemini, tramite endpoint OpenAI-compatible
LLM_PROVIDER=gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash

# Qualsiasi endpoint compatibile con OpenAI Chat Completions
LLM_PROVIDER=openai_compatible
LLM_API_KEY=...
LLM_BASE_URL=https://provider.example.com/openai/v1
LLM_MODEL=...
```

Se `LLM_PROVIDER` non e impostato, il backend prova ad autodetectare la chiave
presente con questa priorita: `GROQ_API_KEY`, poi `GEMINI_API_KEY`, poi
`OPENAI_API_KEY`, infine `LLM_API_KEY` con `LLM_BASE_URL`.
Durante una chiamata chat, se il provider primario fallisce per quota, rate limit,
errore temporaneo o chiave non valida, l'agente prova il fallback successivo
configurato nella stessa catena.
Per una consegna tecnica, e comunque preferibile impostare `LLM_PROVIDER`
esplicitamente.

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

- Approva il trasferimento dinamico proposto verso `Emergency_Fund`.
- Cambia l'importo e visualizza/approva l'anteprima.
- Cambia l'importo a EUR 750 e osserva il blocco deterministico con MFA.
- Apri il pannello di grounding per vedere policy attive e obsolete.
- Chiedi in chat: `Quanto ho speso in sport di recente?`
- Chiedi in chat: `Puoi dirmi il rischio del mio mutuo?`
