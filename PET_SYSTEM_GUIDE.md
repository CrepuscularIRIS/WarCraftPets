# Pet Subsystem Implementation Guide

## Overview

This guide documents the complete implementation of the Pet subsystem for calculating pet stats and skill damages in the World of Warcraft pet battle engine.

## Components

### 1. ProgressionDB (`engine/pets/progression.py`)

The `ProgressionDB` class loads and manages pet progression data from `pet_progression_tables.json`.

**Key Data:**
- `quality_multiplier`: Rarity quality multipliers (quality IDs 1-6)
- `breed_stats`: Breed-specific stat bonuses for each breed ID
- `base_pet_stats`: Base stats for each pet species (pet IDs)

**Methods:**
- `has_base(pet_id)`: Check if a pet has base stats defined
- `compute_stats(pet_id, breed_id, rarity_id, level)`: Calculate complete stats for a pet

### 2. PetStats Model (`engine/pets/pet_stats.py`)

The `PetStats` dataclass represents calculated stats for a specific pet configuration.

**Attributes:**
- `pet_id`: Species ID
- `rarity_id`: Quality/Rarity ID (1-6)
- `breed_id`: Breed ID
- `level`: Pet level
- `health`: Calculated health points
- `power`: Calculated attack power
- `speed`: Calculated speed

**Methods:**
- `skill_panel_damage(skill_base_points)`: Calculate skill damage
- `skill_panel_heal(skill_base_points)`: Calculate healing amounts
- `skill_duration_based_damage(base_damage, duration)`: Calculate per-tick damage

### 3. PetStatsCalculator (`engine/pets/pet_stats.py`)

High-level calculator for batch computing pet stats.

**Methods:**
- `calculate(pet_id, rarity_id, breed_id, level)`: Calculate stats for single pet
- `batch_calculate(pets)`: Calculate stats for multiple pets
- `calculate_skill_damages(pet_stats, skills)`: Calculate damages for multiple skills

## Formulas

### Health Calculation
```
Health = ((Base Health + (Health_BreedPoints / 10)) * 5 * Level * Quality) + 100
```

### Power Calculation
```
Power = (Base Power + (Power_BreedPoints / 10)) * Level * Quality
```

### Speed Calculation
```
Speed = (Base Speed + (Speed_BreedPoints / 10)) * Level * Quality
```

Where:
- `Base Health/Power/Speed`: From `base_pet_stats[pet_id]`
- `Health_BreedPoints/Power_BreedPoints/Speed_BreedPoints`: From `breed_stats[breed_id]`
- `Quality`: From `quality_multiplier[rarity_id]`
- `Level`: Pet's current level (1-25)

### Skill Damage Calculation
```
Panel Damage = floor(skill_base_points * (1 + power / 20))
```

Where:
- `skill_base_points`: Base damage value defined in skill data
- `power`: The pet's calculated power stat

## Usage Examples

### Example 1: Calculate stats for a single pet

```python
from pathlib import Path
from engine.pets.progression import ProgressionDB
from engine.pets.pet_stats import PetStatsCalculator

# Initialize
progression_path = Path("pet_progression_tables.json")
progression_db = ProgressionDB(progression_path)
calculator = PetStatsCalculator(progression_db)

# Calculate stats for a level 25, rare (rarity 2) pet
pet_stats = calculator.calculate(
    pet_id=2,
    rarity_id=2,
    breed_id=3,
    level=25
)

print(f"Health: {pet_stats.health}")
print(f"Power: {pet_stats.power}")
print(f"Speed: {pet_stats.speed}")
```

### Example 2: Calculate skill damage

```python
# Calculate damage for a skill with 10 base points
skill_damage = pet_stats.skill_panel_damage(10)
print(f"Skill damage: {skill_damage}")

# Formula: floor(10 * (1 + power / 20))
```

### Example 3: Batch calculate multiple pets

```python
pets = [
    {'pet_id': 2, 'rarity_id': 1, 'breed_id': 3, 'level': 1},
    {'pet_id': 2, 'rarity_id': 3, 'breed_id': 3, 'level': 15},
    {'pet_id': 2, 'rarity_id': 6, 'breed_id': 3, 'level': 25},
]

results = calculator.batch_calculate(pets)

for key, stats in results.items():
    pet_id, rarity_id, breed_id, level = key
    print(f"Pet {pet_id} (R{rarity_id}, B{breed_id}, L{level}): "
          f"HP={stats.health}, Power={stats.power}, Speed={stats.speed}")
```

### Example 4: Calculate multiple skill damages

```python
skills = {
    'attack': 10,
    'power_attack': 15,
    'special': 8,
}

damages = calculator.calculate_skill_damages(pet_stats, skills)

for skill_name, damage in damages.items():
    print(f"{skill_name}: {damage}")
```

### Example 5: Level progression analysis

```python
# Compare stats across different levels
for level in [1, 10, 15, 20, 25]:
    stats = calculator.calculate(
        pet_id=2,
        rarity_id=2,
        breed_id=3,
        level=level
    )
    print(f"Level {level}: HP={stats.health}, Power={stats.power}, Speed={stats.speed}")
```

### Example 6: Rarity progression analysis

```python
# Compare stats across different rarities
for rarity in [1, 2, 3, 4, 5, 6]:
    stats = calculator.calculate(
        pet_id=2,
        rarity_id=rarity,
        breed_id=3,
        level=25
    )
    print(f"Rarity {rarity}: HP={stats.health}, Power={stats.power}, Speed={stats.speed}")
```

## Integration with PetFactory

The `PetFactory` class in `engine/pets/pet_factory.py` has been updated to use the new ProgressionDB for non-level-25 pets:

```python
from engine.pets.pet_factory import PetFactory

factory = PetFactory(
    pets_all_path="pets_all.json",
    progression_path="pet_progression_tables.json",
    config=PetFactoryConfig(strict_level25=False)
)

# This will use ProgressionDB for level != 25
pet_instance = factory.create(
    instance_id=1,
    pet_id=2,
    rarity_id=2,
    breed_id=3,
    level=15
)
```

## Testing

Run the comprehensive test suite:

```bash
python -m pytest test_pet_stats.py -v
```

Tests cover:
- Data loading from progression tables
- Formula correctness for all three attributes
- Level and rarity scaling
- Batch calculations
- Skill damage calculations
- Error handling for missing data

## Key Features

1. **Accurate Formulas**: Implements the exact formulas from pet progression tables
2. **Flexible Calculation**: Supports any combination of pet_id, breed_id, rarity_id, and level
3. **Skill Integration**: Easy calculation of skill damages using power stat
4. **Batch Operations**: Efficient processing of multiple pets
5. **Error Handling**: Clear error messages for missing data
6. **Type Safety**: Full type hints for better IDE support

## Data Sources

- **pet_progression_tables.json**: Contains quality multipliers, breed stats, and base pet stats
- **pets_all.json**: (Optional) Contains exact level-25 stats for specific pet combinations
- **Skill Data**: Integrated with skill system for damage calculations

## Performance Considerations

- Calculation is O(1) per pet (simple arithmetic operations)
- Batch operations are O(n) where n is number of pets
- No caching needed for typical usage (calculations are fast)
- Load progression DB once at startup and reuse

## Future Enhancements

Potential improvements:
1. Support for pet stat bonuses/buffs
2. Type advantage damage modifiers
3. Weather-based stat multipliers
4. PvP damage scaling
5. Caching for frequently accessed pets
