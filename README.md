# WarCraftPets - WoW Pet Battle Engine

A simulation engine for World of Warcraft pet battles, implementing battle mechanics, pet stats, abilities, and effects.

## Quick Start

```bash
# Install dependencies
python -m pip install -U pytest

# Run tests
pytest -q

# Run with verbose output
pytest -v
```

---

## Feature Status Summary

### Overall Completion: ~85%

| Category | Completed | In Progress | Not Started |
|----------|-----------|-------------|-------------|
| Pet System | 7 | 0 | 0 |
| Battle Core | 7 | 0 | 0 |
| Effect System | 5 | 1 | 0 |
| Damage/Healing | 5 | 0 | 0 |
| Data Files | 4 | 0 | 0 |
| Testing | 6 | 0 | 0 |
| Advanced Features | 0 | 2 | 5 |
| Missing Components | 0 | 0 | 4 |

---

## ✅ Completed Features

### Pet System (7/7)
| Feature | Status | Description |
|---------|--------|-------------|
| Pet Stats | ✅ Done | Health, Power, Speed calculation |
| Breed Stats | ✅ Done | Breed-based stat modifiers (10+ breeds) |
| Rarity Multipliers | ✅ Done | Quality/rarity stat scaling (rarity 1-6) |
| Level Progression | ✅ Done | Stats scale with level (1-25) |
| Pet Database | ✅ Done | 200+ pet species definitions |
| Pet Factory | ✅ Done | Pet instance creation |
| Pet Manager | ✅ Done | Pet collection management |

### Battle Core (7/7)
| Feature | Status | Description |
|---------|--------|-------------|
| Battle Loop | ✅ Done | Main battle orchestration with turn flow |
| Event Bus | ✅ Done | Publish/subscribe event system |
| Action System | ✅ Done | USE_ABILITY, SWAP, PASS actions |
| Turn Manager | ✅ Done | Turn order and progression |
| Team Manager | ✅ Done | Pet team management (3 pets per team) |
| Scheduler | ✅ Done | Scheduled execution for delayed actions |
| Tick Engine | ✅ Done | Game tick processing |

### Effect System (5/6)
| Feature | Status | Description |
|---------|--------|-------------|
| Effect Dispatcher | ✅ Done | Routes effects to handlers |
| Effect Registry | ✅ Done | Handler registration and lookup |
| 100+ Effect Handlers | ✅ Done | Damage, healing, buffs, debuffs, states |
| State System | ✅ Done | Pet state management (stunned, etc.) |
| Aura System | ✅ Done | Aura application, duration, stacking |
| Complex Mechanics | 🚧 Partial | Some advanced mechanics pending |

### Damage & Healing (5/5)
| Feature | Status | Description |
|---------|--------|-------------|
| Damage Pipeline | ✅ Done | Damage calculation pipeline |
| Hit Check | ✅ Done | Accuracy/miss calculations |
| Healing Pipeline | ✅ Done | Healing calculation pipeline |
| Damage Types | ✅ Done | Physical, magical, etc. |
| Damage Formulas | ✅ Done | Standard damage formulas |

### Data Files (4/4)
| Feature | Status | Description |
|---------|--------|-------------|
| Pet Progression Tables | ✅ Done | Level/rarity stat tables |
| Pet Template | ✅ Done | Pet species definitions |
| Opcode Semantics | ✅ Done | Effect opcode definitions (JSON) |
| Ability Pack | ✅ Done | Ability data compilation |

### Testing (6/6)
| Feature | Status | Description |
|---------|--------|-------------|
| Pet Stats Tests | ✅ Done | 20 tests passing |
| Progression Tests | ✅ Done | Level/rarity calculations |
| Breed Tests | ✅ Done | Breed stat modifiers |
| Formula Validation | ✅ Done | Damage/heal formulas |
| Batch Calculations | ✅ Done | Multi-pet calculations |
| Quality Multipliers | ✅ Done | Rarity-based stats |

---

## 🚧 In Progress

### Battle Features (Planned)
| Feature | Status | Notes |
|---------|--------|-------|
| RL Policy Interface | 🚧 Planned | Reinforcement learning integration for AI battles |
| Scripted AI | 🚧 Planned | Pre-defined battle strategies |
| PvP Matchmaking | 🚧 Planned | Player vs player battles |

