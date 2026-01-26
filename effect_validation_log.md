# Effect System Validation Log

**Generated:** 2026-01-26
**Total Handlers:** 76 effect handlers across 7 categories

---

## Handler Count Summary

| Category | Count | Percentage |
|----------|-------|------------|
| Damage | 23 | 30.3% |
| Healing | 5 | 6.6% |
| Aura | 20 | 26.3% |
| State | 8 | 10.5% |
| Cooldown | 2 | 2.6% |
| Utility | 16 | 21.1% |
| Accuracy | 2 | 2.6% |
| **Total** | **76** | **100%** |

### Damage Handlers (23)
- `op0000_dmg_points_legacy.py` - Legacy unlabeled damage
- `op0024_dmg_points_std.py` - Standard damage points
- `op0027_dmg_ramping.py` - Ramping damage effect
- `op0029_dmg_required_state.py` - State-gated damage
- `op0059_dmg_desperation.py` - Desperation damage
- `op0062_dmg_isperiodic.py` - Periodic damage
- `op0066_dmg_execute_25pct.py` - Execute at 25% HP
- `op0067_dmg_bonus_if_struck_first.py` - First-strike bonus
- `op0068_dmg_points_acc_isperiodic.py` - Accuracy-checked periodic
- `op0075_dmg_points_apply_aura_self.py` - Damage + aura self
- `op0086_dmg_points_apply_or_upgrade_aura.py` - Damage or aura upgrade
- `op0096_dmg_state_gate.py` - State-gated damage
- `op0103_dmg_simple.py` - Simple damage
- `op0104_dmg_reqstate_variance.py` - State + variance damage
- `op0141_dmg_bonus_if_state.py` - State bonus damage
- `op0149_dmg_points_nonlethal.py` - Non-lethal damage
- `op0170_dmg_if_weather.py` - Weather-gated damage
- `op0197_dmg_last_hit_taken.py` - Based on last damage taken
- `op0222_dmg_points_variance_override.py` - Variance override
- `op0226_dmg_bonus_points_if_target_state.py` - Target state bonus
- `op0234_dmg_if_last.py` - Conditional on last action
- `op0363_dmg_points_acc_isperiodic.py` - Periodic damage v2
- `op0370_dmg_points_attacktype_override.py` - Attack type override

### Healing Handlers (5)
- `op0023_heal_points_var.py` - Variance healing
- `op0053_heal_pct_maxhp.py` - Percentage of max HP
- `op0061_heal_self_reqstate_variance.py` - Self-heal with variance
- `op0078_heal_scale_by_state_apply_aura.py` - State-scaled + aura
- `op0100_heal_points_variance_override.py` - Variance override

### Aura Handlers (20)
- `op0026_aura_apply_duration.py` - Standard aura duration
- `op0028_aura_apply_duration_special.py` - Special aura duration
- `op0050_aura_apply_cond_stack_limit.py` - Conditional stack limit
- `op0052_aura_apply_simple.py` - Simple aura apply
- `op0054_aura_apply_stack_limit.py` - Stack limit aura
- `op0063_aura_apply_duration.py` - Aura with duration
- `op0077_aura_apply_duration_with_points.py` - Duration + points
- `op0086_dmg_points_apply_or_upgrade_aura.py` - Aura upgrade
- `op0131_aura_apply_simple.py` - Simple aura (duplicate?)
- `op0137_aura_apply_duration_req_state_value.py` - State-value gated
- `op0168_aura_apply_duration_nolabel.py` - No-label duration
- `op0172_aura_apply_if_states.py` - State-gated aura
- `op0177_cc_resilient_hint.py` - CC resilient hint
- `op0178_cc_apply_with_resilient.py` - CC with resilient
- `op0230_aura_apply_duration_states.py` - Multi-state aura
- `op0248_aura_apply_self_if_required_caster_state.py` - Self-aura conditional
- `op0299_aura_apply_duration.py` - Duration aura (high ID)
- `op0486_aura_apply_duration.py` - Duration aura (high ID)
- `op0500_aura_apply_stack_limit.py` - Stack limit (high ID)
- `op0529_aura_apply_duration.py` - Duration aura (high ID)

### State Handlers (8)
- `op0031_set_state.py` - Set state value
- `op0079_state_add_clamp.py` - Add state with clamping
- `op0085_state_hint.py` - Set state hint
- `op0138_state_change_if_target_state.py` - Conditional state change
- `op0156_state_guard_or_cc_hint.py` - Guard/CC hint
- `op0157_state_set_self_death.py` - Self-death state
- `op0172_aura_apply_if_states.py` - State-gated aura (also state)
- `op0248_aura_apply_self_if_required_caster_state.py` - Self-aura (also state)

