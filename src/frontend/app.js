const eur = new Intl.NumberFormat("it-IT", {
  style: "currency",
  currency: "EUR",
});

let state = null;
let currentProposal = null;
let lastTrace = null;
let inspectorOpen = false;
let deepDiveOpen = false;
let activeInspectorTab = "context";
let actionInboxOpen = false;
let amountPreviewTimer = null;
let transferInFlight = false;
let sandboxInFlight = false;

const PROPOSAL_PENDING = "PROPOSAL_PENDING";
const PROPOSAL_EXECUTED = "PROPOSAL_EXECUTED";

const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error(`API error ${response.status}`);
  return response.json();
}

async function loadState() {
  state = await api("/api/state");
  currentProposal = state.proposal;
  renderAll();
}

function renderAll() {
  renderUser();
  renderGoal();
  renderFinancialRulesSettings();
  renderSandboxControls();
  renderSupervisorCashflow();
  renderAgentInbox();
  renderRecentTransactions();
  renderDeepDive();
  renderInspector();
  renderInitialChat();
}

function renderFinancialRulesSettings() {
  const target = $("financial-rules-settings");
  if (!target) return;
  const rules = currentProposal.financial_rules || {};
  target.innerHTML = `
    <div class="rule-setting">
      <div>
        <strong>Imposta limite di rischio dinamico</strong>
        <span>Valore corrente: ${eur.format(rules.autonomous_transfer_limit_eur || 0)}. Sopra questa soglia il trasferimento richiede MFA.</span>
      </div>
      <div class="rule-setting-control">
        <input id="risk-limit-input" type="number" min="1" step="50" value="${Number(rules.autonomous_transfer_limit_eur || 0)}" />
        <button type="button" class="secondary" onclick="saveRiskLimit()">Salva limite</button>
      </div>
    </div>
  `;
}

function renderSandboxControls() {
  const checkingInput = $("sandbox-checking-balance");
  const emergencyInput = $("sandbox-emergency-balance");
  const upcomingInput = $("sandbox-upcoming-expenses");
  if (!checkingInput || !emergencyInput || !upcomingInput) return;

  const activeElement = document.activeElement;
  const checking = findAccount("Checking");
  const emergency = findAccount("Emergency_Fund");
  const inputs = [checkingInput, emergencyInput, upcomingInput];
  if (!inputs.includes(activeElement)) {
    checkingInput.value = Number(checking?.available_balance || checking?.balance || 0);
    emergencyInput.value = Number(emergency?.balance || 0);
    upcomingInput.value = Number(currentProposal?.upcoming_expenses_30d || 0);
  }
}

function renderGoal() {
  const goal = state.user_goal || {};
  const projection = state.emergency_goal_projection || {};
  const behindPlan = isBehindGoalPlan(projection);
  const statusTitle = behindPlan
    ? "Sei in ritardo sul ritmo richiesto"
    : "Sei allineato al piano";
  const statusSummary = goalStatusSummary(projection, behindPlan);
  $("goal-summary").innerHTML = `
    <div class="goal-grid">
      <div class="goal-progress-card">
        <span>${escapeHtml(goal.description || "Costruire il fondo emergenze.")}</span>
        <strong>${eur.format(projection.current_balance || 0)} / ${eur.format(projection.target_balance || 0)}</strong>
        <div class="goal-progress-bar">
          <span style="width:${Math.min(projection.current_progress || 0, 100)}%"></span>
        </div>
        <small>${projection.current_progress || 0}% completato · gap ${eur.format(projection.gap || 0)}</small>
      </div>
      ${goalMetric("Data obiettivo", projection.target_label)}
      ${goalMetric("Al ritmo attuale", projection.historical_eta_label)}
      ${goalMetric("Necessario da oggi", `${eur.format(projection.required_monthly_savings || 0)} / mese`)}
    </div>
    <div class="goal-timeline">
      <div>
        <span>Media storica rilevata</span>
        <strong>${eur.format(projection.historical_monthly_savings || 0)} / mese</strong>
      </div>
      <div>
        <span>Gap rimanente</span>
        <strong>${eur.format(projection.gap || 0)}</strong>
      </div>
      <div>
        <span>Obiettivo</span>
        <strong>${eur.format(projection.target_balance || 0)}</strong>
      </div>
    </div>
    <div class="goal-status ${behindPlan ? "behind" : "aligned"}">
      <strong>${statusTitle}</strong>
      <p>${escapeHtml(statusSummary)}</p>
      <span>${escapeHtml(projection.agent_timeline_note || "")}</span>
    </div>
  `;
}

function isBehindGoalPlan(projection) {
  if (typeof projection.is_behind_plan === "boolean") {
    return projection.is_behind_plan;
  }

  const currentMonthly = Number(projection.historical_monthly_savings || 0);
  const requiredMonthly = Number(projection.required_monthly_savings || 0);
  const targetMonths = Number(projection.target_months || 0);
  const historicalEta = projection.historical_eta_months;

  if (requiredMonthly <= 0) return false;
  if (historicalEta === null || historicalEta === undefined) return true;
  return currentMonthly < requiredMonthly || Number(historicalEta) > targetMonths;
}

function goalStatusSummary(projection, behindPlan) {
  const currentMonthly = eur.format(projection.historical_monthly_savings || 0);
  const requiredMonthly = eur.format(projection.required_monthly_savings || 0);
  const targetLabel = projection.target_label || "la data obiettivo";

  if (behindPlan) {
    return `Al ritmo storico stai versando ${currentMonthly}/mese, ma per arrivare entro ${targetLabel} servono ${requiredMonthly}/mese.`;
  }

  return `Il ritmo storico copre il piano richiesto di ${requiredMonthly}/mese.`;
}

function renderUser() {
  $("user-name").textContent = `${state.user.first_name} ${state.user.last_name}`;
  $("auth-level").textContent =
    state.user.auth_level === "mfa_verified" ? "Contesto MFA caricato" : "Contesto standard";
}