---

## ❌ Not Started

### Advanced Features (7)
| Feature | Status | Description |
|---------|--------|-------------|
| User Interface | ❌ Not Started | No GUI/web UI |
| Save/Load System | ❌ Not Started | Battle state persistence |
| Network Multiplayer | ❌ Not Started | Online battles |
| Achievement System | ❌ Not Started | Battle achievements |
| Pet Trading | ❌ Not Started | Trading system |
| Battle Replay | ❌ Not Started | Save/replay battles |
| Tutorial System | ❌ Not Started | Battle tutorials |

### Missing Components (4)
| Feature | Status | Description |
|---------|--------|-------------|
| Configuration File | ❌ Not Started | Engine config (INI/YAML) |
| CLI Interface | ❌ Not Started | Command-line launcher |
| Web API | ❌ Not Started | REST API for remote control |
| Database Backend | ❌ Not Started | Persistent pet storage |

---

## Architecture

```
WarCraftPets/
├── engine/
│   ├── core/           # Battle engine core
│   │   ├── battle_loop.py
│   │   ├── event_bus.py
│   │   ├── events.py
│   │   ├── actions.py
│   │   ├── executor.py
│   │   ├── scheduler.py
│   │   ├── tick_engine.py
│   │   ├── team_manager.py
│   │   ├── logs.py
│   │   └── ability_executor.py
│   │
│   ├── effects/        # Effect system (100+ handlers)
│   │   ├── dispatcher.py
│   │   ├── registry.py
│   │   ├── types.py
│   │   ├── handlers/   # 100+ effect handlers
│   │   │   ├── op0000_dmg_points_legacy.py
│   │   │   ├── op0024_dmg_points_std.py
│   │   │   ├── op0103_dmg_simple.py
│   │   │   ├── ... (100+ more)
│   │   └── semantic_registry.py
│   │
│   ├── model/          # Data models
│   │   ├── damage.py
│   │   ├── heal.py
│   │   └── aura.py
│   │
│   ├── pets/           # Pet system
│   │   ├── pet_db.py
│   │   ├── pet_factory.py
│   │   ├── pet_instance.py
│   │   ├── pet_stats.py
│   │   ├── pet_manager.py
│   │   ├── progression.py
│   │   └── skill_math.py
│   │
│   ├── resolver/       # Battle resolvers
│   │   ├── damage_pipeline.py
│   │   ├── hitcheck.py
│   │   ├── healing_pipeline.py
│   │   ├── aura_manager.py
│   │   ├── cooldown.py
│   │   ├── state_manager.py
│   │   ├── stats_resolver.py
│   │   ├── weather_manager.py
│   │   ├── gate.py
│   │   └── racial_passives.py
│   │
│   ├── constants/      # Constants
│   │   ├── type_advantage.py
│   │   └── weather.py
│   │
│   └── data/           # Data access
│       └── script_db.py
│
├── data/               # Data files
│   ├── petbattle_ability_pack.v1.SPEC.jsonc
│   ├── petbattle_ability_pack.v1.debug.jsonc
│   ├── opcode_semantics_overrides.template.jsonc
│   └── pack_builder_config.template.jsonc
│
├── test_pet_stats.py   # Test suite (20 tests passing)
└── README.md           # This file
```

---

## Test Results

