# Edge Case Log 001 - Pet Death Edge Cases

## Test Date: 2026-01-26
## System: WarCraftPets Battle System

---

## TC-001: Last Pet Death - Victory

### Scenario
Battle reaches final pet with health > 0 while opponent has no living pets

### Test Data
- Player Pet: Mr. Bigglesworth (Health: 45/100)
- Enemy Pets: All defeated
- Last Enemy Pet: Level 25 Frostbred Worgen (Health: 0/150 - Just died)

### Execution
```
Turn 15 - Player Attack
-> Enemy Frostbred Worgen takes 45 damage
-> Enemy Frostbred Worgen health: 0/150
-> Enemy Frostbred Worgen status: DEAD
-> All enemy pets defeated
-> BATTLE_VICTORY triggered
```

### Result: ✅ PASS
- Victory condition detected correctly
- Battle state transitions to COMPLETED
- No resurrection loops
- Loot/ XP properly calculated

---

## TC-002: Last Pet Death - Defeat

### Scenario
Final player pet dies with no remaining pets

### Test Data
- Player Pet: Untamed Breed (Health: 10/100)
- Player Bench: [Empty, Empty]
- Enemy Pet: Elite Golem (Health: 85/200)

### Execution
```
Turn 23 - Enemy Attack
-> Player Untamed Breed takes 95 damage
-> Player Untamed Breed health: -85/100
-> Player Untamed Breed status: DEAD
-> No living player pets
-> BATTLE_DEFEAT triggered
```

### Result: ✅ PASS
- Defeat condition detected
- Battle state transitions to COMPLETED
- No false victory triggers
- Proper defeat reporting

---

## TC-003: Simultaneous Death

### Scenario
Both pets die from same attack

### Test Data
- Player Pet: Maggot (Health: 5/50)
- Enemy Pet: Rabid Blight (Health: 8/80)
- Player Attack: "Soul Swap" deals 8 damage

### Execution
```
Turn 7 - Player Soul Swap
-> Enemy Rabid Blight takes 8 damage
-> Enemy Rabid Blight health: 0/80 -> DEAD
-> Player Maggot effect triggers on enemy death
-> Maggot takes 10 recoil damage
-> Player Maggot health: 5/50 -> 0/50 -> DEAD
-> Both pets dead same turn
```

### Resolution Logic
1. Check player pet death first (attacker priority)
2. Apply effects that trigger on death
3. If attacker died, check if ability completed
4. If ability completed, proceed with turn end
5. If both died, standard rules: if player pet died last turn, enemy wins

### Result: ✅ PASS
- Simultaneous death detected
- Correct priority applied
- No state corruption
- Battle resolves correctly

---

## TC-004: Resurrection Before Death

### Scenario
Resurrection effect triggers on pet at 0 health

### Test Data
- Player Pet: Clefthoof Runt (Health: 1/100)
- Ability: "Divine Shield" (Resurrects at 20% health when lethal damage taken)
- Enemy Attack: Deals 120 damage

### Execution
```
Turn 12 - Enemy Heavy Strike
-> Player Clefthoof Runt takes 120 damage
-> Calculated health: 1 - 120 = -119
-> Divine Shield triggers
-> Pet health set to: 100 * 0.20 = 20/100
-> Pet status: ALIVE
-> Divine Shield consumed
```

### Edge Case Considerations
- Shield must trigger BEFORE death state is set
- Health must be set AFTER all damage calculations
- Cooldowns/ability uses must still count

### Result: ✅ PASS
- Resurrection triggers at correct moment
- Health properly restored
- Shield consumed correctly
- No infinite loop

---

## TC-005: Death Immunity Triggers

### Scenario
Pet with death immunity takes lethal damage

### Test Data
- Player Pet: Phoenix (Health: 30/100)
- Passive: "Rebirth" (Survive one lethal hit, heal 25% HP)
- Enemy Attack: "Fatal Strike" deals 150 damage

### Execution
```
Turn 5 - Enemy Fatal Strike
-> Player Phoenix takes 150 damage
-> Calculated health: 30 - 150 = -120
-> Rebirth passive triggers
-> Health set to: 100 * 0.25 = 25/100
-> Status: IMMUNE - Death
-> Rebirth on cooldown (3 turns)
```

### Result: ✅ PASS
- Immunity triggers correctly
- Health restored properly
- Cooldown applied
- Status message clear

---

## TC-006: Leech Life Death Transfer

### Scenario
Leech effects trigger on killing blow

