export const $ = (id) => document.getElementById(id);
export function setHtml(id, html) {
  const element = $(id);
  element && (element.innerHTML = html);
}
export const eur = new Intl.NumberFormat("it-IT", {
  style: "currency",
  currency: "EUR",
});
export function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
export function factRow(label, value) {
  return `<div class="fact-row"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}
export function goalMetric(label, value) {
  return `\n    <div class="goal-metric">\n      <span>${escapeHtml(label)}</span>\n      <strong>${escapeHtml(value || "-")}</strong>\n    </div>\n  `;
}
export function formatSignedCurrency(value) {
  if (0 === value) return eur.format(0);
  return `${value > 0 ? "+" : "-"}${eur.format(Math.abs(value))}`;
}
export function formatSignedPoints(value) {
  if (0 === value) return "0 pp";
  return `${value > 0 ? "+" : ""}${value} pp`;
}
export function formatPercent(value) {
  return `${Math.round(100 * Number(value || 0))}%`;
}
export function isFiniteNumber(value) {
  return null != value && "" !== value && Number.isFinite(Number(value));
}
export function eventDate(dateValue) {
  const [year, month, day] = String(dateValue).split("-").map(Number);
  return year && month && day ? new Date(Date.UTC(year, month - 1, day)) : null;
}
export function formatEventDate(dateValue) {
  const date = eventDate(dateValue);
  return date
    ? new Intl.DateTimeFormat("it-IT", {
        day: "2-digit",
        month: "long",
        year: "numeric",
        timeZone: "UTC",
      }).format(date)
    : String(dateValue || "-");
}
export function routeClass(route) {
  return "INFO" === route
    ? "info"
    : "BLOCKED" === route
      ? "blocked"
      : "REVIEW_REQUIRED" === route || "STEP_UP_REQUIRED" === route
        ? "step-up"
        : "ALREADY_EXECUTED" === route
          ? "done"
          : "INVALID_INPUT" === route
            ? "invalid"
            : "approval";
}
export function routeLabel(route) {
  return (
    {
      APPROVAL_REQUIRED: "Approvazione richiesta",
      REVIEW_REQUIRED: "Revisione richiesta",
      BLOCKED: "Bloccato",
      STEP_UP_REQUIRED: "Verifica rafforzata richiesta",
      INVALID_INPUT: "Input non valido",
      ALREADY_EXECUTED: "Operazione completata",
      INFO: "Informativo",
    }[route] || route
  );
}
export function statusLabel(status) {
  return (
    {
      EXECUTED: "Eseguito",
      DUPLICATE: "Operazione gia eseguita",
      BLOCKED: "Bloccato",
      NO_DATA: "Dato non disponibile",
      NO_TOOL_NEEDED: "Nessun tool necessario",
    }[status] || status
  );
}
export function actionLabel(action) {
  return (
    {
      CUSTOMER_APPROVAL: "Approvazione cliente",
      REQUEST_MFA: "Richiedi MFA",
      CUSTOMER_REVIEW: "Revisione cliente",
      FIX_AMOUNT: "Correggi importo",
      REVIEW_CASHFLOW: "Rivedi cashflow",
      NO_ACTION: "Nessuna azione",
      none: "Nessuna",
    }[action] || action
  );
}
export function riskLabel(risk) {
  return { LOW: "BASSO", MEDIUM: "MEDIO", HIGH: "ALTO" }[risk] || risk;
}
export function riskAssessment(route) {
  return "APPROVAL_REQUIRED" === route
    ? { label: "LOW · Customer approval", className: "low" }
    : "STEP_UP_REQUIRED" === route
      ? { label: "HIGH · MFA required", className: "high" }
      : "REVIEW_REQUIRED" === route
        ? { label: "MEDIUM · Customer review", className: "medium" }
        : "BLOCKED" === route
          ? { label: "HIGH · Blocked by guardrail", className: "high" }
          : { label: "INFO · No execution", className: "medium" };
}
export const PROPOSAL_PENDING = "PROPOSAL_PENDING";
export const PROPOSAL_EXECUTED = "PROPOSAL_EXECUTED";
export function isExecutedState(currentProposal, lastTrace) {
  return Boolean(
    currentProposal?.already_executed ||
    ["EXECUTED", "DUPLICATE"].includes(lastTrace?.tool_result?.status),
  );
}
export function proposalUiState(currentProposal, lastTrace) {
  return ["APPROVAL_REQUIRED", "REVIEW_REQUIRED", "STEP_UP_REQUIRED"].includes(
    currentProposal?.route,
  )
    ? PROPOSAL_PENDING
    : isExecutedState(currentProposal, lastTrace)
      ? PROPOSAL_EXECUTED
      : PROPOSAL_PENDING;
}
export function executedTrace(currentProposal, lastTrace) {
  return ["EXECUTED", "DUPLICATE"].includes(lastTrace?.tool_result?.status)
    ? lastTrace
    : currentProposal?.executed_operation || null;
}
export function executedAmount(currentProposal, lastTrace) {
  const trace = executedTrace(currentProposal, lastTrace);
  return Number(
    void 0 !== trace?.tool_result?.amount
      ? trace.tool_result.amount
      : void 0 !== trace?.proposal?.amount
        ? trace.proposal.amount
        : currentProposal?.amount || 0,
  );
}
export function isExecutableMoneyMovement(actionType) {
  return ["TRANSFER", "TRANSFER_REVERSE"].includes(actionType);
}
export function moneyMovementSummary(proposal, eur) {
  return "TRANSFER_REVERSE" === proposal.action_type
    ? `Recupero liquidità: ${eur.format(proposal.amount)} dal fondo emergenze al conto corrente`
    : `Proposta una tantum: ${eur.format(proposal.amount)}`;
}
export function executedTransferCopy(proposal, eur) {
  return "TRANSFER_REVERSE" === proposal.action_type
    ? `${eur.format(proposal.amount)} ritirati dal fondo emergenze al conto corrente`
    : `${eur.format(proposal.amount)} spostati nel fondo emergenze`;
}
export async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) throw new Error(`API error ${response.status}`);
  return response.json();
}
