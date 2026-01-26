from dataclasses import dataclass
from typing import Optional, Any, List

@dataclass
class EffectRow:
    ability_id: int
    turn_id: int
    effect_id: int
    prop_id: int
    order_index: int
    param_label: str
    param_raw: str
    aura_ability_id: Optional[int] = None
    scheduled_effect_rows: Optional[List[Any]] = None