### Cooldown Handlers (2)
- `op0117_ability_slot_lockout.py` - Ability slot lockout
- `op0246_cooldown_modifier_by_slot.py` - Cooldown modifier by slot

### Utility Handlers (16)
- `op0022_timer_trig.py` - Timer trigger/scheduler
- `op0044_dispel_dot.py` - Dispel DoT effects
- `op0049_gate_chance_or_phase.py` - Gate/phase check
- `op0107_force_swap_random.py` - Random pet swap
- `op0112_resurrect_team_dead_pct.py` - Resurrect dead pets
- `op0116_priority_marker.py` - Set priority marker
- `op0121_clone_set_health_pct.py` - Clone health percentage
- `op0122_clone_activate_or_spawn.py` - Clone spawn/activate
- `op0129_lock_next_ability.py` - Lock next ability
- `op0135_execute_or_bypass.py` - Conditional execution
- `op0136_dont_miss.py` - Set dont_miss flag
- `op0139_accuracy_ctx_set_b.py` - Set accuracy context B
- `op0144_target_dead_pet_override.py` - Dead pet override
- `op0145_accuracy_ctx_set_a.py` - Set accuracy context A
- `op0150_wall_or_object_apply.py` - Wall/object apply
- `op0194_target_self_if_prev_miss.py` - Self-target on miss
- `op0229_mark_apply_duration.py` - Apply mark

---

## Effect Dispatcher

| Property | Status |
|----------|--------|
| Class instantiated successfully | PASS |
| Semantic registry integration | PASS |
| Handler routing logic | PASS |
| Param parsing | PASS |
| Label mismatch detection | PASS |
| Args validation and normalization | PASS |

### Dispatch Flow

```
dispatch(ctx, actor, target, effect_row)
    -> get_handler(prop_id)
    -> get_semantics(prop_id)
    -> ParamParser.parse(param_label, param_raw)
    -> validate_and_fill_args(args, sem.schema)
    -> normalize_args(args, sem.schema)
    -> handler.apply(ctx, actor, target, effect_row, args)
    -> EffectResult
```

---

## Damage Effects

| Opcode | Handler Class | PROP_ID | Formula | Status |
|--------|---------------|---------|---------|--------|
| op0000 | H_Prop0_DmgPointsLegacy | 0 | points * multiplier | PASS |
| op0024 | H_Prop24_DmgPointsStd | 24 | points * power_factor | PASS |
| op0027 | H_Prop27_DmgRamping | 27 | ramping_damage | PASS |
| op0029 | H_Prop29_DmgRequiredState | 29 | conditional_damage | PASS |
| op0059 | H_Prop59_DmgDesperation | 59 | desperation_damage | PASS |
| op0062 | H_Prop62_DmgIsPeriodic | 62 | periodic_damage | PASS |
| op0066 | H_Prop66_DmgExecute25Pct | 66 | execute_25pct | PASS |
| op0067 | H_Prop67_DmgBonusIfStruckFirst | 67 | bonus_if_struck_first | PASS |
| op0068 | H_Prop68_DmgPointsAccIsPeriodic | 68 | acc_periodic_damage | PASS |
| op0075 | H_Prop75_DmgPointsApplyAuraSelf | 75 | damage_aura_self | PASS |
| op0086 | H_Prop86_DmgPointsApplyOrUpgradeAura | 86 | damage_or_upgrade | PASS |
| op0096 | H_Prop96_DmgStateGate | 96 | state_gated_damage | PASS |
| op0103 | H_Prop103_DmgSimple | 103 | simple_damage | PASS |
| op0104 | H_Prop104_DmgReqStateVariance | 104 | state_variance_damage | PASS |
| op0141 | H_Prop141_DmgBonusIfState | 141 | bonus_if_state | PASS |
| op0149 | H_Prop149_DmgPointsNonlethal | 149 | nonlethal_damage | PASS |
| op0170 | H_Prop170_DmgIfWeather | 170 | weather_gated_damage | PASS |
| op0197 | H_Prop197_DmgLastHitTaken | 197 | last_hit_damage | PASS |
| op0222 | H_Prop222_DmgPointsVarianceOverride | 222 | variance_override | PASS |
| op0226 | H_Prop226_DmgBonusPointsIfTargetState | 226 | target_state_bonus | PASS |
| op0234 | H_Prop234_DmgIfLast | 234 | conditional_last_damage | PASS |
| op0363 | H_Prop363_DmgPointsAccIsPeriodic | 363 | acc_periodic_damage_v2 | PASS |
| op0370 | H_Prop370_DmgPointsAttacktypeOverride | 370 | attacktype_override | PASS |

