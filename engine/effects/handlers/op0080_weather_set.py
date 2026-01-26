from __future__ import annotations

"""Prop80: WEATHER_SET

DB2 ParamLabel: Points,Accuracy,Duration,ChainFailure,,

Semantics (v0.1 engine):
  - Performs a hit check (Accuracy) against the chosen target.
  - On hit, replaces any existing weather and applies a "weather aura" to the caster
    as the anchor for battlefield weather lifetime.

Rationale:
  - Retail WoW models weather as battlefield-wide, but the source DB2 data represents it
    as an aura. This skeleton engine uses a *single anchor aura* (on the caster) and
    WeatherManager scans aura meta state binds to determine active weather.
  - Keeping weather attached to one persistent pet avoids duplicating auras across all pets
    while still producing correct global modifiers (damage/heal/hit) via WeatherManager.
"""

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult
from engine.constants.weather import WEATHER_STATE_IDS


def _is_weather_aura(ctx, aura) -> bool:
    """Best-effort check: is this aura binding any Weather_* state id."""
    if aura is None:
        return False

    # 1) Prefer attached meta on aura instance
    try:
        binds = (getattr(aura, "meta", None) or {}).get("state_binds", [])
        for b in binds:
            sid = int(b.get("state_id", 0) or 0)
            if sid in WEATHER_STATE_IDS:
                return True
    except Exception:
        pass

    # 2) Fall back to ScriptDB meta if available
    scripts = getattr(ctx, "scripts", None)
    if scripts is not None and hasattr(scripts, "get_aura_meta"):
        try:
            meta = scripts.get_aura_meta(int(getattr(aura, "aura_id", 0) or 0)) or {}
            for b in (meta.get("state_binds", []) or []):
                sid = int(b.get("state_id", 0) or 0)
                if sid in WEATHER_STATE_IDS:
                    return True
        except Exception:
            return False

    return False


def _iter_all_pet_ids(ctx, actor, target):
    # Prefer ctx.pets (battle loop populates this)
    pets = getattr(ctx, "pets", None)
    if isinstance(pets, dict) and pets:
        return [int(pid) for pid in pets.keys()]

    # Next, attempt to read from TeamManager
    teams = getattr(ctx, "teams", None)
    if teams is not None and hasattr(teams, "teams"):
        out = []
        for t in getattr(teams, "teams", []) or []:
            for pid in getattr(t, "pet_ids", []) or []:
                out.append(int(pid))
        if out:
            return out

    # Fallback: actor/target only
    out = []
    if actor is not None and hasattr(actor, "id"):
        out.append(int(getattr(actor, "id")))
    if target is not None and hasattr(target, "id"):
        tid = int(getattr(target, "id"))
        if tid not in out:
            out.append(tid)
    return out


@register_handler(80)
class WeatherSet:
    def apply(self, ctx, actor, target, effect_row, args: dict) -> EffectResult:
        accuracy = args.get("accuracy", 1)
        duration = int(args.get("duration", 0) or 0)
        chain_failure = int(args.get("chain_failure", 0) or 0)

        # Hit check (weather can miss in the source data)
        hit = True
        reason = "HIT"
        if hasattr(ctx, "hitcheck") and ctx.hitcheck is not None:
            try:
                hit, reason = ctx.hitcheck.compute(
                    ctx,
                    actor,
                    target,
                    accuracy=accuracy,
                    dont_miss=bool(getattr(getattr(ctx, "acc_ctx", None), "dont_miss", False)),
                )
            except Exception:
                hit, reason = True, "HIT"

        if not hit:
            if hasattr(ctx, "log"):
                ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False, flow_control=("STOP_ABILITY" if chain_failure else "CONTINUE"))

        aura_id = int(getattr(effect_row, "aura_ability_id", 0) or 0)
        if aura_id <= 0:
            if hasattr(ctx, "log") and hasattr(ctx.log, "warn"):
                ctx.log.warn(effect_row, code="NO_AURA_ID", detail={"prop_id": 80})
            return EffectResult(executed=False)

        # Remove any existing weather auras (battlefield weather is exclusive).
        pet_ids = _iter_all_pet_ids(ctx, actor, target)
        if hasattr(ctx, "aura") and ctx.aura is not None:
            for pid in pet_ids:
                try:
                    for a in list(ctx.aura.list_owner(int(pid)).values()):
                        if _is_weather_aura(ctx, a):
                            ctx.aura.remove(int(pid), int(getattr(a, "aura_id", 0) or 0))
                            if hasattr(ctx, "log"):
                                ctx.log.aura_remove(int(pid), int(getattr(a, "aura_id", 0) or 0), reason="WEATHER_OVERRIDE")
                except Exception:
                    continue

        # Duration=0 is treated as "clear weather" in this engine.
        if duration <= 0:
            if hasattr(ctx, "weather") and ctx.weather is not None:
                try:
                    ctx.weather.clear()
                except Exception:
                    pass
            if hasattr(ctx, "log"):
                ctx.log.effect_result(effect_row, actor, target, code="WEATHER_CLEAR", reason="DURATION0")
            return EffectResult(executed=False)

        # Apply a single anchor aura to the caster.
        owner_id = int(getattr(actor, "id", 0) or 0)
        caster_id = owner_id
        if not hasattr(ctx, "aura") or ctx.aura is None:
            if hasattr(ctx, "log") and hasattr(ctx.log, "warn"):
                ctx.log.warn(effect_row, code="NO_AURA_MANAGER", detail={"prop_id": 80})
            return EffectResult(executed=False)

        ar = ctx.aura.apply(
            owner_pet_id=owner_id,
            caster_pet_id=caster_id,
            aura_id=aura_id,
            duration=duration,
            source_effect_id=int(getattr(effect_row, "effect_id", 0) or 0),
            tickdown_first_round=False,
        )

        if ar.aura is None:
            if hasattr(ctx, "log"):
                ctx.log.aura_apply(effect_row, actor, target, aura_id, duration, False, getattr(ar, "reason", "NO_AURA"))
            return EffectResult(executed=False)

        # Attach periodic/meta scripts (best-effort).
        if hasattr(ctx, "scripts") and ctx.scripts is not None:
            try:
                if hasattr(ctx.scripts, "attach_periodic_to_aura"):
                    ctx.scripts.attach_periodic_to_aura(ar.aura)
                if hasattr(ctx.scripts, "attach_meta_to_aura"):
                    ctx.scripts.attach_meta_to_aura(ar.aura)
            except Exception:
                pass

        # Inform WeatherManager (can also be inferred from aura meta later).
        if hasattr(ctx, "weather") and ctx.weather is not None:
            try:
                ctx.weather.on_aura_applied(ar.aura)
            except Exception:
                pass

        if hasattr(ctx, "log"):
            if getattr(ar, "refreshed", False) and ar.aura is not None:
                ctx.log.aura_refresh(effect_row, actor, target, aura_id, int(ar.aura.remaining_duration), False)
            ctx.log.aura_apply(effect_row, actor, target, aura_id, duration, False, getattr(ar, "reason", "OK"))

        executed = bool(getattr(ar, "applied", False) or getattr(ar, "refreshed", False))
        return EffectResult(executed=executed)