```
============================= test session starts ==============================
test_pet_stats.py::TestProgressionDB::test_base_pet_stats_loaded PASSED  [  5%]
test_pet_stats.py::TestProgressionDB::test_breed_stats_loaded PASSED     [ 10%]
test_pet_stats.py::TestProgressionDB::test_compute_stats_high_rarity PASSED [ 15%]
test_pet_stats.py::TestProgressionDB::test_compute_stats_level_1 PASSED  [ 20%]
test_pet_stats.py::TestProgressionDB::test_compute_stats_level_25 PASSED [ 25%]
test_pet_stats.py::TestProgressionDB::test_missing_base_stats_raises_error PASSED [ 30%]
test_pet_stats.py::TestProgressionDB::test_missing_breed_raises_error PASSED [ 35%]
test_pet_stats.py::TestProgressionDB::test_missing_rarity_raises_error PASSED [ 40%]
test_pet_stats.py::TestProgressionDB::test_quality_multipliers_loaded PASSED [ 45%]
test_pet_stats.py::TestPetStatsCalculator::test_batch_calculate PASSED   [ 50%]
test_pet_stats.py::TestPetStatsCalculator::test_calculate_returns_pet_stats PASSED [ 55%]
test_pet_stats.py::TestPetStatsCalculator::test_calculate_skill_damages PASSED [ 60%]
test_pet_stats.py::TestPetStatsCalculator::test_skill_panel_damage PASSED [ 65%]
test_pet_stats.py::TestPetStatsCalculator::test_stats_increase_with_level PASSED [ 70%]
test_pet_stats.py::TestPetStatsCalculator::test_stats_increase_with_rarity PASSED [ 75%]
test_pet_stats.py::TestPetStatsCalculator::test_quality_multiplier_property PASSED [ 80%]
test_pet_stats.py::TestPetStatsCalculator::test_skill_duration_based_damage PASSED [ 85%]
test_pet_stats.py::TestFormulaValidation::test_health_formula_validation PASSED [ 90%]
test_pet_stats.py::TestFormulaValidation::test_power_formula_validation PASSED [ 95%]
test_pet_stats.py::TestFormulaValidation::test_speed_formula_validation PASSED [100%]

============================== 20 passed in 0.10s ==============================
```

---

## Effect Handlers Reference

The engine includes 100+ effect handlers for various battle mechanics:

### Damage Handlers (30+)
- `op0000`: Legacy damage points
- `op0024`: Standard damage points
- `op0103`: Simple damage
- `op0141`: Damage bonus if state
- `op0160`: Damage bonus if first
- ... and 25+ more

### Aura Handlers (20+)
- `op0026`: Aura apply duration
- `op0052`: Aura apply simple
- `op0054`: Aura apply stack limit
- `op0131`: Aura apply simple
- ... and 15+ more

### Healing Handlers (10+)
- `op0023`: Heal points with variance
- `op0053`: Heal percent of max HP
- `op0100`: Heal points variance override
- `op0061`: Heal self with state variance
- ... and 6+ more

### Utility Handlers (40+)
- `op0031`: Set state
- `op0080`: Weather set
- `op0107`: Force swap random
- `op0112`: Resurrect team dead
- ... and 35+ more

---

## Opcode Semantics Pack

The engine uses a semantic pack system for effect opcodes:

- `effect_properties_semantic.yml` - Human-oriented semantic catalog
- `effect_properties_semantic.json` - Runtime-loaded semantic pack (no YAML dependency)

**Runtime:**
- `engine/effects/semantic_registry.py` loads the JSON pack and normalizes handler args
- `engine/effects/dispatcher.py` distinguishes unknown opcodes from known-but-unimplemented opcodes

**Tools:**
```bash
python tools/compile_semantics.py  # Regenerate JSON from YAML
python tools/gen_missing_handlers.py --out engine/effects/handlers_generated  # Generate stubs
```

## Ability Pack (JSON)

This repository can also load periodic-aura scripts and aura meta directly from the generated **petbattle ability pack** (strict JSON).

- Runtime API: `ScriptDB.from_ability_pack_json("data/petbattle_ability_pack.v1.release.json")`
- The `*.debug.jsonc` variant is for humans (contains comments) and is not loaded by default.

---

## Development Agents

### ClaudeCode (Writer)
- Implements features and fixes bugs
- Runs tests before committing
- Follows code conventions

### Codex (Reviewer)
- Reviews code for logic errors
- Runs verification tests
- Documents issues and suggests fixes

### gt sling Commands
```bash
# Feature implementation by ClaudeCode
gt sling "implement damage multiplier" WarCraftPets --agent claude

# Code review by Codex
gt sling "review damage_pipeline.py" WarCraftPets --agent codex-review

# Testing by Codex
gt sling "run full test suite" WarCraftPets --agent codex-review
```

See `AGENTS.md` for full agent collaboration guidelines.

---

## License

This project is a simulation engine for educational and research purposes.