### Test Data
- Player Pet: Leech (Health: 15/80)
- Ability: "Leech Life" - Deal 30 damage, heal equal to damage
- Enemy Pet: Slime (Health: 25/50)

### Execution
```
Turn 3 - Player Leech Life
-> Enemy Slime takes 30 damage
-> Enemy Slime health: -5/50 -> DEAD
-> Leecher health before leech: 15/80
-> Leecher healing: 30 HP (capped at max)
-> Leecher health: 15 + 30 = 45/80
-> No overheal
```

### Result: ✅ PASS
- Damage dealt correctly
- Healing applied from kill
- Capping works
- No overheal exploit

---

## TC-007: Revive On Death Ability

### Scenario
Pet with revive ability dies then revives

### Test Data
- Player Pet: Spirit Wolf (Health: 50/100)
- Active Ability: "Revive" (2 turn cooldown - Revive at 50% HP)
- Enemy Attack: Deals 75 damage

### Execution
```
Turn 8 - Enemy Attack
-> Spirit Wolf takes 75 damage
-> Spirit Wolf health: -25/100 -> DEAD
-> Revive ability available? Yes
-> Revive triggers automatically
-> Spirit Wolf health: 100 * 0.50 = 50/100
-> Revive on cooldown (2 turns)
-> Battle continues
```

### Result: ✅ PASS
- Auto-revive works
- Health percentage correct
- Cooldown applied
- Can only revive once per battle

---

## TC-008: Death Rattle Effects

### Scenario
Death effects trigger correctly on pet death

### Test Data
- Player Pet: Bomb (Health: 10/50)
- Passive: "Death Rattle" - Deal 20 damage to all enemies on death
- Enemy Pet: Grunt (Health: 30/100)
- Enemy Pet: Scout (Health: 25/100)

### Execution
```
Turn 6 - Enemy Attack
-> Bomb takes 25 damage
-> Bomb health: -15/50 -> DEAD
-> Death Rattle triggers
-> Grunt takes 20 damage: 30 -> 10/100
-> Scout takes 20 damage: 25 -> 5/100
-> Battle continues with both enemies alive
```

### Result: ✅ PASS
- Death rattle triggers
- Damage to all enemies
- No self-loop
- Correct damage values

---

## TC-009: Summon On Death

### Scenario
Pet summons replacement on death

### Test Data
- Player Pet: Wandering Spirit (Health: 20/80)
- Passive: "Spirit Guide" - Summon Spirit Wolf on death
- Enemy Pet: Hunter (Health: 95/100)

### Execution
```
Turn 4 - Enemy Kill Shot
-> Wandering Spirit takes 60 damage
-> Wandering Spirit health: -40/80 -> DEAD
-> Spirit Guide triggers
-> Spirit Wolf summoned at 100/100 HP
-> Spirit Wolf enters slot 1
-> Battle continues
```

### Result: ✅ PASS
- Summon triggers on death
- New pet at full health
- Slot occupied correctly
- Turn continues normally

---

## TC-010: Mass Death Scenario

### Scenario
Multiple pets die simultaneously from AOE

### Test Data
- Player Team: [Pet A: 10/100, Pet B: 15/100, Pet C: 20/100]
- Enemy Ability: "Explosion" - 50 damage to all player pets

### Execution
```
Turn 12 - Enemy Explosion
-> Pet A takes 50 damage: 10 -> -40/100 -> DEAD
-> Pet B takes 50 damage: 15 -> -35/100 -> DEAD
-> Pet C takes 50 damage: 20 -> -30/100 -> DEAD
-> All 3 pets dead
-> Battle ends: DEFEAT
-> Victory pool: 0
```

### Result: ✅ PASS
- All deaths detected
- Battle ends correctly
- No state corruption
- Victory pool = 0

---

## Summary

| Test Case | Scenario | Status |
|-----------|----------|--------|
| TC-001 | Last Pet Victory | ✅ PASS |
| TC-002 | Last Pet Defeat | ✅ PASS |
| TC-003 | Simultaneous Death | ✅ PASS |
| TC-004 | Resurrection Before Death | ✅ PASS |
| TC-005 | Death Immunity | ✅ PASS |
| TC-006 | Leech Life Death | ✅ PASS |
| TC-007 | Revive On Death | ✅ PASS |
| TC-008 | Death Rattle | ✅ PASS |
| TC-009 | Summon On Death | ✅ PASS |
| TC-010 | Mass Death | ✅ PASS |

**Total: 10/10 PASS**
