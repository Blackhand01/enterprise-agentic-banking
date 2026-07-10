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
    ? `\n    <section class="agent-reasoning-panel inline">\n      <div class="panel-heading compact">\n        <div>\n          <p class="eyebrow">Explainability</p>\n        </div>\n        <button class="secondary small" type="button" onclick="toggleExplainabilityPanel()" aria-expanded="${expanded}">\n          ${expanded ? "Collapse" : "Open"}\n        </button>\n      </div>\n      ${expanded ? `<div class="agent-reasoning">${html}</div>` : ""}\n    </section>\n  `
    : "";
}
function reasoningStepHtml(step) {
  return `\n    <li class="reasoning-step">\n      <div class="reasoning-marker">${escapeHtml(((stepName = step.step), { Context_Analysis: "1", Goal_Evaluation: "2", Decision_Logic: "3", Compliance_Check: "4" }[stepName] || ""))}</div>\n      <div class="reasoning-content">\n        <strong>${escapeHtml(step.title)}</strong>\n        <p>${escapeHtml(step.summary)}</p>\n        <div class="reasoning-facts">\n          ${(step.facts || []).map(reasoningFactHtml).join("")}\n        </div>\n      </div>\n    </li>\n  `;
  var stepName;
}
function reasoningFactHtml(fact) {
  return "Risk route" === fact.label
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
        return '<p class="muted">Checking liquidity unavailable.</p>';
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
          marginAfterProposal >= safetyBuffer ? "Coverage OK" : "Needs review",
        statusClass = marginAfterProposal >= safetyBuffer ? "ok" : "risk",
        decisionLabel = hasMoneyMovement ? "After proposal" : "Agent decision",
        decisionDetail = hasMoneyMovement ? status : "Liquidity preserved";
      return `\n    <div class="liquidity-gauge" aria-label="Checking liquidity bar">\n      <div class="liquidity-gauge-header">\n        <div>\n          <p class="eyebrow">Liquidity bar</p>\n          <h3>${eur.format(available)} available in checking</h3>\n        </div>\n        <span>${horizonDays} days</span>\n      </div>\n\n      <div class="liquidity-bar dynamic" role="img" aria-label="Visual liquidity distribution over the next ${horizonDays} days">\n        <div class="liquidity-segment expenses" style="width:${expensePct}%"></div>\n        <div class="liquidity-segment margin" style="width:${marginPct}%"></div>\n        ${safetyBuffer > 0 ? `<span class="liquidity-marker" style="left:${bufferPct}%"><span>Buffer</span></span>` : ""}\n      </div>\n\n      <div class="liquidity-dashboard">\n        ${liquidityTile("30d outflows", eur.format(expenses), "Already planned commitments", "expense")}\n        ${liquidityTile(
        "Current margin",
        eur.format(currentMargin),
        (function (margin, safetyBuffer) {
          const delta = margin - safetyBuffer;
          return Math.abs(delta) < 0.005
            ? "At minimum buffer"
            : delta > 0
              ? "Above customer buffer"
              : "Below customer buffer";
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
      "Ask me about the loaded banking context.",
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
    const query = toolResult.search_query || toolResult.category || "request";
    return (
      (node.innerHTML = `\n      <strong>Transactions considered</strong>\n      <span>0 movements found for "${escapeHtml(query)}"</span>\n    `),
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
  ((node.innerHTML = `\n    <strong>Transactions considered</strong>\n    <span>${toolResult.count} movements · total ${eur.format(total)}</span>\n    <div class="chat-transaction-list">\n      ${toolResult.transactions
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
    ((toggle.textContent = "Agent action history"),
      toggle.setAttribute("aria-expanded", String(deepDiveOpen))),
    panel &&
    (panel.classList.toggle("open", deepDiveOpen),
      panel.setAttribute("aria-hidden", deepDiveOpen ? "false" : "true")),
    content.classList.toggle("open", deepDiveOpen),
    (content.innerHTML = deepDiveOpen
      ? `\n    <div class="source-note">Here you can find only registered agent actions and their audit trail.</div>\n    ${(function (
        auditEvents,
      ) {
        if (!auditEvents.length)
          return '<p class="muted">No agent action recorded in this session.</p>';
        return `\n    <div class="audit-list">\n      ${auditEvents
          .map((event) =>
            (function (event) {
              const title = (function (title) {
                return (
                  String(title)
                    .replace(/^[^\p{L}\p{N}]+/u, "")
                    .trim() || "Agent action"
                );
              })(event.proposal?.title || "Agent action"),
                status =
                  event.tool_result?.status ||
                  event.proposal?.route ||
                  "Recorded",
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
                  if (!timestamp) return "Timestamp unavailable";
                  const parsed = new Date(timestamp);
                  return Number.isNaN(parsed.getTime())
                    ? timestamp
                    : parsed.toLocaleString("it-IT", {
                      dateStyle: "short",
                      timeStyle: "short",
                    });
                })(event.timestamp),
              )}</span>\n      <strong>${escapeHtml(title)}</strong>\n      <small>${escapeHtml(event.trace_id || "trace unavailable")} · ${escapeHtml(status)}${amountCopy}</small>\n      ${layers ? `<div class="audit-layer-list">${layers}</div>` : ""}\n    </article>\n  `;
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
  content.innerHTML = `\n    <div class="source-note">Here you can inspect historical data and transactions used for grounding. Numbers come from the SQLite ledger and read models, not from model memory.</div>\n    <div class="deep-dive-grid">\n      <section class="evidence-card">\n        <h3>Balance trend</h3>\n        ${renderLineChart(snapshots)}\n      </section>\n      <section class="evidence-card">\n        <h3>Monthly spending considered</h3>\n        ${(function (
    snapshots,
  ) {
    if (!snapshots.length)
      return '<p class="muted">Monthly history unavailable.</p>';
    const categories = [
      ["rent_eur", "Rent", "rent"],
      ["utilities_eur", "Utilities", "utilities"],
      ["groceries_eur", "Groceries", "groceries"],
      ["sport_eur", "Sports", "sports"],
      ["discretionary_eur", "Discretionary", "discretionary"],
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
  )}\n      </section>\n      <section class="evidence-card wide">\n        <h3>Transactions considered</h3>\n        ${(function (
    transactions,
  ) {
    if (!transactions.length)
      return '<p class="muted">None transaction available.</p>';
    return `\n    <div class="table-wrap">\n      <table class="data-table">\n        <thead>\n          <tr>\n            <th>Date</th>\n            <th>Merchant</th>\n            <th>Category</th>\n            <th>Amount</th>\n          </tr>\n        </thead>\n        <tbody>${transactions.map((tx) => `\n        <tr>\n          <td>${tx.date}</td>\n          <td>${escapeHtml(tx.merchant)}</td>\n          <td>${escapeHtml(tx.category)}</td>\n          <td class="numeric">${eur.format(tx.amount)}</td>\n        </tr>\n      `).join("")}</tbody>\n      </table>\n    </div>\n  `;
  })(state.transactions || [])}\n      </section>\n    </div>\n  `;
}
export function renderLineChart(snapshots) {
  if (!snapshots.length)
    return '<p class="muted">Monthly history unavailable.</p>';
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
  return `\n    <div class="chart-card">\n      <svg viewBox="0 0 640 220" role="img" aria-label="Monthly trend for checking and emergency-fund balances">\n        <line class="axis" x1="28" y1="192" x2="612" y2="192"></line>\n        <line class="axis" x1="28" y1="28" x2="28" y2="192"></line>\n        <polyline class="line checking-line" points="${lineFor("checking_end_balance_eur")}"></polyline>\n        <polyline class="line emergency-line" points="${lineFor("emergency_fund_balance_eur")}"></polyline>\n        ${labels}\n      </svg>\n      <div class="chart-legend">\n        <span><i class="legend-dot checking"></i>Checking account</span>\n        <span><i class="legend-dot emergency"></i>Emergency fund</span>\n      </div>\n    </div>\n  `;
}
export function renderUser(state) {
  (($("user-name").textContent =
    `${state.user.first_name} ${state.user.last_name}`),
    ($("auth-level").textContent =
      "mfa_verified" === state.user.auth_level
        ? "MFA context loaded"
        : "Standard context"));
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
      ? "You are behind the required pace"
      : "You are on track",
    statusSummary = (function (projection, behindPlan) {
      const currentMonthly = eur.format(
        projection.historical_monthly_savings || 0,
      ),
        requiredMonthly = eur.format(projection.required_monthly_savings || 0),
        targetLabel = projection.target_label || "the target date";
      if (behindPlan)
        return `At the historical pace you are contributing ${currentMonthly}/month, but to arrive by ${targetLabel} you need ${requiredMonthly}/month.`;
      return `The historical pace covers the required plan of ${requiredMonthly}/month.`;
    })(projection, behindPlan);
  setHtml(
    "goal-summary",
    `\n    <div class="goal-grid">\n      <div class="goal-progress-card">\n        <span>${escapeHtml(goal.description || "Build the emergency fund.")}</span>\n        <strong>${eur.format(projection.current_balance || 0)} / ${eur.format(projection.target_balance || 0)}</strong>\n        <div class="goal-progress-bar">\n          <span style="width:${Math.min(projection.current_progress || 0, 100)}%"></span>\n        </div>\n        <small>${projection.current_progress || 0}% complete · gap ${eur.format(projection.gap || 0)}</small>\n      </div>\n      ${goalMetric("Target date", projection.target_label)}\n      ${goalMetric("At current pace", projection.historical_eta_label)}\n      ${goalMetric("Required from today", `${eur.format(projection.required_monthly_savings || 0)} / month`)}\n    </div>\n    <div class="goal-timeline">\n      <div>\n        <span>Observed historical average</span>\n        <strong>${eur.format(projection.historical_monthly_savings || 0)} / month</strong>\n      </div>\n      <div>\n        <span>Remaining gap</span>\n        <strong>${eur.format(projection.gap || 0)}</strong>\n      </div>\n      <div>\n        <span>Goal</span>\n        <strong>${eur.format(projection.target_balance || 0)}</strong>\n      </div>\n    </div>\n    <div class="goal-status ${behindPlan ? "behind" : "aligned"}">\n      <strong>${statusTitle}</strong>\n      <p>${escapeHtml(statusSummary)}</p>\n      <span>${escapeHtml(projection.agent_timeline_note || "")}</span>\n    </div>\n  `,
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
    `\n    <article class="inbox-proposal ${executed ? "completed" : "pending"}">\n      <button class="inbox-summary" type="button" onclick="toggleActionInbox()" aria-expanded="${expanded}">\n        <span class="route-pill ${routeClass(currentProposal.route)}">${route}</span>\n        <span>\n          <strong>${escapeHtml(currentProposal.title)}</strong>\n          <small>${escapeHtml(amountCopy)}</small>\n        </span>\n        <span class="inbox-chevron">${expanded ? "Collapse" : "Open"}</span>\n      </button>\n      ${expanded
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
              return `\n    <div class="simulation-block">\n      <div class="panel-heading compact">\n        <div>\n          <p class="eyebrow">Proposal impact</p>\n        </div>\n        <button class="secondary small" type="button" onclick="toggleImpactPanel()" aria-expanded="${impactOpen}">\n          ${impactOpen ? "Collapse" : "Open"}\n        </button>\n      </div>\n      ${impactOpen ? `\n            <div class="transition-table" role="table" aria-label="Proposal impact on balances">\n              <div class="transition-row transition-head" role="row">\n                <span>Indicator</span>\n                <span>Before</span>\n                <span>Movement</span>\n                <span>After</span>\n              </div>\n              ${transitionRow({ label: "Checking account", note: "Available balance", before: eur.format(checking.available_balance), movement: formatSignedCurrency(checkingMovement), after: eur.format(checkingAfter), direction: checkingDirection })}\n              ${transitionRow({ label: "Margin after known expenses", note: `${eur.format(upcoming)} already planned over the next 30 days`, before: eur.format(beforeExpenseBuffer), movement: formatSignedCurrency(checkingMovement), after: eur.format(afterExpenseBuffer), direction: afterExpenseBuffer >= 0 ? "safe" : "risk", afterBadge: afterExpenseBuffer >= 0 ? `Covers expected expenses of ${eur.format(upcoming)}` : "Expected expenses not covered" })}\n              ${transitionRow({ label: "Emergency fund", note: `Goal ${eur.format(emergency.target_balance)}`, before: eur.format(emergency.balance), movement: formatSignedCurrency(emergencyMovement), after: eur.format(emergencyAfter), direction: emergencyDirection })}\n              ${transitionRow({ label: "Goal progress", note: "Emergency-fund coverage", before: `${progress}%`, movement: currentProposal.already_executed ? "0 pp" : formatSignedPoints(currentProposal.projected_goal_progress - progress), after: `${currentProposal.projected_goal_progress}%`, direction: currentProposal.projected_goal_progress >= progress ? "increase" : "decrease" })}\n            </div>\n            <div class="transition-context">\n              <div>\n                <span>Latest detected salary</span>\n                <strong>${eur.format(currentProposal.salary_detected.amount)}</strong>\n                <small>${currentProposal.salary_detected.merchant} · ${currentProposal.salary_detected.date}</small>\n              </div>\n              <div>\n                <span>Known expenses considered</span>\n                <strong>${eur.format(upcoming)}</strong>\n                <small>Scheduled payments in the ledger</small>\n              </div>\n            </div>\n          ` : ""}\n    </div>\n  `;
            })(ctx)
            : ""
            }\n    ${isExecutable
              ? (function (currentProposal) {
                return `\n    <div class="decision-card inline">\n      <label for="amount-input" id="amount-label">Transfer amount</label>\n      <div class="amount-control" id="amount-control">\n        <input id="amount-input" type="number" min="0" step="50" value="${currentProposal.amount}" oninput="scheduleAmountPreview()" />\n      </div>\n      <div class="decision-actions">\n        <button id="approve-button" type="button" onclick="approveTransfer()">Approve</button>\n        <button id="reject-button" type="button" class="ghost" onclick="rejectProposal()">Reject</button>\n      </div>\n    </div>\n  `;
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
      ? "Transfer completed"
      : duplicate
        ? "Operation already executed"
        : "MFA required",
    copy = executed
      ? `${executedTransferCopy(trace.proposal, eur)} and recorded in the database.`
      : duplicate
        ? "The request uses an operation ID that has already been consumed. No new movement was created."
        : "This amount requires stronger confirmation before execution. No money was moved.";
  setHtml(
    "customer-result",
    `\n    <div class="result-box ${className}">\n      <strong>${title}</strong>\n      <p>${copy}</p>\n    </div>\n  `,
  );
}
export function renderRejectedProposal() {
  setHtml(
    "customer-result",
    '\n    <div class="result-box blocked">\n      <strong>Proposal rejected</strong>\n      <p>No action was executed.</p>\n    </div>\n  ',
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
      ? (button.textContent = "Already executed")
      : nonExecutable
        ? (button.textContent = "Needs review")
        : "BLOCKED" === currentProposal.route
          ? (button.textContent = "Blocked")
          : "STEP_UP_REQUIRED" === currentProposal.route
            ? (button.textContent = "Confirm MFA")
            : (button.textContent = "Approve"));
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
  return `\n    <div class="executed-state">\n      <div class="success-banner">\n        <strong>✅ SAVINGS OPERATION COMPLETED SUCCESSFULLY.</strong>\n        <span>Transfer of ${eur.format(amount)} recorded in SQLite.</span>\n      </div>\n      <div class="executed-grid">\n        ${executedMetric("Checking account", "Updated available balance", eur.format(checking.available_balance || checking.balance))}\n        ${executedMetric("Emergency fund", `${progress}% of ${eur.format(emergency.target_balance)}`, eur.format(emergency.balance))}\n        ${executedMetric("Safety margin", "Covers expenses for the next 30 days", eur.format(margin))}\n        ${executedMetric("Goal plan", `Estimated time to target: ${projection.historical_eta_months || "-"} months`, `Remaining required monthly contribution: ${eur.format(projection.required_monthly_savings || 0)} / month`)}\n      </div>\n      <p class="executed-note">Trace ID: ${escapeHtml(trace?.trace_id || currentProposal.trace_id || "-")}. Balances are read from updated SQLite state, not from a simulation.</p>\n    </div>\n  `;
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
    ((toggle.textContent = "⚙️ Sandbox Settings"),
      toggle.setAttribute("aria-expanded", String(inspectorOpen)));
}
export function renderFinancialRulesSettings(currentProposal) {
  const target = $("financial-rules-settings");
  if (!target) return;
  const rules = currentProposal.financial_rules || {};
  target.innerHTML = `\n    <div class="rule-setting">\n      <div>\n        <strong>Set dynamic risk limit</strong>\n        <span>Current value: ${eur.format(rules.autonomous_transfer_limit_eur || 0)}. Above this threshold, the transfer requires MFA.</span>\n      </div>\n      <div class="rule-setting-control">\n        <input id="risk-limit-input" type="number" min="1" step="50" value="${Number(rules.autonomous_transfer_limit_eur || 0)}" />\n        <button type="button" class="secondary" onclick="saveRiskLimit()">Save limit</button>\n      </div>\n    </div>\n  `;
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
  target.innerHTML = `\n    <div class="result-box ${ok ? "ok" : "blocked"}">\n      <strong>${ok ? "Sandbox state applied" : "Invalid mutation"}</strong>\n      <p>${ok ? `Checking ${eur.format(result.checking_balance)}, emergency fund ${eur.format(result.emergency_balance)}, known expenses ${eur.format(result.upcoming_expenses)}.` : escapeHtml(result?.reason || "Unable to apply the mutation.")}</p>\n    </div>\n  `;
}
export function updateSandboxButton(sandboxInFlight) {
  const button = $("sandbox-apply-button");
  button &&
    ((button.disabled = sandboxInFlight),
      (button.textContent = sandboxInFlight
        ? "Applying..."
        : "Apply state mutation"));
}
