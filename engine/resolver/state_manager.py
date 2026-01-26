from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class StateChange:
    pet_id: int
    state_id: int
    value: int

class StateManager:
    def __init__(self):
        # pet_id -> state_id -> value
        self._m: Dict[int, Dict[int, int]] = {}

    def get(self, pet_id: int, state_id: int, default: int = 0) -> int:
        return int(self._m.get(int(pet_id), {}).get(int(state_id), default))

    def set(self, pet_id: int, state_id: int, value: int) -> StateChange:
        pid = int(pet_id); sid = int(state_id); v = int(value)
        self._m.setdefault(pid, {})[sid] = v
        return StateChange(pet_id=pid, state_id=sid, value=v)

    def clear_pet(self, pet_id: int) -> None:
        self._m.pop(int(pet_id), None)

    def snapshot_pet(self, pet_id: int) -> Dict[int, int]:
        return dict(self._m.get(int(pet_id), {}))
