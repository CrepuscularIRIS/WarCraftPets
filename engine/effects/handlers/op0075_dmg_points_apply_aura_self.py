from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent

@register_handler(75)
class H_Prop75_DmgPointsApplyAuraSelf:
    """Damage + apply self aura marker on hit.

    Export observation (wow_export_merged.xlsx):
      - Prop75 uses ParamLabel: Points,Accuracy,,,, and includes AuraBattlePetAbilityID.
      - Example: Ability 293 "Launch Rocket" (prop75, aura=294 "Setup Rocket").

    Implemented semantics:
      1) Hit check (Accuracy; respects ctx.acc_ctx.dont_miss)
      2) On hit: standard damage using Points via damage_pipeline
      3) On hit: apply aura_ability_id to the ACTOR (self) with permanent duration (-1)

    If aura_ability_id is missing/0, only the damage is applied.
    """
    PROP_ID = 75

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=args.get("accuracy", 1),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.miss(effect_row, actor, target, reason=reason)
            return EffectResult(executed=False)

        dmg_event = DamageEvent(
            source_actor=actor,
            target=target,
            ability_id=int(getattr(effect_row, "ability_id", 0)),
            effect_id=int(getattr(effect_row, "effect_id", 0)),
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

        aura_id = getattr(effect_row, "aura_ability_id", None)
        if aura_id:
            try:
                ar = ctx.aura.apply(
                    owner_pet_id=int(getattr(actor, "id", 0)),
                    caster_pet_id=int(getattr(actor, "id", 0)),
                    aura_id=int(aura_id),
                    duration=-1,
                    tickdown_first_round=False,
                    source_effect_id=int(getattr(effect_row, "effect_id", 0)),
                )
                if ar.applied or ar.refreshed:
                    ctx.log.aura_apply(effect_row, actor, actor, int(aura_id), -1, False, ar.reason)
            except Exception:
                pass

        return EffectResult(executed=True, spawned_damage_events=[dmg_event])
