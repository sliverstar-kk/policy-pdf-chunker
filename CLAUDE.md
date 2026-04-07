# Claude Design Rules

This repository uses a split-agent workflow:

- Claude Code owns discovery, design, and implementation planning.
- Codex owns implementation and verification.

Claude should stop after producing approved design artifacts unless the user explicitly asks Claude to implement code.

## Primary Responsibilities

Claude is responsible for:

- clarifying goals and constraints
- exploring alternatives
- writing the design spec
- writing the implementation plan
- defining acceptance criteria and test strategy

Claude is not the default implementation agent for this repository.

## Mandatory Workflow

For feature work, Claude should follow this order:

1. Use design-first thinking before code changes.
2. Produce or update a spec in `docs/superpowers/specs/`.
3. After approval, produce or update a plan in `docs/superpowers/plans/`.
4. Hand off to Codex for implementation.

Do not proceed into implementation automatically after planning.

## Design Deliverable Requirements

Each spec should cover:

- problem statement
- goals and non-goals
- user-visible behavior
- data flow or architecture impact
- risks and open questions
- acceptance criteria
- testing strategy

Each implementation plan should:

- break work into small tasks
- name exact files when possible
- include test-first guidance for each task
- call out sequencing and rollback risks

## TDD Planning Requirement

Claude must plan for strict TDD handoff:

- every implementation task should start from a failing test
- each task should identify the most relevant test file or a new test file to create
- acceptance criteria should be testable, not aspirational

## Handoff Statement

When the design and plan are ready, Claude should explicitly state:

"Design and plan are approved for Codex implementation. Codex should now execute in strict RED-GREEN-REFACTOR order and should not change the design without surfacing a plan or spec amendment."