function impactSimulationHtml() {
  if (proposalUiState() === PROPOSAL_EXECUTED) {
    return executedAccountStateHtml();
  }

  const checking = findAccount("Checking");
  const emergency = findAccount("Emergency_Fund");
  const progress = Math.round((emergency.balance / emergency.target_balance) * 100);
  const upcoming = currentProposal.upcoming_expenses_30d;
  const checkingAfter = currentProposal.projected_checking_balance;
  const emergencyAfter = currentProposal.projected_emergency_balance;
  const beforeExpenseBuffer = checking.available_balance - upcoming;
  const afterExpenseBuffer = checkingAfter - upcoming;
  const movementAmount = currentProposal.already_executed ? 0 : currentProposal.amount;

  return `
    <div class="simulation-block">
      <div class="panel-heading compact">
      <div>
        <p class="eyebrow">Impatto proposta</p>
        <h2>Simulazione saldi</h2>
      </div>
      <span class="route-pill ${routeClass(currentProposal.route)}">${routeLabel(currentProposal.route)}</span>
      </div>
      <div class="transition-table" role="table" aria-label="Impatto della proposta sui saldi">
        <div class="transition-row transition-head" role="row">
          <span>Indicatore</span>
          <span>Prima</span>
          <span>Movimento</span>
          <span>Dopo</span>
        </div>
        ${transitionRow({
          label: "Conto corrente",
          note: "Saldo disponibile",
          before: eur.format(checking.available_balance),
          movement: formatSignedCurrency(-movementAmount),
          after: eur.format(checkingAfter),
          direction: "decrease",
        })}
        ${transitionRow({
          label: "Margine dopo spese note",
          note: `${eur.format(upcoming)} gia pianificati nei prossimi 30 giorni`,
          before: eur.format(beforeExpenseBuffer),
          movement: formatSignedCurrency(-movementAmount),
          after: eur.format(afterExpenseBuffer),
          direction: afterExpenseBuffer >= 0 ? "safe" : "risk",
          afterBadge: afterExpenseBuffer >= 0 ? `Copre le spese previste di ${eur.format(upcoming)}` : "Spese previste non coperte",
        })}
        ${transitionRow({
          label: "Fondo emergenze",
          note: `Obiettivo ${eur.format(emergency.target_balance)}`,
          before: eur.format(emergency.balance),
          movement: formatSignedCurrency(movementAmount),
          after: eur.format(emergencyAfter),
          direction: "increase",
        })}
        ${transitionRow({
          label: "Avanzamento obiettivo",
          note: "Copertura fondo emergenze",
          before: `${progress}%`,
          movement: currentProposal.already_executed ? "0 pp" : `+${currentProposal.projected_goal_progress - progress} pp`,
          after: `${currentProposal.projected_goal_progress}%`,
          direction: "increase",
        })}
      </div>
      <div class="transition-context">
        <div>
          <span>Ultimo stipendio rilevato</span>
          <strong>${eur.format(currentProposal.salary_detected.amount)}</strong>
          <small>${currentProposal.salary_detected.merchant} · ${currentProposal.salary_detected.date}</small>
        </div>
        <div>
          <span>Spese note considerate</span>
          <strong>${eur.format(upcoming)}</strong>
          <small>Pagamenti pianificati nel ledger</small>
        </div>
      </div>
    </div>
  `;
}

function executedAccountStateHtml() {
  const checking = findAccount("Checking");
  const emergency = findAccount("Emergency_Fund");
  const projection = state.emergency_goal_projection || {};
  const upcoming = currentProposal.upcoming_expenses_30d || 0;
  const margin = Number(checking.available_balance || checking.balance || 0) - upcoming;
  const progress = Math.round((emergency.balance / emergency.target_balance) * 100);
  const trace = executedTrace();
  const amount = executedAmount();

  return `
    <div class="executed-state">
      <div class="success-banner">
        <strong>✅ OPERAZIONE DI RISPARMIO COMPLETATA CON SUCCESSO.</strong>
        <span>Trasferimento di ${eur.format(amount)} registrato in SQLite.</span>
      </div>
      <div class="executed-grid">
        ${executedMetric("Conto corrente", "Saldo disponibile aggiornato", eur.format(checking.available_balance || checking.balance))}
        ${executedMetric("Fondo emergenze", `${progress}% di ${eur.format(emergency.target_balance)}`, eur.format(emergency.balance))}
        ${executedMetric("✓ Margine di Sicurezza", "Copre le spese dei prossimi 30gg", eur.format(margin))}
        ${executedMetric("Piano obiettivo", `Tempo stimato al target: ${projection.historical_eta_months || "-"} mesi`, `Contributo mensile residuo necessario: ${eur.format(projection.required_monthly_savings || 0)} / mese`)}
      </div>
      <p class="executed-note">Trace ID: ${escapeHtml(trace?.trace_id || currentProposal.trace_id || "-")}. I saldi sono letti dallo stato SQLite aggiornato, non da una simulazione.</p>
    </div>
  `;
}

function renderRecentTransactions() {
  const activities = (state.customer_activity || []).slice(0, 6);
  $("recent-transactions").innerHTML = activities
    .map(
      (activity) => `
        <div class="recent-transaction">
          <div>
            <strong>${escapeHtml(activity.title)}</strong>
            <span>${activity.date} · ${escapeHtml(activity.subtitle)}</span>
          </div>
          <strong class="${activity.amount >= 0 ? "credit" : "debit"}">${eur.format(activity.amount)}</strong>
        </div>
      `,
    )
    .join("");
}

