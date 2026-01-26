from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(66)
class H_Prop66_DmgExecute25Pct:
    """Execute-style damage: deals bonus damage if target is below 25% health.

    DB2 param schema (from pack):
      - Points (i32)
      - Accuracy (u8_pct)
      - Boost (i32): percent bonus to apply when execute condition holds (100 => double)
    """

    PROP_ID = 66

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        points = int(args.get("points", 0) or 0)
        accuracy = args.get("accuracy", 100)
        boost = float(args.get("boost", 0) or 0)

        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=accuracy,
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, "MISS", reason)
            return EffectResult(executed=False)

        # Execute gate: strictly below 25% health.
        hp = int(getattr(target, "hp", 0) or 0)
        max_hp = int(getattr(target, "max_hp", 0) or 0)

        eff_points = points
        if max_hp > 0 and (hp * 100) < (max_hp * 25):
            eff_points = int(round(points * (1.0 + (boost / 100.0))))

        dmg_event = DamageEvent(
            source_actor=actor,
            target=target,
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=int(eff_points),
            is_periodic=bool(args.get("isperiodic", args.get("is_periodic", 0))),
            override_index=args.get("override_index"),
        )

        resolved = ctx.damage_pipeline.resolve(ctx, dmg_event)
        ctx.apply_damage(target, resolved.final_damage, trace=resolved.trace)
        # For post-damage effects (e.g., Prop32 lifesteal)
        try:
            ctx.acc_ctx.last_damage_dealt = int(resolved.final_damage)
            ctx.acc_ctx.last_damage_target_id = int(getattr(target, "id", 0))
        except Exception:
            pass
        ctx.log.damage(effect_row, actor, target, resolved)
        ctx.event_bus.emit(Event.ON_DAMAGE, payload=resolved)

        return EffectResult(executed=True, spawned_damage_events=[dmg_event])
