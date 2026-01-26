from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(76)
class H_Prop76_ChargeOrRelease:
    """Two-step "charge then release" ability.

    Pack schema: Points,Accuracy with an aura_ability_id reference.

    Observed pattern in retail pet battles (MoP era):
      - First use applies a short-lived "charged" aura to the *caster* (e.g., Pump, Wind-Up),
        typically lasting 1 round.
      - Second use (while the aura is present) consumes the aura and deals damage.

    Conservative implementation:
      - If aura_ability_id is present:
          * If caster already has the aura -> deal Points damage to target, then remove aura.
          * Else -> apply the aura to caster with duration=1 (tickdown_first_round=False).
      - If aura_ability_id is missing -> treat as a simple Points damage (like Prop24).

    Notes:
      - This keeps the simulator runnable and semantically close for the known charge skills.
      - If later you add more precise semantics from DB2/tooltip, this handler is the correct hook.
    """

    PROP_ID = 76

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        points = int(args.get("points", 0) or 0)

        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=args.get("accuracy", 1),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False)

        aura_id = getattr(effect_row, "aura_ability_id", None)

        # No aura ref -> behave like standard damage
        if not aura_id:
            dmg_event = DamageEvent(
                source_actor=actor,
                target=target,
                ability_id=int(getattr(effect_row, "ability_id", 0)),
                effect_id=int(getattr(effect_row, "effect_id", 0)),
                points=int(points),
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
            return EffectResult(executed=True, spawned_damage_events=[dmg_event])

        aura_id = int(aura_id)

        # If already charged -> release damage and consume aura
        existing = ctx.aura.get(actor.id, aura_id)
        if existing is not None:
            dmg_event = DamageEvent(
                source_actor=actor,
                target=target,
                ability_id=int(getattr(effect_row, "ability_id", 0)),
                effect_id=int(getattr(effect_row, "effect_id", 0)),
                points=int(points),
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
            ctx.aura.remove(actor.id, aura_id)
            ctx.log.damage(effect_row, actor, target, resolved)
            ctx.event_bus.emit(Event.ON_DAMAGE, payload=resolved)
            return EffectResult(executed=True, spawned_damage_events=[dmg_event], notes={"consumed_aura": aura_id})

        # Not charged yet -> apply charge aura to caster for 1 round
        ar = ctx.aura.apply(
            owner_pet_id=actor.id,
            caster_pet_id=actor.id,
            aura_id=aura_id,
            duration=1,
            tickdown_first_round=False,
            source_effect_id=effect_row.effect_id,
        )
        if ar.aura is not None:
            # Record points for debugging/RL (best-effort; not relied upon)
            try:
                ar.aura.meta["charge_points"] = int(points)
                ar.aura.meta["charge_opcode"] = int(self.PROP_ID)
            except Exception:
                pass

        if ar.refreshed:
            ctx.log.aura_refresh(effect_row, actor, actor, int(aura_id), int(ar.aura.remaining_duration) if ar.aura else 0, False)
        ctx.log.aura_apply(effect_row, actor, actor, int(aura_id), 1, False, ar.reason)
        return EffectResult(executed=True, notes={"charge": True, "aura_id": aura_id, "points": points})