function renderDeepDive() {
  $("deep-dive-toggle").textContent = deepDiveOpen ? "Chiudi" : "Apri";
  const content = $("deep-dive-content");
  content.classList.toggle("open", deepDiveOpen);

  if (!deepDiveOpen) {
    content.innerHTML = `
      <div class="deep-dive-teaser">
        <span>Apri per vedere fonti deterministiche, storico mensile e transazioni usate.</span>
      </div>
    `;
    return;
  }

  const snapshots = state.monthly_snapshots || [];
  content.innerHTML = `
    <div class="source-note">Qui trovi i dati storici e le transazioni usate come grounding. I numeri arrivano dal ledger SQLite e dai read model, non dalla memoria del modello.</div>
    <div class="deep-dive-grid">
      <section class="evidence-card">
        <h3>Andamento saldi</h3>
        ${renderLineChart(snapshots)}
      </section>
      <section class="evidence-card">
        <h3>Spese mensili considerate</h3>
        ${renderMonthlyExpenseBars(snapshots)}
      </section>
      <section class="evidence-card wide">
        <h3>Transazioni considerate</h3>
        ${renderTransactionsTable(state.transactions || [])}
      </section>
    </div>
  `;
}

function renderSupervisorCashflow() {
  const forecast = state.cashflow_forecast || {};
  const checking = findAccount("Checking");
  const currentMargin = Number(checking?.available_balance || 0) - Number(forecast.known_expenses_total || 0);
  $("cashflow-supervisor").innerHTML = `
    <div class="cashflow-grid">
      <div class="cashflow-gauge-card">
        ${renderLiquidityGauge(forecast, checking)}
      </div>
      <div class="cashflow-facts">
        ${factRow("Saldo disponibile attuale", eur.format(checking?.available_balance || 0))}
        ${factRow("Spese note prossimi 30 giorni", eur.format(forecast.known_expenses_total || 0))}
        ${factRow("Orizzonte previsione", `${forecast.horizon_days || 30} giorni`)}
        ${factRow("Margine attuale dopo spese note", eur.format(currentMargin))}
      </div>
    </div>
  `;
}

function renderAgentInbox() {
  const executed = proposalUiState() === PROPOSAL_EXECUTED;
  const expanded = actionInboxOpen || executed;
  const route = routeLabel(currentProposal.route);
  const amountCopy = currentProposal.action_type === "TRANSFER"
    ? `Proposta una tantum: ${eur.format(currentProposal.amount)}`
    : currentProposal.recommended_action;

  $("agent-inbox").innerHTML = `
    <article class="inbox-proposal ${executed ? "completed" : "pending"}">
      <button class="inbox-summary" type="button" onclick="toggleActionInbox()" aria-expanded="${expanded}">
        <span class="route-pill ${routeClass(currentProposal.route)}">${route}</span>
        <span>
          <strong>${escapeHtml(currentProposal.title)}</strong>
          <small>${escapeHtml(amountCopy)}</small>
        </span>
        <span class="inbox-chevron">${expanded ? "Riduci" : "Apri"}</span>
      </button>
      ${
        expanded
          ? `
            <div class="inbox-detail">
              ${executed ? executedAccountStateHtml() : pendingProposalDetailHtml()}
            </div>
          `
          : ""
      }
    </article>
  `;
  updateApproveButton();
}

function pendingProposalDetailHtml() {
  const isTransfer = currentProposal.action_type === "TRANSFER";
  return `
    <div class="proposal-copy compact">
      <p>${escapeHtml(currentProposal.summary)}</p>
      <ul>${currentProposal.rationale.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
    </div>
    ${isTransfer ? impactSimulationHtml() : informationalPlanHtml()}
    ${isTransfer ? transferDecisionControlsHtml() : ""}
  `;
}

function informationalPlanHtml() {
  return `
    <div class="info-plan-card">
      <span class="route-pill ${routeClass(currentProposal.route)}">${routeLabel(currentProposal.route)}</span>
      <strong>${escapeHtml(currentProposal.recommended_action)}</strong>
      <p>${escapeHtml(currentProposal.reason)}</p>
    </div>
  `;
}

function transferDecisionControlsHtml() {
  return `
    <div class="decision-card inline">
      <div class="route-header">
        <span class="route-pill ${routeClass(currentProposal.route)}">${routeLabel(currentProposal.route)}</span>
        <span class="muted">${nextStepLabel()}</span>
      </div>
      <label for="amount-input" id="amount-label">Importo trasferimento</label>
      <div class="amount-control" id="amount-control">
        <input id="amount-input" type="number" min="0" step="50" value="${currentProposal.amount}" oninput="scheduleAmountPreview()" />
        <button type="button" class="secondary" onclick="openDeepDiveFromDecision()">Fonti</button>
      </div>
      <div class="decision-actions">
        <button id="approve-button" type="button" onclick="approveTransfer()">Approva</button>
        <button id="reject-button" type="button" class="ghost" onclick="rejectProposal()">Rifiuta</button>
      </div>
    </div>
  `;
}

function renderCustomerResult(trace) {
  if (!trace) {
    $("customer-result").innerHTML = "";
    return;
  }

  const executed = trace.tool_result.status === "EXECUTED";
  const duplicate = trace.tool_result.status === "DUPLICATE";
  const className = executed ? "ok" : "blocked";
  const title = executed
    ? "Trasferimento completato"
    : duplicate
      ? "Operazione gia eseguita"
      : "MFA richiesta";
  const copy = executed
    ? `${eur.format(trace.proposal.amount)} spostati nel fondo emergenze e registrati nel database.`
    : duplicate
      ? "La richiesta usa un identificativo operativo gia consumato. Nessun nuovo movimento e stato creato."
      : "Questo importo richiede una conferma piu forte prima dell'esecuzione. Nessun denaro e stato spostato.";

  $("customer-result").innerHTML = `
    <div class="result-box ${className}">
      <strong>${title}</strong>
      <p>${copy}</p>
    </div>
  `;
}

function proposalUiState() {
  return isExecutedState() ? PROPOSAL_EXECUTED : PROPOSAL_PENDING;
}

