# Development-v1 Salvage Map

This document maps what can be reused from `development-v1` and what should be rebuilt in the new clean branch.

## Decision Summary

- Do not merge `development-v1` into the new branch.
- Rebuild core integration architecture from scratch on top of current Home Assistant standards.
- Selectively copy small, low-risk assets and constants from `development-v1`.
- Move robot communication and protobuf ownership to a separate PyPI module.

## Reuse Candidates

These are good candidates for direct reuse or near-direct reuse:

- `custom_components/vector/assets/vector_sleep.png`
- `custom_components/vector/assets/vector_unknown.png`
- `custom_components/vector/translations/en.json` (review and align keys with new entities)
- Dataset content in `Datasets/*.json` (if feature remains in scope)
- High-level product text from `README.md` and docs (rewrite structure, keep factual content)

## Reuse With Refactor

These can be used as references, but require cleanup and redesign:

- `custom_components/vector/const.py`
  - Keep domain/state naming intent, fix naming typos, remove duplicates.
- `custom_components/vector/mappings.py`
  - Keep concept, verify every mapping against real SDK/module outputs.
- `custom_components/vector/helpers/states.py`
  - Keep state container idea, rewrite API for clarity and HA entity compatibility.
- `custom_components/vector/helpers/cubes.py`
  - Keep cube model idea, rewrite around coordinator lifecycle and entity registry.

## Rebuild From Scratch

These currently violate HA standards or have high bug risk:

- `custom_components/vector/manifest.json`
  - Replace VCS dependency (`git+https`) with PyPI dependency.
- `custom_components/vector/__init__.py`
  - Rebuild entry setup/unload lifecycle and service registration guards.
- `custom_components/vector/config_flow.py`
  - Rebuild validation flow, errors, unique IDs, and discovery handling.
- `custom_components/vector/coordinator.py`
  - Remove blocking `.result(timeout=...)` calls, eliminate broad exceptions, redesign update/event model.
- `custom_components/vector/services.py`
  - Implement real target resolution and action execution.
- `custom_components/vector/vector_setup.py`
  - Move to separate communication module; avoid direct auth/cert protocol logic in HA integration.
- `custom_components/vector/helpers/connection.py`
  - Move robot control logic to communication module; keep HA side thin.

## Key Risks Found in development-v1

- Blocking synchronous calls inside async paths.
- Broad `except:` usage hiding errors.
- Duplicate entity definitions (`dock_charger` appears twice in buttons).
- Typo/consistency issues (`CHARGNING` naming).
- Service handler is currently incomplete.
- Dependency strategy is not HA-compliant (`git+https` in manifest).

## Target Architecture (New Branch)

- HA custom integration package contains:
  - config flow
  - coordinator
  - entities (binary_sensor, sensor, button, optional camera)
  - services
  - diagnostics/repairs as needed
- External PyPI module contains:
  - protobuf files and generated code
  - robot connection/auth/session handling
  - command/event client API used by HA integration

## Execution Plan

1. Scaffold a minimal HA-compliant integration skeleton.
2. Add config flow + entry setup/unload + manifest aligned with HA requirements.
3. Implement communication adapter interface against the PyPI module.
4. Implement coordinator (non-blocking) and basic health/battery entities.
5. Add button/services features incrementally.
6. Add tests for config flow, coordinator, and core entities.
7. Import low-risk assets/translations/datasets selectively.

## Definition of "Salvaged"

A component is only considered salvaged if:

- It is copied with explicit provenance from `development-v1`,
- It passes lint/type checks,
- It has tests for changed behavior,
- It satisfies Home Assistant integration standards.
