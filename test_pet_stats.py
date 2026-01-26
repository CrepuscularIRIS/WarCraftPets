"""
Unit tests for the Pet Stats system.

Tests the calculation of pet attributes (health, power, speed) using
the formulas from pet_progression_tables.json.
"""

import unittest
from pathlib import Path

from engine.pets.progression import ProgressionDB
from engine.pets.pet_stats import PetStatsCalculator, PetStats


class TestProgressionDB(unittest.TestCase):
    """Test the ProgressionDB class."""

    @classmethod
    def setUpClass(cls):
        """Load the progression database once for all tests."""
        progression_path = Path(__file__).parent / "pet_progression_tables.json"
        cls.progression_db = ProgressionDB(progression_path)

    def test_quality_multipliers_loaded(self):
        """Test that quality multipliers are correctly loaded."""
        self.assertEqual(len(self.progression_db._quality), 6)
        # 质量乘数已乘以2
        self.assertAlmostEqual(self.progression_db._quality[1], 1.0)
        self.assertAlmostEqual(self.progression_db._quality[2], 1.100000023841858)
        self.assertAlmostEqual(self.progression_db._quality[6], 1.5)

    def test_breed_stats_loaded(self):
        """Test that breed stats are correctly loaded."""
        self.assertIn(3, self.progression_db._breeds)
        self.assertIn(4, self.progression_db._breeds)
        self.assertIn(12, self.progression_db._breeds)

        breed_3 = self.progression_db._breeds[3]
        self.assertAlmostEqual(breed_3["health_add"], 0.5)
        self.assertAlmostEqual(breed_3["power_add"], 0.5)
        self.assertAlmostEqual(breed_3["speed_add"], 0.5)

    def test_base_pet_stats_loaded(self):
        """Test that base pet stats are correctly loaded."""
        self.assertTrue(self.progression_db.has_base(2))
        self.assertFalse(self.progression_db.has_base(1))

        base_2 = self.progression_db._base[2]
        self.assertAlmostEqual(base_2["base_health"], 10.5)
        self.assertAlmostEqual(base_2["base_power"], 8.0)
        self.assertAlmostEqual(base_2["base_speed"], 9.5)

    def test_compute_stats_level_1(self):
        """Test stat computation at level 1."""
        # Pet ID 2, Breed 3, Rarity 1, Level 1
        stats = self.progression_db.compute_stats(pet_id=2, breed_id=3, rarity_id=1, level=1)

        # Formula check:
        # base_health = 10.5, health_breed_points = 0.5
        # base_power = 8.0, power_breed_points = 0.5
        # base_speed = 9.5, speed_breed_points = 0.5
        # quality = 0.5 * 2 = 1.0 (质量乘数基准为0.5，需乘以2)
        # level = 1

        # health = ((10.5 + 0.5) * 5 * 1 * 1.0) + 100
        #        = (11.0 * 5 * 1.0) + 100
        #        = 55 + 100 = 155
        expected_health = 155

        # power = (8.0 + 0.5) * 1 * 1.0
        #       = 8.5 * 1.0
        #       = 8.5 ≈ 8 或 9 (取决于舍入)
        expected_power = 8  # 实际计算: int(round(8.5 * 1.0)) = 8

        # speed = (9.5 + 0.5) * 1 * 1.0
        #       = 10.0 * 1.0
        #       = 10
        expected_speed = 10

        self.assertEqual(stats["health"], expected_health)
        self.assertEqual(stats["power"], expected_power)
        self.assertEqual(stats["speed"], expected_speed)

    def test_compute_stats_level_25(self):
        """Test stat computation at level 25."""
        # Pet ID 2, Breed 3, Rarity 2, Level 25
        stats = self.progression_db.compute_stats(pet_id=2, breed_id=3, rarity_id=2, level=25)

        # base_health = 10.5, health_breed_points = 0.5
        # base_power = 8.0, power_breed_points = 0.5
        # base_speed = 9.5, speed_breed_points = 0.5
        # quality = 0.550000011920929 * 2 = 1.100000023841858
        # level = 25

        # health = ((10.5 + 0.5) * 5 * 25 * 1.100000023841858) + 100
        expected_health = int(round((10.5 + 0.5) * 5.0 * 25 * 0.550000011920929 * 2.0 + 100.0))

        # power = (8.0 + 0.5) * 25 * 1.100000023841858
        expected_power = int(round((8.0 + 0.5) * 25 * 0.550000011920929 * 2.0))

        # speed = (9.5 + 0.5) * 25 * 1.100000023841858
        expected_speed = int(round((9.5 + 0.5) * 25 * 0.550000011920929 * 2.0))

        self.assertEqual(stats["health"], expected_health)
        self.assertEqual(stats["power"], expected_power)
        self.assertEqual(stats["speed"], expected_speed)

    def test_compute_stats_high_rarity(self):
        """Test stat computation with high rarity (quality 0.75 * 2 = 1.5)."""
        stats = self.progression_db.compute_stats(pet_id=2, breed_id=3, rarity_id=6, level=25)

        # Using quality multiplier 0.75 * 2 = 1.5
        expected_health = int(round((10.5 + 0.5) * 5.0 * 25 * 0.75 * 2.0 + 100.0))
        expected_power = int(round((8.0 + 0.5) * 25 * 0.75 * 2.0))
        expected_speed = int(round((9.5 + 0.5) * 25 * 0.75 * 2.0))

        self.assertEqual(stats["health"], expected_health)
        self.assertEqual(stats["power"], expected_power)
        self.assertEqual(stats["speed"], expected_speed)

    def test_missing_base_stats_raises_error(self):
        """Test that missing base stats raises KeyError."""
        with self.assertRaises(KeyError) as ctx:
            self.progression_db.compute_stats(pet_id=1, breed_id=3, rarity_id=1, level=1)
        self.assertIn("No base stats", str(ctx.exception))

    def test_missing_breed_raises_error(self):
        """Test that missing breed raises KeyError."""
        with self.assertRaises(KeyError) as ctx:
            self.progression_db.compute_stats(pet_id=2, breed_id=999, rarity_id=1, level=1)
        self.assertIn("No progression", str(ctx.exception))

    def test_missing_rarity_raises_error(self):
        """Test that missing rarity raises KeyError."""
        with self.assertRaises(KeyError) as ctx:
            self.progression_db.compute_stats(pet_id=2, breed_id=3, rarity_id=99, level=1)
        self.assertIn("No quality multiplier", str(ctx.exception))


