from dataclasses import dataclass
from typing import Optional

@dataclass
class HealEvent:
    source_actor: object
    target: object
    ability_id: int
    effect_id: int
    points: int
    is_periodic: bool = False
    # Optional variance override (to mirror DamageEvent variance support).
    variance: Optional[float] = None
