from __future__ import annotations

"""Global weather detector/holder.

Source data may represent weather as:
  - an aura applied to all pets, with `aura.meta.state_binds` containing a `Weather_*` state id, or
  - a battlefield-only aura (not modeled in v1), or
  - a direct state setter (Prop31) targeting a synthetic "battlefield" entity.

We keep the interface intentionally small:
  - `set_from_aura(...)` to update current weather
  - `detect_from_ctx(...)` fallback scanner
  - `clear_if_gone(...)` used from TickEngine when auras expire
"""

from dataclasses import dataclass
from typing import Any, Optional, Tuple

from engine.constants.weather import WEATHER_STATE_IDS


def _extract_weather_state_id(aura_meta: Any) -> Optional[int]:
    meta = aura_meta or {}
    binds = meta.get("state_binds") or []
    if not isinstance(binds, list):
        return None
    for b in binds:
        if not isinstance(b, dict):
            continue
        try:
            sid = int(b.get("state_id") or 0)
            val = int(b.get("value") or 0)
        except Exception:
            continue
        if sid in WEATHER_STATE_IDS and val != 0:
            return sid
    return None


@dataclass
class WeatherSnapshot:
    state_id: int
    aura_id: int
    remaining: int


class WeatherManager:
    def __init__(self):
        self._state_id: int = 0
        self._aura_id: int = 0

    def clear(self) -> None:
        self._state_id = 0
        self._aura_id = 0

    def on_aura_applied(self, aura: Any) -> None:
        """Hook for aura handlers; keeps weather cache up-to-date."""
        self.set_from_aura(aura)

    @property
    def active_state_id(self) -> int:
        return int(self._state_id)

    def set_from_aura(self, aura: Any) -> None:
        """Update active weather if the aura carries a Weather_* state bind."""
        if aura is None:
            return
        sid = _extract_weather_state_id(getattr(aura, "meta", {}) or {})
        if not sid:
            return
        self._state_id = int(sid)
        self._aura_id = int(getattr(aura, "aura_id", 0) or 0)

    def detect_from_ctx(self, ctx: Any) -> int:
        """Best-effort detection by scanning all active auras.

        Returns the detected weather state id (and updates internal cache).
        """
        # If already set, trust it.
        if self._state_id:
            return int(self._state_id)

        aura_mgr = getattr(ctx, "aura", None)
        if aura_mgr is None:
            return 0

        best: Optional[WeatherSnapshot] = None
        # Scan every owner list.
        for owner_id, mp in getattr(aura_mgr, "_auras", {}).items():
            for aura in (mp or {}).values():
                sid = _extract_weather_state_id(getattr(aura, "meta", {}) or {})
                if not sid:
                    continue
                rem = int(getattr(aura, "remaining_duration", 0) or 0)
                snap = WeatherSnapshot(state_id=int(sid), aura_id=int(getattr(aura, "aura_id", 0) or 0), remaining=rem)
                if best is None or snap.remaining > best.remaining:
                    best = snap

        if best is None:
            return 0

        self._state_id = int(best.state_id)
        self._aura_id = int(best.aura_id)
        return int(self._state_id)

    def clear_if_gone(self, ctx: Any) -> None:
        """Clear cache if the cached aura no longer exists."""
        if not self._state_id or not self._aura_id:
            return
        aura_mgr = getattr(ctx, "aura", None)
        if aura_mgr is None:
            self._state_id = 0
            self._aura_id = 0
            return

        for mp in getattr(aura_mgr, "_auras", {}).values():
            if int(self._aura_id) in (mp or {}):
                return

        self._state_id = 0
        self._aura_id = 0

    def current(self, ctx: Any) -> int:
        """Return current weather state id (0 if none)."""
        sid = int(self._state_id) if self._state_id else int(self.detect_from_ctx(ctx))
        if sid:
            self.clear_if_gone(ctx)
            return int(self._state_id)
        return 0
