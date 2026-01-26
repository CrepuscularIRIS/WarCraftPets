from engine.effects.registry import register_handler
from engine.effects.types import EffectResult

import math


@register_handler(128)
class H_Prop128_SetTargetHpPct:
    """Set target HP to a fixed percentage of its max HP (GM/DNT helpers).

    Observed in ability_pack:
      - 733: GM Execute Range   (24,100,...)
      - 2468: [DNT] TRAP HELP   (1,0,...)
      - 2502: [DNT] INSTADEAD   (0,0,...)

    DB2 exports for this prop have no ParamLabel in the pack; we therefore
    parse EffectRow.param_raw directly (slot1, slot2).
    """
    PROP_ID = 128

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # Best-effort parse: param_raw is "slot1,slot2,slot3,slot4,slot5,slot6"
        raw = (getattr(effect_row, "param_raw", "") or "").split(",")
        raw += ["0"] * (6 - len(raw))
        try:
            pct = int(float(raw[0] or 0))
        except Exception:
            pct = 0
        try:
            acc_raw = float(raw[1] or 0)
        except Exception:
            acc_raw = 0.0

        # Pack uses 0 to mean "always" for these helper props.
        accuracy = 100.0 if acc_raw == 0 else acc_raw

        hit, reason = ctx.hitcheck.compute(
            ctx, actor, target,
            accuracy=accuracy,
            dont_miss=bool(getattr(getattr(ctx, "acc_ctx", None), "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False)

        max_hp = int(getattr(target, "max_hp", 0) or 0)
        cur_hp = int(getattr(target, "hp", 0) or 0)

        # pct == 0 => kill target (instadead)
        desired = int(math.floor(max_hp * (pct / 100.0))) if max_hp > 0 else 0
        if pct > 0:
            desired = max(1, desired)
        desired = max(0, min(max_hp if max_hp > 0 else desired, desired))

        if desired >= cur_hp:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="HP_ALREADY_AT_OR_BELOW_THRESHOLD")
            return EffectResult(executed=True)

        dmg = cur_hp - desired
        ctx.apply_damage(target, dmg, trace={"kind": "SET_HP_PCT", "pct": pct, "damage": dmg, "desired_hp": desired})
        ctx.log.effect_result(effect_row, actor, target, code="OK", reason=f"SET_HP_TO_{pct}PCT")
        return EffectResult(executed=True)
