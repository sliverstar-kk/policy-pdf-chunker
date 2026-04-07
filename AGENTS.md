# Codex Implementation Rules

This repository uses a split-agent workflow:

- Claude Code owns product clarification, design, and implementation planning.
- Codex owns implementation, tests, refactors, and verification.

Codex must follow these rules unless the user explicitly overrides them.

## Required Inputs Before Coding

Do not write production code until all of the following exist:

- An approved design spec under `docs/superpowers/specs/`
- An approved implementation plan under `docs/superpowers/plans/`
- A clear task slice from the current plan

If the design or plan is missing, stop and ask for the missing artifact instead of inventing one.

## TDD Contract

Codex implements with strict RED-GREEN-REFACTOR:

1. Write or update a failing test first.
2. Run the smallest relevant test and confirm it fails for the expected reason.
3. Write the minimal production code needed to pass.
4. Re-run the same test and confirm it passes.
5. Refactor only while keeping tests green.

Never add production code before the first failing test for that behavior.
Never silently weaken assertions just to make tests pass.

## Design Ownership

Codex must not silently rewrite the design contract.

- Treat the latest approved spec and plan as the source of truth.
- If implementation exposes a design issue, pause and report it.
- Propose a spec or plan amendment instead of freelancing a new design.

## Git and Worktree Flow

- Prefer isolated work on a feature branch or git worktree.
- Use `.worktrees/` for project-local worktrees when isolation is needed.
- Keep commits small and TDD-shaped when practical.
- Do not mix implementation with unrelated documentation rewrites.

Suggested branch prefixes:

- `claude/spec-*` for design branches
- `codex/impl-*` for implementation branches
- `integration/*` for merge and validation branches

## Handoff Expectations

When Codex starts implementation, read these artifacts first:

- `docs/ai-collaboration-playbook.md`
- the latest relevant file in `docs/superpowers/specs/`
- the latest relevant file in `docs/superpowers/plans/`

When Codex finishes a slice:

- summarize what was implemented
- list tests that were added or updated
- call out any design ambiguity discovered during implementation
