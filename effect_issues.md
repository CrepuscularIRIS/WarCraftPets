# Effect System Issues Log

**Generated:** 2026-01-26

---

## Critical Issues (High Priority)

### 1. Handler Registration System Validation

**Issue:** The handler registration via `@register_handler(prop_id)` decorator creates singleton instances at import time. This means all effects share the same handler instances.

**Location:** `/home/yarizakurahime/engine/wow_claude/engine/effects/registry.py`

**Code:**
```python
def register_handler(prop_id: int):
    def deco(cls):
        _HANDLERS[prop_id] = cls()  # Singleton creation
        return cls
    return deco
```

**Impact:**
- Handler state is shared across all uses
- Thread safety concerns in concurrent battles
- Cannot have per-battle handler configurations

**Recommendation:** Consider factory pattern for handler creation if stateful handlers are needed.

---

### 2. Missing Error Handling in Effect Dispatcher

**Issue:** The dispatcher doesn't handle exceptions from handlers gracefully.

**Location:** `/home/yarizakurahime/engine/wow_claude/engine/effects/dispatcher.py:37`

**Code:**
```python
return h.apply(ctx, actor, target, effect_row, args)
```

**Impact:** A single faulty handler can crash the entire battle loop.

**Recommendation:** Wrap handler call in try/except with fallback to EffectResult(executed=False).

---

### 3. Param Parser Vulnerability

**Issue:** The ParamParser uses simple type conversion without validation.

**Location:** `/home/yarizakurahime/engine/wow_claude/engine/effects/param_parser.py:7-12`

**Code:**
```python
def _to_num(s: str):
    try:
        if "." in s or "e" in s.lower():
            return float(s)
        return int(s)
    except ValueError:
        return s  # Returns string on failure!
```

**Impact:** Invalid params may pass through as strings, causing type errors later.

**Recommendation:** Either raise exception or return default value (0) on parse failure.

---

## Medium Priority Issues

### 4. Inconsistent Flow Control Values

**Issue:** Handlers use inconsistent flow_control values:

| Handler | flow_control Value |
|---------|-------------------|
| op0000 | "CONTINUE" on miss |
| op0022 | "STOP_TURN" |
| op0023 | "CONTINUE" |
| op0024 | None (default) |
| op0025 | Not specified |
| op0052 | "STOP_ABILITY" if chain_failure |

**Impact:** Unclear semantics for when each flow control applies.

**Recommendation:** Document flow_control values and ensure consistency.

---

### 5. State 141 Special Case Hardcoded

**Issue:** State 141 (Dispel All Auroras) is hardcoded in op0031.

**Location:** `/home/yarizakurahime/engine/wow_claude/engine/effects/handlers/op0031_set_state.py:4,31-42`

**Code:**
```python
STATE_DISPEL_ALL_AURAS = 141
...
if state_id == STATE_DISPEL_ALL_AURAS and value == 1:
    ...
```

**Impact:** Magic numbers reduce maintainability.

**Recommendation:** Use constant from state definitions or make configurable.

---

### 6. Duplicate Handler Registration Risk

**Issue:** If two handlers register the same prop_id, later one overwrites earlier.

**Impact:** Silent failures if duplicate opcodes are added.

**Recommendation:** Add check in `register_handler` to warn on duplicate registration.

---

### 7. CC Resilient System Complexity

**Issue:** Multiple handlers (op0177, op0178, op026) interact with CC resilient states:

- op0177: Sets `cc_resilient_state` hint
- op0178: Applies CC with resilient reduction
- op0026: Reduces duration by resilient stacks

**Impact:** Complex state flow may lead to bugs.

**Recommendation:** Add integration tests for CC resilient flow.

---

## Low Priority Issues

### 8. Naming Inconsistencies

| Pattern | Examples |
|---------|----------|
| `H_Prop{id}_{name}` | H_Prop0_DmgPointsLegacy, H_Prop24_DmgPointsStd |
| Different capitalization | Some use `_dmg_`, some use `_Dmg_` |
| Duplicate handlers | op0052 and op0131 both named "aura_apply_simple" |

