#!/usr/bin/env python3
"""
Comprehensive Pet Stats Validation Script

This script validates the pet stats calculation system by:
1. Testing pet stats at levels 1, 5, 10, 15, 20, 25
2. Testing all rarity levels (1-6)
3. Testing breed multipliers
4. Calculating expected values based on formulas
5. Comparing with actual computed values
6. Logging any discrepancies
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add the engine directory to path
sys.path.insert(0, '/home/yarizakurahime/engine/wow_claude')

from engine.pets.progression import ProgressionDB
from engine.pets.pet_stats import PetStatsCalculator, PetStats
from engine.pets.skill_math import SkillMath


class PetStatsValidator:
    """Comprehensive validator for pet stats calculation system."""

    def __init__(self):
        self.progression_path = Path('/home/yarizakurahime/engine/wow_claude/pet_progression_tables.json')
        self.progression_db = ProgressionDB(self.progression_path)
        self.calculator = PetStatsCalculator(self.progression_db)
        self.issues = []
        self.test_results = []

    def log_test(self, category: str, test_name: str, expected, actual, status: str, details: str = ""):
        """Log a test result."""
        result = {
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'test_name': test_name,
            'expected': expected,
            'actual': actual,
            'status': status,
            'details': details
        }
        self.test_results.append(result)
        if status == "FAIL":
            self.issues.append(result)
        return result

    def validate_quality_multipliers(self) -> bool:
        """Validate quality multipliers are correctly loaded and applied."""
        print("\n### Quality Multipliers Validation ###")
        quality = self.progression_db._quality

        # Expected multipliers (raw * 2.0)
        expected = {
            1: 1.0,      # Common
            2: 1.1,      # Uncommon
            3: 1.2,      # Rare
            4: 1.3,      # Epic
            5: 1.4,      # Legendary
            6: 1.5       # Mythical
        }

        all_passed = True
        print(f"{'Rarity':<10} {'Expected':<15} {'Actual':<15} {'Status':<10}")
        print("-" * 50)

        for rarity, exp_val in expected.items():
            actual = quality.get(rarity, 0)
            # Allow small floating point tolerance
            tolerance = 0.001
            passed = abs(actual - exp_val) < tolerance
            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False
            print(f"{rarity:<10} {exp_val:.4f}x{'':<8} {actual:.6f}{'':<6} {status}")
            self.log_test(
                "Quality Multipliers",
                f"Rarity {rarity}",
                f"{exp_val:.4f}x",
                f"{actual:.6f}",
                status,
                f"Expected {exp_val:.4f}, got {actual:.6f}"
            )

        return all_passed

    def validate_breed_bonuses(self) -> bool:
        """Validate breed bonus calculations."""
        print("\n### Breed Bonus Validation ###")
        breeds = self.progression_db._breeds

        # Known breed bonuses from the JSON file
        known_breeds = {
            3: {"health_add": 0.5, "power_add": 0.5, "speed_add": 0.5},
            4: {"health_add": 0.0, "power_add": 2.0, "speed_add": 0.0},  # Power
            5: {"health_add": 0.0, "power_add": 0.0, "speed_add": 2.0},  # Speed
            6: {"health_add": 2.0, "power_add": 0.0, "speed_add": 0.0},  # HP
            7: {"health_add": 0.9, "power_add": 0.9, "speed_add": 0.0},
            8: {"health_add": 0.0, "power_add": 0.9, "speed_add": 0.9},
            9: {"health_add": 0.9, "power_add": 0.0, "speed_add": 0.9},
            10: {"health_add": 0.4, "power_add": 0.9, "speed_add": 0.4},
            11: {"health_add": 0.4, "power_add": 0.4, "speed_add": 0.9},
            12: {"health_add": 0.9, "power_add": 0.4, "speed_add": 0.4},
        }

        all_passed = True
        print(f"{'Breed':<8} {'HP Bonus':<12} {'POW Bonus':<12} {'SPD Bonus':<12} {'Status':<10}")
        print("-" * 55)

        for breed_id, expected in known_breeds.items():
            if breed_id not in breeds:
                print(f"{breed_id:<8} {'N/A':<12} {'N/A':<12} {'N/A':<12} {'FAIL':<10}")
                all_passed = False
                continue

            actual = breeds[breed_id]
            hp_pass = abs(actual['health_add'] - expected['health_add']) < 0.001
            pow_pass = abs(actual['power_add'] - expected['power_add']) < 0.001
            spd_pass = abs(actual['speed_add'] - expected['speed_add']) < 0.001
            passed = hp_pass and pow_pass and spd_pass

            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False

            print(f"{breed_id:<8} {actual['health_add']:<12} {actual['power_add']:<12} {actual['speed_add']:<12} {status}")
            self.log_test(
                "Breed Bonuses",
                f"Breed {breed_id}",
                f"HP:{expected['health_add']}, POW:{expected['power_add']}, SPD:{expected['speed_add']}",
                f"HP:{actual['health_add']}, POW:{actual['power_add']}, SPD:{actual['speed_add']}",
                status
            )

        return all_passed

    def validate_level_progression(self) -> bool:
        """Validate stats increase correctly from level 1 to 25."""
        print("\n### Level 1 to 25 Progression Test (Pet 2, Breed 3, Rarity 1) ###")
        levels = [1, 5, 10, 15, 20, 25]

        all_passed = True
        print(f"{'Level':<8} {'HP':<10} {'Power':<10} {'Speed':<10} {'Status':<10}")
        print("-" * 50)

        prev_stats = None
        for level in levels:
            stats = self.calculator.calculate(pet_id=2, rarity_id=1, breed_id=3, level=level)

            # Calculate expected values manually
            base = self.progression_db._base[2]
            breed = self.progression_db._breeds[3]
            quality = self.progression_db._quality[1] * 2.0

            expected_hp = int(round((base['base_health'] + breed['health_add']) * 5.0 * level * quality + 100))
            expected_power = int(round((base['base_power'] + breed['power_add']) * level * quality))
            expected_speed = int(round((base['base_speed'] + breed['speed_add']) * level * quality))

            hp_match = stats.health == expected_hp
            pow_match = stats.power == expected_power
            spd_match = stats.speed == expected_speed
            passed = hp_match and pow_match and spd_match

            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False

            print(f"{level:<8} {stats.health:<10} {stats.power:<10} {stats.speed:<10} {status}")
            self.log_test(
                "Level Progression",
                f"Level {level}",
                f"HP:{expected_hp}, POW:{expected_power}, SPD:{expected_speed}",
                f"HP:{stats.health}, POW:{stats.power}, SPD:{stats.speed}",
                status
            )

            # Check monotonic increase
            if prev_stats:
                if not (stats.health > prev_stats.health and stats.power > prev_stats.power and stats.speed > prev_stats.speed):
                    print(f"  WARNING: Stats not monotonically increasing from level {prev_stats.level}")

            prev_stats = stats

        return all_passed

    def validate_rarity_progression(self) -> bool:
        """Validate stats increase correctly with rarity."""
        print("\n### Rarity Progression Test (Level 25, Pet 2, Breed 3) ###")
        rarities = list(range(1, 7))

        all_passed = True
        print(f"{'Rarity':<10} {'Multiplier':<15} {'HP':<10} {'Power':<10} {'Speed':<10} {'Status':<10}")
        print("-" * 65)

        prev_stats = None
        for rarity in rarities:
            stats = self.calculator.calculate(pet_id=2, rarity_id=rarity, breed_id=3, level=25)
            multiplier = self.progression_db._quality.get(rarity, 0) * 2.0

            # Calculate expected values manually
            base = self.progression_db._base[2]
            breed = self.progression_db._breeds[3]
            quality = self.progression_db._quality[rarity] * 2.0

            expected_hp = int(round((base['base_health'] + breed['health_add']) * 5.0 * 25 * quality + 100))
            expected_power = int(round((base['base_power'] + breed['power_add']) * 25 * quality))
            expected_speed = int(round((base['base_speed'] + breed['speed_add']) * 25 * quality))

            hp_match = stats.health == expected_hp
            pow_match = stats.power == expected_power
            spd_match = stats.speed == expected_speed
            passed = hp_match and pow_match and spd_match

            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False

            print(f"{rarity:<10} {multiplier:.4f}x{'':<8} {stats.health:<10} {stats.power:<10} {stats.speed:<10} {status}")
            self.log_test(
                "Rarity Progression",
                f"Rarity {rarity}",
                f"HP:{expected_hp}, POW:{expected_power}, SPD:{expected_speed}",
                f"HP:{stats.health}, POW:{stats.power}, SPD:{stats.speed}",
                status
            )

            # Check monotonic increase
            if prev_stats:
                if not (stats.health > prev_stats.health and stats.power > prev_stats.power and stats.speed > prev_stats.speed):
                    print(f"  WARNING: Stats not monotonically increasing from rarity {prev_stats.rarity_id}")

            prev_stats = stats

        return all_passed

    def validate_damage_formula(self) -> bool:
        """Validate the skill panel damage formula."""
        print("\n### Damage Formula Validation ###")
        print("Formula: floor(points * (20 + power) / 20)")

        # Get a pet's stats
        stats = self.calculator.calculate(pet_id=2, rarity_id=1, breed_id=3, level=25)
        power = stats.power

        all_passed = True
        print(f"{'Base Points':<15} {'Power':<10} {'Expected':<15} {'Actual':<15} {'Status':<10}")
        print("-" * 65)

        test_cases = [10, 15, 20, 25, 50, 100]
        for points in test_cases:
            # Expected using the formula
            expected = int(points * (20 + power) // 20)
            # Actual from SkillMath
            actual = SkillMath.panel_value(points, power)

            passed = expected == actual
            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False

            print(f"{points:<15} {power:<10} {expected:<15} {actual:<15} {status}")
            self.log_test(
                "Damage Formula",
                f"Base points={points}",
                expected,
                actual,
                status,
                f"Formula: floor({points} * (20 + {power}) / 20) = {expected}"
            )

        return all_passed

    def validate_breed_impact(self) -> bool:
        """Validate that different breeds produce different stat distributions."""
        print("\n### Breed Impact Test (Level 25, Rarity 1, Pet 2) ###")

        breeds = self.progression_db._breeds
        all_passed = True
        print(f"{'Breed':<8} {'HP Bonus':<12} {'POW Bonus':<12} {'SPD Bonus':<12} {'HP':<10} {'POW':<10} {'SPD':<10} {'Status':<10}")
        print("-" * 85)

        # Get baseline stats (Breed 3 - balanced)
        baseline = self.calculator.calculate(pet_id=2, rarity_id=1, breed_id=3, level=25)

        for breed_id in sorted(breeds.keys()):
            breed = breeds[breed_id]
            stats = self.calculator.calculate(pet_id=2, rarity_id=1, breed_id=breed_id, level=25)

            # Verify breed bonuses are applied correctly
            base = self.progression_db._base[2]
            quality = self.progression_db._quality[1] * 2.0

            expected_hp = int(round((base['base_health'] + breed['health_add']) * 5.0 * 25 * quality + 100))
            expected_power = int(round((base['base_power'] + breed['power_add']) * 25 * quality))
            expected_speed = int(round((base['base_speed'] + breed['speed_add']) * 25 * quality))

            hp_match = stats.health == expected_hp
            pow_match = stats.power == expected_power
            spd_match = stats.speed == expected_speed
            passed = hp_match and pow_match and spd_match

            status = "PASS" if passed else "FAIL"
            if not passed:
                all_passed = False

            print(f"{breed_id:<8} {breed['health_add']:<12} {breed['power_add']:<12} {breed['speed_add']:<12} {stats.health:<10} {stats.power:<10} {stats.speed:<10} {status}")
            self.log_test(
                "Breed Impact",
                f"Breed {breed_id}",
                f"HP:{expected_hp}, POW:{expected_power}, SPD:{expected_speed}",
                f"HP:{stats.health}, POW:{stats.power}, SPD:{stats.speed}",
                status
            )

        return all_passed

    def generate_validation_log(self) -> str:
        """Generate the validation log as markdown."""
        log = []
        log.append("# Pet Stats Validation Log")
        log.append(f"\n**Generated:** {datetime.now().isoformat()}")
        log.append(f"**Total Tests:** {len(self.test_results)}")
        log.append(f"**Passed:** {sum(1 for r in self.test_results if r['status'] == 'PASS')}")
        log.append(f"**Failed:** {len(self.issues)}")

        # Quality Multipliers
        log.append("\n## Quality Multipliers Validation")
        log.append("| Rarity | Expected | Actual | Status |")
        log.append("|--------|----------|--------|--------|")
        for r in self.test_results:
            if r['category'] == 'Quality Multipliers':
                log.append(f"| {r['test_name']} | {r['expected']} | {r['actual']} | {r['status']} |")

        # Breed Bonuses
        log.append("\n## Breed Bonus Validation")
        log.append("| Breed | HP Bonus | POW Bonus | SPD Bonus | Status |")
        log.append("|-------|----------|-----------|-----------|--------|")
        for r in self.test_results:
            if r['category'] == 'Breed Bonuses':
                log.append(f"| {r['test_name'].replace('Breed ', '')} | {r['expected']} | {r['actual']} | {r['status']} |")

        # Level Progression
        log.append("\n## Level 1 to 25 Progression Test")
        log.append("| Level | Expected HP | Actual HP | Expected POW | Actual POW | Expected SPD | Actual SPD | Status |")
        log.append("|-------|-------------|-----------|--------------|------------|--------------|------------|--------|")
        for r in self.test_results:
            if r['category'] == 'Level Progression':
                level = r['test_name'].replace('Level ', '')
                exp_parts = r['expected'].replace('HP:', '').replace('POW:', '').replace('SPD:', '').split(', ')
                act_parts = r['actual'].replace('HP:', '').replace('POW:', '').replace('SPD:', '').split(', ')
                log.append(f"| {level} | {exp_parts[0]} | {act_parts[0]} | {exp_parts[1]} | {act_parts[1]} | {exp_parts[2]} | {act_parts[2]} | {r['status']} |")

        # Rarity Progression
        log.append("\n## Rarity Progression Test")
        log.append("| Rarity | Multiplier | HP | Power | Speed | Status |")
        log.append("|--------|------------|-----|-------|-------|--------|")
        for r in self.test_results:
            if r['category'] == 'Rarity Progression':
                rarity = r['test_name'].replace('Rarity ', '')
                log.append(f"| {rarity} | {r['actual'].split(', ')[0]} | {r['actual'].split('HP:')[1].split(',')[0]} | {r['actual'].split('POW:')[1].split(',')[0]} | {r['actual'].split('SPD:')[1]} | {r['status']} |")

        # Damage Formula
        log.append("\n## Damage Formula Validation")
        log.append("| Base Points | Power | Expected | Actual | Status |")
        log.append("|-------------|-------|----------|--------|--------|")
        for r in self.test_results:
            if r['category'] == 'Damage Formula':
                base = r['test_name'].replace('Base points=', '')
                log.append(f"| {base} | {r['details'].split('Power: ')[1].split(',')[0]} | {r['expected']} | {r['actual']} | {r['status']} |")

        # Summary
        log.append("\n## Summary")
        log.append(f"- Total tests run: {len(self.test_results)}")
        log.append(f"- Tests passed: {sum(1 for r in self.test_results if r['status'] == 'PASS')}")
        log.append(f"- Tests failed: {len(self.issues)}")

        if self.issues:
            log.append("\n### Issues Found")
            for issue in self.issues:
                log.append(f"- **{issue['category']} - {issue['test_name']}**: {issue['details']}")

        return '\n'.join(log)

    def generate_issues_log(self) -> str:
        """Generate the issues log as markdown."""
        if not self.issues:
            return "# No Issues Found\n\nAll validation tests passed successfully!"

        log = []
        log.append("# Pet Stats Validation Issues")
        log.append(f"\n**Generated:** {datetime.now().isoformat()}")
        log.append(f"**Total Issues:** {len(self.issues)}")

        # Group issues by category
        categories = {}
        for issue in self.issues:
            cat = issue['category']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(issue)

        for cat, issues in categories.items():
            log.append(f"\n## {cat}")
            for issue in issues:
                log.append(f"\n### {issue['test_name']}")
                log.append(f"- **Status:** {issue['status']}")
                log.append(f"- **Expected:** {issue['expected']}")
                log.append(f"- **Actual:** {issue['actual']}")
                log.append(f"- **Details:** {issue['details']}")

        return '\n'.join(log)

    def run_all_validations(self) -> bool:
        """Run all validation tests."""
        print("=" * 60)
        print("PET STATS COMPREHENSIVE VALIDATION")
        print("=" * 60)

        results = []
        results.append(("Quality Multipliers", self.validate_quality_multipliers()))
        results.append(("Breed Bonuses", self.validate_breed_bonuses()))
        results.append(("Level Progression", self.validate_level_progression()))
        results.append(("Rarity Progression", self.validate_rarity_progression()))
        results.append(("Damage Formula", self.validate_damage_formula()))
        results.append(("Breed Impact", self.validate_breed_impact()))

        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)
        for name, passed in results:
            status = "PASS" if passed else "FAIL"
            print(f"{name}: {status}")

        all_passed = all(r[1] for r in results)
        print(f"\nOverall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
        print("=" * 60)

        return all_passed


def main():
    """Main entry point."""
    validator = PetStatsValidator()
    all_passed = validator.run_all_validations()

    # Generate logs
    validation_log = validator.generate_validation_log()
    issues_log = validator.generate_issues_log()

    # Save logs
    with open('/home/yarizakurahime/engine/wow_claude/validation_log.md', 'w', encoding='utf-8') as f:
        f.write(validation_log)

    with open('/home/yarizakurahime/engine/wow_claude/validation_issues.md', 'w', encoding='utf-8') as f:
        f.write(issues_log)

    print(f"\nValidation log saved to: /home/yarizakurahime/engine/wow_claude/validation_log.md")
    print(f"Issues log saved to: /home/yarizakurahime/engine/wow_claude/validation_issues.md")

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