function isExecutedState() {
  return Boolean(
    currentProposal?.already_executed
      || ["EXECUTED", "DUPLICATE"].includes(lastTrace?.tool_result?.status),
  );
}

function executedTrace() {
  if (["EXECUTED", "DUPLICATE"].includes(lastTrace?.tool_result?.status)) {
    return lastTrace;
  }
  return currentProposal?.executed_operation || null;
}

function executedAmount() {
  const trace = executedTrace();
  if (trace?.tool_result?.amount !== undefined) return Number(trace.tool_result.amount);
  if (trace?.proposal?.amount !== undefined) return Number(trace.proposal.amount);
  return Number(currentProposal?.amount || 0);
}

function executedMetric(title, subtitle, value) {
  return `
    <div class="executed-metric">
      <span>${escapeHtml(title)}</span>
      <strong>${escapeHtml(value)}</strong>
      <small>${escapeHtml(subtitle)}</small>
    </div>
  `;
}

function renderInspector() {
  const inspector = $("inspector");
  inspector.classList.toggle("open", inspectorOpen);
  inspector.setAttribute("aria-hidden", inspectorOpen ? "false" : "true");
  document.body.classList.toggle("inspector-open", inspectorOpen);
  $("inspector-toggle").textContent = inspectorOpen ? "Nascondi inspector" : "Inspector tecnico";

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.tab === activeInspectorTab);
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `tab-${activeInspectorTab}`);
  });

  renderInspectorContext();
  renderInspectorPolicies();
  renderInspectorExecution();
  renderInspectorAudit();
  renderInspectorRaw();
}

function renderInspectorContext() {
  const rules = currentProposal.financial_rules || {};
  $("tab-context").innerHTML = `
    <div class="fact-list">
      ${factRow("Saldo disponibile", eur.format(currentProposal.available_balance))}
      ${factRow("Spese previste", eur.format(currentProposal.upcoming_expenses_30d))}
      ${factRow("Fondo emergenze attuale", eur.format(currentProposal.emergency_balance))}
      ${factRow("Obiettivo fondo emergenze", eur.format(currentProposal.target_balance))}
      ${factRow("Surplus investibile", eur.format(currentProposal.available_balance - currentProposal.upcoming_expenses_30d - Number(rules.minimum_cash_buffer_eur || 0)))}
      ${factRow("Buffer minimo cliente", eur.format(rules.minimum_cash_buffer_eur || 0))}
      ${factRow("Regola investimento", `${formatPercent(rules.surplus_investment_ratio || 0)} del surplus`)}
      ${factRow("Limite rischio dinamico", eur.format(rules.autonomous_transfer_limit_eur || 0))}
      ${factRow("Destinazione affidabile", currentProposal.trusted_target ? "si" : "no")}
      ${factRow("Prossimo passo richiesto", actionLabel(currentProposal.required_next_step))}
    </div>
  `;
}

function renderInspectorPolicies() {
  const active = state.policies.active
    .map(
      (policy) => `
        <div class="policy">
          <span>${policy.id}<br><small>${policy.title}</small></span>
          <strong>${riskLabel(policy.risk_level)}</strong>
        </div>
      `,
    )
    .join("");
  const stale = state.policies.stale
    .map(
      (policy) => `
        <div class="policy stale">
          <span>${policy.id}<br><small>${policy.title}</small></span>
          <strong>OBSOLETA</strong>
        </div>
      `,
    )
    .join("");

  $("tab-policies").innerHTML = `
    <p class="eyebrow">Policy attive inviate all'agente</p>
    <div class="policy-list">${active}</div>
    <p class="eyebrow">Filtrate prima del contesto</p>
    <div class="policy-list">${stale}</div>
  `;
}

function renderInspectorExecution() {
  const trace = lastTrace || state.audit[0];
  if (!trace) {
    $("tab-execution").innerHTML = `
      ${riskAssessmentBlock(currentProposal.route)}
      ${factRow("Percorso corrente", routeLabel(currentProposal.route))}
      ${factRow("Motivo anteprima", currentProposal.reason)}
      ${factRow("Risultato tool", "Nessuna esecuzione")}
    `;
    return;
  }

  $("tab-execution").innerHTML = `
    ${riskAssessmentBlock(trace.proposal.route)}
    <div class="fact-list">
      ${factRow("Trace ID", trace.trace_id)}
      ${factRow("Percorso", routeLabel(trace.proposal.route))}
      ${factRow("Importo", eur.format(trace.proposal.amount))}
      ${factRow("Stato tool", statusLabel(trace.tool_result.status))}
      ${factRow("Azione richiesta", actionLabel(trace.tool_result.action_required || "none"))}
    </div>
    <pre>${JSON.stringify(trace.tool_result, null, 2)}</pre>
  `;
}

function renderInspectorAudit() {
  const trace = lastTrace || state.audit[0];
  if (!trace) {
    $("tab-audit").innerHTML = `
      <div class="audit-item">
        <span>Nessuna traccia</span>
        <strong>Approva un trasferimento per creare un evento di audit.</strong>
      </div>
    `;
    return;
  }

  $("tab-audit").innerHTML = `
    <div class="audit-list">
      <div class="audit-item">
        <span>${trace.timestamp}</span>
        <strong>${trace.trace_id}</strong>
      </div>
      <div class="trace-list">
        ${trace.layer_events
          .map((event) => `<div class="trace-item"><span>${event.layer}</span><strong>${event.event}</strong></div>`)
          .join("")}
      </div>
      <div class="audit-item">
        <span>Metriche</span>
        <pre>${JSON.stringify(trace.metrics, null, 2)}</pre>
      </div>
    </div>
  `;
}

function riskAssessmentBlock(route) {
  const assessment = riskAssessment(route);
  return `
    <div class="risk-assessment ${assessment.className}">
      <span>Risk Assessment</span>
      <strong>${assessment.label}</strong>
    </div>
  `;
}

