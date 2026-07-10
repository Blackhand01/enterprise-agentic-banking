import { $, api, setHtml } from "./core.js";
import {
  addMessage,
  renderChatToolCard,
  renderDeepDive,
  renderFinancialRulesSettings,
  renderGoal,
  renderInitialChat,
  renderInsights,
  renderInspector,
  renderRejectedProposal,
  renderSandboxControls,
  renderSandboxResult,
  renderAgentInbox,
  renderCustomerResult,
  renderSupervisorCashflow,
  renderUser,
  updateSandboxButton,
  updateApproveButton,
} from "./components.js";
import {
  PROPOSAL_EXECUTED,
  isExecutableMoneyMovement,
  proposalUiState,
} from "./core.js";
export class BankingDashboardApp {
  constructor() {
    ((this.state = null),
      (this.currentProposal = null),
      (this.lastTrace = null),
      (this.inspectorOpen = !1),
      (this.deepDiveOpen = !1),
      (this.insightsOpen = !1),
      (this.chatOpen = !1),
      (this.activeInspectorTab = "context"),
      (this.actionInboxOpen = !1),
      (this.explainabilityOpen = !1),
      (this.impactOpen = !1),
      (this.amountPreviewTimer = null),
      (this.transferInFlight = !1),
      (this.sandboxInFlight = !1));
  }
  async start() {
    (this.exposeGlobalHandlers(), this.bindDomEvents(), await this.loadState());
  }
  async loadState() {
    ((this.state = await api("/api/state")),
      (this.currentProposal = this.state.proposal),
      this.renderAll());
  }
  renderAll() {
    (renderUser(this.state),
      renderGoal(this.state),
      renderFinancialRulesSettings(this.currentProposal),
      renderSandboxControls(this.context()),
      renderSupervisorCashflow(this.context()),
      renderAgentInbox(this.context()),
      this.updateApproveButton(),
      renderDeepDive(this.context()),
      renderInsights(this.context()),
      this.renderChatDrawer(),
      renderInspector(this.context()),
      renderInitialChat());
  }
  clearTransientResults() {
    (renderCustomerResult(null), renderSandboxResult(null));
  }
  context() {
    return {
      state: this.state,
      currentProposal: this.currentProposal,
      lastTrace: this.lastTrace,
      inspectorOpen: this.inspectorOpen,
      deepDiveOpen: this.deepDiveOpen,
      insightsOpen: this.insightsOpen,
      chatOpen: this.chatOpen,
      activeInspectorTab: this.activeInspectorTab,
      actionInboxOpen: this.actionInboxOpen,
      explainabilityOpen: this.explainabilityOpen,
      impactOpen: this.impactOpen,
      transferInFlight: this.transferInFlight,
      sandboxInFlight: this.sandboxInFlight,
      findAccount: (name) => this.findAccount(name),
    };
  }
  findAccount(name) {
    return this.state.accounts.find((account) => account.name === name);
  }
  currentProposalUiState() {
    return proposalUiState(this.currentProposal, this.lastTrace);
  }
  async syncAmountPreview() {
    if (this.currentProposalUiState() === PROPOSAL_EXECUTED) return;
    const input = $("amount-input");
    if (!input) return;
    const amount = Number(input.value);
    if (!Number.isFinite(amount)) return;
    const result = await api("/api/preview-transfer", {
      method: "POST",
      body: JSON.stringify({ amount: amount }),
    });
    ((this.currentProposal = result.proposal),
      (this.lastTrace = null),
      renderAgentInbox(this.context()),
      this.updateApproveButton(),
      renderSupervisorCashflow(this.context()),
      renderDeepDive(this.context()),
      renderInsights(this.context()),
      renderCustomerResult(null),
      renderInspector(this.context()));
  }
  scheduleAmountPreview() {
    (window.clearTimeout(this.amountPreviewTimer),
      (this.amountPreviewTimer = window.setTimeout(
        () => this.syncAmountPreview(),
        350,
      )));
  }
  async approveTransfer() {
    if (
      this.transferInFlight ||
      this.currentProposalUiState() === PROPOSAL_EXECUTED ||
      this.currentProposal.already_executed ||
      !isExecutableMoneyMovement(this.currentProposal.action_type) ||
      ["BLOCKED", "INVALID_INPUT"].includes(this.currentProposal.route)
    )
      return;
    ((this.transferInFlight = !0), this.updateApproveButton());
    const amount = Number($("amount-input").value);
    try {
      const trace = await api("/api/submit-transfer", {
        method: "POST",
        body: JSON.stringify({
          amount: amount,
          action_type: this.currentProposal.action_type,
        }),
      });
      ((this.lastTrace = trace),
        "EXECUTED" === trace.tool_result.status ||
        "DUPLICATE" === trace.tool_result.status
          ? ((this.state = await api("/api/state")),
            (this.currentProposal = this.state.proposal),
            (this.actionInboxOpen = !0),
            this.renderAll())
          : (this.state.audit = [
              trace,
              ...this.state.audit.filter(
                (item) => item.trace_id !== trace.trace_id,
              ),
            ]),
        this.shouldShowExecutionResult(trace)
          ? renderCustomerResult(trace)
          : renderCustomerResult(null),
        renderInspector(this.context()));
    } finally {
      ((this.transferInFlight = !1), this.updateApproveButton());
    }
  }
  shouldShowExecutionResult(trace) {
    if (
      !trace ||
      !["EXECUTED", "DUPLICATE"].includes(trace.tool_result?.status)
    )
      return !0;
    const traceProposalId = trace.proposal?.proposal_id,
      currentProposalId = this.currentProposal?.proposal_id,
      currentTraceId = this.currentProposal?.executed_operation?.trace_id;
    return (
      Boolean(traceProposalId && traceProposalId === currentProposalId) ||
      currentTraceId === trace.trace_id
    );
  }
  async applySandboxState() {
    if (this.sandboxInFlight) return;
    const checkingBalance = Number($("sandbox-checking-balance")?.value),
      emergencyBalance = Number($("sandbox-emergency-balance")?.value),
      upcomingExpenses = Number($("sandbox-upcoming-expenses")?.value);
    if (
      !Number.isFinite(checkingBalance) ||
      !Number.isFinite(emergencyBalance) ||
      !Number.isFinite(upcomingExpenses) ||
      checkingBalance < 0 ||
      emergencyBalance < 0 ||
      upcomingExpenses < 0
    )
      renderSandboxResult({
        status: "ERROR",
        reason: "Enter only numeric values greater than or equal to zero.",
      });
    else {
      ((this.sandboxInFlight = !0), updateSandboxButton(this.sandboxInFlight));
      try {
        const result = await api("/api/sandbox/inject-state", {
          method: "POST",
          body: JSON.stringify({
            checking_balance: checkingBalance,
            emergency_balance: emergencyBalance,
            upcoming_expenses: upcomingExpenses,
          }),
        });
        ((this.state = result.state),
          (this.currentProposal = this.state.proposal),
          (this.lastTrace = null),
          (this.actionInboxOpen = !1),
          this.renderAll(),
          renderCustomerResult(null),
          renderSandboxResult(result.mutation),
          renderInspector(this.context()));
      } finally {
        ((this.sandboxInFlight = !1),
          updateSandboxButton(this.sandboxInFlight));
      }
    }
  }
  async saveRiskLimit() {
    const input = $("risk-limit-input");
    if (!input) return;
    const limit = Number(input.value);
    if (!Number.isFinite(limit) || limit <= 0) return;
    const result = await api("/api/financial-rules", {
      method: "POST",
      body: JSON.stringify({ autonomous_transfer_limit_eur: limit }),
    });
    ((this.state = result.state),
      (this.currentProposal = this.state.proposal),
      (this.lastTrace = null),
      (this.actionInboxOpen = !1),
      this.renderAll(),
      this.clearTransientResults());
  }
  async askChat(prompt) {
    const message = (prompt || $("chat-input").value).trim();
    if (!message) return;
    (($("chat-input").value = message), addMessage("user", message));
    const result = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: message }),
    });
    (addMessage("assistant", result.answer),
      renderChatToolCard(result.tool_result));
  }
  rejectProposal() {
    this.currentProposalUiState() !== PROPOSAL_EXECUTED &&
      ((this.lastTrace = null),
      renderRejectedProposal(),
      renderInspector(this.context()));
  }
  toggleInspector(force) {
    ((this.inspectorOpen =
      "boolean" == typeof force ? force : !this.inspectorOpen),
      this.inspectorOpen && (this.chatOpen = !1),
      this.renderChatDrawer(),
      renderInspector(this.context()));
  }
  toggleDeepDive(force) {
    ((this.deepDiveOpen =
      "boolean" == typeof force ? force : !this.deepDiveOpen),
      this.deepDiveOpen && (this.insightsOpen = !1),
      renderDeepDive(this.context()),
      renderInsights(this.context()));
  }
  toggleInsights(force) {
    ((this.insightsOpen =
      "boolean" == typeof force ? force : !this.insightsOpen),
      this.insightsOpen && (this.deepDiveOpen = !1),
      renderDeepDive(this.context()),
      renderInsights(this.context()));
  }
  toggleChat(force) {
    ((this.chatOpen = "boolean" == typeof force ? force : !this.chatOpen),
      this.chatOpen && (this.inspectorOpen = !1),
      this.renderChatDrawer(),
      renderInspector(this.context()));
  }
  renderChatDrawer() {
    const drawer = $("chat-drawer"),
      toggle = $("chat-toggle");
    (drawer &&
      (drawer.classList.toggle("open", this.chatOpen),
      drawer.setAttribute("aria-hidden", this.chatOpen ? "false" : "true")),
      toggle &&
        ((toggle.textContent = "Chat"),
        toggle.setAttribute("aria-expanded", String(this.chatOpen))));
  }
  toggleActionInbox() {
    const nextOpen =
      this.currentProposalUiState() === PROPOSAL_EXECUTED ||
      !this.actionInboxOpen;
    (this.currentProposalUiState() === PROPOSAL_EXECUTED
      ? (this.actionInboxOpen = !0)
      : (this.actionInboxOpen = nextOpen),
      nextOpen && ((this.explainabilityOpen = !1), (this.impactOpen = !1)),
      renderAgentInbox(this.context()),
      this.updateApproveButton(),
      renderCustomerResult(null));
  }
  toggleExplainabilityPanel() {
    ((this.explainabilityOpen = !this.explainabilityOpen),
      renderAgentInbox(this.context()),
      this.updateApproveButton());
  }
  toggleImpactPanel() {
    ((this.impactOpen = !this.impactOpen),
      renderAgentInbox(this.context()),
      this.updateApproveButton());
  }
  switchInspectorTab(tabName) {
    ((this.activeInspectorTab = tabName), renderInspector(this.context()));
  }
  updateApproveButton() {
    updateApproveButton(this.context());
  }
  bindDomEvents() {
    ($("deep-dive-toggle").addEventListener("click", () =>
      this.toggleDeepDive(),
    ),
      $("deep-dive-close").addEventListener("click", () =>
        this.toggleDeepDive(!1),
      ),
      $("insights-toggle").addEventListener("click", () =>
        this.toggleInsights(),
      ),
      $("insights-close").addEventListener("click", () =>
        this.toggleInsights(!1),
      ),
      $("chat-toggle").addEventListener("click", () => this.toggleChat()),
      $("chat-close").addEventListener("click", () => this.toggleChat(!1)),
      $("chat-button").addEventListener("click", () => this.askChat()),
      $("chat-input").addEventListener("keydown", (event) => {
        "Enter" === event.key && this.askChat();
      }),
      $("sandbox-toggle").addEventListener("click", () =>
        this.toggleInspector(),
      ),
      $("sandbox-close").addEventListener("click", () =>
        this.toggleInspector(!1),
      ),
      [
        $("sandbox-checking-balance"),
        $("sandbox-emergency-balance"),
        $("sandbox-upcoming-expenses"),
      ].forEach((input) => {
        input?.addEventListener("input", () => renderSandboxResult(null));
      }),
      $("financial-rules-settings")?.addEventListener("input", () =>
        renderSandboxResult(null),
      ),
      document.querySelectorAll(".quick-prompt").forEach((button) => {
        button.addEventListener("click", () =>
          this.askChat(button.dataset.prompt),
        );
      }),
      $("sandbox-apply-button")?.addEventListener("click", () =>
        this.applySandboxState(),
      ));
  }
  exposeGlobalHandlers() {
    ((window.scheduleAmountPreview = () => this.scheduleAmountPreview()),
      (window.approveTransfer = () => this.approveTransfer()),
      (window.rejectProposal = () => this.rejectProposal()),
      (window.toggleActionInbox = () => this.toggleActionInbox()),
      (window.toggleExplainabilityPanel = () =>
        this.toggleExplainabilityPanel()),
      (window.toggleImpactPanel = () => this.toggleImpactPanel()),
      (window.saveRiskLimit = () => this.saveRiskLimit()),
      (window.__tcsBankingApp = this));
  }
}
export async function bootstrap() {
  const app = new BankingDashboardApp();
  return (await app.start(), app);
}
bootstrap().catch((error) => {
  document.body.innerHTML = `<pre>Unable to load the prototype: ${error.message}</pre>`;
});
