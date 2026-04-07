# Python Rules

# Engineering & Architecture Rules (Python / JS / Universal)

## 1. Anti-Hallucination & Quality
- Do NOT invent libraries, APIs, or behaviors. Use only existing, documented features.
- If uncertain about requirements or behavior, ask for clarification. Never guess.
- Explicit Self-Check: Before output, verify correctness, naming clarity, SRP, and alignment with these rules. If a tradeoff is made, state it explicitly.
- Naming: Intent-based names only. Avoid generic names (`data`, `manager`, `utils`). Booleans must read as questions (`is_valid`, `has_access`).
- No Junk Files: Do NOT create auxiliary or temporary files (.md, .txt, test.py, etc.) unless explicitly requested. Output only core, relevant code.
- Minimal Comments: Comment only non-obvious logic or architectural decisions. Avoid trivial explanations and version history notes. Prefer self-descriptive names.

## 2. Architecture (Structure & Domain Purity)
- Prefer layered separation (Domain / Application / Infrastructure) when business logic is non-trivial or expected to evolve.
- Domain Purity: Domain logic must not depend on frameworks, databases, or external services. Use pure language constructs (e.g., dataclasses in Python).
- Business logic must be framework-agnostic and testable without infrastructure.
- SOLID & Loose Coupling: Use dependency injection where it improves changeability. Do not abstract prematurely.

## 3. Production Hardening
- No Hidden Side Effects: Functions must not mutate global state.
- Explicit Dependencies: Avoid imports inside functions unless justified (performance, optional dependencies, or circular dependency). If used, explain why.
- No mutable default arguments.
- Logging: Use the standard logging system. Never use print for runtime behavior.
- Time Handling: Always use timezone-aware datetime objects.
- Fail-Fast: Validate inputs early and explicitly. Use schema validation (e.g., Pydantic) only at system boundaries (API / Infrastructure).
- Stability Without Hacks: Do not use artificial delays (e.g., sleep) for “stability”. Prefer correct async handling, retries, or proper design.

## 4. Async & Concurrency
- Do not mix synchronous I/O inside async flows.
- CPU-bound work must be delegated to executors or worker processes.
- Shared mutable state must be avoided; prefer immutability.
- If forced to mix sync and async due to external library constraints, isolate and document the boundary explicitly.

## 5. Simplicity & Technical Debt
- Prefer the simplest solution that satisfies current requirements (KISS, YAGNI).
- Technical debt is acceptable if it is explicit, localized, and understood.
- Do not introduce architectural complexity without a clear, present need.

