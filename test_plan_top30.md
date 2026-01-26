# Top30 EffectProperties Unit Test Plan (wow_export_merged.xlsx)

- Total effect rows: 2791
- Top30 coverage: 89.5378%
- All tests MUST be deterministic under a fixed RNG seed (injectable RNG provider).

## 0. Test harness conventions

### 0.1 Deterministic RNG
- Provide an RNG interface that can be fed a pre-defined sequence for: hit rolls, gate rolls, variance rolls, crit rolls.
- Each test must assert both the final result and the consumption order of RNG values (replayability).

### 0.2 Canonical pets for tests
- Use a minimal Pet model with: type (PetTypeEnum 0..9), max_hp, cur_hp, power, speed, active_auras[], states{}.
- Unless the test requires otherwise: no auras, no states, no weather, type advantage neutral, variance=1.0, crit disabled.

### 0.3 Canonical damage pipeline (S0..S10)
- Pipeline MUST follow the locked order S0..S10 and apply floor at each step boundary where defined.
- Type advantage uses exact rationals: strong=3/2, weak=2/3, neutral=1.

## 1. Cross-cutting pipeline tests (not tied to a single PropID)

### UT-DMG-BASE-001: points/power base damage
**Given** points=15, caster.power=100 (power/20=5) and a neutral context (no mods)\
**When** computing D_base using floor(points*(1+power/20))\
**Then** D_base = floor(15*(1+5)) = 90

### UT-DMG-TADV-001: type advantage (strong/weak)
**Given** D4=90, strong advantage\
**When** applying type advantage\
**Then** D5 = floor(90 * 3/2) = 135
**And** for weak advantage, D5 = floor(90 * 2/3) = 60

### UT-DMG-MH-001: multi-hit independence
**Given** a 2-hit skill (two separate DamageEvents) with flat reduction -10 (S4)\
**When** both hits resolve\
**Then** S4 applies -10 to each hit separately and total damage is the sum of per-hit finals

## 2. Top30 PropID-specific tests

> For each PropID below, implement at least the listed tests. Use either a minimal synthetic skill script or a real ability from the dataset (examples listed in effect_properties_semantic.yml).

### PropID 24: DMG_POINTS_STD
ParamLabel: `Points,Accuracy,IsPeriodic,OverrideIndex,,`

- **UT-OP24-001**: Parse Points/Accuracy/IsPeriodic/OverrideIndex; with Accuracy=0 and dont_miss absent, Step0 must miss and FinalDamage=0.
- **UT-OP24-002**: IsPeriodic=1 marks a tick event; ensure it is routed through periodic scheduling and can be modified by Aquatic DoT passive (if DoT).

### PropID 26: AURA_APPLY_DURATION
ParamLabel: `Unused,Accuracy,Duration,TickDownFirstRound,,`

- **UT-OP26-001**: Apply aura with duration=3 and TickDownFirstRound=0 vs 1; verify remaining duration after application and at next turn boundary.
- **UT-OP26-002**: Accuracy miss: aura is not applied; chain continues according to outer Turn semantics.

### PropID 50: AURA_APPLY_COND_STACK_LIMIT
ParamLabel: `ChainFailure,Accuracy,Duration,MaxAllowed,CasterState,TargetState`

- **UT-OP50-001**: Gate fails (missing caster_state/target_state): aura not applied; validate chain_failure behaviour (continue/stop effects).
- **UT-OP50-002**: MaxAllowed reached: further applications are rejected or refresh per rules; validate stack count and chain_failure.

### PropID 49: GATE_CHANCE_OR_PHASE
ParamLabel: `Chance,unused,,,,`

- **UT-OP49-001**: Chance gate consumes gate RNG; when fails, effect is skipped and log shows gate_pass=false (deterministic under seed).
- **UT-OP49-002**: If used for phase (e.g., airborne/underground), verify that subsequent Step0 hit checks respect unattackable phase.

### PropID 23: DMG_POINTS_VARIANCE
ParamLabel: `Points,Accuracy,Variance,,,`

- **UT-OP23-001**: Variance parameter overrides default S7; with fixed variance roll, verify the exact pre/post-floor value.
- **UT-OP23-002**: Variance interacts with crit: apply S7 then S8; verify flooring order.

### PropID 222: DMG_POINTS_VARIANCE_OVERRIDE
ParamLabel: `Points,Accuracy,Variance,OverrideIndex,,`

