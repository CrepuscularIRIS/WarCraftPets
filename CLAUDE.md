# WarCraftPets CLAUDE.md

## Project Overview

WarCraftPets is a Python-based simulation engine for World of Warcraft pet battles. It implements battle mechanics, pet stats, abilities, and effects using an event-driven architecture.

## Development Stack

- **Language**: Python 3.11+
- **Testing**: pytest (20 tests passing)
- **Architecture**: Event-driven battle simulation

## Project Structure

```
WarCraftPets/
├── engine/               # Core engine modules
│   ├── core/            # Battle loop, events, actions
│   │   ├── battle_loop.py    # Main battle orchestration
│   │   ├── event_bus.py      # Publish/subscribe event system
│   │   ├── events.py         # Event definitions
│   │   ├── actions.py        # USE_ABILITY, SWAP, PASS actions
│   │   ├── executor.py       # Action execution
│   │   ├── scheduler.py      # Scheduled execution
│   │   ├── tick_engine.py    # Game tick processing
│   │   ├── team_manager.py   # Pet team management
│   │   ├── logs.py           # Battle logging
│   │   └── ability_executor.py
│   │
│   ├── effects/         # Effect system (100+ opcodes)
│   │   ├── dispatcher.py     # Routes effects to handlers
│   │   ├── registry.py       # Handler registration
│   │   ├── types.py          # Effect type definitions
│   │   ├── handlers/         # Individual effect handlers (100+)
│   │   └── semantic_registry.py
│   │
│   ├── model/           # Data models
│   │   ├── damage.py        # Damage calculations
│   │   ├── heal.py          # Healing calculations
│   │   └── aura.py          # Aura effects
│   │
│   ├── pets/            # Pet system
│   │   ├── pet_db.py        # Pet species database
│   │   ├── pet_factory.py   # Pet instance creation
│   │   ├── pet_instance.py  # Pet instance class
│   │   ├── pet_stats.py     # Stats calculation
│   │   ├── pet_manager.py   # Pet collection management
│   │   ├── progression.py   # Level/rarity progression
│   │   └── skill_math.py    # Skill damage formulas
│   │
│   ├── resolver/        # Battle resolvers
│   │   ├── damage_pipeline.py   # Damage calculation pipeline
│   │   ├── hitcheck.py          # Accuracy/miss calculations
│   │   ├── healing_pipeline.py  # Healing pipeline
│   │   ├── aura_manager.py      # Aura application/expiration
│   │   ├── cooldown.py          # Ability cooldowns
│   │   ├── state_manager.py     # Pet state management
│   │   ├── stats_resolver.py    # Stats resolution
│   │   ├── weather_manager.py   # Weather effects
│   │   ├── gate.py              # Gate conditions
│   │   └── racial_passives.py   # Racial passive abilities
│   │
│   ├── constants/       # Constants
│   │   ├── type_advantage.py    # Pet type advantages
│   │   └── weather.py           # Weather effects
│   │
│   └── data/            # Data access
│       └── script_db.py       # Script database
│
├── data/                # Configuration and data files
│   ├── petbattle_ability_pack.v1.*.jsonc
│   ├── opcode_semantics_overrides.template.jsonc
│   └── pack_builder_config.template.jsonc
│
├── test_pet_stats.py    # Main test suite (20 tests passing)
├── PET_*.md             # Documentation files
└── README.md            # Project documentation
```

## Key Components

### Battle System
- **BattleLoop**: Main battle orchestration - manages turn flow, pet selection, action execution
- **EventBus**: Publish/subscribe event system for loose coupling
- **Actions**: Three action types - USE_ABILITY, SWAP, PASS
- **TeamManager**: Manages pet teams (3 pets per team)

### Effect System
- **EffectDispatcher**: Routes effect rows to appropriate handlers
- **EffectRegistry**: Manages effect handler registration
- **100+ Effect Handlers**: Handle damage, healing, buffs, debuffs, state changes
- **Semantic Registry**: Loads effect semantics from JSON pack

### Pet System
- **PetStats**: Health, Power, Speed calculations based on level/rarity/breed
- **Progression**: Stat scaling tables for levels 1-25
- **PetDB**: Pet species definitions and properties
- **SkillMath**: Skill damage and healing formulas

### Resolver System
- **DamagePipeline**: Processes damage with mitigation, crit, etc.
- **HitCheck**: Calculates hit/miss based on accuracy
- **AuraManager**: Manages aura application, duration, stacking
- **Cooldown**: Tracks ability cooldowns
- **StateManager**: Manages pet states (stunned, etc.)

## Development Workflow

### Running Tests
```bash
pytest -q              # Quick test run
pytest -v              # Verbose output
pytest test_pet_stats.py  # Specific file
```

### Code Conventions

**Python:**
- `snake_case` for functions and variables
- `PascalCase` for classes
- Type hints required for public APIs
- Docstrings for public functions (Google style)

**Git:**
- Conventional commits: `type: description`
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
- Pull before push, rebase on main

### Adding New Features

1. Create feature branch from main
2. Implement changes following existing patterns
3. Add/update tests
4. Run `pytest -q` to verify
5. Commit with descriptive message
6. Push and create PR

### Adding New Effect Handlers

1. Create handler in `engine/effects/handlers/opXXXX_name.py`
2. Register handler in `EffectRegistry`
3. Add semantic definitions if needed
4. Add unit tests
5. Run tests to verify

## Testing Status

**Test Suite**: `test_pet_stats.py`
- **20 tests passing** (100% pass rate)
- Categories: Progression, Stats, Calculator, Properties, Formulas

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and test
pytest -q

# Commit
git add -A
git commit -m "feat: add new feature (issue-id)"

# Push
git push origin feature/new-feature
```

## Notes

- This is a simulation engine, not a game client
- Battle logic is based on WoW pet battle mechanics
- Effect system uses opcode-based handler pattern for extensibility
- Event-driven architecture enables modular and testable code
