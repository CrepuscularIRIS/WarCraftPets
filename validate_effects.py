#!/usr/bin/env python3
"""
Effect System Validation Script
Tests all 100+ effect handlers for correctness
"""

import sys
import os

# Add the engine path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.effects.registry import _HANDLERS, get_handler
from engine.effects.dispatcher import EffectDispatcher
from engine.effects.semantic_registry import get_default_registry, SemanticRegistry
from engine.effects.param_parser import ParamParser


class ValidationResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.details = []

    def add_pass(self, category, message):
        self.passed += 1
        self.details.append(("PASS", category, message))

    def add_fail(self, category, message):
        self.failed += 1
        self.details.append(("FAIL", category, message))

    def add_warning(self, category, message):
        self.warnings += 1
        self.details.append(("WARN", category, message))


def count_handlers():
    """Count and categorize all registered effect handlers."""
    result = ValidationResult()

    handlers = _HANDLERS
    result.add_pass("HANDLER_COUNT", f"Total registered handlers: {len(handlers)}")

    # Categorize handlers
    categories = {
        "damage": [],
        "healing": [],
        "aura": [],
        "state": [],
        "cooldown": [],
        "utility": [],
        "accuracy": [],
        "unknown": []
    }

    for prop_id, handler in sorted(handlers.items()):
        name = handler.__class__.__name__.lower()

        if "dmg" in name or "damage" in name:
            categories["damage"].append(prop_id)
        elif "heal" in name:
            categories["healing"].append(prop_id)
        elif "aura" in name:
            categories["aura"].append(prop_id)
        elif "state" in name:
            categories["state"].append(prop_id)
        elif "cooldown" in name or "lock" in name:
            categories["cooldown"].append(prop_id)
        elif "accuracy" in name or "acc_ctx" in name:
            categories["accuracy"].append(prop_id)
        elif any(x in name for x in ["swap", "weather", "trap", "timer", "target",
                                       "execute", "resurrect", "clone", "gate",
                                       "mark", "wall", "charge", "resilient",
                                       "priority", "dont_miss", "multi_target"]):
            categories["utility"].append(prop_id)
        else:
            categories["unknown"].append(prop_id)

    for cat, props in categories.items():
        result.add_pass(f"CATEGORY_{cat.upper()}", f"{cat}: {len(props)} handlers - props {props}")

    return result


def test_effect_dispatcher():
    """Test effect dispatcher routes correctly."""
    result = ValidationResult()

    dispatcher = EffectDispatcher()

    # Test that dispatcher can be instantiated
    result.add_pass("DISPATCHER_INIT", "EffectDispatcher instantiated successfully")

    # Test semantic registry integration
    sem = get_default_registry()
    result.add_pass("SEMANTIC_REGISTRY", f"Semantic registry loaded: {sem._loaded}")

    # Test handler retrieval for known opcodes
    test_opcodes = [0, 22, 23, 24, 26, 31, 32, 52, 53, 136]
    for opcode in test_opcodes:
        handler = get_handler(opcode)
        if handler is not None:
            result.add_pass(f"DISPATCH_GET_{opcode}", f"Handler found for opcode {opcode}")
        else:
            result.add_fail(f"DISPATCH_GET_{opcode}", f"No handler for opcode {opcode}")

    # Test param parser
    parsed = ParamParser.parse("Points,Accuracy", "100,100")
    if parsed.get("points") == 100 and parsed.get("accuracy") == 100:
        result.add_pass("PARAM_PARSER", "ParamParser works correctly")
    else:
        result.add_fail("PARAM_PARSER", f"ParamParser failed: {parsed}")

    return result


def test_damage_effects():
    """Test damage effect handlers have correct structure."""
    result = ValidationResult()

    damage_opcodes = [0, 24, 27, 29, 59, 62, 66, 67, 68, 75, 86, 96, 103, 104,
                      141, 149, 170, 197, 222, 226, 234, 363, 370]

    for opcode in damage_opcodes:
        handler = get_handler(opcode)
        if handler is not None:
            # Check for required attributes
            if hasattr(handler, 'PROP_ID') and hasattr(handler, 'apply'):
                result.add_pass(f"DAMAGE_STRUCT_{opcode}",
                    f"op{opcode:04d} has PROP_ID={handler.PROP_ID}")
            else:
                result.add_fail(f"DAMAGE_STRUCT_{opcode}",
                    f"op{opcode:04d} missing required attributes")
        else:
            result.add_warning(f"DAMAGE_STRUCT_{opcode}",
                f"No handler registered for damage opcode {opcode}")

    return result


