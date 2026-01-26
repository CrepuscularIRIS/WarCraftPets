from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(157)
class H_Prop157_StateSetSelfDeath:
    """Set a BattlePetState on the *caster* (opcode 157).

    DB2 ParamLabel: `State,StatePoints,unused,unused,,`

    This opcode shows up around death / resurrection flows (e.g. Haunt, Cheat
    Death, Rise from the Ash), and also as a generic "self-state marker" in a
    few abilities.

    Minimal deterministic behavior implemented here:
      - Write `State=StatePoints` onto the **actor** in `ctx.states`.
      - Special-case `State==1 (Is_Dead)`:
          * If `StatePoints != 0`, mark the actor dead (hp=0, alive=False)
            so the battle loop and action generator treat it as dead.
          * If `StatePoints == 0`, only clear the state; resurrection is
            handled by other opcodes (e.g. 111 set hp pct / 112 resurrect).
      - Best-effort `stats.sync_pet` after state changes.
    """

    PROP_ID = 157

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        sid = args.get("state", 0)
        sp = args.get("state_points", args.get("statepoints", 0))
        try:
            sid = int(sid)
        except Exception:
            sid = 0
        try:
            sp = int(sp)
        except Exception:
            sp = 0

        # Store on actor (self).
        sm = getattr(ctx, "states", None)
        if sm is not None:
            sm.set(int(getattr(actor, "id", 0)), sid, sp)
        if hasattr(ctx, "log"):
            ctx.log.state_set(effect_row, actor, actor, sid, sp)

        # Special-case: Is_Dead.
        if sid == 1 and sp != 0:
            try:
                actor.hp = 0
            except Exception:
                pass
            try:
                actor.alive = False
            except Exception:
                pass

        # Best-effort runtime stat sync.
        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "sync_pet"):
            try:
                stats.sync_pet(ctx, actor)
            except Exception:
                pass

        return EffectResult(executed=True, notes={"code": "STATE_SET_SELF", "state": sid, "value": sp})
