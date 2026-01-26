#!/usr/bin/env python3
"""
Example script demonstrating how to use the Pet Stats subsystem.

This shows practical usage patterns for calculating pet stats and skill damages.
"""

from pathlib import Path
from engine.pets.progression import ProgressionDB
from engine.pets.pet_stats import PetStatsCalculator


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def example_1_basic_calculation():
    """Example 1: Basic stat calculation for a single pet."""
    print_section("Example 1: Basic Pet Stats Calculation")

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

    print(f"\nPet ID: {pet_stats.pet_id}")
    print(f"Rarity: {pet_stats.rarity_id}")
    print(f"Breed: {pet_stats.breed_id}")
    print(f"Level: {pet_stats.level}")
    print(f"\nCalculated Stats:")
    print(f"  Health: {pet_stats.health}")
    print(f"  Power:  {pet_stats.power}")
    print(f"  Speed:  {pet_stats.speed}")
    print(f"\nQuality Multiplier: {pet_stats.quality_multiplier:.4f}")


def example_2_skill_damage():
    """Example 2: Calculate skill damage for a pet."""
    print_section("Example 2: Skill Damage Calculation")

    progression_path = Path("pet_progression_tables.json")
    progression_db = ProgressionDB(progression_path)
    calculator = PetStatsCalculator(progression_db)

    pet_stats = calculator.calculate(pet_id=2, rarity_id=3, breed_id=3, level=25)

    print(f"\nPet Stats: HP={pet_stats.health}, Power={pet_stats.power}, Speed={pet_stats.speed}")

    # Calculate damages for different skills
    skill_base_damages = [8, 10, 12, 15, 20]

    print(f"\nSkill Damage Calculation (Formula: floor(base * (1 + power/20))):")
    print(f"\n{'Base Damage':<15} {'Panel Damage':<15} {'Multiplier':<15}")
    print("-" * 45)

    for base_damage in skill_base_damages:
        panel_damage = pet_stats.skill_panel_damage(base_damage)
        multiplier = panel_damage / base_damage
        print(f"{base_damage:<15} {panel_damage:<15} {multiplier:<15.2f}")


def example_3_level_progression():
    """Example 3: Show how stats scale with level."""
    print_section("Example 3: Level Progression Analysis")

    progression_path = Path("pet_progression_tables.json")
    progression_db = ProgressionDB(progression_path)
    calculator = PetStatsCalculator(progression_db)

    print(f"\nPet Stats at Different Levels (Pet ID=2, Rarity=2, Breed=3)")
    print(f"\n{'Level':<10} {'Health':<12} {'Power':<12} {'Speed':<12}")
    print("-" * 46)

    for level in [1, 5, 10, 15, 20, 25]:
        stats = calculator.calculate(pet_id=2, rarity_id=2, breed_id=3, level=level)
        print(f"{level:<10} {stats.health:<12} {stats.power:<12} {stats.speed:<12}")


def example_4_rarity_comparison():
    """Example 4: Compare stats across different rarities."""
    print_section("Example 4: Rarity Comparison (Level 25)")

    progression_path = Path("pet_progression_tables.json")
    progression_db = ProgressionDB(progression_path)
    calculator = PetStatsCalculator(progression_db)

    print(f"\nPet Stats at Different Rarities (Pet ID=2, Level=25, Breed=3)")
    print(f"\n{'Rarity':<12} {'Quality':<12} {'Health':<12} {'Power':<12} {'Speed':<12}")
    print("-" * 60)

    rarity_names = {1: "Poor", 2: "Common", 3: "Uncommon", 4: "Rare", 5: "Epic", 6: "Legendary"}

    for rarity in [1, 2, 3, 4, 5, 6]:
        stats = calculator.calculate(pet_id=2, rarity_id=rarity, breed_id=3, level=25)
        quality = progression_db._quality[rarity]
        print(f"{rarity_names[rarity]:<12} {quality:<12.4f} {stats.health:<12} "
              f"{stats.power:<12} {stats.speed:<12}")


