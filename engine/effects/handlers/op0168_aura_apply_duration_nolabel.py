from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(168)
class H_Prop168_AuraApplyDurationNoLabel:
    """Prop168: Apply aura with explicit duration (raw-slot schema).

    Observed in this engine's ability_pack:
      - 522  Nevermore     params_raw: [0,100,2,0,0,0] aura=738
      - 1558 Buuurp!       params_raw: [1,100,1,0,0,0] aura=516
      - 1858 Spell Gulp    params_raw: [0,100,2,0,0,0] aura=1859

    The pack exports for this prop have no ParamLabel. We therefore interpret:
      slot0: ChainFailure (miss -> STOP_ABILITY if non-zero)
      slot1: Accuracy (0 treated as 100 for these cases)
      slot2: Duration (turns; -1 allowed)
    """

    PROP_ID = 168

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        raw = getattr(effect_row, "param_raw", []) or []
        if isinstance(raw, str):
            raw = [s.strip() for s in raw.split(",")]
        raw = list(raw)
        raw += ["0"] * (6 - len(raw))

        try:
            cf = int(float(raw[0] or 0))
        except Exception:
            cf = 0

        try:
            acc_raw = float(raw[1] or 0)
        except Exception:
            acc_raw = 0.0

        # Observed convention in this pack for unlabeled props: 0 means always hit.
        accuracy = 100.0 if acc_raw == 0 else acc_raw

        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            target,
            accuracy=accuracy,
            dont_miss=bool(getattr(getattr(ctx, "acc_ctx", None), "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False, flow_control=("STOP_ABILITY" if cf else "CONTINUE"))

        try:
            duration = int(float(raw[2] or 0))
        except Exception:
            duration = 0

        aura_id = getattr(effect_row, "aura_ability_id", 0) or 0
        if not aura_id:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="NO_AURA_ID")
            return EffectResult(executed=False)

        ar = ctx.aura.apply(
            owner_pet_id=target.id,
            caster_pet_id=actor.id,
            aura_id=int(aura_id),
            duration=int(duration),
            tickdown_first_round=False,
            source_effect_id=int(getattr(effect_row, "effect_id", 0) or 0),
        )

        # Attach script metadata / periodic payloads if available.
        scripts = getattr(ctx, "scripts", None)
        if scripts is not None and ar.aura is not None:
            try:
                scripts.attach_periodic_to_aura(ar.aura)
            except Exception:
                pass
            try:
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

        ctx.log.aura_apply(effect_row, actor, target, int(aura_id), int(duration), False, ar.reason)

        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "sync_pet"):
            try:
                stats.sync_pet(ctx, target)
            except Exception:
                pass

        return EffectResult(
            executed=(ar.applied or ar.refreshed),
            flow_control="CONTINUE",
            notes={"aura_id": int(aura_id), "duration": int(duration), "aura_reason": ar.reason},
        )
