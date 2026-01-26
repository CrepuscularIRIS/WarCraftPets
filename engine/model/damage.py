from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class DamageEvent:
    source_actor: Any
    target: Any
    ability_id: int
    effect_id: int
    points: int
    is_periodic: bool = False
    override_index: Optional[int] = None
    variance: Optional[float] = None
    attack_type_override: Optional[int] = None