def example_5_batch_calculation():
    """Example 5: Batch calculate multiple pets."""
    print_section("Example 5: Batch Calculation")

    progression_path = Path("pet_progression_tables.json")
    progression_db = ProgressionDB(progression_path)
    calculator = PetStatsCalculator(progression_db)

    # Define multiple pet configurations
    pets = [
        {'pet_id': 2, 'rarity_id': 1, 'breed_id': 3, 'level': 1},
        {'pet_id': 2, 'rarity_id': 2, 'breed_id': 3, 'level': 10},
        {'pet_id': 2, 'rarity_id': 3, 'breed_id': 3, 'level': 15},
        {'pet_id': 2, 'rarity_id': 4, 'breed_id': 3, 'level': 20},
        {'pet_id': 2, 'rarity_id': 5, 'breed_id': 3, 'level': 25},
        {'pet_id': 2, 'rarity_id': 6, 'breed_id': 3, 'level': 25},
    ]

    results = calculator.batch_calculate(pets)

    print(f"\nCalculated {len(results)} pet configurations:")
    print(f"\n{'Pet':<8} {'Rarity':<10} {'Level':<10} {'Health':<12} {'Power':<12} {'Speed':<12}")
    print("-" * 64)

    for key, stats in sorted(results.items()):
        pet_id, rarity_id, breed_id, level = key
        rarity_names = {1: "Poor", 2: "Common", 3: "Uncommon", 4: "Rare", 5: "Epic", 6: "Legendary"}
        print(f"{pet_id:<8} {rarity_names[rarity_id]:<10} {level:<10} "
              f"{stats.health:<12} {stats.power:<12} {stats.speed:<12}")


def example_6_skill_damages_all():
    """Example 6: Calculate damages for multiple skills at once."""
    print_section("Example 6: Multiple Skill Damages")

    progression_path = Path("pet_progression_tables.json")
    progression_db = ProgressionDB(progression_path)
    calculator = PetStatsCalculator(progression_db)

    pet_stats = calculator.calculate(pet_id=2, rarity_id=3, breed_id=3, level=25)

    # Define multiple skills with their base damage
    skills = {
        'Attack': 10,
        'Power Attack': 15,
        'Ancient Power': 8,
        'Bite': 12,
        'Scratch': 7,
        'Special Ability': 20,
    }

    damages = calculator.calculate_skill_damages(pet_stats, skills)

    print(f"\nPet: ID=2, Rarity=3, Level=25")
    print(f"Power: {pet_stats.power}")
    print(f"\nSkill Damages:")
    print(f"\n{'Skill Name':<20} {'Base Damage':<15} {'Panel Damage':<15}")
    print("-" * 50)

    for skill_name, base_damage in skills.items():
        panel_damage = damages[skill_name]
        print(f"{skill_name:<20} {base_damage:<15} {panel_damage:<15}")


def example_7_breed_comparison():
    """Example 7: Compare different breeds."""
    print_section("Example 7: Breed Comparison (Level 25, Rarity 3)")

    progression_path = Path("pet_progression_tables.json")
    progression_db = ProgressionDB(progression_path)
    calculator = PetStatsCalculator(progression_db)

    # Test different breeds
    test_breeds = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

    print(f"\nComparing different breeds for Pet ID=2:")
    print(f"\n{'Breed':<10} {'Health Add':<15} {'Power Add':<15} {'Speed Add':<15} "
          f"{'Health':<12} {'Power':<12} {'Speed':<12}")
    print("-" * 92)

    for breed_id in test_breeds:
        if breed_id not in progression_db._breeds:
            continue

        breed = progression_db._breeds[breed_id]
        stats = calculator.calculate(pet_id=2, rarity_id=3, breed_id=breed_id, level=25)

        health_add = breed.get('health_add', 0)
        power_add = breed.get('power_add', 0)
        speed_add = breed.get('speed_add', 0)

        print(f"{breed_id:<10} {health_add:<15.1f} {power_add:<15.1f} {speed_add:<15.1f} "
              f"{stats.health:<12} {stats.power:<12} {stats.speed:<12}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Pet Stats Subsystem - Usage Examples")
    print("="*60)

    try:
        example_1_basic_calculation()
        example_2_skill_damage()
        example_3_level_progression()
        example_4_rarity_comparison()
        example_5_batch_calculation()
        example_6_skill_damages_all()
        example_7_breed_comparison()

        print_section("Examples Completed Successfully!")
        print("\nFor more information, see PET_SYSTEM_GUIDE.md")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
