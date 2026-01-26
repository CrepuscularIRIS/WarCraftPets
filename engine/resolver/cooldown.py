from dataclasses import dataclass
from typing import Dict, Tuple

@dataclass
class CooldownManager:
    # key: (pet_id, ability_id) -> remaining turns
    _cd: Dict[Tuple[int, int], int]

    def __init__(self):
        self._cd = {}

    def get(self, pet_id: int, ability_id: int) -> int:
        return int(self._cd.get((int(pet_id), int(ability_id)), 0))

    def set(self, pet_id: int, ability_id: int, turns: int) -> None:
        t = int(turns)
        if t <= 0:
            self._cd.pop((int(pet_id), int(ability_id)), None)
        else:
            self._cd[(int(pet_id), int(ability_id))] = t

    def tick_down(self) -> None:
        # called once per battle round (TURN_START)
        remove = []
        for k, v in self._cd.items():
            nv = int(v) - 1
            if nv <= 0:
                remove.append(k)
            else:
                self._cd[k] = nv
        for k in remove:
            self._cd.pop(k, None)
