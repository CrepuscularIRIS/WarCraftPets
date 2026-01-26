from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent

@register_handler(86)
class H_Prop86_DmgPointsApplyOrUpgradeAura:
    """
    DB2 ParamLabel: Points,Accuracy,Duration,AuraID,Duration2,

    Observed usage (Ability 323 Gravity):
      - Deals Points damage on hit.
      - Applies primary aura (AuraID) to the target for Duration turns.
      - If the target is struck while it already has AuraID, then:
          * remove AuraID
          * apply secondary aura (effect_row.aura_ability_id) for Duration2 turns.
    """

    PROP_ID = 86

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=args.get("accuracy", 1),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False)

        # 1) Damage (standard pipeline)
        dmg_event = DamageEvent(
            source_actor=actor,
            target=target,
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=int(args.get("points", 0) or 0),
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

        # 2) Aura apply / upgrade
        primary_aura_id = args.get("aura_id", None)
        try:
            primary_aura_id = int(primary_aura_id) if primary_aura_id is not None else None
        except Exception:
            primary_aura_id = None

        primary_dur = int(args.get("duration", 0) or 0)
        secondary_dur = int(args.get("duration2", primary_dur) or 0)

        secondary_aura_id = getattr(effect_row, "aura_ability_id", None)
        try:
            secondary_aura_id = int(secondary_aura_id) if secondary_aura_id is not None else None
        except Exception:
            secondary_aura_id = None

        if primary_aura_id is None:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="AURA_ID_MISSING")
            return EffectResult(executed=True)

        already = ctx.aura.get(int(getattr(target, "id", 0)), int(primary_aura_id)) is not None

        def _apply_aura(aura_id: int, dur: int):
            ar = ctx.aura.apply(
                owner_pet_id=target.id,
                caster_pet_id=actor.id,
                aura_id=int(aura_id),
                duration=int(dur),
                tickdown_first_round=False,
                source_effect_id=effect_row.effect_id,
            )

            scripts = getattr(ctx, "scripts", None)
            if scripts is not None and ar.aura is not None:
                try:
                    scripts.attach_periodic_to_aura(ar.aura)
                    scripts.attach_meta_to_aura(ar.aura)
                except Exception:
                    pass

            wm = getattr(ctx, "weather", None)
            if wm is not None and ar.aura is not None:
                try:
                    wm.on_aura_applied(ar.aura)
                except Exception:
                    pass

            if ar.refreshed and ar.aura is not None:
                ctx.log.aura_refresh(effect_row, actor, target, int(aura_id), int(ar.aura.remaining_duration), False)
            ctx.log.aura_apply(effect_row, actor, target, int(aura_id), int(dur), False, ar.reason)

            stats = getattr(ctx, "stats", None)
            if stats is not None and hasattr(stats, "sync_pet"):
                try:
                    stats.sync_pet(ctx, target)
                except Exception:
                    pass
            return ar

        if already and secondary_aura_id is not None:
            ctx.aura.remove(target.id, primary_aura_id)
            ctx.log.aura_remove(target.id, primary_aura_id, reason="UPGRADED_BY_PROP86")
            _apply_aura(secondary_aura_id, secondary_dur)
            return EffectResult(executed=True, notes={
                "upgraded": True,
                "removed_primary_aura": int(primary_aura_id),
                "applied_secondary_aura": int(secondary_aura_id),
                "secondary_duration": int(secondary_dur),
            })

        _apply_aura(primary_aura_id, primary_dur)
        return EffectResult(executed=True, notes={
            "upgraded": False,
            "applied_primary_aura": int(primary_aura_id),
            "primary_duration": int(primary_dur),
        })