function riskAssessment(route) {
  if (route === "APPROVAL_REQUIRED") {
    return { label: "LOW · Customer approval", className: "low" };
  }
  if (route === "STEP_UP_REQUIRED") {
    return { label: "HIGH · MFA required", className: "high" };
  }
  if (route === "REVIEW_REQUIRED") {
    return { label: "MEDIUM · Customer review", className: "medium" };
  }
  if (route === "BLOCKED") {
    return { label: "HIGH · Blocked by guardrail", className: "high" };
  }
  return { label: "INFO · No execution", className: "medium" };
}

function renderInspectorRaw() {
  const raw = {
    current_proposal: currentProposal,
    last_trace: lastTrace,
  };
  $("tab-raw").innerHTML = `<pre>${JSON.stringify(raw, null, 2)}</pre>`;
}

function renderInitialChat() {
  if ($("chat-box").children.length) return;
  addMessage(
    "assistant",
    "Chiedimi informazioni sul contesto bancario caricato. Posso rispondere sulle spese sport o spiegare quando un dato non e disponibile.",
  );
}

function addMessage(role, text) {
  const node = document.createElement("div");
  node.className = `message ${role}`;
  node.textContent = text;
  $("chat-box").appendChild(node);
  $("chat-box").scrollTop = $("chat-box").scrollHeight;
}

async function syncAmountPreview() {
  if (proposalUiState() === PROPOSAL_EXECUTED) return;
  const amount = Number($("amount-input").value);
  if (!Number.isFinite(amount)) return;
  const result = await api("/api/preview-transfer", {
    method: "POST",
    body: JSON.stringify({ amount }),
  });
  currentProposal = result.proposal;
  lastTrace = null;
  renderAgentInbox();
  renderSupervisorCashflow();
  renderDeepDive();
  renderCustomerResult(null);
  renderInspector();
}

function scheduleAmountPreview() {
  window.clearTimeout(amountPreviewTimer);
  amountPreviewTimer = window.setTimeout(syncAmountPreview, 350);
}

async function approveTransfer() {
  if (
    transferInFlight
    || proposalUiState() === PROPOSAL_EXECUTED
    || currentProposal.already_executed
    || currentProposal.action_type !== "TRANSFER"
    || ["BLOCKED", "INVALID_INPUT"].includes(currentProposal.route)
  ) {
    return;
  }
  transferInFlight = true;
  updateApproveButton();

  const amount = Number($("amount-input").value);
  try {
    const trace = await api("/api/submit-transfer", {
      method: "POST",
      body: JSON.stringify({ amount }),
    });
    lastTrace = trace;

    if (trace.tool_result.status === "EXECUTED" || trace.tool_result.status === "DUPLICATE") {
      state = await api("/api/state");
      currentProposal = state.proposal;
      actionInboxOpen = true;
      renderAll();
    } else {
      state.audit = [trace, ...state.audit.filter((item) => item.trace_id !== trace.trace_id)];
    }

    renderCustomerResult(trace);
    renderInspector();
  } finally {
    transferInFlight = false;
    updateApproveButton();
  }
}

async function applySandboxState() {
  if (sandboxInFlight) return;
  const checkingBalance = Number($("sandbox-checking-balance")?.value);
  const emergencyBalance = Number($("sandbox-emergency-balance")?.value);
  const upcomingExpenses = Number($("sandbox-upcoming-expenses")?.value);
  if (
    !Number.isFinite(checkingBalance)
    || !Number.isFinite(emergencyBalance)
    || !Number.isFinite(upcomingExpenses)
    || checkingBalance < 0
    || emergencyBalance < 0
    || upcomingExpenses < 0
  ) {
    renderSandboxResult({
      status: "ERROR",
      reason: "Inserisci solo valori numerici maggiori o uguali a zero.",
    });
    return;
  }

  sandboxInFlight = true;
  updateSandboxButton();
  try {
    const result = await api("/api/sandbox/inject-state", {
      method: "POST",
      body: JSON.stringify({
        checking_balance: checkingBalance,
        emergency_balance: emergencyBalance,
        upcoming_expenses: upcomingExpenses,
      }),
    });
    state = result.state;
    currentProposal = state.proposal;
    lastTrace = null;
    actionInboxOpen = false;
    renderAll();
    renderSandboxResult(result.mutation);
    renderInspector();
  } finally {
    sandboxInFlight = false;
    updateSandboxButton();
  }
}

async function saveRiskLimit() {
  const input = $("risk-limit-input");
  if (!input) return;
  const limit = Number(input.value);
  if (!Number.isFinite(limit) || limit <= 0) return;

  const result = await api("/api/financial-rules", {
    method: "POST",
    body: JSON.stringify({ autonomous_transfer_limit_eur: limit }),
  });
  state = result.state;
  currentProposal = state.proposal;
  lastTrace = null;
  actionInboxOpen = false;
  renderAll();
}

function renderSandboxResult(result) {
  const target = $("sandbox-result");
  if (!target) return;
  const ok = result?.status === "SANDBOX_STATE_INJECTED";
  target.innerHTML = `
    <div class="result-box ${ok ? "ok" : "blocked"}">
      <strong>${ok ? "Stato sandbox applicato" : "Mutazione non valida"}</strong>
      <p>${
        ok
          ? `Checking ${eur.format(result.checking_balance)}, fondo emergenze ${eur.format(result.emergency_balance)}, spese note ${eur.format(result.upcoming_expenses)}.`
          : escapeHtml(result?.reason || "Impossibile applicare la mutazione.")
      }</p>
    </div>
  `;
}