class TestPetStatsCalculator(unittest.TestCase):
    """Test the PetStatsCalculator class."""

    @classmethod
    def setUpClass(cls):
        """Set up calculator with progression database."""
        progression_path = Path(__file__).parent / "pet_progression_tables.json"
        cls.progression_db = ProgressionDB(progression_path)
        cls.calculator = PetStatsCalculator(cls.progression_db)

    def test_calculate_returns_pet_stats(self):
        """Test that calculate returns a PetStats object."""
        stats = self.calculator.calculate(pet_id=2, rarity_id=1, breed_id=3, level=1)
        self.assertIsInstance(stats, PetStats)
        self.assertEqual(stats.pet_id, 2)
        self.assertEqual(stats.rarity_id, 1)
        self.assertEqual(stats.breed_id, 3)
        self.assertEqual(stats.level, 1)

    def test_stats_increase_with_level(self):
        """Test that stats increase with pet level."""
        stats_l1 = self.calculator.calculate(pet_id=2, rarity_id=1, breed_id=3, level=1)
        stats_l10 = self.calculator.calculate(pet_id=2, rarity_id=1, breed_id=3, level=10)
        stats_l25 = self.calculator.calculate(pet_id=2, rarity_id=1, breed_id=3, level=25)

        # All stats should increase monotonically with level
        self.assertLess(stats_l1.health, stats_l10.health)
        self.assertLess(stats_l10.health, stats_l25.health)

        self.assertLess(stats_l1.power, stats_l10.power)
        self.assertLess(stats_l10.power, stats_l25.power)

        self.assertLess(stats_l1.speed, stats_l10.speed)
        self.assertLess(stats_l10.speed, stats_l25.speed)

    def test_stats_increase_with_rarity(self):
        """Test that stats increase with rarity."""
        stats_r1 = self.calculator.calculate(pet_id=2, rarity_id=1, breed_id=3, level=25)
        stats_r3 = self.calculator.calculate(pet_id=2, rarity_id=3, breed_id=3, level=25)
        stats_r6 = self.calculator.calculate(pet_id=2, rarity_id=6, breed_id=3, level=25)

        # All stats should increase monotonically with rarity
        self.assertLess(stats_r1.health, stats_r3.health)
        self.assertLess(stats_r3.health, stats_r6.health)

        self.assertLess(stats_r1.power, stats_r3.power)
        self.assertLess(stats_r3.power, stats_r6.power)

        self.assertLess(stats_r1.speed, stats_r3.speed)
        self.assertLess(stats_r3.speed, stats_r6.speed)

    def test_skill_panel_damage(self):
        """Test skill panel damage calculation."""
        stats = self.calculator.calculate(pet_id=2, rarity_id=1, breed_id=3, level=25)

        # Test with base damage value
        base_damage = 10
        panel_damage = stats.skill_panel_damage(base_damage)

        # Formula: floor(points * (1 + power/20))
        expected = int((base_damage * (1 + stats.power / 20.0)))
        self.assertEqual(panel_damage, expected)

    def test_batch_calculate(self):
        """Test batch calculation of multiple pets."""
        pets = [
            {'pet_id': 2, 'rarity_id': 1, 'breed_id': 3, 'level': 1},
            {'pet_id': 2, 'rarity_id': 1, 'breed_id': 3, 'level': 25},
            {'pet_id': 2, 'rarity_id': 6, 'breed_id': 3, 'level': 25},
        ]

        results = self.calculator.batch_calculate(pets)
        self.assertEqual(len(results), 3)

        # Verify keys are tuples
        for key in results.keys():
            self.assertIsInstance(key, tuple)
            self.assertEqual(len(key), 4)

    def test_calculate_skill_damages(self):
        """Test calculating damages for multiple skills."""
        stats = self.calculator.calculate(pet_id=2, rarity_id=1, breed_id=3, level=25)

        skills = {
            'attack': 10,
            'power_attack': 15,
            'special': 8,
        }

        damages = self.calculator.calculate_skill_damages(stats, skills)
        self.assertEqual(len(damages), 3)
        self.assertIn('attack', damages)
        self.assertIn('power_attack', damages)
        self.assertIn('special', damages)

        # Damages should be positive and ordered correctly
        self.assertLess(damages['special'], damages['attack'])
        self.assertLess(damages['attack'], damages['power_attack'])