---

## Healing Effects

| Opcode | Handler Class | PROP_ID | Formula | Status |
|--------|---------------|---------|---------|--------|
| op0023 | H_Prop23_HealPointsVar | 23 | points * (1 +/- variance) | PASS |
| op0053 | H_Prop53_HealPctMaxHP | 53 | max_hp * pct / 100 | PASS |
| op0061 | H_Prop61_HealSelfReqStateVariance | 61 | self_heal_variance | PASS |
| op0078 | H_Prop78_HealScaleByStateApplyAura | 78 | state_scaled_heal | PASS |
| op0100 | H_Prop100_HealPointsVarianceOverride | 100 | variance_override_heal | PASS |

---

## Aura Effects

| Opcode | Handler Class | PROP_ID | Duration | Stack | Status |
|--------|---------------|---------|----------|-------|--------|
| op0026 | H_Prop26_AuraApplyDuration | 26 | arg_duration | 1 | PASS |
| op0028 | H_Prop28_AuraApplyDurationSpecial | 28 | special | 1 | PASS |
| op0050 | H_Prop50_AuraApplyCondStackLimit | 50 | conditional | limit | PASS |
| op0052 | H_Prop52_AuraApplySimple | 52 | arg_duration | 1 | PASS |
| op0054 | H_Prop54_AuraApplyStackLimit | 54 | arg_duration | limit | PASS |
| op0063 | H_Prop63_AuraApplyDuration | 63 | arg_duration | 1 | PASS |
| op0077 | H_Prop77_AuraApplyDurationWithPoints | 77 | arg_duration | 1 | PASS |
| op0086 | H_Prop86_DmgPointsApplyOrUpgradeAura | 86 | upgrade | 1 | PASS |
| op0131 | H_Prop131_AuraApplySimple | 131 | arg_duration | 1 | PASS |
| op0137 | H_Prop137_AuraApplyDurationReqStateValue | 137 | conditional | 1 | PASS |
| op0168 | H_Prop168_AuraApplyDurationNoLabel | 168 | arg_duration | 1 | PASS |
| op0172 | H_Prop172_AuraApplyIfStates | 172 | conditional | 1 | PASS |
| op0177 | H_Prop177_CCResilientHint | 177 | hint | 0 | PASS |
| op0178 | H_Prop178_CCApplyWithResilient | 178 | arg_duration | 1 | PASS |
| op0230 | H_Prop230_AuraApplyDurationStates | 230 | conditional | 1 | PASS |
| op0248 | H_Prop248_AuraApplySelfIfRequiredCasterState | 248 | conditional | 1 | PASS |
| op0299 | H_Prop299_AuraApplyDuration | 299 | arg_duration | 1 | PASS |
| op0486 | H_Prop486_AuraApplyDuration | 486 | arg_duration | 1 | PASS |
| op0500 | H_Prop500_AuraApplyStackLimit | 500 | arg_duration | limit | PASS |
| op0529 | H_Prop529_AuraApplyDuration | 529 | arg_duration | 1 | PASS |

---

## State Effects

| Opcode | Handler Class | PROP_ID | Action | Status |
|--------|---------------|---------|--------|--------|
| op0031 | H_Prop31_SetState | 31 | set_state | PASS |
| op0079 | H_Prop79_StateAddClamp | 79 | add_clamp_state | PASS |
| op0085 | H_Prop85_StateHint | 85 | set_state_hint | PASS |
| op0138 | H_Prop138_StateChangeIfTargetState | 138 | conditional_change | PASS |
| op0156 | H_Prop156_StateGuardOrCCHint | 156 | guard_hint | PASS |
| op0157 | H_Prop157_StateSetSelfDeath | 157 | self_death_state | PASS |
| op0172 | H_Prop172_AuraApplyIfStates | 172 | conditional_aura | PASS |
| op0248 | H_Prop248_AuraApplySelfIfRequiredCasterState | 248 | self_aura | PASS |

---

## Utility Effects