- **UT-OP222-001**: OverrideIndex routes to the intended component/variant; verify the selected base points.
- **UT-OP222-002**: Same as UT-OP23-001 but with override_index present; ensure logs include override_index.

### PropID 31: STATE_SET
ParamLabel: `State,StateValue,,,,`

- **UT-OP31-001**: State overwrite: set state=141 to value=1 then set again to 3; verify final=3 (not additive).
- **UT-OP31-002**: State influences a gated damage effect (combine with PropID 29/141): verify branch changes when state differs.

### PropID 54: AURA_APPLY_STACK_LIMIT
ParamLabel: `ChainFailure,Accuracy,Duration,MaxAllowed,,`

- **UT-OP54-001**: MaxAllowed=1: second application is rejected or refreshes per policy; validate chain_failure.
- **UT-OP54-002**: Stack count does not exceed MaxAllowed; ensure deterministic results across replays.

### PropID 158: GATE_CHANCE
ParamLabel: `Chance,,,,,`

- **UT-OP158-001**: Chance gate controls whether subsequent effect executes; verify skip list and RNG consumption.
- **UT-OP158-002**: Gate pass executes next effect and produces expected output (use a simple damage effect as follower).

### PropID 22: TIMER_TRIG
ParamLabel: `Points,MorePoints,EvenMorePoints,,,`

- **UT-OP22-001**: Registers a countdown that fires after N turns; verify scheduling key and fire time.
- **UT-OP22-002**: Timer cancelled or replaced by re-application: verify only one active timer per key (if policy says so).

### PropID 116: PRIORITY_MARKER
ParamLabel: `,,,,,`

- **UT-OP116-001**: Two pets same speed: priority marker makes one act first; validate tie-break vs RNG.
- **UT-OP116-002**: Priority marker does not change damage numbers; only order of execution.

### PropID 52: AURA_APPLY_SIMPLE
ParamLabel: `ChainFailure,Accuracy,Duration,,,`

- **UT-OP52-001**: Apply aura duration=2; verify expiry and removal.
- **UT-OP52-002**: If aura is CC (stun/sleep), verify Critter passive filter reduces/blocks accordingly.

### PropID 28: AURA_APPLY_DURATION_SPECIAL
ParamLabel: `Unused,Accuracy,Duration,TickDownFirstRound,,`

- **UT-OP28-001**: Duration=-1 treated as permanent until removed; verify it persists across turns.
- **UT-OP28-002**: TickDownFirstRound behaviour still applies even for special durations (if defined).

### PropID 85: STATE_HINT
ParamLabel: `State,,,,,`

- **UT-OP85-001**: Set a context hint state and ensure the next handler reads it and changes behaviour (assert via logs).
- **UT-OP85-002**: Hint alone does not change stats or damage; verify no side effect.

### PropID 177: CC_RESILIENT_HINT
ParamLabel: `State,StatePoints,unused,unused,,`

- **UT-OP177-001**: Apply CC with target resilient state; verify duration reduction and immune reporting if applicable.
- **UT-OP177-002**: Resilient hint is consumed/updated as designed (state points change).

### PropID 79: STATE_ADD_CLAMP
ParamLabel: `State,StateChange,StateMin,StateMax,,`

- **UT-OP79-001**: Delta pushes above max: clamp at max; below min: clamp at min.
- **UT-OP79-002**: If used for speed mod, verify initiative changes accordingly (couple with priority/speed test).

### PropID 32: POST_DAMAGE_LIFESTEAL
ParamLabel: `Points,Accuracy,ChainFailure,,,`

- **UT-OP32-001**: When last damage dealt is 0, no heal occurs; when >0, heal occurs deterministically.
- **UT-OP32-002**: Multi-hit semantics: configure per-hit vs per-ability; assert the chosen policy and log it.

### PropID 80: WEATHER_SET
ParamLabel: `Points,Accuracy,Duration,ChainFailure,,`

- **UT-OP80-001**: Weather replace: new weather overwrites old; duration tracked; Step6 uses the active weather modifier.
- **UT-OP80-002**: Elemental passive: negative weather effects filtered; verify different outcomes for Elemental vs non-Elemental targets.

