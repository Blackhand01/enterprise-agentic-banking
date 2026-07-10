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
  rationale: ["The planner verified balance, known expenses, and goal."],
  reasoning_trace: [
    {
      step: "Context_Analysis",
      title: "Context analysis",
      summary: "I read balance, expenses, and emergency fund.",
      facts: [{ label: "Available balance", value: 4250, unit: "EUR" }],
    },
    {
      step: "Compliance_Check",
      title: "Safety check",
      summary: "The route requires customer approval.",
      facts: [{ label: "Risk route", value: "APPROVAL_REQUIRED" }],
    },
  ],
  reason: "Movement toward an existing internal destination.",
  recipient: "Emergency_Fund",
  recommended_action: "Move 500.00 EUR",
  required_next_step: "CUSTOMER_APPROVAL",
  route: "APPROVAL_REQUIRED",
  salary_detected: {
    amount: 3200,
    date: "2026-07-08",
    merchant: "Tata Innovation Hub Payroll",
  },
  summary: "The active goal is to build the emergency fund.",
  target_balance: 10000,
  title: "Increase the emergency fund",
  trace_id: "trc_current",
  trusted_target: true,
  upcoming_expenses_30d: 759.9,
};

const baseState = {
  user: { first_name: "Stefano", last_name: "Roy", auth_level: "mfa_verified" },
  user_goal: { description: "Reach EUR 10,000 in the emergency fund within 18 months." },
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
    past_points: [{ month_label: "Jul 2026", label: "Jul 2026", balance: 3900 }],
  },
  scheduled_transactions: [
    {
      amount: -39.9,
      category: "utilities",
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
      title: "Maintain savings pace",
      recommended_action:
        "You are fully aligned with your savings plan. No extra transfers are needed this month.",
      reason: "The customer is already aligned with the pace required to reach the goal.",
      rationale: [
        "The historical average contribution covers the required monthly contribution.",
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
      title: "Liquidity alert: recovery required",
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
      title: "Preserve liquidity in checking",
      recommended_action:
        "Do not move funds now: the customer-configured minimum margin absorbs available liquidity after known expenses.",
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
    search_query: "how much did I spend at the seaside?",
    count: 0,
    transactions: [],
  });
  const card = chatBox.children[0];
  if (!card || !card.innerHTML.includes("0 movements found")) {
    throw new Error("NO_DATA chat tool card missing");
  }
  if (!card.classList.values.has("empty")) {
    throw new Error("NO_DATA chat tool card is not marked empty");
  }
}