**Recommendation:** Establish naming convention and audit.

---

### 9. Semantic Registry Not Found

**Issue:** If `effect_properties_semantic.json` is not found, semantic registry returns None for all lookups.

**Impact:** Missing semantics means no validation or normalization.

**Code:**
```python
def load(self) -> None:
    ...
    if path is None or not path.exists():
        return  # Silent failure
```

**Recommendation:** Log warning when semantic file is missing.

---

### 10. Aura Manager Dependency

**Issue:** Aura handlers assume `ctx.aura` exists but don't validate before use.

**Location:** Multiple aura handlers (op0026, op0052, etc.)

**Impact:** AttributeError if aura manager not provided.

**Recommendation:** Add defensive check with graceful fallback.

---

## Handler-Specific Issues

| Handler | Issue | Priority |
|---------|-------|----------|
| op0000 | Legacy param_raw parsing may not match all formats | Medium |
| op0022 | Requires `ctx.scheduler` - may fail if not provided | Low |
| op0032 | Depends on `last_damage_dealt` being set | Medium |
| op0049 | Gate/phase logic may be incomplete | Medium |
| op0116 | Priority marker implementation may be partial | Low |
| op0136 | Sets `ctx.acc_ctx.dont_miss` without validation | Low |
| op0157 | Self-death state may not trigger game over | Low |

---

## Suggested Fixes Summary

### High Priority

1. Add try/except wrapper around handler.apply() calls
2. Add duplicate registration detection
3. Validate parameter parsing with proper defaults
4. Document flow_control values

### Medium Priority

5. Replace magic numbers with constants
6. Add defensive checks for ctx dependencies
7. Implement semantic registry warning on missing file
8. Add CC resilient integration tests

### Low Priority

9. Standardize handler naming convention
10. Review and document aura manager dependency
11. Add unit tests for edge cases
12. Consider thread safety for singleton handlers

---

## Verification Checklist

- [x] All 76 handlers have PROP_ID attribute
- [x] All handlers have apply() method
- [x] Handler PROP_ID matches registry key
- [x] Dispatcher routes correctly
- [x] ParamParser handles basic cases
- [x] Semantic registry loads if file exists
- [x] Damage pipeline implements formula
- [x] Heal pipeline implements formula
- [x] HitCheck computes correctly
- [ ] State manager handles edge cases
- [ ] Aura manager handles stack limits
- [ ] Cooldown system tracks expiration

---

## Testing Recommendations

### 1. Unit Tests Required

| Category | Test Cases |
|----------|------------|
| Damage | Zero points, max power, type advantage, crit, weather |
| Healing | Max HP scaling, variance, weather modifiers |
| Aura | Duration, refresh, stack limits, expire |
| State | Set, add, clamp, conditional |
| Hit Check | Accuracy, dodge, miss, weather |
| Pipeline | All modifiers combined |

### 2. Integration Tests

- Full ability chains with multiple effects
- Conditional effect execution
- Aura expiration triggering secondary effects
- State changes affecting subsequent effects

### 3. Edge Cases

- Zero/negative values
- Missing context attributes
- Invalid parameter types
- Concurrent access patterns

---

## Files Analyzed

| File | Purpose |
|------|---------|
| `engine/effects/dispatcher.py` | Effect routing |
| `engine/effects/registry.py` | Handler registration |
| `engine/effects/semantic_registry.py` | Schema validation |
| `engine/effects/param_parser.py` | Parameter parsing |
| `engine/effects/types.py` | EffectResult dataclass |
| `engine/resolver/hitcheck.py` | Hit chance calculation |
| `engine/resolver/damage_pipeline.py` | Damage formula |
| `engine/resolver/heal_pipeline.py` | Healing formula |
| `engine/resolver/state_manager.py` | State tracking |
| 76 handler files | Individual effect implementations |

---

*Generated by validate_effects.py*