### PropID 178: APPLY_CC_WITH_IMMUNE_REPORT
ParamLabel: `StatePoints,Accuracy,Duration,TargetState,ChainFailure,ReportFailsAsImmune`

- **UT-OP178-001**: Target has immune/resilient state: CC application fails; if report_fails_as_immune=1, must report immune.
- **UT-OP178-002**: Successful CC application applies duration and updates states; logs include target_state and report flag.

### PropID 135: IMMUNITY_FILTER_BYPASS_PASSIVES
ParamLabel: `Accuracy,CasterImmuneState,TargetImmuneState,enableReverse,BypassPetPassives,`

- **UT-OP135-001**: When bypass_pet_passives=1, define and enforce which passives are bypassed (at minimum MagicCap/UndeadClip tests must cover).
- **UT-OP135-002**: enableReverse flips immune logic: verify immune becomes vulnerable (or the inverse) per policy.

### PropID 29: DMG_REQUIRED_STATE
ParamLabel: `Points,Accuracy,RequiredCasterState,RequiredTargetState,IsPeriodic,`

- **UT-OP29-001**: Missing required states: no damage event created and no post hooks fired.
- **UT-OP29-002**: Required states present: damage resolves through Step0..10 with expected result.

### PropID 62: DMG_ISPERIODIC
ParamLabel: `Points,Accuracy,IsPeriodic,,,`

- **UT-OP62-001**: Periodic tick resolves as DamageEvent; verify periodic flag, tick counter, and deterministic RNG consumption.
- **UT-OP62-002**: Aquatic passive: periodic (DoT) damage taken is reduced by a fixed factor (recommended default 0.75, configurable); tests must enforce the chosen value and insertion point.

### PropID 141: DMG_BONUS_IF_STATE
ParamLabel: `Points,Accuracy,BonusState,BonusPoints,,`

- **UT-OP141-001**: BonusState absent: base points only.
- **UT-OP141-002**: BonusState present: bonus_points applied (policy: add-to-points vs add-component) and logged.

### PropID 103: DMG_SIMPLE
ParamLabel: `Points,Accuracy,,,,`

- **UT-OP103-001**: Simple damage points+accuracy; verify match with UT-DMG-BASE-001 in neutral context.
- **UT-OP103-002**: With strong/weak type advantage, verify UT-DMG-TADV-001 results.

### PropID 27: DMG_RAMPING
ParamLabel: `Points,Accuracy,PointsIncreasePerUse,PointsMax,StateToTriggerMaxPoints,`

- **UT-OP27-001**: Use count increments points by points_increase_per_use until points_max; verify three successive uses.
- **UT-OP27-002**: StateToTriggerMaxPoints forces points to points_max; verify when state toggles.

### PropID 136: DONT_MISS
ParamLabel: `DontMiss,,,,,`

- **UT-OP136-001**: Force hit: even if accuracy=0, Step0 must hit; verify RNG hit roll not consumed (or consumed but ignored, per policy).
- **UT-OP136-002**: Interaction with immunity: define whether dont_miss bypasses immunity; tests must enforce chosen behaviour.

### PropID 145: ACCURACY_CTX_SET_A
ParamLabel: `Accuracy,,,,,`

- **UT-OP145-001**: Accuracy override applies to subsequent damage effects within scope; verify push/pop by effect order.
- **UT-OP145-002**: Scope ends correctly (end of turn or end of ability) and does not leak to other abilities.

### PropID 139: ACCURACY_CTX_SET_B
ParamLabel: `Accuracy,,,,,`

- **UT-OP139-001**: If treated as same family as 145, stacking works; verify two overrides use last-wins within scope.
- **UT-OP139-002**: If future reverse-engineering shows different scope, update mapping and adjust tests accordingly.

### PropID 157: DEATH_FLOW_STATE
ParamLabel: `State,StatePoints,unused,unused,,`

- **UT-OP157-001**: Death flow hook: integrate with Undead clip and Mechanical resurrection; verify only one passive proc per policy.
- **UT-OP157-002**: State transitions on death are deterministic and logged (replayable).

### PropID 111: PCT_HP_EFFECT
ParamLabel: `Percentage,Unused,Unused,Unused,,`

- **UT-OP111-001**: Percentage-of-HP base: lock reference (maxhp vs currenthp) and verify computed base at Step1.
- **UT-OP111-002**: Percent damage still respects caps (MagicCap) and death interceptors (Undead clip).
