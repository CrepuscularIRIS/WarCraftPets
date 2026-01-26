from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.core.events import Event
from engine.model.damage import DamageEvent


@register_handler(67)
class H_Prop67_DmgBonusIfStruckFirst:
    """Conditional bonus damage.

    Observed tooltip pattern (e.g. *Blast of Hatred*):
      - Deals [StandardDamage(1$1)] damage.
      - Deals [StandardDamage(1$2)] extra damage if you were struck first this round.

    Engine semantics (v1, conservative):
      - base_points := Points
      - bonus_points := MorePoints
      - If caster was struck (took damage) during FIRST_ACTION phase of the current round,
        then total_points := base_points + bonus_points
      - Otherwise total_points := base_points
    """

    PROP_ID = 67

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # Hit check
        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            target,
            accuracy=args.get("accuracy", 1),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False)

        base = int(args.get("points", 0) or 0)
        bonus = int(
            args.get(
                "more_points",
                args.get("morepoints", args.get("bonus_points", 0)),
            )
            or 0
        )

        struck = False
        try:
            btl = getattr(ctx, "btl", None)
            if btl is not None:
                # Preferred: set[str] tracking on ctx.btl.struck_before_action_ids (set by ctx.apply_damage)
                ids = getattr(btl, "struck_before_action_ids", None)
                if ids is not None and int(getattr(actor, "id", 0)) in set(ids):
                    struck = True
                # Backward-compat: a simple flag for second actor
                if int(getattr(btl, "round_second_was_struck_first", 0) or 0) != 0 and int(getattr(btl, "round_second_actor_id", 0) or 0) == int(getattr(actor, "id", 0) or 0):
                    struck = True
        except Exception:
            struck = False

        points = base + bonus if struck else base

        dmg_event = DamageEvent(
            source_actor=actor,
            target=target,
            ability_id=effect_row.ability_id,
            effect_id=effect_row.effect_id,
            points=points,
            is_periodic=bool(args.get("isperiodic", args.get("is_periodic", 0))),
            override_index=args.get("override_index"),
        )

        resolved = ctx.damage_pipeline.resolve(ctx, dmg_event)
        ctx.apply_damage(target, resolved.final_damage, trace=resolved.trace)

        # For post-damage effects
        try:
            ctx.acc_ctx.last_damage_dealt = int(resolved.final_damage)
            ctx.acc_ctx.last_damage_target_id = int(getattr(target, "id", 0))
        except Exception:
            pass

        ctx.log.damage(effect_row, actor, target, resolved)
        ctx.event_bus.emit(Event.ON_DAMAGE, payload=resolved)
        return EffectResult(executed=True, spawned_damage_events=[dmg_event], notes={"bonus_applied": 1 if struck else 0})
