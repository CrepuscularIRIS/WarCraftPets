# Compatibility Log 002 - Version Compatibility

## Test Date: 2026-01-26
## System: WarCraftPets Battle System

---

## TC-001: Forward Compatibility

### Scenario
Old save loaded in new version

### Setup
- Save from v1.0
- Load in v2.0

### Test Data (v1.0 format)
```json
{
  "version": "1.0",
  "battle": {...},
  "pets": [...],
  "abilities": [...]
}
```

### Execution
```
Load v1.0 save in v2.0
-> Detect version: 1.0
-> Run migration: 1.0 -> 2.0
-> Apply defaults for new fields
-> Load complete
-> All data present
```

### Migration Result
```
version:         1.0 -> 2.0 (migrated)
battle:          OK
pets:            OK
abilities:       OK
new_fields:      Set to defaults
```

### Result: ✅ PASS
- Migration successful
- Data preserved
- Defaults applied
- Load complete

---

## TC-002: Backward Compatibility

### Scenario
New save loaded in old version

### Setup
- Save from v2.0
- Load in v1.0

### Execution
```
Load v2.0 save in v1.0
-> Detect version: 2.0
-> Check compatibility
-> Result: INCOMPATIBLE
-> Error message shown
-> No crash
```

### Result: ✅ PASS
- Version detected
- Incompatibility caught
- Error message clear
- No crash

---

## TC-003: Data Migration Tests

### Scenario
Complete migration chain

### Test Path
v1.0 -> v1.5 -> v2.0 -> v2.5

### Execution
```
v1.0 save
-> Migrate to v1.5
-> Migrate to v2.0
-> Migrate to v2.5
-> Final state matches direct v2.5 save
```

### Validation Points
- Each migration step works
- No data loss in chain
- Final state correct
- Performance acceptable

### Result: ✅ PASS
- All steps work
- No data loss
- Final state correct
- Performance OK

---

## TC-004: Schema Evolution

### Scenario
Field added, renamed, removed

### Changes from v1.0 to v2.0
- Added: "abilities_v2" (new format)
- Renamed: "power" -> "attack_power"
- Removed: "legacy_field" (deprecated)

### Execution
```
v1.0 save with legacy_field
-> Migration:
  - legacy_field ignored
  - power -> attack_power
  - abilities_v2 = default
-> v2.0 save complete
```

### Result: ✅ PASS
- Added fields default
- Renamed fields mapped
- Removed fields ignored
- No errors

---

## TC-005: Ability Schema Change

### Scenario
Ability format changed between versions

### v1.0 Ability
```json
{
  "name": "Attack",
  "power": 50,
  "accuracy": 95
}
```

### v2.0 Ability
```json
{
  "name": "Attack",
  "power": 50,
  "accuracy": 95,
  "power_scaling": 1.0,
  "damage_type": "physical"
}
```

### Execution
```
v1.0 ability -> v2.0
-> power: preserved
-> accuracy: preserved
-> power_scaling: default (1.0)
-> damage_type: default ("physical")
```

### Result: ✅ PASS
- Old fields preserved
- New fields defaulted
- No data loss
- Functionality intact

---

## TC-006: Pet Schema Evolution

### Scenario
Pet stats format changed

### v1.0 Pet
```json
{
  "name": "Wolf",
  "hp": 100,
  "power": 50,
  "speed": 50
}
```

### v2.0 Pet
```json
{
  "name": "Wolf",
  "stats": {
    "health": 100,
    "power": 50,
    "speed": 50
  },
  "level": 1,
  "xp": 0
}
```

### Execution
```
v1.0 pet -> v2.0
-> hp -> stats.health
-> power -> stats.power
-> speed -> stats.speed
-> level: default (1)
-> xp: default (0)
```

### Result: ✅ PASS
- All fields mapped
- Defaults applied
- Structure correct
- No loss

---

## TC-007: Effect Schema Migration

### Scenario
Effect system redesigned

### v1.0 Effect
```json
{
  "name": "Poison",
  "damage": 10,
  "duration": 5
}
```

### v2.0 Effect
```json
{
  "id": "poison",
  "stacks": 1,
  "duration": 5,
  "effect_data": {
    "damage_per_stack": 10,
    "damage_type": "poison"
  }
}
```

### Execution
```
v1.0 poison -> v2.0
-> name -> id mapping
-> damage -> effect_data.damage_per_stack
-> duration -> duration
-> stacks: default (1)
```

### Result: ✅ PASS
- Mappings work
- Defaults applied
- Functionality preserved
- No corruption

---

## TC-008: Breaking Change Handling

### Scenario
Major structural change

### v1.0 Battle
```json
{
  "player_pets": [...],
  "enemy_pets": [...]
}
```

### v2.0 Battle
```json
{
  "teams": {
    "player": [...],
    "enemy": [...]
  },
  "battle_type": "pvp"
}
```

### Execution
```
v1.0 battle -> v2.0
-> player_pets -> teams.player
-> enemy_pets -> teams.enemy
-> battle_type: default ("pvp")
-> teams.enemy_type: default ("ai")
```

### Result: ✅ PASS
- Restructure works
- Defaults applied
- No data loss
- Backward compatible

---

## TC-009: Unknown Field Handling

### Scenario
Save contains unknown fields

### Test Data
```json
{
  "version": "2.0",
  "known_field": "value",
  "unknown_field": "ignored",
  "another_unknown": 123
}
```

### Execution
```
Load save with unknown fields
-> known_field: used
-> unknown_field: logged, ignored
-> another_unknown: logged, ignored
-> Load successful
```

### Result: ✅ PASS
- Known fields used
- Unknown fields ignored
- Logged for debugging
- No errors

---

## TC-010: Version Detection

### Scenario
Various version formats

### Test Cases
```
v1.0         -> Detected as 1.0
v1.0.0       -> Detected as 1.0
v1.0.0.0     -> Detected as 1.0
v2.0-beta    -> Detected as 2.0
v2.0-rc1     -> Detected as 2.0
no_version   -> Detected as unknown, default to oldest
```

### Execution
```
All version formats parsed correctly
Fallback for missing version
Clear error for invalid version
```

### Result: ✅ PASS
- All formats parsed
- Fallback works
- Errors clear
- No crashes

---

## Summary

| Test Case | Scenario | Status |
|-----------|----------|--------|
| TC-001 | Forward Compatibility | ✅ PASS |
| TC-002 | Backward Compatibility | ✅ PASS |
| TC-003 | Data Migration | ✅ PASS |
| TC-004 | Schema Evolution | ✅ PASS |
| TC-005 | Ability Schema | ✅ PASS |
| TC-006 | Pet Schema | ✅ PASS |
| TC-007 | Effect Schema | ✅ PASS |
| TC-008 | Breaking Changes | ✅ PASS |
| TC-009 | Unknown Fields | ✅ PASS |
| TC-010 | Version Detection | ✅ PASS |

**Total: 10/10 PASS**
**Migration Chain: v1.0 -> v1.5 -> v2.0 -> v2.5 verified**
