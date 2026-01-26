from dataclasses import dataclass
from typing import Any, Tuple

@dataclass
class GateCheck:
    rng: Any

    @staticmethod
    def _normalize_chance(chance) -> float:
        # Accept: 0..1 probability, or 0..100 percentage (and tolerate ints >100 as 1.0 clamp)
        if chance is None:
            return 0.0
        try:
            c = float(chance)
        except Exception:
            return 0.0
        if c <= 0.0:
            return 0.0
        if c <= 1.0:
            return c
        # treat as percent
        c = c / 100.0
        if c > 1.0:
            c = 1.0
        return c

    def compute(self, chance) -> Tuple[bool, float, float]:
        # Always consume RNG gate roll for determinism.
        c = self._normalize_chance(chance)
        r = float(self.rng.rand_gate())
        passed = (r <= c)
        return passed, c, r
