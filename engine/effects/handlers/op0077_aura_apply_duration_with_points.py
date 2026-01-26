from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(77)
class H_Prop77_AuraApplyDurationWithPoints:
    """Prop77: Apply aura to target with explicit duration and a numeric payload.

    ParamLabel (pack): Points,Accuracy,Duration

    Observed:
      - Ability 301 "Lock-On" applies aura 300 "Locked On" with Points=45, Duration=1.
      - GM-only variants exist with Points=0.

    Practical engine behavior:
      - Performs a hit check using Accuracy.
      - Applies aura_ability_id to TARGET with remaining_duration=Duration (0 => permanent).
      - If Points != 0, binds it to Mod_DamageTakenPercent (BattlePetState=24) via aura.meta.state_binds.
        This matches how downstream damage uses StatsResolver state aggregation.

    Notes:
      - This opcode family is stateful and is best modeled via aura meta rather than a bare StateManager set,
        so that dispel/refresh semantics remain consistent.
    """

    PROP_ID = 77
    _DEFAULT_STATE_ID = 24  # Mod_DamageTakenPercent

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
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

        aura_id = getattr(effect_row, "aura_ability_id", None)
        if aura_id is None or int(aura_id) == 0:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="AURA_ID_MISSING")
            return EffectResult(executed=False)

        points = args.get("points", 0)
        try:
            points = int(points)
        except Exception:
            points = 0

        duration = args.get("duration", 0)
        try:
            duration = int(duration)
        except Exception:
            duration = 0
        if duration == 0:
            duration = -1

        ar = ctx.aura.apply(
            owner_pet_id=target.id,
            caster_pet_id=actor.id,
            aura_id=int(aura_id),
            duration=int(duration),
            tickdown_first_round=False,
            source_effect_id=effect_row.effect_id,
        )

        # Attach payload to aura meta so StatsResolver can consume it.
        if ar.aura is not None:
            meta = getattr(ar.aura, "meta", None)
            if meta is None or not isinstance(meta, dict):
                meta = {}
                ar.aura.meta = meta
            meta["points"] = int(points)
            if int(points) != 0:
                meta.setdefault("state_binds", [])
                # Avoid duplicate bind rows on refresh.
                binds = meta.get("state_binds") or []
                if not any((b or {}).get("state_id") == self._DEFAULT_STATE_ID for b in binds if isinstance(b, dict)):
                    binds.append({"state_id": self._DEFAULT_STATE_ID, "value": int(points), "flags": 0})
                    meta["state_binds"] = binds

        if ar.refreshed and ar.aura is not None:
            ctx.log.aura_refresh(effect_row, actor, target, int(aura_id), int(ar.aura.remaining_duration), False)
        ctx.log.aura_apply(effect_row, actor, target, int(aura_id), int(duration), False, ar.reason)

        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "sync_pet"):
            try:
                stats.sync_pet(ctx, target)
            except Exception:
                pass

        return EffectResult(
            executed=bool(ar.applied or ar.refreshed),
            notes={"aura_id": int(aura_id), "duration": int(duration), "points": int(points), "aura_reason": ar.reason},
        )
