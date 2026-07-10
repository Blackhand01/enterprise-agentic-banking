# Part C - Process and Decisions

## Strategy

I treated the exercise as an architectural prototype for banking engineering leads and business stakeholders. I did not try to simulate every banking product. I chose one narrow flow: after salary arrives, the agent proposes moving idle liquidity to `Emergency_Fund`.

That flow was enough to show the important boundary: the model can reason, retrieve context, and explain a recommendation, but deterministic systems must authorize and execute any action on money.

## Tools and AI Assistance

I used Python + FastAPI for a small backend with clear service boundaries, static HTML/CSS/JavaScript to avoid a frontend build step, SQLite with JSON seed data for repeatable banking state, Pydantic for typed API and tool contracts, Mermaid and Pandoc for documentation, and OpenAI-compatible tool calling so the assistant can use a real model when configured.

AI assistance helped with bounded tasks: mock data, scaffolding, UI copy, refactoring, and smoke-test coverage. I did not delegate safety decisions to AI. Amount validation, active-policy filtering, route decisions, idempotency, and execution results are implemented in code.

## Main Decisions

I kept the prototype to one agent. A production system can split planning, retrieval, policy, execution, and oversight into specialized services, but in five days the important proof was the AI-to-ledger boundary.

Guardrails are deterministic. The model can explain why an action is blocked or approval-gated, but it cannot reinterpret a blocked action as success. Current numbers come from SQLite read models; policy text comes from the active policy catalog. In production, that maps to bank APIs for facts and document retrieval for policy knowledge.

The UI shows customer value first: proposal, impact, approval, and outcome. The technical inspection panel is included because agentic banking also needs operator trust.

## Production Next Step

I left out real login, core-banking writes, real MFA tokens, shared-account approval, WORM audit storage, cloud deployment, and a full evaluation pipeline.

For production, I would start with read-only cash-flow insights and savings recommendations, then add approval-gated internal transfers to trusted destinations. More autonomous reversible actions should come only after shadow mode, evals, monitoring, and clear audit.

The success criterion is simple: the agent does not invent financial facts, cannot move money beyond deterministic controls, and has a credible path from prototype to regulated product.
