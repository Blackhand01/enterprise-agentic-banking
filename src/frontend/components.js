import {
  $,
  setHtml,
  escapeHtml,
  eur,
  goalMetric,
  formatSignedCurrency,
  formatSignedPoints,
  routeClass,
  routeLabel,
  PROPOSAL_EXECUTED,
  executedAmount,
  executedTrace,
  executedTransferCopy,
  isExecutableMoneyMovement,
  moneyMovementSummary,
  proposalUiState,
} from "./core.js";
export function agentReasoningPanelHtml(currentProposal, expanded = !0) {
  const html = (function (currentProposal) {
    const trace = currentProposal?.reasoning_trace || [];
    return trace.length
      ? `\n    <ol class="reasoning-steps">\n      ${trace.map(reasoningStepHtml).join("")}\n    </ol>\n  `
      : "";
  })(currentProposal);
  return html
    ? `\n    <section class="agent-reasoning-panel inline">\n      <div class="panel-heading compact">\n        <div>\n          <p class="eyebrow">Explainability</p>\n        </div>\n        <button class="secondary small" type="button" onclick="toggleExplainabilityPanel()" aria-expanded="${expanded}">\n          ${expanded ? "Riduci" : "Apri"}\n        </button>\n      </div>\n      ${expanded ? `<div class="agent-reasoning">${html}</div>` : ""}\n    </section>\n  `
    : "";
}
function reasoningStepHtml(step) {
  return `\n    <li class="reasoning-step">\n      <div class="reasoning-marker">${escapeHtml(((stepName = step.step), { Analisi_Contesto: "1", Valutazione_Obiettivo: "2", Logica_Decisionale: "3", Verifica_Compliance: "4" }[stepName] || ""))}</div>\n      <div class="reasoning-content">\n        <strong>${escapeHtml(step.title)}</strong>\n        <p>${escapeHtml(step.summary)}</p>\n        <div class="reasoning-facts">\n          ${(step.facts || []).map(reasoningFactHtml).join("")}\n        </div>\n      </div>\n    </li>\n  `;
  var stepName;
}
function reasoningFactHtml(fact) {
  return "Route rischio" === fact.label
    ? ""
    : `\n    <span>\n      ${escapeHtml(fact.label)}\n      <strong>${escapeHtml(
      (function (fact) {
        return "EUR" === fact.unit
          ? eur.format(Number(fact.value || 0))
          : (fact.value ?? "-");
      })(fact),
    )}</strong>\n    </span>\n  `;
}
export function renderSupervisorCashflow({
  state: state,
  currentProposal: currentProposal,
  findAccount: findAccount,
}) {
  const forecast = state.cashflow_forecast || {},
    checking = findAccount("Checking");
  setHtml(
    "cashflow-supervisor",
    `\n    <div class="cashflow-grid">\n      <div class="cashflow-gauge-card">\n        ${(function ({
      forecast: forecast,
      checking: checking,
      currentProposal: currentProposal,
    }) {
      const available = Number(
        checking?.available_balance || checking?.balance || 0,
      ),
        expenses = Number(forecast.known_expenses_total || 0);
      if (available <= 0 && expenses <= 0)
        return '<p class="muted">Liquidità conto corrente non disponibile.</p>';
      const horizonDays = forecast.horizon_days || 30,
        currentMargin = available - expenses,
        hasMoneyMovement = isExecutableMoneyMovement(
          currentProposal?.action_type,
        ),
        proposalAmount = hasMoneyMovement
          ? Number(currentProposal.amount || 0)
          : 0,
        proposalImpact =
          "TRANSFER_REVERSE" === currentProposal?.action_type
            ? proposalAmount
            : -proposalAmount,
        marginAfterProposal = currentMargin + proposalImpact,
        safetyBuffer = Number(
          currentProposal?.financial_rules?.minimum_cash_buffer_eur || 0,
        ),
        barTotal = Math.max(available, expenses, safetyBuffer, 1),
        expensePct = clampPercent((expenses / barTotal) * 100),
        marginPct = clampPercent((Math.max(currentMargin, 0) / barTotal) * 100),
        bufferPct = clampPercent((safetyBuffer / barTotal) * 100),
        status =
          marginAfterProposal >= safetyBuffer ? "Copertura ok" : "Da rivedere",
        statusClass = marginAfterProposal >= safetyBuffer ? "ok" : "risk",
        decisionLabel = hasMoneyMovement ? "Dopo proposta" : "Decisione agente",
        decisionDetail = hasMoneyMovement ? status : "Liquidita preservata";
      return `\n    <div class="liquidity-gauge" aria-label="Barra di liquidità conto corrente">\n      <div class="liquidity-gauge-header">\n        <div>\n          <p class="eyebrow">Barra di liquidità</p>\n          <h3>${eur.format(available)} disponibili sul conto corrente</h3>\n        </div>\n        <span>${horizonDays} giorni</span>\n      </div>\n\n      <div class="liquidity-bar dynamic" role="img" aria-label="Distribuzione visuale della liquidità nei prossimi ${horizonDays} giorni">\n        <div class="liquidity-segment expenses" style="width:${expensePct}%"></div>\n        <div class="liquidity-segment margin" style="width:${marginPct}%"></div>\n        ${safetyBuffer > 0 ? `<span class="liquidity-marker" style="left:${bufferPct}%"><span>Buffer</span></span>` : ""}\n      </div>\n\n      <div class="liquidity-dashboard">\n        ${liquidityTile("Uscite 30g", eur.format(expenses), "Impegni gia pianificati", "expense")}\n        ${liquidityTile(
        "Margine ora",
        eur.format(currentMargin),
        (function (margin, safetyBuffer) {
          const delta = margin - safetyBuffer;
          return Math.abs(delta) < 0.005
            ? "Al buffer minimo"
            : delta > 0
              ? "Sopra buffer cliente"
              : "Sotto buffer cliente";
        })(currentMargin, safetyBuffer),
        currentMargin >= safetyBuffer ? "safe" : "risk",
      )}\n        ${liquidityTile(decisionLabel, eur.format(marginAfterProposal), decisionDetail, statusClass)}\n      </div>\n    </div>\n  `;
    })({
      forecast: forecast,
      checking: checking,
      currentProposal: currentProposal,
    })}\n      </div>\n    </div>\n  `,
  );
}
function liquidityTile(label, value, detail, tone) {
  return `\n    <div class="liquidity-tile ${tone}">\n      <span>${label}</span>\n      <strong>${value}</strong>\n      <small>${detail}</small>\n    </div>\n  `;
}
function clampPercent(value) {
  return Math.min(100, Math.max(0, value));
}
export function renderInitialChat() {
  $("chat-box").children.length ||
    addMessage(
      "assistant",
      "Chiedimi informazioni sul contesto bancario caricato.",
    );
}
export function addMessage(role, text) {
  const node = document.createElement("div");
  ((node.className = `message ${role}`),
    (node.textContent = text),
    $("chat-box").appendChild(node),
    ($("chat-box").scrollTop = $("chat-box").scrollHeight));
}
export function renderChatToolCard(toolResult) {
  if (!toolResult || !Array.isArray(toolResult.transactions)) return;
  const node = document.createElement("div");
  if (
    ((node.className = "message assistant tool-card"),
      !toolResult.transactions.length)
  ) {
    node.classList.add("empty");
    const query = toolResult.search_query || toolResult.category || "richiesta";
    return (
      (node.innerHTML = `\n      <strong>Transazioni considerate</strong>\n      <span>0 movimenti trovati per "${escapeHtml(query)}"</span>\n    `),
      $("chat-box").appendChild(node),
      void ($("chat-box").scrollTop = $("chat-box").scrollHeight)
    );
  }
  const total = Math.abs(
    toolResult.transactions.reduce(
      (sum, tx) => sum + Number(tx.amount || 0),
      0,
    ),
  );
  ((node.innerHTML = `\n    <strong>Transazioni considerate</strong>\n    <span>${toolResult.count} movimenti · totale ${eur.format(total)}</span>\n    <div class="chat-transaction-list">\n      ${toolResult.transactions
    .slice(0, 4)
    .map(
      (tx) =>
        `\n            <div class="chat-transaction">\n              <span>${escapeHtml(tx.date)} · ${escapeHtml(tx.merchant)}</span>\n              <strong>${eur.format(tx.amount)}</strong>\n            </div>\n          `,
    )
    .join("")}\n    </div>\n  `),
    $("chat-box").appendChild(node),
    ($("chat-box").scrollTop = $("chat-box").scrollHeight));
}
export function clearCustomerResult() {
  setHtml("customer-result", "");
}
export function renderDeepDive({ state: state, deepDiveOpen: deepDiveOpen }) {
  const toggle = $("deep-dive-toggle"),
    panel = $("deep-dive-panel"),
    content = $("deep-dive-content");
  (toggle &&
    ((toggle.textContent = "Storico azioni agente"),
      toggle.setAttribute("aria-expanded", String(deepDiveOpen))),
    panel &&
    (panel.classList.toggle("open", deepDiveOpen),
      panel.setAttribute("aria-hidden", deepDiveOpen ? "false" : "true")),
    content.classList.toggle("open", deepDiveOpen),
    (content.innerHTML = deepDiveOpen
      ? `\n    <div class="source-note">Qui trovi solo le azioni agente registrate e il relativo audit trail.</div>\n    ${(function (
        auditEvents,
      ) {
        if (!auditEvents.length)
          return '<p class="muted">Nessuna azione agente registrata in questa sessione.</p>';
        return `\n    <div class="audit-list">\n      ${auditEvents
          .map((event) =>
            (function (event) {
              const title = (function (title) {
                return (
                  String(title)
                    .replace(/^[^\p{L}\p{N}]+/u, "")
                    .trim() || "Azione agente"
                );
              })(event.proposal?.title || "Azione agente"),
                status =
                  event.tool_result?.status ||
                  event.proposal?.route ||
                  "Registrata",
                amount = Number(
                  event.tool_result?.amount || event.proposal?.amount || 0,
                ),
                amountCopy = amount > 0 ? ` · ${eur.format(amount)}` : "",
                layers = (event.layer_events || [])
                  .slice(0, 5)
                  .map(
                    (item) =>
                      `\n        <span>\n          <strong>${escapeHtml(item.layer)}</strong>\n          ${escapeHtml(item.event)}\n        </span>\n      `,
                  )
                  .join("");
              return `\n    <article class="audit-item">\n      <span>${escapeHtml(
                (function (timestamp) {
                  if (!timestamp) return "Timestamp non disponibile";
                  const parsed = new Date(timestamp);
                  return Number.isNaN(parsed.getTime())
                    ? timestamp
                    : parsed.toLocaleString("it-IT", {
                      dateStyle: "short",
                      timeStyle: "short",
                    });
                })(event.timestamp),
              )}</span>\n      <strong>${escapeHtml(title)}</strong>\n      <small>${escapeHtml(event.trace_id || "trace non disponibile")} · ${escapeHtml(status)}${amountCopy}</small>\n      ${layers ? `<div class="audit-layer-list">${layers}</div>` : ""}\n    </article>\n  `;
            })(event),
          )
          .join("")}\n    </div>\n  `;
      })(state.audit || [])}\n  `
      : ""));
}
export function renderInsights({ state: state, insightsOpen: insightsOpen }) {
  const toggle = $("insights-toggle"),
    panel = $("insights-panel"),
    content = $("insights-content");
  if (
    (toggle &&
      ((toggle.textContent = "Insights"),
        toggle.setAttribute("aria-expanded", String(insightsOpen))),
      panel &&
      (panel.classList.toggle("open", insightsOpen),
        panel.setAttribute("aria-hidden", insightsOpen ? "false" : "true")),
      content.classList.toggle("open", insightsOpen),
      !insightsOpen)
  )
    return void (content.innerHTML = "");
  const snapshots = state.monthly_snapshots || [];
  content.innerHTML = `\n    <div class="source-note">Qui trovi i dati storici e le transazioni usate come grounding. I numeri arrivano dal ledger SQLite e dai read model, non dalla memoria del modello.</div>\n    <div class="deep-dive-grid">\n      <section class="evidence-card">\n        <h3>Andamento saldi</h3>\n        ${renderLineChart(snapshots)}\n      </section>\n      <section class="evidence-card">\n        <h3>Spese mensili considerate</h3>\n        ${(function (
    snapshots,
  ) {
    if (!snapshots.length)
      return '<p class="muted">Storico mensile non disponibile.</p>';
    const categories = [
      ["rent_eur", "Affitto", "rent"],
      ["utilities_eur", "Bollette", "utilities"],
      ["groceries_eur", "Spesa", "groceries"],
      ["sport_eur", "Sport", "sport"],
      ["discretionary_eur", "Discrezionali", "discretionary"],
    ],
      totals = snapshots.map((snapshot) =>
        categories.reduce((sum, [key]) => sum + snapshot[key], 0),
      ),
      maxTotal = Math.max(...totals),
      rows = snapshots
        .map((snapshot, index) => {
          const total = totals[index],
            segments = categories
              .map(
                ([key, label, className]) =>
                  `<span class="bar-segment ${className}" style="width:${maxTotal ? (snapshot[key] / maxTotal) * 100 : 0}%" title="${label}: ${eur.format(snapshot[key])}"></span>`,
              )
              .join("");
          return `\n        <div class="bar-row">\n          <span>${snapshot.month_label}</span>\n          <div class="stacked-bar">${segments}</div>\n          <strong>${eur.format(total)}</strong>\n        </div>\n      `;
        })
        .join("");
    return `\n    <div class="bar-chart">${rows}</div>\n    <div class="chart-legend wrap">\n      ${categories.map(([, label, className]) => `<span><i class="legend-dot ${className}"></i>${label}</span>`).join("")}\n    </div>\n  `;
  })(
    snapshots,
  )}\n      </section>\n      <section class="evidence-card wide">\n        <h3>Transazioni considerate</h3>\n        ${(function (
    transactions,
  ) {
    if (!transactions.length)
      return '<p class="muted">Nessuna transazione disponibile.</p>';
    return `\n    <div class="table-wrap">\n      <table class="data-table">\n        <thead>\n          <tr>\n            <th>Data</th>\n            <th>Merchant</th>\n            <th>Categoria</th>\n            <th>Importo</th>\n          </tr>\n        </thead>\n        <tbody>${transactions.map((tx) => `\n        <tr>\n          <td>${tx.date}</td>\n          <td>${escapeHtml(tx.merchant)}</td>\n          <td>${escapeHtml(tx.category)}</td>\n          <td class="numeric">${eur.format(tx.amount)}</td>\n        </tr>\n      `).join("")}</tbody>\n      </table>\n    </div>\n  `;
  })(state.transactions || [])}\n      </section>\n    </div>\n  `;
}
export function renderLineChart(snapshots) {
  if (!snapshots.length)
    return '<p class="muted">Storico mensile non disponibile.</p>';
  const keys = ["checking_end_balance_eur", "emergency_fund_balance_eur"],
    values = snapshots.flatMap((snapshot) => keys.map((key) => snapshot[key])),
    min = 0.92 * Math.min(...values),
    max = 1.08 * Math.max(...values),
    xStep = snapshots.length > 1 ? 584 / (snapshots.length - 1) : 0,
    lineFor = (key) =>
      snapshots
        .map((snapshot, index) => {
          return `${28 + index * xStep},${((value = snapshot[key]), 192 - ((value - min) / (max - min)) * 164).toFixed(1)}`;
          var value;
        })
        .join(" "),
    labels = snapshots
      .map((snapshot, index) =>
        index % 2 != 0 && index !== snapshots.length - 1
          ? ""
          : `<text x="${28 + index * xStep}" y="214" text-anchor="middle">${snapshot.month_label.split(" ")[0]}</text>`,
      )
      .join("");
  return `\n    <div class="chart-card">\n      <svg viewBox="0 0 640 220" role="img" aria-label="Andamento mensile saldi conto corrente e fondo emergenze">\n        <line class="axis" x1="28" y1="192" x2="612" y2="192"></line>\n        <line class="axis" x1="28" y1="28" x2="28" y2="192"></line>\n        <polyline class="line checking-line" points="${lineFor("checking_end_balance_eur")}"></polyline>\n        <polyline class="line emergency-line" points="${lineFor("emergency_fund_balance_eur")}"></polyline>\n        ${labels}\n      </svg>\n      <div class="chart-legend">\n        <span><i class="legend-dot checking"></i>Conto corrente</span>\n        <span><i class="legend-dot emergency"></i>Fondo emergenze</span>\n      </div>\n    </div>\n  `;
}
export function renderUser(state) {
  (($("user-name").textContent =
    `${state.user.first_name} ${state.user.last_name}`),
    ($("auth-level").textContent =
      "mfa_verified" === state.user.auth_level
        ? "Contesto MFA caricato"
        : "Contesto standard"));
}
export function renderGoal(state) {
  const goal = state.user_goal || {},
    projection = state.emergency_goal_projection || {},
    behindPlan = (function (projection) {
      if ("boolean" == typeof projection.is_behind_plan)
        return projection.is_behind_plan;
      const currentMonthly = Number(projection.historical_monthly_savings || 0),
        requiredMonthly = Number(projection.required_monthly_savings || 0),
        targetMonths = Number(projection.target_months || 0),
        historicalEta = projection.historical_eta_months;
      return (
        !(requiredMonthly <= 0) &&
        (null == historicalEta ||
          currentMonthly < requiredMonthly ||
          Number(historicalEta) > targetMonths)
      );
    })(projection),
    statusTitle = behindPlan
      ? "Sei in ritardo sul ritmo richiesto"
      : "Sei allineato al piano",
    statusSummary = (function (projection, behindPlan) {
      const currentMonthly = eur.format(
        projection.historical_monthly_savings || 0,
      ),
        requiredMonthly = eur.format(projection.required_monthly_savings || 0),
        targetLabel = projection.target_label || "la data obiettivo";
      if (behindPlan)
        return `Al ritmo storico stai versando ${currentMonthly}/mese, ma per arrivare entro ${targetLabel} servono ${requiredMonthly}/mese.`;
      return `Il ritmo storico copre il piano richiesto di ${requiredMonthly}/mese.`;
    })(projection, behindPlan);
  setHtml(
    "goal-summary",
    `\n    <div class="goal-grid">\n      <div class="goal-progress-card">\n        <span>${escapeHtml(goal.description || "Costruire il fondo emergenze.")}</span>\n        <strong>${eur.format(projection.current_balance || 0)} / ${eur.format(projection.target_balance || 0)}</strong>\n        <div class="goal-progress-bar">\n          <span style="width:${Math.min(projection.current_progress || 0, 100)}%"></span>\n        </div>\n        <small>${projection.current_progress || 0}% completato · gap ${eur.format(projection.gap || 0)}</small>\n      </div>\n      ${goalMetric("Data obiettivo", projection.target_label)}\n      ${goalMetric("Al ritmo attuale", projection.historical_eta_label)}\n      ${goalMetric("Necessario da oggi", `${eur.format(projection.required_monthly_savings || 0)} / mese`)}\n    </div>\n    <div class="goal-timeline">\n      <div>\n        <span>Media storica rilevata</span>\n        <strong>${eur.format(projection.historical_monthly_savings || 0)} / mese</strong>\n      </div>\n      <div>\n        <span>Gap rimanente</span>\n        <strong>${eur.format(projection.gap || 0)}</strong>\n      </div>\n      <div>\n        <span>Obiettivo</span>\n        <strong>${eur.format(projection.target_balance || 0)}</strong>\n      </div>\n    </div>\n    <div class="goal-status ${behindPlan ? "behind" : "aligned"}">\n      <strong>${statusTitle}</strong>\n      <p>${escapeHtml(statusSummary)}</p>\n      <span>${escapeHtml(projection.agent_timeline_note || "")}</span>\n    </div>\n  `,
  );
}
export function renderAgentInbox(ctx) {
  const {
    currentProposal: currentProposal,
    lastTrace: lastTrace,
    actionInboxOpen: actionInboxOpen,
  } = ctx,
    executed =
      proposalUiState(currentProposal, lastTrace) === PROPOSAL_EXECUTED,
    expanded = actionInboxOpen || executed,
    route = routeLabel(currentProposal.route),
    amountCopy = isExecutableMoneyMovement(currentProposal.action_type)
      ? moneyMovementSummary(currentProposal, eur)
      : currentProposal.recommended_action;
  setHtml(
    "agent-inbox",
    `\n    <article class="inbox-proposal ${executed ? "completed" : "pending"}">\n      <button class="inbox-summary" type="button" onclick="toggleActionInbox()" aria-expanded="${expanded}">\n        <span class="route-pill ${routeClass(currentProposal.route)}">${route}</span>\n        <span>\n          <strong>${escapeHtml(currentProposal.title)}</strong>\n          <small>${escapeHtml(amountCopy)}</small>\n        </span>\n        <span class="inbox-chevron">${expanded ? "Riduci" : "Apri"}</span>\n      </button>\n      ${expanded
      ? `\n            <div class="inbox-detail">\n              ${executed
        ? executedAccountStateHtml(ctx)
        : (function (ctx) {
          const { currentProposal: currentProposal } = ctx,
            isExecutable = ["TRANSFER", "TRANSFER_REVERSE"].includes(
              currentProposal.action_type,
            ),
            reasoningHtml = agentReasoningPanelHtml(
              currentProposal,
              ctx.explainabilityOpen,
            );
          return `\n    ${reasoningHtml}\n    ${isExecutable
            ? (function (ctx) {
              const {
                currentProposal: currentProposal,
                findAccount: findAccount,
                impactOpen: impactOpen,
                lastTrace: lastTrace,
              } = ctx;
              if (
                proposalUiState(currentProposal, lastTrace) ===
                PROPOSAL_EXECUTED
              )
                return executedAccountStateHtml(ctx);
              const checking = findAccount("Checking"),
                emergency = findAccount("Emergency_Fund"),
                progress = Math.round(
                  (emergency.balance / emergency.target_balance) *
                  100,
                ),
                upcoming = currentProposal.upcoming_expenses_30d,
                checkingAfter =
                  currentProposal.projected_checking_balance,
                emergencyAfter =
                  currentProposal.projected_emergency_balance,
                beforeExpenseBuffer =
                  checking.available_balance - upcoming,
                afterExpenseBuffer = checkingAfter - upcoming,
                movementAmount = currentProposal.already_executed
                  ? 0
                  : currentProposal.amount,
                checkingMovement =
                  "TRANSFER_REVERSE" === currentProposal.action_type
                    ? movementAmount
                    : -movementAmount,
                emergencyMovement =
                  "TRANSFER_REVERSE" === currentProposal.action_type
                    ? -movementAmount
                    : movementAmount,
                checkingDirection =
                  checkingMovement >= 0 ? "increase" : "decrease",
                emergencyDirection =
                  emergencyMovement >= 0 ? "increase" : "decrease";
              return `\n    <div class="simulation-block">\n      <div class="panel-heading compact">\n        <div>\n          <p class="eyebrow">Impatto proposta</p>\n        </div>\n        <button class="secondary small" type="button" onclick="toggleImpactPanel()" aria-expanded="${impactOpen}">\n          ${impactOpen ? "Riduci" : "Apri"}\n        </button>\n      </div>\n      ${impactOpen ? `\n            <div class="transition-table" role="table" aria-label="Impatto della proposta sui saldi">\n              <div class="transition-row transition-head" role="row">\n                <span>Indicatore</span>\n                <span>Prima</span>\n                <span>Movimento</span>\n                <span>Dopo</span>\n              </div>\n              ${transitionRow({ label: "Conto corrente", note: "Saldo disponibile", before: eur.format(checking.available_balance), movement: formatSignedCurrency(checkingMovement), after: eur.format(checkingAfter), direction: checkingDirection })}\n              ${transitionRow({ label: "Margine dopo spese note", note: `${eur.format(upcoming)} gia pianificati nei prossimi 30 giorni`, before: eur.format(beforeExpenseBuffer), movement: formatSignedCurrency(checkingMovement), after: eur.format(afterExpenseBuffer), direction: afterExpenseBuffer >= 0 ? "safe" : "risk", afterBadge: afterExpenseBuffer >= 0 ? `Copre le spese previste di ${eur.format(upcoming)}` : "Spese previste non coperte" })}\n              ${transitionRow({ label: "Fondo emergenze", note: `Obiettivo ${eur.format(emergency.target_balance)}`, before: eur.format(emergency.balance), movement: formatSignedCurrency(emergencyMovement), after: eur.format(emergencyAfter), direction: emergencyDirection })}\n              ${transitionRow({ label: "Avanzamento obiettivo", note: "Copertura fondo emergenze", before: `${progress}%`, movement: currentProposal.already_executed ? "0 pp" : formatSignedPoints(currentProposal.projected_goal_progress - progress), after: `${currentProposal.projected_goal_progress}%`, direction: currentProposal.projected_goal_progress >= progress ? "increase" : "decrease" })}\n            </div>\n            <div class="transition-context">\n              <div>\n                <span>Ultimo stipendio rilevato</span>\n                <strong>${eur.format(currentProposal.salary_detected.amount)}</strong>\n                <small>${currentProposal.salary_detected.merchant} · ${currentProposal.salary_detected.date}</small>\n              </div>\n              <div>\n                <span>Spese note considerate</span>\n                <strong>${eur.format(upcoming)}</strong>\n                <small>Pagamenti pianificati nel ledger</small>\n              </div>\n            </div>\n          ` : ""}\n    </div>\n  `;
            })(ctx)
            : ""
            }\n    ${isExecutable
              ? (function (currentProposal) {
                return `\n    <div class="decision-card inline">\n      <label for="amount-input" id="amount-label">Importo trasferimento</label>\n      <div class="amount-control" id="amount-control">\n        <input id="amount-input" type="number" min="0" step="50" value="${currentProposal.amount}" oninput="scheduleAmountPreview()" />\n      </div>\n      <div class="decision-actions">\n        <button id="approve-button" type="button" onclick="approveTransfer()">Approva</button>\n        <button id="reject-button" type="button" class="ghost" onclick="rejectProposal()">Rifiuta</button>\n      </div>\n    </div>\n  `;
              })(currentProposal)
              : ""
            }\n  `;
        })(ctx)
      }\n            </div>\n          `
      : ""
    }\n    </article>\n  `,
  );
}
export function renderCustomerResult(trace) {
  if (!trace) return void setHtml("customer-result", "");
  const executed = "EXECUTED" === trace.tool_result.status,
    duplicate = "DUPLICATE" === trace.tool_result.status,
    className = executed ? "ok" : "blocked",
    title = executed
      ? "Trasferimento completato"
      : duplicate
        ? "Operazione gia eseguita"
        : "MFA richiesta",
    copy = executed
      ? `${executedTransferCopy(trace.proposal, eur)} e registrati nel database.`
      : duplicate
        ? "La richiesta usa un identificativo operativo gia consumato. Nessun nuovo movimento e stato creato."
        : "Questo importo richiede una conferma piu forte prima dell'esecuzione. Nessun denaro e stato spostato.";
  setHtml(
    "customer-result",
    `\n    <div class="result-box ${className}">\n      <strong>${title}</strong>\n      <p>${copy}</p>\n    </div>\n  `,
  );
}
export function renderRejectedProposal() {
  setHtml(
    "customer-result",
    '\n    <div class="result-box blocked">\n      <strong>Proposta rifiutata</strong>\n      <p>Nessuna azione e stata eseguita.</p>\n    </div>\n  ',
  );
}
export function updateApproveButton({
  currentProposal: currentProposal,
  lastTrace: lastTrace,
  transferInFlight: transferInFlight,
}) {
  const button = $("approve-button");
  if (!button) return;
  const nonExecutable = !isExecutableMoneyMovement(currentProposal.action_type),
    blocked = ["ALREADY_EXECUTED", "BLOCKED", "INVALID_INPUT"].includes(
      currentProposal.route,
    ),
    executed =
      proposalUiState(currentProposal, lastTrace) === PROPOSAL_EXECUTED;
  ((button.disabled = transferInFlight || executed || blocked || nonExecutable),
    executed
      ? (button.textContent = "Gia eseguito")
      : nonExecutable
        ? (button.textContent = "Da rivedere")
        : "BLOCKED" === currentProposal.route
          ? (button.textContent = "Bloccato")
          : "STEP_UP_REQUIRED" === currentProposal.route
            ? (button.textContent = "Conferma MFA")
            : (button.textContent = "Approva"));
}
function executedAccountStateHtml(ctx) {
  const {
    state: state,
    currentProposal: currentProposal,
    findAccount: findAccount,
    lastTrace: lastTrace,
  } = ctx,
    checking = findAccount("Checking"),
    emergency = findAccount("Emergency_Fund"),
    projection = state.emergency_goal_projection || {},
    upcoming = currentProposal.upcoming_expenses_30d || 0,
    margin =
      Number(checking.available_balance || checking.balance || 0) - upcoming,
    progress = Math.round((emergency.balance / emergency.target_balance) * 100),
    trace = executedTrace(currentProposal, lastTrace),
    amount = executedAmount(currentProposal, lastTrace);
  return `\n    <div class="executed-state">\n      <div class="success-banner">\n        <strong>✅ OPERAZIONE DI RISPARMIO COMPLETATA CON SUCCESSO.</strong>\n        <span>Trasferimento di ${eur.format(amount)} registrato in SQLite.</span>\n      </div>\n      <div class="executed-grid">\n        ${executedMetric("Conto corrente", "Saldo disponibile aggiornato", eur.format(checking.available_balance || checking.balance))}\n        ${executedMetric("Fondo emergenze", `${progress}% di ${eur.format(emergency.target_balance)}`, eur.format(emergency.balance))}\n        ${executedMetric("✓ Margine di Sicurezza", "Copre le spese dei prossimi 30gg", eur.format(margin))}\n        ${executedMetric("Piano obiettivo", `Tempo stimato al target: ${projection.historical_eta_months || "-"} mesi`, `Contributo mensile residuo necessario: ${eur.format(projection.required_monthly_savings || 0)} / mese`)}\n      </div>\n      <p class="executed-note">Trace ID: ${escapeHtml(trace?.trace_id || currentProposal.trace_id || "-")}. I saldi sono letti dallo stato SQLite aggiornato, non da una simulazione.</p>\n    </div>\n  `;
}
function executedMetric(title, subtitle, value) {
  return `\n    <div class="executed-metric">\n      <span>${escapeHtml(title)}</span>\n      <strong>${escapeHtml(value)}</strong>\n      <small>${escapeHtml(subtitle)}</small>\n    </div>\n  `;
}
function transitionRow({
  label: label,
  note: note,
  before: before,
  movement: movement,
  after: after,
  direction: direction,
  afterBadge: afterBadge,
}) {
  return `\n    <div class="transition-row ${direction}" role="row">\n      <div class="transition-label">\n        <strong>${escapeHtml(label)}</strong>\n        <span>${escapeHtml(note)}</span>\n      </div>\n      <strong>${escapeHtml(before)}</strong>\n      <span class="transition-arrow">${escapeHtml(movement)}</span>\n      <strong class="transition-after">\n        ${escapeHtml(after)}\n        ${afterBadge ? `<span class="coverage-badge" title="${escapeHtml(afterBadge)}">✓</span>` : ""}\n      </strong>\n    </div>\n  `;
}
export function renderInspector({ inspectorOpen: inspectorOpen }) {
  const drawer = $("inspector");
  if (!drawer) return;
  (drawer.classList.toggle("open", inspectorOpen),
    drawer.setAttribute("aria-hidden", inspectorOpen ? "false" : "true"),
    document.body.classList.toggle("inspector-open", inspectorOpen));
  const toggle = $("sandbox-toggle");
  toggle &&
    ((toggle.textContent = "⚙️ Imposta Sandbox"),
      toggle.setAttribute("aria-expanded", String(inspectorOpen)));
}
export function renderFinancialRulesSettings(currentProposal) {
  const target = $("financial-rules-settings");
  if (!target) return;
  const rules = currentProposal.financial_rules || {};
  target.innerHTML = `\n    <div class="rule-setting">\n      <div>\n        <strong>Imposta limite di rischio dinamico</strong>\n        <span>Valore corrente: ${eur.format(rules.autonomous_transfer_limit_eur || 0)}. Sopra questa soglia il trasferimento richiede MFA.</span>\n      </div>\n      <div class="rule-setting-control">\n        <input id="risk-limit-input" type="number" min="1" step="50" value="${Number(rules.autonomous_transfer_limit_eur || 0)}" />\n        <button type="button" class="secondary" onclick="saveRiskLimit()">Salva limite</button>\n      </div>\n    </div>\n  `;
}
export function renderSandboxControls({
  currentProposal: currentProposal,
  findAccount: findAccount,
}) {
  const checkingInput = $("sandbox-checking-balance"),
    emergencyInput = $("sandbox-emergency-balance"),
    upcomingInput = $("sandbox-upcoming-expenses");
  if (!checkingInput || !emergencyInput || !upcomingInput) return;
  const activeElement = document.activeElement,
    checking = findAccount("Checking"),
    emergency = findAccount("Emergency_Fund");
  [checkingInput, emergencyInput, upcomingInput].includes(activeElement) ||
    ((checkingInput.value = Number(
      checking?.available_balance || checking?.balance || 0,
    )),
      (emergencyInput.value = Number(emergency?.balance || 0)),
      (upcomingInput.value = Number(
        currentProposal?.upcoming_expenses_30d || 0,
      )));
}
export function renderSandboxResult(result) {
  const target = $("sandbox-result");
  if (!target) return;
  if (!result) return void (target.innerHTML = "");
  const ok = "SANDBOX_STATE_INJECTED" === result?.status;
  target.innerHTML = `\n    <div class="result-box ${ok ? "ok" : "blocked"}">\n      <strong>${ok ? "Stato sandbox applicato" : "Mutazione non valida"}</strong>\n      <p>${ok ? `Checking ${eur.format(result.checking_balance)}, fondo emergenze ${eur.format(result.emergency_balance)}, spese note ${eur.format(result.upcoming_expenses)}.` : escapeHtml(result?.reason || "Impossibile applicare la mutazione.")}</p>\n    </div>\n  `;
}
export function updateSandboxButton(sandboxInFlight) {
  const button = $("sandbox-apply-button");
  button &&
    ((button.disabled = sandboxInFlight),
      (button.textContent = sandboxInFlight
        ? "Applicazione..."
        : "Applica mutazione di stato"));
}
