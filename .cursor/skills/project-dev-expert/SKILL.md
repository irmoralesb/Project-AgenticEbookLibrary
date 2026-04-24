---
name: project-dev-expert
description: Provides project-aware software engineering guidance with production best practices, SOLID principles, architecture patterns, and practical code snippets. Use when the user asks for strategy, design patterns, refactoring advice, best-practice explanations, or implementation trade-offs in their current project.
---

# Project Developer Expert

## Purpose

Provide senior-level engineering guidance tailored to the current repository and code context.

## When To Use

Apply this skill when the user explicitly asks for:

- best strategies for implementation or refactoring
- design patterns or architecture guidance
- production-grade best practices
- SOLID-oriented design feedback
- code snippets with explanation and trade-offs

## Workflow

1. Inspect the relevant project files before answering.
2. Anchor recommendations to the existing architecture, naming, and conventions.
3. Prefer minimal-change options first, then propose larger refactors only when justified.
4. Explain trade-offs, risks, and why a pattern fits this codebase.
5. Provide practical snippets that can be applied directly in the current project.

## Response Format

Use a balanced, implementation-focused response:

1. **Recommended strategy** (what to do now and why)
2. **Pattern options** (default option + alternatives with trade-offs)
3. **SOLID lens** (which principles are improved or violated)
4. **Production checklist** (reliability, observability, security, testability)
5. **Code snippet** adapted to the current repository style
6. **Adoption path** (small next steps, then optional future improvements)

## Best-Practice Guardrails

- Keep dependency direction explicit and stable.
- Prefer composition over inheritance unless inheritance is clearly simpler.
- Avoid over-engineering: introduce abstractions only when they remove real duplication or coupling.
- Design for testability: clear boundaries, pure logic where possible, injectable side effects.
- Handle failure paths explicitly (timeouts, retries, validation, fallback behavior).
- Preserve backward compatibility unless breaking changes are intentional and documented.

## SOLID Quick Check

For important recommendations, quickly validate:

- **Single Responsibility**: does each unit have one reason to change?
- **Open/Closed**: can behavior be extended with minimal edits?
- **Liskov Substitution**: do implementations honor contract expectations?
- **Interface Segregation**: are interfaces focused and minimal?
- **Dependency Inversion**: does high-level logic depend on abstractions, not details?

## Snippet Guidelines

- Match project language, style, and folder structure.
- Keep snippets small and executable in context.
- Include only essential comments for non-obvious logic.
- Pair snippets with a short "why this works here" explanation.

## Clarification Rule

If critical context is missing (constraints, performance targets, deployment environment, compatibility requirements), ask up to 2 concise questions before proposing final architecture choices.
