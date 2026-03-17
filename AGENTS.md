# AGENTS.md — DDL / Anki Vector Integration

This document is intended for AI coding agents (e.g., OpenAI Codex) working in this repository.
It defines setup, constraints, workflow, safety rules, and quality expectations for the DDL / Anki Vector integration.

Agents must follow this document strictly.

---

## Agent Objectives

1. Implement and maintain the DDL / Anki Vector integration.
2. Keep changes minimal, isolated, and testable.
3. Prefer deterministic, explicit implementations over implicit or heuristic behavior.
4. Never fabricate missing technical details.

---

## No-Assumption Rule (Facts Only)

If required technical details are missing (API endpoints, protobuf fields, certificate paths, environment variables, ports, auth flows, firmware requirements, etc.), the agent MUST:

- Locate the information inside the repository (docs, source, CI config, comments), or
- Explicitly request clarification before implementing a dependent solution.

The agent must NOT:

- Invent API endpoints
- Invent protocol structures
- Guess authentication flows
- Assume certificate locations
- Assume firmware compatibility
- Introduce undocumented environment variables

If there is uncertainty, stop and request clarification.

---

## Repository Structure

(Adjust once the structure is finalized.)

- `custom_components/vector` — Core integration logic
- `tests/` — Unit and integration tests
- `docs/` — Protocol documentation, architecture notes
- `scripts/` — Development utilities, mostly for running Home Assistant tasks

If the repository becomes a monorepo, additional `AGENTS.md` files may exist in subdirectories with scoped instructions.

## External Module Repository

The Python communication module source code is maintained in:

- `/workspaces/pyddlvector`

From this workspace, the agent has access to work in that repository as well, including creating branches, making edits, committing, and pushing.

All module changes MUST be made in dedicated branches intended for merge (no direct commits to main/master), so full change tracking is preserved.

When testing integration changes in this repository that depend on in-progress `pyddlvector` module changes, the agent MUST update `custom_components/vector/manifest.json` to point to the specific `pyddlvector` branch being used for that test cycle.

## Reference Source (Ideas and Code)

The agent may use the following project as a technical reference for ideas and implementation patterns:

- https://github.com/kercre123/wire-pod

Reference use means:

- Compare protocol behavior and integration approaches
- Reuse concepts selectively where they improve quality and maintainability
- Validate assumptions against known working implementations

Reference use does NOT mean:

- Blind copying of architecture or legacy patterns
- Copying code without adapting it to Home Assistant standards and this repository's constraints
- Bypassing security, async, or quality requirements defined in this document

---

## Environment & Setup

The agent must use the exact versions defined in the project configuration files.

### Requirements

- OS: (Specify if restricted)
- Runtime: Python 3.13

## Vector Robot Integration Rules

Vector robots must be treated as external hardware systems.

The agent must:

- Avoid changes that require physical hardware validation unless:
  - Proper mocks are provided, or
  - A clear manual test plan is included.
- Ensure network calls include timeouts.
- Avoid infinite retry loops.
- Handle disconnections gracefully.

If certificates or tokens are required:

- Never commit them.
- Never log them in plaintext.
- Always load them from environment variables or a local secure store.
- Document required environment variables clearly.

---

## Logging & Error Handling

- Never log credentials, tokens, certificates, or sensitive identifiers.
- Prefer structured errors where applicable.
- Fail explicitly rather than silently ignoring errors.
- Surface actionable error messages.
- ALWAYS test for race conditions in relevant async/concurrent flows before considering a change complete.

---

## Code Standards

- Follow existing project formatting and naming conventions.
- Do not introduce large refactors in the same change as functional modifications unless explicitly requested.
- Keep commits small and focused.
- Avoid introducing new dependencies unless justified.
- Use `ruff` as formatter/linter in this repository.

## Home Assistant Compliance

The integration MUST comply with Home Assistant integration standards and developer guidelines.

The agent must:

- Follow Home Assistant architecture patterns for config entries, setup/unload flows, and platform forwarding.
- Implement entities according to Home Assistant entity model conventions (state, availability, device info, unique IDs, and naming).
- Use `DataUpdateCoordinator` where periodic or shared polling is required.
- Provide and maintain `config_flow`, diagnostics/repair handling (when relevant), and translations.
- Keep `manifest.json`, services, and supported features aligned with Home Assistant requirements.
- Ensure changes target and maintain at least Home Assistant Silver quality expectations, and move toward Gold where feasible.
- Add or update tests for behavior changes, especially setup, coordinator behavior, and entity state handling.

---

## Git Workflow

Branch naming convention:

```
feature/<name>
fix/<name>
refactor/<name>
```

Each PR must include:

- A clear description of changes
- Test strategy (automated or manual)
- Known limitations
- Any required configuration changes
- If the PR resolves an issue, include the text `Fixes #<issue-id>`

When a branch is merged it must also be deleted both local and remote, and changes merged to master must be pulled

---

## Security Constraints

The agent must NOT:

- Introduce telemetry without explicit approval
- Send robot or user data to third-party services
- Add undocumented network endpoints
- Bypass certificate validation
- Disable encryption for convenience

All cloud endpoints must be documented in `docs/`.

---

## When in Doubt

The agent must stop and request clarification regarding:

- Supported robot models
- Supported firmware versions
- Authentication flow
- API contract details
- CI expectations
- Required vs optional features

---

## Definition of Done

A change is considered complete when:

- All relevant tests pass locally and in CI
- New behavior is covered by tests (where feasible)
- Documentation is updated if configuration or API changes
- No secrets are committed
- Linting and formatting checks pass
- The implementation adheres strictly to the No-Assumption Rule
