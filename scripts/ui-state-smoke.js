import { pathToFileURL } from "url";

class ClassList {
  constructor() {
    this.values = new Set();
  }

  add(name) {
    this.values.add(name);
  }

  toggle(name, enabled) {
    if (enabled) this.values.add(name);
    else this.values.delete(name);
  }
}

class Element {
  constructor(id = "") {
    this.id = id;
    this.children = [];
    this.className = "";
    this.dataset = {};
    this.innerHTML = "";
    this.scrollHeight = 0;
    this.scrollTop = 0;
    this.style = {};
    this.textContent = "";
    this.classList = new ClassList();
  }

  addEventListener() {}

  appendChild(child) {
    this.children.push(child);
  }

  setAttribute(name, value) {
    this[name] = value;
  }

  scrollIntoView() {}
}

const staticIds = [
  "agent-inbox",
  "auth-level",
  "cashflow-supervisor",
  "chat-box",
  "chat-button",
  "chat-close",
  "chat-drawer",
  "chat-input",
  "chat-toggle",
  "customer-result",
  "deep-dive-close",
  "deep-dive-content",
  "deep-dive-panel",
  "deep-dive-toggle",
  "financial-rules-settings",
  "goal-summary",
  "insights-close",
  "insights-content",
  "insights-panel",
  "insights-toggle",
  "inspector",
  "sandbox-apply-button",
  "sandbox-checking-balance",
  "sandbox-close",
  "sandbox-emergency-balance",
  "sandbox-result",
  "sandbox-toggle",
  "sandbox-upcoming-expenses",
  "user-name",
];

const baseProposal = {
  action_type: "TRANSFER",
  amount: 500,
  available_balance: 4250,
  currency: "EUR",
  emergency_balance: 3000,
  evidence: [],
  financial_rules: {
    autonomous_transfer_limit_eur: 500,
    minimum_cash_buffer_eur: 750,
    surplus_investment_ratio: 0.25,
  },
  goal_progress: 30,
  projected_checking_balance: 3750,
  projected_emergency_balance: 3500,
  projected_expense_buffer: 2990.1,
  projected_goal_progress: 35,
  rationale: ["Il planner ha verificato saldo, spese note e obiettivo."],
  reasoning_trace: [
    {
      step: "Analisi_Contesto",
      title: "Analisi contesto",
      summary: "Ho letto saldo, spese e fondo emergenze.",
      facts: [{ label: "Saldo disponibile", value: 4250, unit: "EUR" }],
    },
    {
      step: "Verifica_Compliance",
      title: "Verifica safety",
      summary: "La route richiede approvazione cliente.",
      facts: [{ label: "Route rischio", value: "APPROVAL_REQUIRED" }],
    },
  ],
  reason: "Spostamento verso una destinazione interna esistente.",
  recipient: "Emergency_Fund",
  recommended_action: "Spostare 500.00 EUR",
  required_next_step: "CUSTOMER_APPROVAL",
  route: "APPROVAL_REQUIRED",
  salary_detected: {
    amount: 3200,
    date: "2026-07-08",
    merchant: "Tata Innovation Hub Payroll",
  },
  summary: "L'obiettivo attivo e costruire il fondo emergenze.",
  target_balance: 10000,
  title: "Aumenta il fondo emergenze",
  trace_id: "trc_current",
  trusted_target: true,
  upcoming_expenses_30d: 759.9,
};

const baseState = {
  user: { first_name: "Stefano", last_name: "Roy", auth_level: "mfa_verified" },
  user_goal: { description: "Raggiungere 10.000 EUR nel fondo emergenze entro 18 mesi." },
  accounts: [
    { name: "Checking", balance: 4250, available_balance: 4250 },
    { name: "Emergency_Fund", balance: 3000, target_balance: 10000 },
  ],
  proposal: { ...baseProposal, already_executed: false, executed_operation: null },
  emergency_goal_projection: {
    current_balance: 3000,
    current_progress: 30,
    gap: 7000,
    historical_eta_label: "Mar 2031",
    historical_eta_months: 56,
    historical_monthly_savings: 125,
    is_behind_plan: true,
    required_monthly_after_agent_action: 361.11,
    required_monthly_savings: 388.89,
    target_balance: 10000,
    target_label: "Gen 2028",
  },
  cashflow_forecast: {
    future_points: [
      { date: "2026-07-09", label: "Oggi", balance: 4250 },
      { date: "2026-07-15", label: "FiberNet", event: "FiberNet", amount: -39.9, balance: 4210.1 },
    ],
    horizon_days: 30,
    known_expenses_total: 759.9,
    past_points: [{ month_label: "Lug 2026", label: "Lug 2026", balance: 3900 }],
  },
  scheduled_transactions: [
    {
      amount: -39.9,
      category: "bollette",
      date: "2026-07-15",
      merchant: "FiberNet",
      scheduled_id: "sch_fibernet",
    },
  ],
  agent_inbox: [],
  audit: [],
  customer_activity: [],
  monthly_snapshots: [],
  policies: { active: [], stale: [] },
  transactions: [],
};

