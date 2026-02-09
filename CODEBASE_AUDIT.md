# JAO Codebase Audit (Quick Technical Review)

## 1) Current architecture snapshot

- Entry point is `project/main.py`: initializes pygame, runs title screen, then enters `menu -> game` loop.
- `project/game.py` acts as a central orchestrator and currently contains multiple responsibilities: game loop, camera/world transforms, combat interactions, effects, and rendering coordination.
- `project/menu.py` stores both menu state machine logic and portions of rendering behavior, with partial renderer extraction already started.
- Subsystems exist and are partially modularized:
  - `project/model/*` for physics/gravity/collisions.
  - `project/entities/*` for gameplay entities.
  - `project/ships/*` for ship classes and registry.
  - `project/view/*` for rendering helpers.

## 2) Key risks / technical debt

1. **Oversized game coordinator (`game.py`)**
   - High cognitive load and harder debugging.
   - Changes in one feature can accidentally break another due to broad coupling.

2. **Mixed import styles / module paths**
   - The code mixes `from menu import ...`, `from config import ...`, and `from project...` styles.
   - This can break depending on launch cwd / IDE / PYTHONPATH.

3. **Menu logic and rendering still partially coupled**
   - Refactoring has started, but rendering extraction is incomplete.
   - Slows down UI iteration and makes testing menu decisions harder.

4. **Sparse guardrails for regressions**
   - No visible automated behavior tests around key game state transitions.
   - Runtime-only verification increases risk during refactors.

## 3) Practical refactor plan (safe incremental)

### Step A — Normalize imports (low-risk, high ROI)
- Pick one strategy and apply consistently, preferably package-qualified imports (e.g. `from project.menu import ...`) where feasible.
- Add a small run guide in README (launch command + expected cwd).

### Step B — Split `game.py` by responsibility
- Extract in order:
  1. `game_state.py` (state containers/timers/counters),
  2. `game_update.py` (input + simulation updates),
  3. `game_combat.py` (projectiles, collisions, deaths),
  4. `game_render.py` (draw pipeline).
- Keep `Game` class as façade that delegates.

### Step C — Finish menu renderer migration
- Move drawing primitives out of `menu.py` into view renderer module.
- Keep pure state transition logic in `menu.py` so behavior is testable without pygame surfaces.

### Step D — Add lightweight regression checks
- Keep existing compile check and add smoke checks for importability and key object construction.
- Add minimal deterministic tests for utility math (`wrap_delta`, bearing/angle helpers).

### Step E — Stabilize launch/runtime contract
- Add one canonical startup command and expected directory.
- Document required assets paths and fallback behavior for missing files.

## 4) Suggested immediate next task

Start with **Step A (import normalization)** for these files first:
- `project/main.py`
- `project/stars.py`
- `project/menu.py`

This gives quick stability gains with minimal gameplay risk, then proceed to `game.py` extraction.

## 5) Validation run performed

- `python -m py_compile project/*.py project/entities/*.py project/model/*.py project/ships/*.py project/view/*.py`
  - Result: passed in current environment.
