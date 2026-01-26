from __future__ import annotations

from engine.core.events import Event
from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.model.damage import DamageEvent


def _round_order_hint(ctx):
    btl = getattr(ctx, "btl", None)
    if btl is None:
        return None
    first = int(getattr(btl, "round_first_actor_id", 0) or 0)
    second = int(getattr(btl, "round_second_actor_id", 0) or 0)
    if first == 0 and second == 0:
        return None
    return first, second


def _guess_attacks_last(ctx, actor, target) -> bool:
    """Best-effort 'attacks last' predicate.

    Preferred: ctx.btl.round_first_actor_id / round_second_actor_id (set by BattleLoop).
    Fallback: compare current effective speeds (or raw speed fields).
    """
    aid = int(getattr(actor, "id", 0) or 0)
    hint = _round_order_hint(ctx)
    if hint is not None:
        _first, _second = hint
        if _second == aid:
            return True
        if _first == aid:
            return False

    # Fallback: speed compare (ignores swap priority & tiebreak RNG)
    try:
        a_speed = int(getattr(actor, "speed", 0) or 0)
        t_speed = int(getattr(target, "speed", 0) or 0)
        return a_speed < t_speed
    except Exception:
        return False

@register_handler(160)
class H_Prop160_DmgBonusIfFirst:
    """Bonus damage that only applies if the user attacks first this round.

    DB2 ParamLabel: Points,Accuracy,,,,

    Observed in this pack:
      - Arcane Slash (1353): base damage (Prop103) + bonus damage if user strikes first (Prop160)
      - Scrabble (2430): base damage (Prop103) + bonus damage if user strikes first (Prop160)

    Notes:
      - If the condition is not met, the effect is skipped (no hit roll, no damage).
    """

    PROP_ID = 160

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        if _guess_attacks_last(ctx, actor, target):
            ctx.log.effect_result(effect_row, actor, target, code="SKIP_ORDER", reason="NOT_FIRST")
            return EffectResult(executed=False, notes={"order": "not_first"})

        # Standard hit check then standard damage pipeline.
        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=args.get("accuracy", 100),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.miss(effect_row, actor, target, reason=reason)
            ctx.event_bus.emit(Event.ON_MISS, payload={"effect_row": effect_row, "reason": reason})
            return EffectResult(executed=False, notes={"miss": True, "reason": reason})

        dmg_event = DamageEvent(
            source_actor=actor,
            target=target,
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=int(args.get("points", 0)),
            is_periodic=False,
            override_index=args.get("override_index"),
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

        return EffectResult(executed=True, spawned_damage_events=[dmg_event], notes={"order": "first"})
