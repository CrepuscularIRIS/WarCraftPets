# WarCraftPets - World of Warcraft Pet Battle Engine

A battle simulation engine for World of Warcraft pet battles, implementing complete battle mechanics, pet stats, abilities, and effects.

## Features

### Pet System
- **Pet Stats**: Health, Power, Speed calculation
- **Breed System**: 10+ breed-based stat modifiers
- **Rarity Scaling**: Quality/rarity multipliers (rarity 1-6)
- **Level Progression**: Stats scale with level (1-25)
- **Pet Database**: 200+ pet species definitions

### Battle Core
- **Battle Loop**: Turn-based battle orchestration
- **Event System**: Publish/subscribe event bus
- **Action System**: USE_ABILITY, SWAP, PASS actions
- **Turn Manager**: Speed-based turn order
- **Team Management**: 3 pets per team

### Effect System (100+ Handlers)
- **Damage**: Direct damage, DoT, execute, lifesteal
- **Healing**: Direct heal, HoT, resurrection
- **Auras**: Buffs, debuffs, stacking, duration
- **States**: Stun, blind, dodge, etc.
- **Weather**: Environmental effects
- **Control**: Stun, freeze, root, etc.

## Quick Start

```bash
# Install dependencies
pip install -U pytest

# Run tests
pytest -q

# Run with verbose
pytest -v
```

## Architecture

```
WarCraftPets/
├── engine/
│   ├── core/           # Battle engine core
│   ├── effects/        # 100+ effect handlers
│   ├── model/          # Data models
│   ├── pets/           # Pet system
│   ├── resolver/       # Damage/healing pipelines
│   ├── constants/      # Type advantages, weather
│   └── data/           # Data access
├── data/               # JSON data files
└── test_pet_stats.py   # Test suite
```

## Test Results

```
============================= test session starts ==============================
test_pet_stats.py::TestProgressionDB::test_base_pet_stats_loaded PASSED  [  5%]
test_pet_stats.py::TestProgressionDB::test_breed_stats_loaded PASSED     [ 10%]
test_pet_stats.py::TestProgressionDB::test_compute_stats_high_rarity PASSED [ 15%]
test_pet_stats.py::TestProgressionDB::test_compute_stats_level_1 PASSED  [ 20%]
test_pet_stats.py::TestProgressionDB::test_compute_stats_level_25 PASSED [ 25%]
test_pet_stats.py::TestFormulaValidation::test_health_formula_validation PASSED [ 90%]
test_pet_stats.py::TestFormulaValidation::test_power_formula_validation PASSED [ 95%]
test_pet_stats.py::TestFormulaValidation::test_speed_formula_validation PASSED [100%]
============================== 20 passed in 0.10s ==============================
```

## License

MIT License