async function main() {
  await runUiState(baseState, async (elements, context) => {
    let inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("Increase the emergency fund")) {
      throw new Error("Pending inbox summary missing");
    }
    if (
      inboxHtml.includes("transition-table")
      || inboxHtml.includes("amount-input")
      || inboxHtml.includes("Agent reasoning")
    ) {
      throw new Error("Pending inbox renders detail content before expansion");
    }
    if (!elements["financial-rules-settings"].innerHTML.includes("Set dynamic risk limit")) {
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
      !cashflowHtml.includes("30d outflows")
      || !cashflowHtml.includes("Current margin")
      || !cashflowHtml.includes("After proposal")
      || !cashflowHtml.includes("liquidity-marker")
    ) {
      throw new Error("Cashflow dashboard is missing the supervisor summary");
    }
    if (cashflowHtml.includes("<svg")) {
      throw new Error("Cashflow still renders an SVG chart");
    }
    if (
      cashflowHtml.includes("Blocked expenses")
      || cashflowHtml.includes("Free margin")
      || cashflowHtml.includes("upcoming-event")
      || cashflowHtml.includes("Current available balance")
      || cashflowHtml.includes("Agent proposal")
      || cashflowHtml.includes("Proposed recovery")
    ) {
      throw new Error("Cashflow renders redundant liquidity details");
    }
    if (cashflowHtml.includes("cashflow-facts") || cashflowHtml.includes("liquidity-breakdown")) {
      throw new Error("Cashflow renders redundant summary sections");
    }
    const app = context.__tcsBankingApp;
    app.toggleDeepDive(true);
    if (elements["deep-dive-toggle"].textContent !== "Agent action history") {
      throw new Error("Action history navbar label should remain stable");
    }
    const historyHtml = elements["deep-dive-content"].innerHTML;
    if (!historyHtml.includes("Action history") && !historyHtml.includes("agent actions")) {
      throw new Error("Action history drawer content missing");
    }
    if (historyHtml.includes("Balance trend") || historyHtml.includes("Monthly spending")) {
      throw new Error("Action history drawer still contains insights content");
    }
    app.toggleInsights(true);
    if (elements["insights-toggle"].textContent !== "Insights") {
      throw new Error("Insights navbar label should remain stable");
    }
    const insightsHtml = elements["insights-content"].innerHTML;
    if (!insightsHtml.includes("Balance trend") || !insightsHtml.includes("Monthly spending")) {
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
    if (elements["sandbox-toggle"].textContent !== "⚙️ Sandbox Settings") {
      throw new Error("Sandbox navbar label should remain stable");
    }
    if (elements["chat-drawer"].classList.values.has("open")) {
      throw new Error("Opening sandbox did not close chat drawer");
    }

    context.toggleActionInbox();
    inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("Explainability") || !inboxHtml.includes("Proposal impact")) {
      throw new Error("Expanded inbox does not render collapsible panel headers");
    }
    if (inboxHtml.includes("transition-table") || inboxHtml.includes("Context analysis")) {
      throw new Error("Expanded inbox renders collapsed panel content by default");
    }
    context.toggleExplainabilityPanel();
    inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("Context analysis")) {
      throw new Error("Explainability panel did not open");
    }
    context.toggleExplainabilityPanel();
    inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("Explainability") || inboxHtml.includes("Context analysis")) {
      throw new Error("Explainability panel did not collapse again");
    }
    context.toggleImpactPanel();
    inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("transition-table")) {
      throw new Error("Impact panel did not open");
    }
    context.toggleImpactPanel();
    inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("Proposal impact") || inboxHtml.includes("transition-table")) {
      throw new Error("Impact panel did not collapse again");
    }
    context.toggleExplainabilityPanel();
    context.toggleActionInbox();
    context.toggleActionInbox();
    inboxHtml = elements["agent-inbox"].innerHTML;
    if (inboxHtml.includes("Context analysis")) {
      throw new Error("Reopening inbox did not reset nested panels to collapsed");
    }
    if (
      inboxHtml.includes("The planner recalculated")
      || inboxHtml.includes("The amount is not fixed")
    ) {
      throw new Error("Expanded inbox renders duplicated rationale copy");
    }
    if (occurrences(inboxHtml, "Approval request") !== 1) {
      throw new Error("Expanded inbox renders duplicated approval route labels");
    }
    if (!inboxHtml.includes("amount-input") || !inboxHtml.includes("approve-button")) {
      throw new Error("Expanded inbox does not render decision controls");
    }
  });

  await runUiState(executedState(), async (elements) => {
    const inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("SAVINGS OPERATION COMPLETED SUCCESSFULLY")) {
      throw new Error("Missing executed success banner");
    }
    if (inboxHtml.includes("transition-table") || inboxHtml.includes("Balance simulation")) {
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
    if (!inboxHtml.includes("You are fully aligned")) {
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
    if (inboxHtml.includes("SAVINGS OPERATION COMPLETED")) {
      throw new Error("Reverse transfer rendered stale executed state");
    }
  });

  await runUiState(reviewCashflowState(), async (elements, context) => {
    const cashflowHtml = elements["cashflow-supervisor"].innerHTML;
    if (
      !cashflowHtml.includes("At minimum buffer")
      || !cashflowHtml.includes("Agent decision")
      || !cashflowHtml.includes("Liquidity preserved")
    ) {
      throw new Error("Review cashflow dashboard copy is inconsistent");
    }
    context.toggleActionInbox();
    const inboxHtml = elements["agent-inbox"].innerHTML;
    if (!inboxHtml.includes("Explainability") || inboxHtml.includes("Context analysis")) {
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
