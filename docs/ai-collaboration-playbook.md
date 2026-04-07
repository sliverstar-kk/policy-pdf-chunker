# Claude Code + Codex TDD Collaboration Playbook

This repository uses a two-agent workflow designed around design handoff and test-driven implementation.

## Role Split

- Claude Code: discovery, specification, implementation planning
- Codex: TDD implementation, test execution, refactor, verification

This separation is intentional. Claude is the design owner. Codex is the delivery owner.

## Standard Flow

1. Start a design branch such as `claude/spec-feature-name`.
2. Claude writes or updates the feature spec in `docs/superpowers/specs/`.
3. Claude writes or updates the implementation plan in `docs/superpowers/plans/`.
4. After approval, create an implementation branch such as `codex/impl-feature-name`.
5. Codex implements one planned slice at a time with strict TDD.
6. Merge into an `integration/feature-name` branch if cross-agent validation is needed.
7. Run project verification before merging to the main branch.

## Artifact Contract

Claude must produce these artifacts before Codex starts:

- Spec: problem, scope, acceptance criteria, constraints, test strategy
- Plan: ordered tasks, file targets, test-first approach, verification steps

Codex must consume those artifacts as binding inputs.

## TDD Rules

For every implementation slice:

1. Add a failing test first.
2. Confirm the test fails for the expected reason.
3. Implement the minimal code required to pass.
4. Re-run the targeted tests.
5. Refactor only with green tests.

If a slice cannot be expressed as a failing test first, the slice is probably too large and should be split.

## Change Control

Codex should not silently change design intent.

Allowed:

- implementation details that preserve the approved behavior
- small naming or structure improvements
- test-focused refactors

Not allowed without explicit amendment:

- changing scope
- changing user-visible behavior
- introducing new architecture not described in the spec
- deleting acceptance criteria because implementation is hard

## Branching Convention

- `claude/spec-*`: design and plan work
- `codex/impl-*`: code and tests
- `integration/*`: merge validation

## Suggested Handoff Prompt For Claude

Use Superpowers to brainstorm and write a design spec for this repository. Save the approved spec under `docs/superpowers/specs/` and the implementation plan under `docs/superpowers/plans/`. Plan explicitly for strict TDD. Stop after the plan is complete and do not implement production code.

## Suggested Handoff Prompt For Codex

Read `docs/ai-collaboration-playbook.md`, then read the latest approved spec and plan under `docs/superpowers/`. Implement only the next planned slice. Follow strict RED-GREEN-REFACTOR. Do not write production code before a failing test. If the spec is incomplete or contradictory, stop and surface an amendment request instead of guessing.