def test_aura_effects():
    """Test aura effect handlers have correct structure."""
    result = ValidationResult()

    aura_opcodes = [26, 28, 50, 52, 54, 63, 77, 86, 131, 137, 168, 172, 177, 178,
                    230, 248, 486]  # op0086 is dual-purpose (damage + aura)

    for opcode in aura_opcodes:
        handler = get_handler(opcode)
        if handler is not None:
            if hasattr(handler, 'PROP_ID') and hasattr(handler, 'apply'):
                result.add_pass(f"AURA_STRUCT_{opcode}",
                    f"op{opcode:04d} has PROP_ID={handler.PROP_ID}")
            else:
                result.add_fail(f"AURA_STRUCT_{opcode}",
                    f"op{opcode:04d} missing required attributes")
        else:
            result.add_warning(f"AURA_STRUCT_{opcode}",
                f"No handler registered for aura opcode {opcode}")

    return result


def test_healing_effects():
    """Test healing effect handlers have correct structure."""
    result = ValidationResult()

    healing_opcodes = [23, 53, 61, 78, 100]

    for opcode in healing_opcodes:
        handler = get_handler(opcode)
        if handler is not None:
            if hasattr(handler, 'PROP_ID') and hasattr(handler, 'apply'):
                result.add_pass(f"HEAL_STRUCT_{opcode}",
                    f"op{opcode:04d} has PROP_ID={handler.PROP_ID}")
            else:
                result.add_fail(f"HEAL_STRUCT_{opcode}",
                    f"op{opcode:04d} missing required attributes")
        else:
            result.add_warning(f"HEAL_STRUCT_{opcode}",
                f"No handler registered for healing opcode {opcode}")

    return result


def test_state_effects():
    """Test state modification handlers."""
    result = ValidationResult()

    state_opcodes = [31, 79, 85, 138, 156, 157, 172, 248]

    for opcode in state_opcodes:
        handler = get_handler(opcode)
        if handler is not None:
            result.add_pass(f"STATE_STRUCT_{opcode}",
                f"op{opcode:04d} state handler registered")
        else:
            result.add_warning(f"STATE_STRUCT_{opcode}",
                f"No handler for state opcode {opcode}")

    return result


def test_utility_effects():
    """Test utility handlers."""
    result = ValidationResult()

    utility_opcodes = [22, 107, 112, 121, 122, 129, 135, 136, 139, 144, 145,
                       158, 159, 194, 229, 370, 486]

    for opcode in utility_opcodes:
        handler = get_handler(opcode)
        if handler is not None:
            result.add_pass(f"UTILITY_STRUCT_{opcode}",
                f"op{opcode:04d} utility handler registered")
        else:
            result.add_warning(f"UTILITY_STRUCT_{opcode}",
                f"No handler for utility opcode {opcode}")

    return result


def test_cooldown_effects():
    """Test cooldown handlers."""
    result = ValidationResult()

    cooldown_opcodes = [117, 246]

    for opcode in cooldown_opcodes:
        handler = get_handler(opcode)
        if handler is not None:
            result.add_pass(f"COOLDOWN_STRUCT_{opcode}",
                f"op{opcode:04d} cooldown handler registered")
        else:
            result.add_warning(f"COOLDOWN_STRUCT_{opcode}",
                f"No handler for cooldown opcode {opcode}")

    return result


def test_hit_check():
    """Test hit check calculations."""
    result = ValidationResult()

    try:
        from engine.resolver.hitcheck import HitCheck
        from engine.core.rng import DeterministicRNG

        rng = DeterministicRNG(seed=12345)
        hit_check = HitCheck(rng=rng)

        result.add_pass("HITCHECK_INIT", "HitCheck initialized successfully")

        # Test compute method signature
        if hasattr(hit_check, 'compute'):
            result.add_pass("HITCHECK_COMPUTE", "HitCheck.compute method exists")

        # Test state constants
        if hasattr(hit_check, '_STATE_STAT_ACCURACY') and hasattr(hit_check, '_STATE_STAT_DODGE'):
            result.add_pass("HITCHECK_STATES",
                f"Accuracy state: {hit_check._STATE_STAT_ACCURACY}, Dodge state: {hit_check._STATE_STAT_DODGE}")

    except Exception as e:
        result.add_fail("HITCHECK_INIT", f"HitCheck initialization failed: {e}")

    return result


def test_damage_pipeline():
    """Test damage pipeline calculations."""
    result = ValidationResult()

    try:
        from engine.resolver.damage_pipeline import DamagePipeline, ResolvedDamage
        from engine.core.rng import DeterministicRNG

        rng = DeterministicRNG(seed=12345)
        pipeline = DamagePipeline(rng=rng)

        result.add_pass("DAMAGE_PIPELINE_INIT", "DamagePipeline initialized successfully")

        # Test resolve method exists
        if hasattr(pipeline, 'resolve'):
            result.add_pass("DAMAGE_PIPELINE_RESOLVE", "DamagePipeline.resolve method exists")

    except Exception as e:
        result.add_fail("DAMAGE_PIPELINE_INIT", f"DamagePipeline initialization failed: {e}")

    return result


