from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

# State ids from BattlePetState table (data-driven):
STATE_SWAP_OUT_LOCK = 36   # LuaName: swapOutLock
STATE_SWAP_IN_LOCK = 98    # LuaName: swapInLock
STATE_TURN_LOCK = 35       # LuaName: turnLock (stun / cannot act)

@dataclass
class Team:
    team_id: int
    pet_ids: List[int]
    active_index: int = 0

@dataclass
class TeamManager:
    teams: Dict[int, Team] = field(default_factory=dict)

    # pet_id -> team_id (for reverse lookup)
    pet_to_team: Dict[int, int] = field(default_factory=dict)

    # Ability lockouts:
    # - slot locks: pet_id -> slot_index (1-based) -> turns remaining
    slot_locks: Dict[int, Dict[int, int]] = field(default_factory=dict)
    # - pending "lock next ability used" duration: pet_id -> duration
    pending_next_ability_lock: Dict[int, int] = field(default_factory=dict)
    # - ability id locks (fallback if slot is unknown): pet_id -> ability_id -> turns remaining
    ability_locks: Dict[int, Dict[int, int]] = field(default_factory=dict)

    def register_team(self, team_id: int, pet_ids: List[int], *, active_index: int = 0) -> None:
        self.teams[int(team_id)] = Team(team_id=int(team_id), pet_ids=[int(x) for x in pet_ids], active_index=int(active_index))
        for pid in pet_ids:
            self.pet_to_team[int(pid)] = int(team_id)

    def team_of_pet(self, pet_id: int) -> Optional[int]:
        return self.pet_to_team.get(int(pet_id))

    def active_pet_id(self, team_id: int) -> int:
        t = self.teams[int(team_id)]
        return int(t.pet_ids[int(t.active_index)])

    def can_act(self, pet_id: int, ctx: Any) -> bool:
        # If pet has turnLock state (35), it cannot act.
        st = getattr(ctx, "states", None)
        if st is not None and st.get(int(pet_id), STATE_TURN_LOCK, 0) > 0:
            return False
        # If pet has aura meta state turnLock => cannot act.
        for aura in ctx.aura.list_owner(int(pet_id)).values():
            st_ids = (getattr(aura, "meta", {}) or {}).get("state_ids", [])
            if STATE_TURN_LOCK in st_ids:
                return False
        return True

    def can_swap_out(self, pet_id: int, ctx: Any) -> bool:
        # If active pet has swapOutLock => cannot be swapped out.
        for aura in ctx.aura.list_owner(int(pet_id)).values():
            st_ids = (getattr(aura, "meta", {}) or {}).get("state_ids", [])
            if STATE_SWAP_OUT_LOCK in st_ids:
                return False
        return True

    def can_swap_in(self, pet_id: int, ctx: Any) -> bool:
        # If candidate pet has swapInLock => cannot be swapped in.
        for aura in ctx.aura.list_owner(int(pet_id)).values():
            st_ids = (getattr(aura, "meta", {}) or {}).get("state_ids", [])
            if STATE_SWAP_IN_LOCK in st_ids:
                return False
        return True

    def swap(self, team_id: int, new_index: int, ctx: Any) -> Tuple[bool, str]:
        team_id = int(team_id); new_index = int(new_index)
        t = self.teams[team_id]
        if new_index < 0 or new_index >= len(t.pet_ids):
            return False, "INDEX_OOB"
        if new_index == int(t.active_index):
            return False, "ALREADY_ACTIVE"

        active_id = int(t.pet_ids[int(t.active_index)])
        if not self.can_swap_out(active_id, ctx):
            return False, "SWAP_OUT_LOCK"

        cand_id = int(t.pet_ids[new_index])
        if not self.can_swap_in(cand_id, ctx):
            return False, "SWAP_IN_LOCK"

        t.active_index = new_index
        return True, "OK"

    # ---- ability lockouts ----
    def lock_slot(self, pet_id: int, slot_index: int, duration: int) -> None:
        pid = int(pet_id); s = int(slot_index); d = int(duration)
        if d <= 0: 
            return
        self.slot_locks.setdefault(pid, {})[s] = max(d, self.slot_locks.get(pid, {}).get(s, 0))

    def lock_next_ability(self, pet_id: int, duration: int) -> None:
        pid = int(pet_id); d = int(duration)
        if d <= 0:
            return
        self.pending_next_ability_lock[pid] = max(d, int(self.pending_next_ability_lock.get(pid, 0)))

    def lock_ability_id(self, pet_id: int, ability_id: int, duration: int) -> None:
        pid = int(pet_id); aid = int(ability_id); d = int(duration)
        if d <= 0:
            return
        self.ability_locks.setdefault(pid, {})[aid] = max(d, self.ability_locks.get(pid, {}).get(aid, 0))

    def is_slot_locked(self, pet_id: int, slot_index: int) -> bool:
        return int(self.slot_locks.get(int(pet_id), {}).get(int(slot_index), 0)) > 0

    def is_ability_locked(self, pet_id: int, ability_id: int) -> bool:
        return int(self.ability_locks.get(int(pet_id), {}).get(int(ability_id), 0)) > 0

    def on_pet_use_ability(self, pet_id: int, *, slot_index: Optional[int], ability_id: Optional[int]) -> None:
        pid = int(pet_id)
        d = int(self.pending_next_ability_lock.get(pid, 0))
        if d <= 0:
            return
        # Consume pending lock and apply lock to the chosen slot if known; otherwise lock ability id.
        self.pending_next_ability_lock.pop(pid, None)
        if slot_index is not None:
            self.lock_slot(pid, int(slot_index), d)
        elif ability_id is not None:
            self.lock_ability_id(pid, int(ability_id), d)


    def _pet_alive(self, ctx: Any, pet_id: int) -> bool:
        # Skeleton: if ctx.pets dict is available, use it; otherwise assume alive.
        pets = getattr(ctx, "pets", None)
        if isinstance(pets, dict) and int(pet_id) in pets:
            p = pets[int(pet_id)]
            return bool(getattr(p, "alive", True)) and int(getattr(p, "hp", 1)) > 0
        return True

    def force_swap_random(self, target_pet_id: int, ctx: Any, *, ignore_swap_out_lock: bool = True) -> Tuple[bool, str, Optional[int]]:
        """Force the target team to swap their active pet to a random other alive pet.
        - Typically used by abilities like Nether Gate / Phase Punch.
        - In retail behavior, forced swaps generally bypass voluntary swap-out locks; we model that via ignore_swap_out_lock=True.
        Returns: (ok, reason, new_active_pet_id)
        """
        target_pet_id = int(target_pet_id)
        team_id = self.team_of_pet(target_pet_id)
        if team_id is None:
            return False, "TEAM_NOT_FOUND", None
        t = self.teams[int(team_id)]
        active_id = int(t.pet_ids[int(t.active_index)])

        if (not ignore_swap_out_lock) and (not self.can_swap_out(active_id, ctx)):
            return False, "SWAP_OUT_LOCK", None

        candidates = []
        for idx, pid in enumerate(t.pet_ids):
            pid = int(pid)
            if idx == int(t.active_index):
                continue
            if not self._pet_alive(ctx, pid):
                continue
            # Candidate must be swappable in unless forced swap ignores swap-in lock (we keep respecting swapInLock).
            if not self.can_swap_in(pid, ctx):
                continue
            candidates.append((idx, pid))

        if not candidates:
            return False, "NO_CANDIDATE", None

        r = float(getattr(ctx, "rng").rand_gate()) if hasattr(getattr(ctx, "rng", None), "rand_gate") else 0.0
        k = int(r * len(candidates))
        if k >= len(candidates):
            k = len(candidates) - 1
        new_idx, new_pid = candidates[k]
        t.active_index = int(new_idx)
        return True, "OK", int(new_pid)

    def tick_down(self) -> None:
        # Called at turn start (same as cooldown tick). Decrements locks.
        for pid, slots in list(self.slot_locks.items()):
            for s, v in list(slots.items()):
                nv = int(v) - 1
                if nv <= 0:
                    slots.pop(s, None)
                else:
                    slots[s] = nv
            if not slots:
                self.slot_locks.pop(pid, None)

        for pid, locks in list(self.ability_locks.items()):
            for a, v in list(locks.items()):
                nv = int(v) - 1
                if nv <= 0:
                    locks.pop(a, None)
                else:
                    locks[a] = nv
            if not locks:
                self.ability_locks.pop(pid, None)
