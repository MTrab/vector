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

- `src/` — Core integration logic
- `tests/` — Unit and integration tests
- `docs/` — Protocol documentation, architecture notes
- `scripts/` — Development utilities
- `proto/` or `anki_vector/messaging/` — Protobuf definitions (if applicable)

If the repository becomes a monorepo, additional `AGENTS.md` files may exist in subdirectories with scoped instructions.

---

## Environment & Setup

The agent must use the exact versions defined in the project configuration files.

### Requirements

- OS: (Specify if restricted)
- Runtime: (e.g., Python X.Y / Node X / .NET X)
- Package manager: (pip / poetry / uv / npm / pnpm / etc.)
- Docker: `docker compose` (v2 syntax only)

### Install

```bash
<INSERT INSTALL COMMANDS>
```

### Run Locally

```bash
<INSERT RUN COMMANDS>
```

### Lint / Format

```bash
<INSERT LINT COMMANDS>
```

### Tests

Quick tests:

```bash
<INSERT TEST COMMAND>
```

Full test suite:

```bash
<INSERT TEST COMMAND>
```

CI-equivalent local check:

```bash
<INSERT COMMAND>
```

---

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

---

## Code Standards

- Follow existing project formatting and naming conventions.
- Do not introduce large refactors in the same change as functional modifications unless explicitly requested.
- Keep commits small and focused.
- Avoid introducing new dependencies unless justified.

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