function executedState() {
  return {
    ...baseState,
    accounts: [
      { name: "Checking", balance: 3750, available_balance: 3750 },
      { name: "Emergency_Fund", balance: 3500, target_balance: 10000 },
    ],
    proposal: {
      ...baseProposal,
      already_executed: true,
      available_balance: 3750,
      emergency_balance: 3500,
      executed_operation: { trace_id: "trc_done" },
      route: "ALREADY_EXECUTED",
      required_next_step: "NO_ACTION",
    },
    emergency_goal_projection: {
      ...baseState.emergency_goal_projection,
      current_balance: 3500,
      current_progress: 35,
      gap: 6500,
      required_monthly_after_agent_action: 361.11,
      required_monthly_savings: 361.11,
    },
  };
}

function maintainPaceState() {
  return {
    ...baseState,
    proposal: {
      ...baseProposal,
      action_type: "MAINTAIN_PACE",
      amount: 0,
      route: "INFO",
      required_next_step: "NO_ACTION",
      title: "Mantieni il ritmo di risparmio",
      recommended_action:
        "Sei perfettamente allineato al tuo piano di risparmio. Non sono necessari trasferimenti extra questo mese.",
      reason: "Il cliente e gia allineato al ritmo necessario per raggiungere l'obiettivo.",
      rationale: [
        "La media storica dei versamenti copre il contributo mensile richiesto.",
      ],
    },
    emergency_goal_projection: {
      ...baseState.emergency_goal_projection,
      historical_monthly_savings: 450,
      is_behind_plan: false,
      monthly_savings_gap: 0,
    },
  };
}

function reverseTransferState() {
  return {
    ...baseState,
    accounts: [
      { name: "Checking", balance: 650, available_balance: 650 },
      { name: "Emergency_Fund", balance: 3000, target_balance: 10000 },
    ],
    proposal: {
      ...baseProposal,
      action_type: "TRANSFER_REVERSE",
      amount: 860,
      available_balance: 650,
      emergency_balance: 3000,
      projected_checking_balance: 1510,
      projected_emergency_balance: 2140,
      projected_expense_buffer: 750,
      projected_goal_progress: 21,
      recipient: "Checking",
      route: "APPROVAL_REQUIRED",
      source: "Emergency_Fund",
      title: "Allerta liquidita: recupero necessario",
    },
  };
}

function reviewCashflowState() {
  return {
    ...baseState,
    accounts: [
      { name: "Checking", balance: 1509.9, available_balance: 1509.9 },
      { name: "Emergency_Fund", balance: 3200.2, target_balance: 10000 },
    ],
    proposal: {
      ...baseProposal,
      action_type: "REVIEW_CASHFLOW",
      amount: 0,
      available_balance: 1509.9,
      emergency_balance: 3200.2,
      projected_checking_balance: 1509.9,
      projected_emergency_balance: 3200.2,
      projected_expense_buffer: 750,
      projected_goal_progress: 32,
      route: "REVIEW_REQUIRED",
      required_next_step: "CUSTOMER_REVIEW",
      title: "Mantieni liquidita sul conto",
      recommended_action:
        "Non spostare fondi ora: il margine minimo configurato dal cliente assorbe la liquidita disponibile dopo le spese note.",
    },
    emergency_goal_projection: {
      ...baseState.emergency_goal_projection,
      current_balance: 3200.2,
      current_progress: 32,
      gap: 6799.8,
    },
    cashflow_forecast: {
      ...baseState.cashflow_forecast,
      known_expenses_total: 759.9,
    },
  };
}

function occurrences(text, needle) {
  return text.split(needle).length - 1;
}

async function runUiState(stateFixture, assertion) {
  const elements = Object.fromEntries(staticIds.map((id) => [id, new Element(id)]));
  const classElements = {
    ".deep-dive-panel": new Element("deep-dive-panel"),
  };
  const document = {
    body: new Element("body"),
    createElement: () => new Element(),
    getElementById: (id) => elements[id] || null,
    querySelector: (selector) => classElements[selector] || new Element(selector),
    querySelectorAll: (selector) => {
      return [];
    },
  };

  const context = {
    window: {
      clearTimeout,
      setTimeout,
    },
  };

  global.console = console;
  global.document = document;
  global.fetch = async () => ({
    ok: true,
    json: async () => stateFixture,
  });
  global.Intl = Intl;
  global.window = context.window;

  const appUrl = pathToFileURL(`${process.cwd()}/src/frontend/app.js`);
  appUrl.search = `ui-smoke=${Date.now()}-${Math.random()}`;
  await import(appUrl.href);
  await new Promise((resolve) => setTimeout(resolve, 0));
  await assertion(elements, context.window);
}