class TestPetStatsProperties(unittest.TestCase):
    """Test PetStats object properties and methods."""

    @classmethod
    def setUpClass(cls):
        """Set up calculator and test stats."""
        progression_path = Path(__file__).parent / "pet_progression_tables.json"
        cls.progression_db = ProgressionDB(progression_path)
        cls.calculator = PetStatsCalculator(cls.progression_db)
        cls.stats = cls.calculator.calculate(pet_id=2, rarity_id=2, breed_id=3, level=15)

    def test_quality_multiplier_property(self):
        """Test quality_multiplier property."""
        # Rarity 2 should have multiplier 0.550000011920929 * 2 = 1.100000023841858
        self.assertAlmostEqual(
            self.stats.quality_multiplier,
            1.100000023841858,
            places=5
        )

    def test_skill_duration_based_damage(self):
        """Test duration-based damage calculation."""
        base_damage = 10
        duration = 3
        per_tick = self.stats.skill_duration_based_damage(base_damage, duration)

        # Should be at least 1 per tick
        self.assertGreaterEqual(per_tick, 1)

        # Total should be close to or less than single-hit damage
        total = per_tick * duration
        single_hit = self.stats.skill_panel_damage(base_damage)
        self.assertLessEqual(total, single_hit + duration)  # Allow some variance


class TestFormulaValidation(unittest.TestCase):
    """Validate the exact formulas used in calculations."""

    @classmethod
    def setUpClass(cls):
        """Set up test data."""
        progression_path = Path(__file__).parent / "pet_progression_tables.json"
        cls.progression_db = ProgressionDB(progression_path)

    def test_health_formula_validation(self):
        """Validate Health formula: ((Base Health + HealthPts) * 5 * Level * Quality) + 100"""
        # Pet 2, Breed 3, Rarity 1, Level 1
        stats = self.progression_db.compute_stats(2, 3, 1, 1)

        # Manual calculation
        # 注意：breed_stats中的值已经是HealthPts，不需要再除以10
        base_health = 10.5
        health_pts = 0.5
        quality = 0.5 * 2.0  # 质量乘数需乘以2
        level = 1

        expected = ((base_health + health_pts) * 5.0 * level * quality) + 100
        expected = int(round(expected))

        self.assertEqual(stats["health"], expected)

    def test_power_formula_validation(self):
        """Validate Power formula: ((Base Power + PowerPts) * Level * Quality)"""
        stats = self.progression_db.compute_stats(2, 3, 1, 1)

        base_power = 8.0
        power_pts = 0.5
        quality = 0.5 * 2.0  # 质量乘数需乘以2
        level = 1

        expected = (base_power + power_pts) * level * quality
        expected = int(round(expected))

        self.assertEqual(stats["power"], expected)

    def test_speed_formula_validation(self):
        """Validate Speed formula: ((Base Speed + SpeedPts) * Level * Quality)"""
        stats = self.progression_db.compute_stats(2, 3, 1, 1)

        base_speed = 9.5
        speed_pts = 0.5
        quality = 0.5 * 2.0  # 质量乘数需乘以2
        level = 1

        expected = (base_speed + speed_pts) * level * quality
        expected = int(round(expected))

        self.assertEqual(stats["speed"], expected)


if __name__ == '__main__':
    unittest.main()
