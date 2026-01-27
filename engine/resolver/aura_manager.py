from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, List, Tuple

from engine.model.aura import AuraInstance

@dataclass
class AuraApplyResult:
    applied: bool
    refreshed: bool
    aura: Optional[AuraInstance]
    reason: str = "OK"  # OK | EXPIRED_IMMEDIATELY

@dataclass
class AuraExpire:
    owner_pet_id: int
    aura_id: int

class AuraManager:
    # Minimal aura storage.
    # - Stores at most one instance per (owner_pet_id, aura_id).
    # - Prop26/52 use apply(): overwrite duration, stacks stays 1.
    # - Prop54 uses apply_with_stack_limit(): stacks increased up to max, duration overwritten.
    # - tick(owner): decrements remaining_duration each TURN_END and expires at 0 (ignores -1).

    def __init__(self):
        self._auras: Dict[int, Dict[int, AuraInstance]] = {}

    def get(self, owner_pet_id: int, aura_id: int) -> Optional[AuraInstance]:
        return self._auras.get(int(owner_pet_id), {}).get(int(aura_id))

    def list_owner(self, owner_pet_id: int) -> Dict[int, AuraInstance]:
        return dict(self._auras.get(int(owner_pet_id), {}))

    def remove(self, owner_pet_id: int, aura_id: int) -> None:
        om = self._auras.get(int(owner_pet_id), {})
        om.pop(int(aura_id), None)
        if not om and int(owner_pet_id) in self._auras:
            self._auras.pop(int(owner_pet_id), None)

    def tick(self, owner_pet_id: int) -> List[AuraExpire]:
        # Decrement duration and expire
        expired: List[AuraExpire] = []
        om = self._auras.get(int(owner_pet_id), {})
        if not om:
            return expired

        to_remove = []
        for aura_id, inst in om.items():
            # Permanent aura (-1): just clear just_applied flag, never expire
            if inst.remaining_duration == -1:
                inst.just_applied = False
                continue

            # First turn after apply: handle tickdown_first_round logic
            if inst.just_applied:
                inst.just_applied = False
                if inst.tickdown_first_round and inst.remaining_duration > 0:
                    inst.remaining_duration -= 1
                    if inst.remaining_duration <= 0:
                        to_remove.append(aura_id)
                continue

            # Normal tick: decrement remaining duration
            if inst.remaining_duration > 0:
                inst.remaining_duration -= 1
                if inst.remaining_duration <= 0:
                    to_remove.append(aura_id)

        for aura_id in to_remove:
            om.pop(aura_id, None)
            expired.append(AuraExpire(owner_pet_id=int(owner_pet_id), aura_id=int(aura_id)))
        if not om:
            self._auras.pop(int(owner_pet_id), None)
        return expired

    def apply(
        self,
        *,
        owner_pet_id: int,
        caster_pet_id: int,
        aura_id: int,
        duration: int,
        tickdown_first_round: bool,
        source_effect_id: int,
    ) -> AuraApplyResult:
        duration = int(duration) if duration is not None else 0

        if duration != -1 and duration < 0:
            duration = 0

        if duration == 0:
            return AuraApplyResult(applied=False, refreshed=False, aura=None, reason="EXPIRED_IMMEDIATELY")

        owner_map = self._auras.setdefault(int(owner_pet_id), {})
        refreshed = int(aura_id) in owner_map

        aura = AuraInstance(
            aura_id=int(aura_id),
            owner_pet_id=int(owner_pet_id),
            caster_pet_id=int(caster_pet_id),
            source_effect_id=int(source_effect_id),
            remaining_duration=int(duration),
            tickdown_first_round=bool(tickdown_first_round),
            just_applied=True,
            stacks=1,
        )
        owner_map[int(aura_id)] = aura
        return AuraApplyResult(applied=not refreshed, refreshed=refreshed, aura=aura, reason="OK")

    def apply_with_stack_limit(
        self,
        *,
        owner_pet_id: int,
        caster_pet_id: int,
        aura_id: int,
        duration: int,
        max_stacks: int,
        source_effect_id: int,
    ) -> AuraApplyResult:
        duration = int(duration) if duration is not None else 0
        max_stacks = int(max_stacks) if max_stacks is not None else 1
        if max_stacks <= 0:
            max_stacks = 1

        if duration != -1 and duration < 0:
            duration = 0
        if duration == 0:
            return AuraApplyResult(applied=False, refreshed=False, aura=None, reason="EXPIRED_IMMEDIATELY")

        owner_map = self._auras.setdefault(int(owner_pet_id), {})
        existing = owner_map.get(int(aura_id))

        if existing is None:
            aura = AuraInstance(
                aura_id=int(aura_id),
                owner_pet_id=int(owner_pet_id),
                caster_pet_id=int(caster_pet_id),
                source_effect_id=int(source_effect_id),
                remaining_duration=int(duration),
                tickdown_first_round=False,
                just_applied=True,
                stacks=1,
            )
            owner_map[int(aura_id)] = aura
            return AuraApplyResult(applied=True, refreshed=False, aura=aura, reason="OK")

        # refresh + increment stacks up to limit
        existing.remaining_duration = int(duration)
        existing.caster_pet_id = int(caster_pet_id)
        existing.source_effect_id = int(source_effect_id)
        existing.just_applied = True
        if existing.stacks < max_stacks:
            existing.stacks += 1
        return AuraApplyResult(applied=False, refreshed=True, aura=existing, reason="OK")