async function runChatCardSmoke() {
  const chatBox = new Element("chat-box");
  const elements = {
    "chat-box": chatBox,
    "customer-result": new Element("customer-result"),
  };
  global.document = {
    createElement: () => new Element(),
    getElementById: (id) => elements[id] || null,
  };
  const moduleUrl = pathToFileURL(`${process.cwd()}/src/frontend/components.js`);
  moduleUrl.search = `chat-smoke=${Date.now()}-${Math.random()}`;
  const { renderChatToolCard } = await import(moduleUrl.href);
  renderChatToolCard({
    status: "NO_DATA",
    search_query: "quanto ho speso in mare?",
    count: 0,
    transactions: [],
  });
  const card = chatBox.children[0];
  if (!card || !card.innerHTML.includes("0 movimenti trovati")) {
    throw new Error("NO_DATA chat tool card missing");
  }
  if (!card.classList.values.has("empty")) {
    throw new Error("NO_DATA chat tool card is not marked empty");
  }
}

async function main() {
  await runUiState(baseState, async (elements, context) => {
    let inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("Aumenta il fondo emergenze")) {
      throw new Error("Pending inbox summary missing");
    }
    if (
      inboxHtml.includes("transition-table")
      || inboxHtml.includes("amount-input")
      || inboxHtml.includes("Ragionamento agente")
    ) {
      throw new Error("Pending inbox renders detail content before expansion");
    }
    if (!elements["financial-rules-settings"].innerHTML.includes("Imposta limite")) {
      throw new Error("Financial rules settings panel missing");
    }
    if (Number(elements["sandbox-checking-balance"].value) !== 4250) {
      throw new Error("Sandbox checking balance input was not initialized");
    }
    if (Number(elements["sandbox-upcoming-expenses"].value) !== 759.9) {
      throw new Error("Sandbox upcoming expenses input was not initialized");
    }
    const cashflowHtml = elements["cashflow-supervisor"].innerHTML;
    if (!cashflowHtml.includes("liquidity-bar")) {
      throw new Error("Liquidity gauge missing");
    }
    if (
      !cashflowHtml.includes("Uscite 30g")
      || !cashflowHtml.includes("Margine ora")
      || !cashflowHtml.includes("Dopo proposta")
      || !cashflowHtml.includes("liquidity-marker")
    ) {
      throw new Error("Cashflow dashboard is missing the supervisor summary");
    }
    if (cashflowHtml.includes("<svg")) {
      throw new Error("Cashflow still renders an SVG chart");
    }
    if (
      cashflowHtml.includes("Spese bloccate")
      || cashflowHtml.includes("Margine libero")
      || cashflowHtml.includes("upcoming-event")
      || cashflowHtml.includes("Saldo disponibile attuale")
      || cashflowHtml.includes("Margine attuale")
      || cashflowHtml.includes("Proposta agente")
      || cashflowHtml.includes("Recupero proposto")
    ) {
      throw new Error("Cashflow renders redundant liquidity details");
    }
    if (cashflowHtml.includes("cashflow-facts") || cashflowHtml.includes("liquidity-breakdown")) {
      throw new Error("Cashflow renders redundant summary sections");
    }
    const app = context.__tcsBankingApp;
    app.toggleDeepDive(true);
    if (elements["deep-dive-toggle"].textContent !== "Storico azioni agente") {
      throw new Error("Action history navbar label should remain stable");
    }
    const historyHtml = elements["deep-dive-content"].innerHTML;
    if (!historyHtml.includes("Storico azioni") && !historyHtml.includes("azioni agente")) {
      throw new Error("Action history drawer content missing");
    }
    if (historyHtml.includes("Andamento saldi") || historyHtml.includes("Spese mensili")) {
      throw new Error("Action history drawer still contains insights content");
    }
    app.toggleInsights(true);
    if (elements["insights-toggle"].textContent !== "Insights") {
      throw new Error("Insights navbar label should remain stable");
    }
    const insightsHtml = elements["insights-content"].innerHTML;
    if (!insightsHtml.includes("Andamento saldi") || !insightsHtml.includes("Spese mensili")) {
      throw new Error("Insights drawer missing trend content");
    }
    if (elements["deep-dive-panel"].classList.values.has("open")) {
      throw new Error("Opening insights did not close action history drawer");
    }
    app.toggleChat(true);
    if (elements["chat-toggle"].textContent !== "Chat") {
      throw new Error("Chat navbar label should remain stable");
    }
    if (!elements["chat-drawer"].classList.values.has("open")) {
      throw new Error("Chat drawer did not open");
    }
    app.toggleInspector(true);
    if (elements["sandbox-toggle"].textContent !== "⚙️ Imposta Sandbox") {
      throw new Error("Sandbox navbar label should remain stable");
    }
    if (elements["chat-drawer"].classList.values.has("open")) {
      throw new Error("Opening sandbox did not close chat drawer");
    }

    context.toggleActionInbox();
    inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("Explainability") || !inboxHtml.includes("Impatto proposta")) {
      throw new Error("Expanded inbox does not render collapsible panel headers");
    }
    if (inboxHtml.includes("transition-table") || inboxHtml.includes("Analisi contesto")) {
      throw new Error("Expanded inbox renders collapsed panel content by default");
    }
    context.toggleExplainabilityPanel();
    inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("Analisi contesto")) {
      throw new Error("Explainability panel did not open");
    }
    context.toggleExplainabilityPanel();
    inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("Explainability") || inboxHtml.includes("Analisi contesto")) {
      throw new Error("Explainability panel did not collapse again");
    }
    context.toggleImpactPanel();
    inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("transition-table")) {
      throw new Error("Impact panel did not open");
    }
    context.toggleImpactPanel();
    inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("Impatto proposta") || inboxHtml.includes("transition-table")) {
      throw new Error("Impact panel did not collapse again");
    }
    context.toggleExplainabilityPanel();
    context.toggleActionInbox();
    context.toggleActionInbox();
    inboxHtml = elements["agent-inbox"].innerHTML;
    if (inboxHtml.includes("Analisi contesto")) {
      throw new Error("Reopening inbox did not reset nested panels to collapsed");
    }
    if (
      inboxHtml.includes("Il planner ha ricalcolato")
      || inboxHtml.includes("L'importo non e fisso")
    ) {
      throw new Error("Expanded inbox renders duplicated rationale copy");
    }
    if (occurrences(inboxHtml, "Approvazione richiesta") !== 1) {
      throw new Error("Expanded inbox renders duplicated approval route labels");
    }
    if (!inboxHtml.includes("amount-input") || !inboxHtml.includes("approve-button")) {
      throw new Error("Expanded inbox does not render decision controls");
    }
  });

  await runUiState(executedState(), async (elements) => {
    const inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("OPERAZIONE DI RISPARMIO COMPLETATA CON SUCCESSO")) {
      throw new Error("Missing executed success banner");
    }
    if (inboxHtml.includes("transition-table") || inboxHtml.includes("Simulazione saldi")) {
      throw new Error("Executed state still renders the impact simulation table");
    }
    if (inboxHtml.includes("amount-input")) {
      throw new Error("Executed state still renders the transfer input");
    }
    if (inboxHtml.includes("approve-button") || inboxHtml.includes("reject-button")) {
      throw new Error("Executed state still renders approve/reject controls");
    }
  });

  await runUiState(maintainPaceState(), async (elements, context) => {
    context.toggleActionInbox();
    const inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("Sei perfettamente allineato")) {
      throw new Error("Maintain pace reasoning missing");
    }
    if (inboxHtml.includes("info-plan-card")) {
      throw new Error("Maintain pace state renders duplicated informational card");
    }
    if (inboxHtml.includes("amount-input") || inboxHtml.includes("approve-button")) {
      throw new Error("Maintain pace state renders transfer controls");
    }
    if (inboxHtml.includes("transition-table")) {
      throw new Error("Maintain pace state renders transfer impact simulation");
    }
  });

  await runUiState(reverseTransferState(), async (elements, context) => {
    const app = context.__tcsBankingApp;
    app.lastTrace = {
      tool_result: { status: "EXECUTED", amount: 500 },
      proposal: { amount: 500, action_type: "TRANSFER" },
    };
    context.toggleActionInbox();
    const inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("amount-input") || !inboxHtml.includes("approve-button")) {
      throw new Error("Reverse transfer pending state does not render decision controls");
    }
    if (inboxHtml.includes("OPERAZIONE DI RISPARMIO COMPLETATA")) {
      throw new Error("Reverse transfer rendered stale executed state");
    }
  });

  await runUiState(reviewCashflowState(), async (elements, context) => {
    const cashflowHtml = elements["cashflow-supervisor"].innerHTML;
    if (
      !cashflowHtml.includes("Al buffer minimo")
      || !cashflowHtml.includes("Decisione agente")
      || !cashflowHtml.includes("Liquidita preservata")
    ) {
      throw new Error("Review cashflow dashboard copy is inconsistent");
    }
    context.toggleActionInbox();
    const inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("Explainability") || inboxHtml.includes("Analisi contesto")) {
      throw new Error("Review cashflow inbox does not keep explainability collapsed by default");
    }
  });

  await runChatCardSmoke();

  console.log("ui state smoke checks passed");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
