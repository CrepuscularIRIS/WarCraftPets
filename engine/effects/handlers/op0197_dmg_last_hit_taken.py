from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(197)
class H_Prop197_DmgLastHitTaken:
    """Damage equal to the last hit taken by the user (scaled).

    ParamLabel (DB2): Power,Accuracy
      - power: percentage multiplier applied to actor's last_hit_taken (e.g. 100, 150)
      - accuracy: hit chance scalar (1 = standard)
    """

    PROP_ID = 197

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # Hit check first (this opcode can miss).
        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=args.get("accuracy", 1),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False)

        last_taken = int(getattr(actor, "last_hit_taken", 0) or 0)
        mul_pct = int(args.get("power", 0) or 0)
        # In shipped data this is 100 or 150. Be defensive.
        base = int(max(0, last_taken))
        raw_base = int((base * mul_pct) // 100)

        # Prop197 damage is defined as "equal to last hit taken" and MUST NOT be further
        # scaled by the caster's Power stat. Our DamagePipeline applies Power scaling at S1,
        # so we pre-divide to neutralize it (keeping type/weather/crit behavior intact).
        actor_power = int(getattr(ctx.stats, "get_power", lambda _a: int(getattr(_a, "power", 0) or 0))(actor))
        power_mul = 1.0 + (float(actor_power) / 20.0)
        dmg_points = int(raw_base // power_mul) if power_mul > 0 else int(raw_base)

        dmg_event = DamageEvent(
            source_actor=actor,
            target=target,
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=int(dmg_points),
            is_periodic=False,
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