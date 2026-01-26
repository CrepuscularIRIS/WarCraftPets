from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(370)
class H_Prop370_DmgPointsAttackTypeOverride:
    """Prop370: Deal damage with explicit attack-type override (raw-slot schema).

    Observed in this engine's ability_pack:
      - 2259 Species Attack   params_raw: [16, 0, 3, 0, 0, 0]
      - 2280 test attack      params_raw: [20, 100, 3, 0, 0, 0]
      - 2283 Dragon's Call    params_raw: [25, 100, 7, 0, 0, 0]

    The pack exports for this prop have no ParamLabel. We interpret:
      slot0: Points
      slot1: Accuracy (0 means always hit, per pack convention)
      slot2: AttackTypeOverride (pet family type enum 0..9)
      slot3: IsPeriodic (optional; 0/1) [not used in this pack but supported]
      slot4: OverrideIndex (optional; used for tracing/branching)
    """

    PROP_ID = 370

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        raw = getattr(effect_row, "params_raw", None)
        if raw is None:
            # tests/mini_models store param_raw string; parse it if needed
            try:
                raw = [int(x.strip() or "0") for x in str(getattr(effect_row, "param_raw", "")).split(",")]
            except Exception:
                raw = []
        raw = list(raw) + [0, 0, 0, 0, 0, 0]
        points = int(raw[0] or 0)

        try:
            acc_raw = float(raw[1] or 0)
        except Exception:
            acc_raw = 0.0
        accuracy = 100.0 if acc_raw == 0 else acc_raw

        attack_type_override = int(raw[2] or 0)
        is_periodic = bool(int(raw[3] or 0))
        override_index = int(raw[4] or 0) if int(raw[4] or 0) != 0 else None

        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            target,
            accuracy=accuracy,
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False)

        dmg_event = DamageEvent(
            source_actor=actor,
            target=target,
            ability_id=int(getattr(effect_row, "ability_id", 0) or 0),
            effect_id=int(getattr(effect_row, "effect_id", 0) or 0),
            points=int(points),
            is_periodic=is_periodic,
            override_index=override_index,
            attack_type_override=attack_type_override,
        )
        resolved = ctx.damage_pipeline.resolve(ctx, dmg_event)
        ctx.apply_damage(target, resolved.final_damage, trace=resolved.trace)

        try:
            ctx.acc_ctx.last_damage_dealt = int(resolved.final_damage)
            ctx.acc_ctx.last_damage_target_id = int(getattr(target, "id", 0))
        except Exception:
            pass

        ctx.log.damage(effect_row, actor, target, resolved)
        ctx.event_bus.emit(Event.ON_DAMAGE, payload=resolved)

        return EffectResult(executed=True, spawned_damage_events=[dmg_event], notes={"attack_type_override": attack_type_override})
