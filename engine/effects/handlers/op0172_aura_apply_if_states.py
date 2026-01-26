from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.constants.weather import WEATHER_STATE_IDS


@register_handler(172)
class H_Prop172_StunIfStates:
    """Conditional aura apply (commonly stun) gated on caster/target states.

    Ability-pack ParamSchema (opcode 172):
      StatePoints, CasterState, Duration, TargetState, ChainFailure, Accuracy

    Observed in pack for abilities:
      - Deep Freeze: requires target chilled -> apply Stunned (aura 927)
      - Surge of Light/Darkness: requires weather state -> apply Stunned
      - Fury of 1,000 Fists: requires target blind -> apply Stunned

    v1 semantics (conservative, evolvable):
      - If CasterState != 0:
          - If it's a Weather_* state: require ctx.weather.current(ctx) == CasterState
          - Else: require actor has state points > 0
      - If TargetState != 0:
          - If it's a Weather_* state: require ctx.weather.current(ctx) == TargetState
          - Else: require target has state points > 0
      - If gates pass and hitcheck succeeds: apply aura_ability_id to target for Duration turns.
      - Accuracy=0 is treated as 100 (matches pack usage).
      - On miss: if ChainFailure != 0 then STOP_ABILITY else CONTINUE
    """

    PROP_ID = 172

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        state_points = int(args.get("state_points", 0))
        caster_state = int(args.get("caster_state", 0))
        duration = int(args.get("duration", 0))
        target_state = int(args.get("target_state", 0))
        chain_failure = int(args.get("chain_failure", 0))
        accuracy = int(args.get("accuracy", 100))
        if accuracy == 0:
            accuracy = 100

        def _has_pet_state(pet_id: int, sid: int) -> bool:
            try:
                return int(ctx.states.get(int(pet_id), int(sid), 0)) != 0
            except Exception:
                return False

        def _has_weather_state(sid: int) -> bool:
            try:
                return int(ctx.weather.current(ctx)) == int(sid)
            except Exception:
                return False

        # Gates
        if caster_state:
            if caster_state in WEATHER_STATE_IDS:
                if not _has_weather_state(caster_state):
                    ctx.log.effect_result(effect_row, actor, target, code="REQ_STATE_FAIL", reason=f"MISSING_WEATHER:{caster_state}")
                    return EffectResult(executed=False, flow_control="CONTINUE", notes={"missing": "weather", "state": caster_state})
            else:
                if not _has_pet_state(getattr(actor, "id", 0), caster_state):
                    ctx.log.effect_result(effect_row, actor, target, code="REQ_STATE_FAIL", reason=f"MISSING_CASTER:{caster_state}")
                    return EffectResult(executed=False, flow_control="CONTINUE", notes={"missing": "caster", "state": caster_state})

        if target_state:
            if target_state in WEATHER_STATE_IDS:
                if not _has_weather_state(target_state):
                    ctx.log.effect_result(effect_row, actor, target, code="REQ_STATE_FAIL", reason=f"MISSING_WEATHER:{target_state}")
                    return EffectResult(executed=False, flow_control="CONTINUE", notes={"missing": "weather", "state": target_state})
            else:
                if not _has_pet_state(getattr(target, "id", 0), target_state):
                    ctx.log.effect_result(effect_row, actor, target, code="REQ_STATE_FAIL", reason=f"MISSING_TARGET:{target_state}")
                    return EffectResult(executed=False, flow_control="CONTINUE", notes={"missing": "target", "state": target_state})

        # Hit check
        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            target,
            accuracy=accuracy,
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            flow = "STOP_ABILITY" if chain_failure else "CONTINUE"
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason, flow=flow)
            return EffectResult(executed=False, flow_control=flow)

        aura_id = int(getattr(effect_row, "aura_ability_id", 0) or 0)
        if aura_id <= 0:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="NO_AURA_ID")
            return EffectResult(executed=False, flow_control="CONTINUE")

        # Some 172 rows use Duration=1; if 0, treat as 1 to keep behavior sane.
        eff_dur = duration if duration != 0 else 1

        ar = ctx.aura.apply(
            owner_pet_id=int(getattr(target, "id", 0)),
            caster_pet_id=int(getattr(actor, "id", 0)),
            aura_id=int(aura_id),
            duration=int(eff_dur),
            tickdown_first_round=False,
            source_effect_id=int(getattr(effect_row, "effect_id", 0)),
        )

        scripts = getattr(ctx, "scripts", None)
        if scripts is not None and ar.aura is not None:
            try:
                scripts.attach_periodic_to_aura(ar.aura)
                scripts.attach_meta_to_aura(ar.aura)
            except Exception:
                pass

        if ar.refreshed and ar.aura is not None:
            ctx.log.aura_refresh(effect_row, actor, target, int(aura_id), int(ar.aura.remaining_duration), False)

        ctx.log.aura_apply(effect_row, actor, target, int(aura_id), int(eff_dur), False, ar.reason)

        # StatePoints not observed non-zero in current pack; keep as optional hook.
        if state_points:
            try:
                # Apply to target state if provided, else to caster state (pet-local).
                if target_state and target_state not in WEATHER_STATE_IDS:
                    ctx.states.set(int(getattr(target, "id", 0)), int(target_state), int(state_points))
                elif caster_state and caster_state not in WEATHER_STATE_IDS:
                    ctx.states.set(int(getattr(actor, "id", 0)), int(caster_state), int(state_points))
            except Exception:
                pass

        return EffectResult(executed=bool(ar.applied or ar.refreshed), notes={"aura_reason": ar.reason, "duration": int(eff_dur)})