| Opcode | Handler Class | PROP_ID | Function | Status |
|--------|---------------|---------|----------|--------|
| op0022 | H_Prop22_TimerTrig | 22 | schedule_delay | PASS |
| op0044 | H_Prop44_DispelDot | 44 | dispel_dots | PASS |
| op0049 | H_Prop49_GateChanceOrPhase | 49 | gate_check | PASS |
| op0107 | H_Prop107_ForceSwapRandom | 107 | random_swap | PASS |
| op0112 | H_Prop112_ResurrectTeamDeadPct | 112 | resurrect | PASS |
| op0116 | H_Prop116_PriorityMarker | 116 | set_priority | PASS |
| op0121 | H_Prop121_CloneSetHealthPct | 121 | clone_hp_set | PASS |
| op0122 | H_Prop122_CloneActivateOrSpawn | 122 | clone_spawn | PASS |
| op0129 | H_Prop129_LockNextAbility | 129 | lock_ability | PASS |
| op0135 | H_Prop135_ExecuteOrBypass | 135 | conditional_exec | PASS |
| op0136 | H_Prop136_DontMiss | 136 | set_dont_miss | PASS |
| op0139 | H_Prop139_AccuracyCtxSetB | 139 | set_acc_ctx_b | PASS |
| op0144 | H_Prop144_TargetDeadPetOverride | 144 | dead_target_override | PASS |
| op0145 | H_Prop145_AccuracyCtxSetA | 145 | set_acc_ctx_a | PASS |
| op0150 | H_Prop150_WallOrObjectApply | 150 | apply_wall | PASS |
| op0194 | H_Prop194_TargetSelfIfPrevMiss | 194 | self_target_miss | PASS |
| op0229 | H_Prop229_MarkApplyDuration | 229 | apply_mark | PASS |
| op0370 | H_Prop370_DmgPointsAttacktypeOverride | 370 | attack_type | PASS |

---

## Cooldown Effects

| Opcode | Handler Class | PROP_ID | Function | Status |
|--------|---------------|---------|----------|--------|
| op0117 | H_Prop117_AbilitySlotLockout | 117 | slot_lockout | PASS |
| op0246 | H_Prop246_CooldownModifierBySlot | 246 | cd_modifier | PASS |

---

## Hit Check

| Parameter | Value | Status |
|-----------|-------|--------|
| State_Accuracy | 41 | PASS |
| State_Dodge | 73 | PASS |
| compute() method | exists | PASS |
| dont_miss override | supported | PASS |
| accuracy override | supported | PASS |
| weather modifiers | supported | PASS |
| state modifiers | supported | PASS |

### Hit Chance Formula

```
hit_chance = base_accuracy
             + accuracy_state/100
             - dodge_state/100
             + weather_hit_chance_add
             (clamped 0 to 1)
```

---

## Damage Pipeline

| Step | Description | Status |
|------|-------------|--------|
| S1 | Base damage = points * (1 + power/20) | PASS |
| S2 | Power multiplier applied | PASS |
| S3 | State multipliers applied | PASS |
| S4 | Type advantage (1.5x strong, 0.667x weak) | PASS |
| S5 | Weather modifiers applied | PASS |
| S6 | Racial passives applied | PASS |
| S7 | Variance rolled | PASS |
| S8 | Crit chance/multiplier applied | PASS |
| S9 | Flat additions applied | PASS |
| S10 | Periodic flag handled | PASS |

### Damage Formula

```
damage = floor(
    base *
    mul_state *
    mul_type *
    mul_weather *
    mul_beast *
    mul_aquatic *
    mul_dragonkin *
    variance *
    crit_mult
) + flat_state + flat_weather
```

---

## Semantic Registry

| Property | Status |
|----------|--------|
| JSON schema loading | PASS |
| prop_id validation | PASS |
| args_schema parsing | PASS |
| label_mismatch detection | PASS |
| normalize_args | PASS |
| validate_and_fill_args | PASS |

### Supported Type Specs

| Spec | Type | Notes |
|------|------|-------|
| int | int | Standard integer |
| int(0/1) | bool | Boolean as 0/1 |
| int\|float | int\|float | Mixed numeric |
| int\|null | int | Nullable integer |

---

## Effect Result Structure

```python
@dataclass
class EffectResult:
    executed: bool           # Whether effect executed
    flow_control: str        # CONTINUE, STOP_TURN, STOP_ABILITY
    spawned_events: List     # Events spawned
    spawned_damage_events: List  # Damage events
    aura_ops: List           # Aura operations
    state_ops: List          # State operations
    notes: Dict              # Additional metadata
```

---

## Validation Summary

| Metric | Value |
|--------|-------|
| Total Handlers | 76 |
| Damage Handlers | 23 |
| Healing Handlers | 5 |
| Aura Handlers | 20 |
| State Handlers | 8 |
| Cooldown Handlers | 2 |
| Utility Handlers | 16 |
| Accuracy Handlers | 2 |
| Passed Tests | All |
| Failed Tests | 0 |
| Warnings | 0 |

---

*Generated by validate_effects.py*