async function askChat(prompt) {
  const message = (prompt || $("chat-input").value).trim();
  if (!message) return;
  $("chat-input").value = message;
  addMessage("user", message);
  const result = await api("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
  addMessage("assistant", result.answer);
  renderChatToolCard(result.tool_result);
}

function renderChatToolCard(toolResult) {
  if (!toolResult || !Array.isArray(toolResult.transactions) || !toolResult.transactions.length) {
    return;
  }

  const node = document.createElement("div");
  node.className = "message assistant tool-card";
  const total = Math.abs(
    toolResult.transactions.reduce((sum, tx) => sum + Number(tx.amount || 0), 0),
  );
  node.innerHTML = `
    <strong>Transazioni considerate</strong>
    <span>${toolResult.count} movimenti · totale ${eur.format(total)}</span>
    <div class="chat-transaction-list">
      ${toolResult.transactions
        .slice(0, 4)
        .map(
          (tx) => `
            <div class="chat-transaction">
              <span>${escapeHtml(tx.date)} · ${escapeHtml(tx.merchant)}</span>
              <strong>${eur.format(tx.amount)}</strong>
            </div>
          `,
        )
        .join("")}
    </div>
  `;
  $("chat-box").appendChild(node);
  $("chat-box").scrollTop = $("chat-box").scrollHeight;
}

function rejectProposal() {
  if (proposalUiState() === PROPOSAL_EXECUTED) return;
  lastTrace = null;
  $("customer-result").innerHTML = `
    <div class="result-box blocked">
      <strong>Proposta rifiutata</strong>
      <p>Nessuna azione e stata eseguita.</p>
    </div>
  `;
  renderInspector();
}

function toggleInspector(force) {
  inspectorOpen = typeof force === "boolean" ? force : !inspectorOpen;
  renderInspector();
}

function toggleDeepDive() {
  deepDiveOpen = !deepDiveOpen;
  renderDeepDive();
}

function toggleActionInbox() {
  if (proposalUiState() === PROPOSAL_EXECUTED) {
    actionInboxOpen = true;
  } else {
    actionInboxOpen = !actionInboxOpen;
  }
  renderAgentInbox();
  renderCustomerResult(null);
}

function openDeepDiveFromDecision() {
  deepDiveOpen = true;
  renderDeepDive();
  document.querySelector(".deep-dive-panel").scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
}

function switchInspectorTab(tabName) {
  activeInspectorTab = tabName;
  renderInspector();
}

function findAccount(name) {
  return state.accounts.find((account) => account.name === name);
}

function isStepUp() {
  return currentProposal.route === "STEP_UP_REQUIRED";
}

function nextStepLabel() {
  if (currentProposal.route === "ALREADY_EXECUTED") return "Operazione gia eseguita";
  if (currentProposal.route === "INFO") return "Nessuna azione richiesta";
  if (currentProposal.route === "REVIEW_REQUIRED") return "Revisione cliente";
  if (currentProposal.route === "BLOCKED") return "Rivedi cashflow";
  if (currentProposal.route === "STEP_UP_REQUIRED") return "MFA richiesta";
  if (currentProposal.route === "INVALID_INPUT") return "Correggi importo";
  return "Approvazione richiesta";
}

function routeClass(route) {
  if (route === "INFO") return "info";
  if (route === "BLOCKED") return "blocked";
  if (route === "REVIEW_REQUIRED") return "step-up";
  if (route === "STEP_UP_REQUIRED") return "step-up";
  if (route === "ALREADY_EXECUTED") return "done";
  if (route === "INVALID_INPUT") return "invalid";
  return "approval";
}

function routeLabel(route) {
  const labels = {
    APPROVAL_REQUIRED: "Approvazione richiesta",
    REVIEW_REQUIRED: "Revisione richiesta",
    BLOCKED: "Bloccato",
    STEP_UP_REQUIRED: "Verifica rafforzata richiesta",
    INVALID_INPUT: "Input non valido",
    ALREADY_EXECUTED: "Operazione completata",
    INFO: "Informativo",
  };
  return labels[route] || route;
}

function statusLabel(status) {
  const labels = {
    EXECUTED: "Eseguito",
    DUPLICATE: "Operazione gia eseguita",
    BLOCKED: "Bloccato",
    NO_DATA: "Dato non disponibile",
    NO_TOOL_NEEDED: "Nessun tool necessario",
  };
  return labels[status] || status;
}

function actionLabel(action) {
  const labels = {
    CUSTOMER_APPROVAL: "Approvazione cliente",
    REQUEST_MFA: "Richiedi MFA",
    CUSTOMER_REVIEW: "Revisione cliente",
    FIX_AMOUNT: "Correggi importo",
    REVIEW_CASHFLOW: "Rivedi cashflow",
    NO_ACTION: "Nessuna azione",
    none: "Nessuna",
  };
  return labels[action] || action;
}

function updateApproveButton() {
  const button = $("approve-button");
  if (!button) return;
  const nonExecutable = currentProposal.action_type !== "TRANSFER";
  const blocked = ["ALREADY_EXECUTED", "BLOCKED", "INVALID_INPUT"].includes(
    currentProposal.route,
  );
  const executed = proposalUiState() === PROPOSAL_EXECUTED;
  button.disabled = transferInFlight || executed || blocked || nonExecutable;
  if (executed) {
    button.textContent = "Gia eseguito";
  } else if (nonExecutable) {
    button.textContent = "Da rivedere";
  } else if (currentProposal.route === "BLOCKED") {
    button.textContent = "Bloccato";
  } else {
    button.textContent = "Approva";
  }
}

function formatRecommendedAction(proposal) {
  if (proposal.action_type === "TRANSFER") {
    return `spostare ${eur.format(proposal.amount)} dal conto corrente al fondo emergenze`;
  }
  return proposal.recommended_action;
}

function updateSandboxButton() {
  const button = $("sandbox-apply-button");
  if (!button) return;
  button.disabled = sandboxInFlight;
  button.textContent = sandboxInFlight
    ? "Applicazione..."
    : "Applica mutazione di stato";
}

function riskLabel(risk) {
  const labels = {
    LOW: "BASSO",
    MEDIUM: "MEDIO",
    HIGH: "ALTO",
  };
  return labels[risk] || risk;
}

function transitionRow({ label, note, before, movement, after, direction, afterBadge }) {
  return `
    <div class="transition-row ${direction}" role="row">
      <div class="transition-label">
        <strong>${escapeHtml(label)}</strong>
        <span>${escapeHtml(note)}</span>
      </div>
      <strong>${escapeHtml(before)}</strong>
      <span class="transition-arrow">${escapeHtml(movement)}</span>
      <strong class="transition-after">
        ${escapeHtml(after)}
        ${afterBadge ? `<span class="coverage-badge" title="${escapeHtml(afterBadge)}">✓</span>` : ""}
      </strong>
    </div>
  `;
}

function formatSignedCurrency(value) {
  if (value === 0) return eur.format(0);
  const sign = value > 0 ? "+" : "-";
  return `${sign}${eur.format(Math.abs(value))}`;
}

function formatPercent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function isFiniteNumber(value) {
  if (value === null || value === undefined || value === "") return false;
  return Number.isFinite(Number(value));
}

function percentOf(value, total) {
  if (!isFiniteNumber(value) || !isFiniteNumber(total) || Number(total) <= 0) return 0;
  return Math.max(0, Math.min(100, (Number(value) / Number(total)) * 100));
}

function eventDate(dateValue) {
  const [year, month, day] = String(dateValue).split("-").map(Number);
  if (!year || !month || !day) return null;
  return new Date(Date.UTC(year, month - 1, day));
}

function formatEventDate(dateValue) {
  const date = eventDate(dateValue);
  if (!date) return String(dateValue || "-");
  return new Intl.DateTimeFormat("it-IT", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

function renderEvidenceRows(evidence) {
  const groups = evidence.reduce((accumulator, item) => {
    const group = item.group || "Evidenze";
    accumulator[group] = accumulator[group] || [];
    accumulator[group].push(item);
    return accumulator;
  }, {});

  return Object.entries(groups)
    .map(
      ([group, items]) => `
        <div class="evidence-group">
          <h4>${escapeHtml(group)}</h4>
          ${items
            .map(
              (item) => `
                <div class="evidence-row">
                  <span>${escapeHtml(item.label)}</span>
                  <strong>${formatEvidenceValue(item)}</strong>
                  <small>${escapeHtml(item.source)}</small>
                  <p>${escapeHtml(item.purpose || "")}</p>
                </div>
              `,
            )
            .join("")}
        </div>
      `,
    )
    .join("");
}

function renderLineChart(snapshots) {
  if (!snapshots.length) return `<p class="muted">Storico mensile non disponibile.</p>`;
  const width = 640;
  const height = 220;
  const padding = 28;
  const keys = ["checking_end_balance_eur", "emergency_fund_balance_eur"];
  const values = snapshots.flatMap((snapshot) => keys.map((key) => snapshot[key]));
  const min = Math.min(...values) * 0.92;
  const max = Math.max(...values) * 1.08;
  const xStep = snapshots.length > 1 ? (width - padding * 2) / (snapshots.length - 1) : 0;
  const y = (value) => height - padding - ((value - min) / (max - min)) * (height - padding * 2);
  const lineFor = (key) =>
    snapshots
      .map((snapshot, index) => `${padding + index * xStep},${y(snapshot[key]).toFixed(1)}`)
      .join(" ");

  const labels = snapshots
    .map((snapshot, index) => {
      if (index % 2 !== 0 && index !== snapshots.length - 1) return "";
      return `<text x="${padding + index * xStep}" y="${height - 6}" text-anchor="middle">${snapshot.month_label.split(" ")[0]}</text>`;
    })
    .join("");

  return `
    <div class="chart-card">
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Andamento mensile saldi conto corrente e fondo emergenze">
        <line class="axis" x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}"></line>
        <line class="axis" x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}"></line>
        <polyline class="line checking-line" points="${lineFor("checking_end_balance_eur")}"></polyline>
        <polyline class="line emergency-line" points="${lineFor("emergency_fund_balance_eur")}"></polyline>
        ${labels}
      </svg>
      <div class="chart-legend">
        <span><i class="legend-dot checking"></i>Conto corrente</span>
        <span><i class="legend-dot emergency"></i>Fondo emergenze</span>
      </div>
    </div>
  `;
}

function renderLiquidityGauge(forecast, checking) {
  const available = Number(checking?.available_balance || checking?.balance || 0);
  if (available <= 0) return `<p class="muted">Liquidità conto corrente non disponibile.</p>`;

  const expenses = Math.min(Number(forecast.known_expenses_total || 0), available);
  const freeMargin = Math.max(available - expenses, 0);
  const proposalAmount = Math.min(Number(forecast.proposed_action_amount || 0), freeMargin);
  const marginAfterProposal = isFiniteNumber(currentProposal?.projected_expense_buffer)
    ? Math.max(Number(currentProposal.projected_expense_buffer), 0)
    : Math.max(freeMargin - proposalAmount, 0);
  const expensePct = percentOf(expenses, available);
  const marginPct = Math.max(0, 100 - expensePct);
  const proposalPct = percentOf(proposalAmount, available);
  const upcomingEvents = scheduledCashflowEvents(forecast);

  return `
    <div class="liquidity-gauge" aria-label="Barra di liquidità conto corrente">
      <div class="liquidity-gauge-header">
        <div>
          <p class="eyebrow">Barra di liquidità</p>
          <h3>${eur.format(available)} disponibili sul conto corrente</h3>
        </div>
        <span>${forecast.horizon_days || 30} giorni</span>
      </div>

      <div class="liquidity-breakdown">
        <div class="liquidity-breakdown-item expenses">
          <span>Spese bloccate</span>
          <strong>${eur.format(expenses)}</strong>
        </div>
        <div class="liquidity-breakdown-item margin">
          <span>Margine libero</span>
          <strong>${eur.format(freeMargin)}</strong>
        </div>
      </div>

      <div class="liquidity-bar" role="img" aria-label="Spese bloccate ${eur.format(expenses)}, margine libero ${eur.format(freeMargin)}">
        <div class="liquidity-segment expenses" style="flex-basis:${expensePct}%">
          <span>Spese bloccate</span>
          <strong>${eur.format(expenses)}</strong>
        </div>
        <div class="liquidity-segment margin" style="flex-basis:${marginPct}%">
          <span>Margine libero</span>
          <strong>${eur.format(freeMargin)}</strong>
        </div>
        ${
          proposalAmount > 0
            ? `<div class="liquidity-proposal-marker" style="left:${expensePct}%; width:${proposalPct}%">
                <span>${eur.format(proposalAmount)}</span>
              </div>`
            : ""
        }
      </div>

      ${
        proposalAmount > 0
          ? `<div class="liquidity-proposal-note">
              <strong>Proposta agente: ${eur.format(proposalAmount)}</strong>
              <span>Margine residuo dopo approvazione: ${eur.format(marginAfterProposal)}</span>
            </div>`
          : ""
      }

      <div class="upcoming-events-list">
        <div class="upcoming-events-title">
          <strong>Spese pianificate</strong>
          <span>${upcomingEvents.length ? "Prossimi pagamenti noti" : "Nessuna spesa nei prossimi 30 giorni"}</span>
        </div>
        ${
          upcomingEvents.length
            ? upcomingEvents.map(renderScheduledEvent).join("")
            : `<div class="upcoming-event empty">Nessuna uscita pianificata nel ledger.</div>`
        }
      </div>
    </div>
  `;
}

function scheduledCashflowEvents(forecast) {
  const scheduled = state.scheduled_transactions || [];
  if (scheduled.length) {
    return scheduled
      .map((event) => ({
        date: event.date,
        merchant: event.merchant,
        category: event.category,
        amount: Number(event.amount || 0),
      }))
      .sort((a, b) => String(a.date || "").localeCompare(String(b.date || "")));
  }

  return (forecast.future_points || [])
    .slice(1)
    .map((event) => ({
      date: event.date,
      merchant: event.label || event.event,
      category: event.category || "",
      amount: Number(event.amount || 0),
    }))
    .sort((a, b) => String(a.date || "").localeCompare(String(b.date || "")));
}

function renderScheduledEvent(event) {
  return `
    <div class="upcoming-event">
      <div>
        <strong>${escapeHtml(event.merchant)}</strong>
        <span>${formatEventDate(event.date)}${event.category ? ` · ${escapeHtml(event.category)}` : ""}</span>
      </div>
      <strong class="event-amount">${eur.format(event.amount)}</strong>
    </div>
  `;
}

function renderMonthlyExpenseBars(snapshots) {
  if (!snapshots.length) return `<p class="muted">Storico mensile non disponibile.</p>`;
  const categories = [
    ["rent_eur", "Affitto", "rent"],
    ["utilities_eur", "Bollette", "utilities"],
    ["groceries_eur", "Spesa", "groceries"],
    ["sport_eur", "Sport", "sport"],
    ["discretionary_eur", "Discrezionali", "discretionary"],
  ];
  const totals = snapshots.map((snapshot) =>
    categories.reduce((sum, [key]) => sum + snapshot[key], 0),
  );
  const maxTotal = Math.max(...totals);
  const rows = snapshots
    .map((snapshot, index) => {
      const total = totals[index];
      const segments = categories
        .map(([key, label, className]) => {
          const width = maxTotal ? (snapshot[key] / maxTotal) * 100 : 0;
          return `<span class="bar-segment ${className}" style="width:${width}%" title="${label}: ${eur.format(snapshot[key])}"></span>`;
        })
        .join("");
      return `
        <div class="bar-row">
          <span>${snapshot.month_label}</span>
          <div class="stacked-bar">${segments}</div>
          <strong>${eur.format(total)}</strong>
        </div>
      `;
    })
    .join("");

  return `
    <div class="bar-chart">${rows}</div>
    <div class="chart-legend wrap">
      ${categories.map(([, label, className]) => `<span><i class="legend-dot ${className}"></i>${label}</span>`).join("")}
    </div>
  `;
}

function renderTransactionsTable(transactions) {
  if (!transactions.length) return `<p class="muted">Nessuna transazione disponibile.</p>`;
  const rows = transactions
    .map(
      (tx) => `
        <tr>
          <td>${tx.date}</td>
          <td>${escapeHtml(tx.merchant)}</td>
          <td>${escapeHtml(tx.category)}</td>
          <td class="numeric">${eur.format(tx.amount)}</td>
        </tr>
      `,
    )
    .join("");
  return `
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th>Data</th>
            <th>Merchant</th>
            <th>Categoria</th>
            <th>Importo</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function formatEvidenceValue(item) {
  if (item.unit === "EUR") return eur.format(item.value);
  if (item.unit === "route") return routeLabel(item.value);
  return escapeHtml(String(item.value));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function factRow(label, value) {
  return `<div class="fact-row"><span>${label}</span><strong>${value}</strong></div>`;
}

function goalMetric(label, value) {
  return `
    <div class="goal-metric">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value || "-")}</strong>
    </div>
  `;
}

$("deep-dive-toggle").addEventListener("click", toggleDeepDive);
$("chat-button").addEventListener("click", () => askChat());
$("chat-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter") askChat();
});
$("inspector-toggle").addEventListener("click", () => toggleInspector());
$("inspector-close").addEventListener("click", () => toggleInspector(false));
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => switchInspectorTab(tab.dataset.tab));
});
document.querySelectorAll(".quick-prompt").forEach((button) => {
  button.addEventListener("click", () => askChat(button.dataset.prompt));
});
$("sandbox-apply-button")?.addEventListener("click", applySandboxState);

loadState().catch((error) => {
  document.body.innerHTML = `<pre>Impossibile caricare il prototipo: ${error.message}</pre>`;
});
