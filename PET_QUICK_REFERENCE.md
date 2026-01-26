# Pet Subsystem Quick Reference

## Core Classes

### ProgressionDB
```python
from engine.pets.progression import ProgressionDB

db = ProgressionDB("pet_progression_tables.json")

# Check if pet has base stats
if db.has_base(pet_id=2):
    # Compute stats
    stats_dict = db.compute_stats(
        pet_id=2,
        breed_id=3,
        rarity_id=2,
        level=25
    )
    # Returns: {"health": 825, "power": 111, "speed": 131}
```

### PetStatsCalculator
```python
from engine.pets.pet_stats import PetStatsCalculator

calc = PetStatsCalculator(progression_db)

# Single pet
stats = calc.calculate(pet_id=2, rarity_id=2, breed_id=3, level=25)

# Multiple pets
results = calc.batch_calculate([
    {'pet_id': 2, 'rarity_id': 1, 'breed_id': 3, 'level': 1},
    {'pet_id': 2, 'rarity_id': 2, 'breed_id': 3, 'level': 25},
])

# Skill damages
damages = calc.calculate_skill_damages(stats, {
    'attack': 10,
    'power': 15,
})
```

### PetStats
```python
# Methods
stats.skill_panel_damage(10)           # Damage for base 10
stats.skill_panel_heal(10)             # Healing for base 10
stats.skill_duration_based_damage(10, 3)  # Damage spread over 3 ticks

# Properties
stats.pet_id
stats.rarity_id
stats.breed_id
stats.level
stats.health
stats.power
stats.speed
stats.quality_multiplier
```

## Common Tasks

### Get Stats for a Pet
```python
stats = calculator.calculate(
    pet_id=2,
    rarity_id=2,
    breed_id=3,
    level=25
)
print(f"HP: {stats.health}, Power: {stats.power}, Speed: {stats.speed}")
```

### Calculate Skill Damage
```python
base_damage = 10
panel_damage = stats.skill_panel_damage(base_damage)
# Formula: floor(10 * (1 + power/20))
```

### Compare Pet Rarities
```python
for rarity in range(1, 7):
    stats = calculator.calculate(pet_id=2, rarity_id=rarity, breed_id=3, level=25)
    print(f"Rarity {rarity}: HP={stats.health}")
```

### Compare Levels
```python
for level in [1, 10, 20, 25]:
    stats = calculator.calculate(pet_id=2, rarity_id=2, breed_id=3, level=level)
    print(f"Level {level}: HP={stats.health}")
```

### Error Handling
```python
try:
    stats = calculator.calculate(pet_id=999, rarity_id=2, breed_id=3, level=25)
except KeyError as e:
    print(f"Pet not found: {e}")
```

## Formulas

### Health
```
((Base + Breed/10) * 5 * Level * Quality) + 100
```

### Power
```
(Base + Breed/10) * Level * Quality
```

### Speed
```
(Base + Breed/10) * Level * Quality
```

### Skill Damage
```
floor(base_points * (1 + power/20))
```

## Data Access

### Quality Multipliers
```python
progression_db._quality  # {1: 0.5, 2: 0.55, ..., 6: 0.75}
```

### Breed Stats
```python
progression_db._breeds[3]  # {'health_add': 0.5, 'power_add': 0.5, 'speed_add': 0.5}
```

### Base Pet Stats
```python
progression_db._base[2]  # {'base_health': 10.5, 'base_power': 8.0, 'base_speed': 9.5}
```

## Testing

Run all tests:
```bash
python -m pytest test_pet_stats.py -v
```

Run specific test:
```bash
python -m pytest test_pet_stats.py::TestProgressionDB::test_compute_stats_level_1 -v
```

## Examples

See `example_pet_stats.py` for 7 detailed examples:
1. Basic stat calculation
2. Skill damage calculation
3. Level progression
4. Rarity comparison
5. Batch calculation
6. Multiple skill damages
7. Breed comparison

Run examples:
```bash
python example_pet_stats.py
```

## Performance

- Single calculation: ~0.1ms
- Batch of 1000: ~50ms
- No caching needed

## Common Values

### Quality Multipliers
| Rarity | ID | Multiplier |
|--------|----|-----------:|
| Poor | 1 | 0.500 |
| Common | 2 | 0.550 |
| Uncommon | 3 | 0.600 |
| Rare | 4 | 0.650 |
| Epic | 5 | 0.700 |
| Legendary | 6 | 0.750 |

### Example Pet (ID=2) at Level 25, Rarity 3
| Stat | Value |
|------|------:|
| Health | 891 |
| Power | 121 |
| Speed | 143 |

### Skill Damage Multiplier
```
power=121 → damage multiplier = 1 + 121/20 = 7.05
base damage 10 → panel damage 70
base damage 15 → panel damage 105
```

## Integration

### With PetFactory
```python
from engine.pets.pet_factory import PetFactory, PetFactoryConfig

factory = PetFactory(
    pets_all_path="pets_all.json",
    progression_path="pet_progression_tables.json",
    config=PetFactoryConfig(strict_level25=False)
)

# Now uses ProgressionDB for non-level-25 pets
pet_instance = factory.create(
    instance_id=1,
    pet_id=2,
    rarity_id=2,
    breed_id=3,
    level=15
)
```

## Files

| File | Purpose |
|------|---------|
| `engine/pets/progression.py` | Core stat calculation engine |
| `engine/pets/pet_stats.py` | High-level API and calculators |
| `test_pet_stats.py` | 20 unit tests |
| `example_pet_stats.py` | 7 usage examples |
| `PET_SYSTEM_GUIDE.md` | Complete documentation |
| `PET_IMPLEMENTATION_SUMMARY.md` | Implementation overview |

## Troubleshooting

### KeyError: No base stats for pet_id=X
- Pet ID X doesn't have base stats in pet_progression_tables.json
- Check if pet_id is valid and data is loaded

### KeyError: No progression for breed_id=X
- Breed ID X doesn't exist in progression tables
- Check valid breed IDs (typically 3-12)

### KeyError: No quality multiplier for rarity_id=X
- Rarity ID X doesn't exist (valid: 1-6)
- Check rarity_id parameter

## Further Reading

- `PET_SYSTEM_GUIDE.md` - Full API documentation
- `example_pet_stats.py` - Code examples
- `test_pet_stats.py` - Test cases
