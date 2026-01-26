from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class MiniLog:
    records: List[Any] = field(default_factory=list)

    # Diagnostics / semantics
    def warn(self, effect_row, code: str, detail: Optional[Dict[str, Any]] = None):
        """Record a non-fatal validation / semantics warning."""
        self.records.append(("warn", effect_row.prop_id, str(code), dict(detail or {})))

    # Generic results
    def unsupported(self, effect_row, reason: str):
        self.records.append(("unsupported", effect_row.prop_id, str(reason)))

    def effect_result(self, effect_row, actor, target, code: str, reason: Optional[str] = None):
        self.records.append(("effect_result", effect_row.prop_id, str(code), (str(reason) if reason is not None else None)))

    # Damage / Heal
    def damage(self, effect_row, actor, target, resolved):
        self.records.append(("damage", effect_row.prop_id, int(resolved.final_damage), dict(resolved.trace or {})))

    def heal(self, effect_row, actor, target, final_heal: int, trace: Optional[Dict[str, Any]] = None):
        self.records.append(("heal", effect_row.prop_id, int(final_heal), dict(trace or {})))

    # State ops
    def state_set(self, effect_row, actor, target, state_id: int, value: int):
        self.records.append(("state_set", effect_row.prop_id, int(state_id), int(value), int(getattr(target, "id", 0))))

    # Aura ops
    def aura_apply(self, effect_row, actor, target, aura_id: int, duration: int, tickdown_first_round: bool, reason: str):
        self.records.append(("aura_apply", effect_row.prop_id, int(aura_id), int(duration), bool(tickdown_first_round), str(reason)))

    def aura_refresh(self, effect_row, actor, target, aura_id: int, remaining_duration: int, tickdown_first_round: bool):
        self.records.append(("aura_refresh", effect_row.prop_id, int(aura_id), int(remaining_duration), bool(tickdown_first_round)))

    def aura_stack(self, effect_row, actor, target, aura_id: int, stacks: int, max_stack: int):
        self.records.append(("aura_stack", effect_row.prop_id, int(aura_id), int(stacks), int(max_stack)))

    def aura_expire(self, owner_pet_id: int, aura_id: int):
        self.records.append(("aura_expire", int(owner_pet_id), int(aura_id)))

    def aura_remove(self, owner_pet_id: int, aura_id: int, reason: str):
        self.records.append(("aura_remove", int(owner_pet_id), int(aura_id), str(reason)))

    def dispel(self, effect_row, actor, target, removed_count: int, reason: str):
        self.records.append(("dispel", effect_row.prop_id, int(removed_count), str(reason), int(getattr(target, "id", 0))))

    
    def cannot_act(self, pet_id: int, reason: str):
        self.records.append(("cannot_act", int(pet_id), str(reason)))

    # Cooldowns
    def cooldown_set(self, pet_id: int, ability_id: int, turns: int):
        self.records.append(("cooldown_set", int(pet_id), int(ability_id), int(turns)))

    def cooldown_tick(self):
        self.records.append(("cooldown_tick",))

    # Gate
    def gate(self, effect_row, actor, target, chance_norm: float, roll: float, passed: bool):
        self.records.append(("gate", effect_row.prop_id, float(chance_norm), float(roll), bool(passed)))

    # Timer scheduling
    def timer_schedule(self, effect_row, actor, target, delay_turns: int, payload_count: int, tag: str):
        self.records.append(("timer_schedule", effect_row.prop_id, int(delay_turns), int(payload_count), str(tag)))

    # Battle loop
    def swap(self, team_id: int, from_pet_id: int, to_pet_id: int, forced: bool, reason: str):
        self.records.append(("swap", int(team_id), int(from_pet_id), int(to_pet_id), bool(forced), str(reason)))
