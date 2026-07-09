const fs = require("fs");
const vm = require("vm");

class ClassList {
  constructor() {
    this.values = new Set();
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
  "chat-input",
  "customer-result",
  "deep-dive-content",
  "deep-dive-toggle",
  "financial-rules-settings",
  "goal-summary",
  "inspector",
  "inspector-close",
  "inspector-toggle",
  "recent-transactions",
  "sandbox-apply-button",
  "sandbox-checking-balance",
  "sandbox-emergency-balance",
  "sandbox-result",
  "sandbox-upcoming-expenses",
  "tab-audit",
  "tab-context",
  "tab-execution",
  "tab-policies",
  "tab-raw",
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

async function runUiState(stateFixture, assertion) {
  const elements = Object.fromEntries(staticIds.map((id) => [id, new Element(id)]));
  const classElements = {
    ".deep-dive-panel": new Element("deep-dive-panel"),
  };
  const tabElements = ["context", "policies", "execution", "audit", "raw"].map((name) => {
    const element = new Element(`tab-${name}-button`);
    element.dataset.tab = name;
    return element;
  });
  const tabPanels = ["context", "policies", "execution", "audit", "raw"].map((name) => {
    const element = elements[`tab-${name}`];
    element.id = `tab-${name}`;
    return element;
  });

  const document = {
    body: new Element("body"),
    createElement: () => new Element(),
    getElementById: (id) => elements[id] || null,
    querySelector: (selector) => classElements[selector] || new Element(selector),
    querySelectorAll: (selector) => {
      if (selector === ".tab") return tabElements;
      if (selector === ".tab-panel") return tabPanels;
      return [];
    },
  };

  const context = {
    console,
    document,
    fetch: async () => ({
      ok: true,
      json: async () => stateFixture,
    }),
    Intl,
    window: {
      clearTimeout,
      setTimeout,
    },
  };

  vm.createContext(context);
  vm.runInContext(fs.readFileSync("src/frontend/app.js", "utf8"), context);
  await new Promise((resolve) => setTimeout(resolve, 0));
  await assertion(elements, context);
}

async function main() {
  await runUiState(baseState, async (elements, context) => {
    let inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("Aumenta il fondo emergenze")) {
      throw new Error("Pending inbox summary missing");
    }
    if (inboxHtml.includes("transition-table") || inboxHtml.includes("amount-input")) {
      throw new Error("Pending inbox renders simulation or controls before expansion");
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
    if (!cashflowHtml.includes("liquidity-bar") || !cashflowHtml.includes("Spese bloccate")) {
      throw new Error("Liquidity gauge missing");
    }
    if (!cashflowHtml.includes("FiberNet") || !cashflowHtml.includes("upcoming-event")) {
      throw new Error("Upcoming events list missing");
    }
    if (cashflowHtml.includes("<svg")) {
      throw new Error("Cashflow still renders an SVG chart");
    }

    context.toggleActionInbox();
    inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("transition-table")) {
      throw new Error("Expanded inbox does not render the impact simulation");
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
      throw new Error("Maintain pace message missing");
    }
    if (!inboxHtml.includes("info-plan-card") || !inboxHtml.includes("Informativo")) {
      throw new Error("Maintain pace informational card missing");
    }
    if (inboxHtml.includes("amount-input") || inboxHtml.includes("approve-button")) {
      throw new Error("Maintain pace state renders transfer controls");
    }
    if (inboxHtml.includes("transition-table")) {
      throw new Error("Maintain pace state renders transfer impact simulation");
    }
  });

  console.log("ui state smoke checks passed");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
