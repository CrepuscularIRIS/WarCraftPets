from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(150)
class H_Prop150_WallOrObjectApply:
    """Prop150: Wall/Object apply.

    DB2/pack schema: ChainFailure, Accuracy

    Observed in the pack as the caster-side opcode for "wall" abilities:
      - Beaver Dam (325) -> aura 326
      - Jade Barrier (433) -> aura 434
      - Onyx Wall (439) -> aura 438
      - Prismatic Barrier (444) -> aura 443
      - Illusionary Barrier (465/2318) -> aura 464
      - Ice Barrier (479) -> aura 480
      - Weald Wall (2398) -> aura 2397

    The battle loop passes the opponent active as `target` for all abilities.
    Wall/barrier abilities are self-side effects, so this handler intentionally
    applies the aura to the *actor* (self) instead of the passed-in target.

    Duration is not encoded in the Prop150 params in the generated pack.
    Policy: use a conservative default duration=3 unless scripts/aura meta
    explicitly provides a duration hint.
    """

    PROP_ID = 150

    DEFAULT_DURATION = 3

    def _resolve_duration(self, ctx, aura_id: int) -> int:
        # Best-effort: read aura meta from ScriptDB if available.
        scripts = getattr(ctx, "scripts", None)
        if scripts is not None and hasattr(scripts, "get_aura_meta"):
            try:
                meta = scripts.get_aura_meta(int(aura_id)) or {}
                for k in ("duration", "default_duration", "turns", "max_duration"):
                    if k in meta:
                        try:
                            v = int(meta.get(k) or 0)
                            if v > 0:
                                return v
                        except Exception:
                            pass
            except Exception:
                pass
        return int(self.DEFAULT_DURATION)

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # Params: ChainFailure,Accuracy
        cf = args.get("chain_failure", args.get("chainfailure", 0))
        try:
            cf = int(cf)
        except Exception:
            cf = 0

        # This opcode can miss (per pack semantics), but it targets self-side.
        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            actor,  # self-side hitcheck; avoids enemy dodge affecting barriers
            accuracy=args.get("accuracy", 1),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, actor, code="MISS", reason=reason)
            return EffectResult(executed=False, flow_control=("STOP_ABILITY" if cf else "CONTINUE"))

        aura_id = getattr(effect_row, "aura_ability_id", None)
        if aura_id is None:
            ctx.log.effect_result(effect_row, actor, actor, code="NOOP", reason="AURA_ID_MISSING")
            return EffectResult(executed=False, flow_control=("STOP_ABILITY" if cf else "CONTINUE"))

        duration = self._resolve_duration(ctx, int(aura_id))
        ar = ctx.aura.apply(
            owner_pet_id=actor.id,
            caster_pet_id=actor.id,
            aura_id=int(aura_id),
            duration=int(duration),
            tickdown_first_round=False,
            source_effect_id=effect_row.effect_id,
        )

        # Attach aura meta/periodic payloads if ScriptDB is present.
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
            ctx.log.aura_refresh(effect_row, actor, actor, int(aura_id), int(ar.aura.remaining_duration), False)

        ctx.log.aura_apply(effect_row, actor, actor, int(aura_id), int(duration), False, ar.reason)

        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "sync_pet"):
            try:
                stats.sync_pet(ctx, actor)
            except Exception:
                pass

        executed = (ar.applied or ar.refreshed)
        return EffectResult(executed=executed, flow_control="CONTINUE", notes={"duration": int(duration), "aura_reason": ar.reason})