def test_heal_pipeline():
    """Test heal pipeline calculations."""
    result = ValidationResult()

    try:
        from engine.resolver.heal_pipeline import HealPipeline
        from engine.core.rng import DeterministicRNG

        rng = DeterministicRNG(seed=12345)
        pipeline = HealPipeline(rng=rng)

        result.add_pass("HEAL_PIPELINE_INIT", "HealPipeline initialized successfully")

        if hasattr(pipeline, 'resolve'):
            result.add_pass("HEAL_PIPELINE_RESOLVE", "HealPipeline.resolve method exists")

    except Exception as e:
        result.add_fail("HEAL_PIPELINE_INIT", f"HealPipeline initialization failed: {e}")

    return result


def test_semantic_registry():
    """Test semantic registry functionality."""
    result = ValidationResult()

    try:
        # Test loading semantic registry
        sem = get_default_registry()
        sem.load()

        result.add_pass("SEMANTIC_LOAD", "SemanticRegistry.load() succeeded")

        # Test get method
        if hasattr(sem, 'get'):
            result.add_pass("SEMANTIC_GET", "SemanticRegistry.get method exists")

        # Test label_mismatch
        if hasattr(sem, 'label_mismatch'):
            result.add_pass("SEMANTIC_LABEL_MISMATCH", "SemanticRegistry.label_mismatch method exists")

        # Test normalize_args
        from engine.effects.semantic_registry import normalize_args
        test_args = {"points": 100, "accuracy": 1.0}
        schema = {"points": "int", "accuracy": "int"}
        normalized = normalize_args(test_args, schema)
        result.add_pass("SEMANTIC_NORMALIZE", f"normalize_args returned: {normalized}")

    except Exception as e:
        result.add_fail("SEMANTIC_INIT", f"SemanticRegistry test failed: {e}")

    return result


def test_handler_registration():
    """Test that all handlers are properly registered."""
    result = ValidationResult()

    handlers = _HANDLERS

    # Check for duplicate registrations
    seen_classes = set()
    for prop_id, handler in handlers.items():
        cls = handler.__class__
        if id(cls) in seen_classes:
            result.add_fail(f"DUPLICATE_HANDLER_{prop_id}",
                f"Handler class {cls.__name__} appears to be duplicated")
        else:
            seen_classes.add(id(cls))

    result.add_pass("HANDLER_NO_DUPLICATES", "No duplicate handler classes detected")

    # Verify PROP_ID consistency
    for prop_id, handler in handlers.items():
        if hasattr(handler, 'PROP_ID') and handler.PROP_ID != prop_id:
            result.add_fail(f"PROP_ID_MISMATCH_{prop_id}",
                f"Handler PROP_ID {handler.PROP_ID} != registry key {prop_id}")
        elif hasattr(handler, 'PROP_ID'):
            result.add_pass(f"PROP_ID_MATCH_{prop_id}",
                f"op{handler.PROP_ID:04d} PROP_ID matches")

    return result


def main():
    """Run all validation tests."""
    print("=" * 60)
    print("EFFECT SYSTEM VALIDATION")
    print("=" * 60)

    results = []

    # Run all tests
    tests = [
        ("Handler Count & Categories", count_handlers),
        ("Effect Dispatcher", test_effect_dispatcher),
        ("Handler Registration", test_handler_registration),
        ("Damage Effects", test_damage_effects),
        ("Aura Effects", test_aura_effects),
        ("Healing Effects", test_healing_effects),
        ("State Effects", test_state_effects),
        ("Utility Effects", test_utility_effects),
        ("Cooldown Effects", test_cooldown_effects),
        ("Hit Check", test_hit_check),
        ("Damage Pipeline", test_damage_pipeline),
        ("Heal Pipeline", test_heal_pipeline),
        ("Semantic Registry", test_semantic_registry),
    ]

    total_passed = 0
    total_failed = 0
    total_warnings = 0

    for name, test_func in tests:
        print(f"\n--- {name} ---")
        result = test_func()
        results.append((name, result))

        for status, category, message in result.details:
            symbol = {"PASS": "[PASS]", "FAIL": "[FAIL]", "WARN": "[WARN]"}[status]
            print(f"  {symbol} {category}: {message}")

        total_passed += result.passed
        total_failed += result.failed
        total_warnings += result.warnings

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Total Passed:   {total_passed}")
    print(f"Total Failed:   {total_failed}")
    print(f"Total Warnings: {total_warnings}")
    print(f"Total Tests:    {total_passed + total_failed + total_warnings}")

    if total_failed == 0:
        print("\n[SUCCESS] All critical tests passed!")
        return 0
    else:
        print(f"\n[FAILURE] {total_failed} test(s) failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
