# Parte C - Processo e decisioni

## 1. Strategia

Ho trattato l'esercizio come un prototipo architetturale per engineering lead bancari. Il punto non era simulare ogni prodotto finanziario, ma rendere verificabile il confine tra ragionamento dell'agente, autorizzazione e azione deterministica.

Ho scelto un singolo flow: dopo l'arrivo dello stipendio, l'agente propone di spostare liquidità inattiva verso `Emergency_Fund`. Questo concentra la demo sui problemi importanti: grounding, soglie di rischio, approvazione cliente, blocco MFA e audit trail.

Sequenza di lavoro:

1. definire il flow e i rischi da dimostrare;
2. creare mock data coerenti per utente, ledger, policy e audit;
3. isolare retrieval, schemi, guardrail e tool execution;
4. costruire una UI che mostri esperienza cliente e pannello tecnico;
5. documentare in Parte B il passaggio da prototipo a produzione;
6. verificare il flow con smoke test ripetibili.

## 2. Tool e framework

| Scelta | Motivo |
|---|---|
| Python + FastAPI | Backend piccolo, leggibile e facile da avviare. |
| HTML/CSS/JavaScript statici | Nessun build step frontend. |
| SQLite locale | System of record del prototipo, con commit SQL reali. |
| JSON locali | Seed iniziale e policy catalog senza infrastruttura extra. |
| Pydantic | Contratti espliciti per request API e tool input. |
| OpenAI-compatible tool calling | LLM reale quando configurato; flow principale funzionante anche senza provider esterno. |
| Mermaid | Diagrammi leggibili in Markdown e HTML. |
| Makefile | Run, reset, smoke test e cleanup ripetibili. |

## 3. Uso dell'AI assistance

Ho usato AI assistance per accelerare task stretti: mock data, scaffolding Python, copy UI, refactor e casi di test minimi.

Non ho delegato all'AI le decisioni di sicurezza. Soglie, validazioni, policy filtering, route di rischio e risultato dei tool sono implementati in codice deterministico.

## 4. Decisioni principali

### Singolo agente nel prototipo

Una soluzione production può usare componenti specializzati, ma nel prototipo ho evitato complessità multi-agent. In cinque giorni era più importante dimostrare bene il confine AI-to-ledger.

### Guardrail deterministici

I controlli principali non vivono nel prompt: policy stale filtering, importi validi, limite EUR 500, MFA e stato `EXECUTED` sono verificati dal codice. Il modello può spiegare un blocco, non reinterpretarlo come successo.

### Grounding separato

I numeri correnti arrivano da SQLite, che rappresenta il system of record locale. `ledger.json` è solo il seed. Le policy arrivano da `policyDB.json` dopo filtro sulle versioni attive. In produzione la stessa distinzione separa API bancarie e RAG documentale.

### UI con pannello tecnico

La UI mostra prima il valore cliente: proposta, impatto, approvazione e chat. Il pannello tecnico espone contesto, policy, audit e payload grezzo per rendere ispezionabile il comportamento agentico.

## 5. Scope lasciato fuori

Ho escluso deliberatamente login reale, scritture su core banking, vector database, orchestrazione multi-agent, approval token MFA reale, conti cointestati completi, audit WORM, eval pipeline production e deployment cloud.

Non sono assunzioni di prodotto: sono scelte di scope. La Parte B spiega come introdurle senza cambiare il principio architetturale centrale.

## 6. Primo passo production

Partirei da un MVP read-only/propose-only:

1. insight cash-flow e categorizzazione spese;
2. raccomandazioni di risparmio senza esecuzione automatica;
3. azioni approval-gated verso destinazioni interne fidate;
4. integrazione MFA e approval token;
5. rollout limitato con shadow mode, eval e audit completo.

Solo dopo introdurrei azioni a basso rischio e reversibili, sempre dietro tool registry, policy engine e audit trail.

## 7. Criterio di successo

Il prototipo è riuscito se il reviewer vede tre cose:

- l'agente non inventa dati fuori contesto;
- l'agente non può muovere denaro oltre i limiti deterministici;
- il passaggio da demo a prodotto è chiaro, auditabile e incrementale.

La scelta centrale è mantenere l'AI come interfaccia di ragionamento e spiegazione, non come autorità bancaria diretta.
