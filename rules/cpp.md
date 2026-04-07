# C++ Rules
# C++ Systems Engineering Rules

## 1. Safety & Undefined Behavior (UB)
- Memory Management: Avoid raw `new`, `delete`, `malloc`, `free`. Prefer RAII and standard smart pointers.
  If raw allocation is required (embedded, low-level, custom allocators, C/HAL interop), ownership and lifetime must be explicit and localized.
- RAII: All resources (memory, files, sockets, mutexes) must be managed via RAII.
- Initialization: All variables and class members must be initialized. Use constructor initializer lists. No uninitialized state.
- Casts: Use `static_cast`, `dynamic_cast`, or `reinterpret_cast` explicitly. No C-style casts.
- Undefined Behavior Awareness: Pointer arithmetic, aliasing, and lifetime rules must be carefully reviewed.
- No Junk Files: Do NOT generate temporary files (e.g., test.cpp, logs.txt) or build artifacts unless explicitly requested. Output core implementation only.

## 2. Concurrency & Performance
- Ownership & Lifetime: Object ownership and lifetime must be clear and documented. Avoid shared mutable state.
- Thread Safety: Protect shared mutable data with mutexes or atomics. Data races are unacceptable.
- Atomics: Specify memory ordering explicitly unless `memory_order_seq_cst` is clearly intended.
- Synchronization: Do not use sleep-based delays (`std::this_thread::sleep_for`) for coordination. Use condition variables, atomics, or proper signaling.
- Performance: Prefer algorithmic and architectural improvements over micro-optimizations. Measure before optimizing.

## 3. Architecture & Clean Code
- SOLID (Pragmatic): Apply SOLID principles where they improve changeability and clarity. Do not abstract prematurely.
- Polymorphism: Prefer value types and compile-time polymorphism (templates, concepts) when runtime polymorphism is unnecessary.
- Interfaces: When using runtime polymorphism, use abstract base classes with virtual destructors.
- Separation of Concerns: Isolate hardware access, low-level code, and platform-specific details from business logic.
- Naming: Intent-based naming. Names must reflect *why* the entity exists, not *how* it is implemented.
- Code Review Mode: Perform internal audit for UB risks, pointer misuse, ownership violations, and thread-safety before output.
- Minimal Comments: Comment only complex algorithms, invariants, or non-obvious design decisions. Avoid change logs and redundant explanations.

## 4. Modern C++ & Error Handling
- Language Level: Use modern C++ (C++17/20) features appropriately (e.g., structured bindings, `constexpr`, concepts where available).
- Error Handling: Exception usage must be explicit. Do not use exceptions for normal control flow.
  In low-level, embedded, or real-time code, prefer explicit error-return types (`std::optional`, `std::variant`, `expected`-like patterns).
- Nullability: Prefer `std::optional` or references over raw nullable pointers.

