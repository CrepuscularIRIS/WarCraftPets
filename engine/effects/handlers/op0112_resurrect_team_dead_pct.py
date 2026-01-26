from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(112)
class H_Prop112_ResurrectDeadTeamPct:
    """Resurrect a dead allied pet at a percentage of its max HP.

    Observed usage in this pack:
      - Ability 2347 "Raise Dead" and 2348 "Mass Resurrection" each contain two Prop112 rows.
      - params_raw = [5, 100, 0, 1, 0, 0]

    Pack schema (auto-derived): Percentage,Unused,RequiredCasterState,RequiredTargetState
    Note: although schema labels slot2 as "Unused", the pack stores a value consistent with
    Accuracy there (100). We therefore interpret slot2 as accuracy in a conservative way.

    Conservative modeling:
      - Each Prop112 row resurrects *one* dead pet on the caster's team.
      - Selection: first dead pet (by team slot order), excluding the actor.
      - Resurrected HP = floor(max_hp * Percentage / 100), clamped to at least 1.
      - Clears all auras and volatile states on the revived pet (fresh start).
      - Can miss (accuracy gate). On miss we apply optional ChainFailure if slot5 is set.
    """

    PROP_ID = 112

    def _pick_dead_ally(self, ctx, actor) -> object | None:
        teams = getattr(ctx, "teams", None)
        pets = getattr(ctx, "pets", None)
        if teams is None or pets is None:
            return None

        team_id = teams.team_of_pet(int(getattr(actor, "id", 0) or 0))
        if team_id is None:
            return None
        team = teams.teams.get(int(team_id))
        if team is None:
            return None

        for pid in team.pet_ids:
            pid = int(pid)
            if pid == int(getattr(actor, "id", 0) or 0):
                continue
            p = pets.get(pid)
            if p is None:
                continue
            if bool(getattr(p, "alive", True)) is False or int(getattr(p, "hp", 1) or 0) <= 0:
                return p
        return None

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # Slot mapping from schema; slot2 is labeled Unused but behaves like Accuracy in this pack.
        try:
            pct = int(args.get("percentage", 0) or 0)
        except Exception:
            pct = 0

        # NOTE: do NOT use `or 100` because 0 is a valid accuracy (always miss).
        acc_raw = args.get("unused", None)
        if acc_raw is None:
            acc_raw = args.get("accuracy", None)
        if acc_raw is None:
            acc_raw = 100
        try:
            accuracy = int(acc_raw)
        except Exception:
            accuracy = 100

        # Pack schemas sometimes camel-case without underscores; ParamParser normalizes to snake_case.
        req_caster_raw = args.get("required_caster_state", args.get("requiredcasterstate", 0))
        req_target_raw = args.get("required_target_state", args.get("requiredtargetstate", 0))
        try:
            req_caster_state = int(req_caster_raw)
        except Exception:
            req_caster_state = 0
        try:
            req_target_state = int(req_target_raw)
        except Exception:
            req_target_state = 0

        # Best-effort extra slots: ChainFailure lives in slot5 in a few other opcodes; keep compatible.
        chain_failure = 0
        try:
            raw = [int(x) for x in str(getattr(effect_row, "param_raw", "") or "").split(",") if x != ""]
            if len(raw) >= 5:
                chain_failure = int(raw[4] or 0)
        except Exception:
            chain_failure = 0

        # Gate on caster state if requested.
        if req_caster_state:
            st = getattr(ctx, "states", None)
            if st is None or st.get(int(getattr(actor, "id", 0) or 0), int(req_caster_state), 0) == 0:
                ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="CASTER_STATE_GATE")
                return EffectResult(executed=False, flow_control="CONTINUE")

        dead = self._pick_dead_ally(ctx, actor)
        if dead is None:
            # Nothing to resurrect.
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="NO_DEAD_ALLY")
            return EffectResult(executed=False, flow_control="CONTINUE")

        # Gate on target state if requested (pack uses Is_Dead=1). We only allow dead targets.
        if req_target_state:
            # Treat "dead" as hp<=0 or alive==False.
            if bool(getattr(dead, "alive", True)) is True and int(getattr(dead, "hp", 0) or 0) > 0:
                ctx.log.effect_result(effect_row, actor, dead, code="NOOP", reason="TARGET_STATE_GATE")
                return EffectResult(executed=False, flow_control="CONTINUE")

        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            dead,
            accuracy=accuracy,
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, dead, code="MISS", reason=reason)
            return EffectResult(executed=False, flow_control=("STOP_ABILITY" if chain_failure else "CONTINUE"), notes={"miss_reason": reason})

        if pct <= 0:
            ctx.log.effect_result(effect_row, actor, dead, code="NOOP", reason="PCT<=0")
            return EffectResult(executed=False, flow_control="CONTINUE")

        max_hp = int(getattr(dead, "max_hp", 0) or 0)
        hp = int((max_hp * pct) // 100)
        if hp <= 0:
            hp = 1
        if hp > max_hp and max_hp > 0:
            hp = max_hp

        # Fresh start: remove all auras and volatile states.
        aura = getattr(ctx, "aura", None)
        if aura is not None:
            try:
                for aid in list(aura.list_owner(int(getattr(dead, "id", 0) or 0)).keys()):
                    aura.remove(int(getattr(dead, "id", 0) or 0), int(aid))
            except Exception:
                pass
        st = getattr(ctx, "states", None)
        if st is not None:
            try:
                st.clear_pet(int(getattr(dead, "id", 0) or 0))
                # Ensure Is_Dead cleared if the state id exists in scripts.
                st.set(int(getattr(dead, "id", 0) or 0), 1, 0)
            except Exception:
                pass

        dead.alive = True
        dead.hp = int(hp)

        ctx.log.effect_result(effect_row, actor, dead, code="RESURRECT", reason="OK")
        return EffectResult(executed=True, notes={"resurrect_hp": int(hp), "pct": int(pct)})
