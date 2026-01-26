from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from engine.core.ability_executor import AbilityExecutor
from engine.core.actions import ActionKind, BattleAction


STATE_MOD_SPEED_PERCENT = 25  # BattlePetState: Mod_SpeedPercent


@dataclass
class RoundOutcome:
    round_no: int
    team0_action: BattleAction
    team1_action: BattleAction
    first_team_id: int
    winner_team_id: Optional[int] = None


class BattleLoop:
    """A minimal but battle-complete loop.

    Design goals:
      - Deterministic and testable (tie-break uses ctx.rng).
      - Data-driven ability execution via AbilityExecutor.use_ability_id.
      - Illegal action filtering (dead pet, swap locks, cooldowns, slot lockouts).

    Non-goals (v1):
      - Full WoW retail ruleset parity.
      - Complex multi-turn queueing for every ability (handled in AbilityExecutor/Scheduler).
    """

    def __init__(self, executor: Optional[AbilityExecutor] = None):
        self.ex = executor or AbilityExecutor()
        self.round_no = 0

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def legal_actions(self, ctx: Any, team_id: int) -> List[BattleAction]:
        """Return the legal action list for the given team.

        The action set is computed from:
          - current active pet (alive + swap-out locks)
          - selected abilities (pet.selected_abilities / pet.ability_slots)
          - cooldown + slot/ability lockouts
        """
        team_id = int(team_id)
        active_id = int(ctx.teams.active_pet_id(team_id))
        active_pet = ctx.pets.get(active_id)
        if active_pet is None:
            return [BattleAction(kind=ActionKind.PASS, note="NO_ACTIVE")]

        # If active pet is dead, only allow swap to an alive pet.
        if not self._pet_alive(active_pet):
            return self._legal_swaps_only(ctx, team_id, note="FORCED_SWAP")

        acts: List[BattleAction] = []

        # Ability actions
        for slot_idx, ability_id in self._get_selected_abilities(active_pet):
            if ability_id <= 0:
                continue
            if not ctx.teams.can_act(active_id, ctx):
                continue
            if hasattr(ctx, "cooldowns") and ctx.cooldowns.get(active_id, ability_id) > 0:
                continue
            if slot_idx > 0 and ctx.teams.is_slot_locked(active_id, slot_idx):
                continue
            if ctx.teams.is_ability_locked(active_id, ability_id):
                continue
            acts.append(BattleAction(kind=ActionKind.USE_ABILITY, ability_id=int(ability_id), slot_index=int(slot_idx)))

        # Swap actions (voluntary)
        if ctx.teams.can_swap_out(active_id, ctx):
            swaps = self._legal_swaps_only(ctx, team_id)
            acts.extend(swaps)

        if not acts:
            acts.append(BattleAction(kind=ActionKind.PASS, note="NO_LEGAL"))
        return acts

    def run_round(self, ctx: Any, action0: BattleAction, action1: BattleAction, pets: List[Any]) -> RoundOutcome:
        """Execute one round: TURN_START -> actions (ordered) -> TURN_END.

        - If a pet dies before its scheduled action, that side skips the action.
        - If an action becomes illegal at execution-time (forced swap etc.), it is replaced by the
          first available legal action.
        """

        self.round_no += 1
        self.ex.on_turn_start(ctx, pets)

        # Racial passive: on_round_start
        racial = getattr(ctx, "racial", None)
        if racial is not None and hasattr(racial, "on_round_start"):
            try:
                racial.on_round_start(ctx, pets)
            except Exception:
                pass

        # Ensure dead actives are immediately replaced (no action this round).
        skip_team: Dict[int, bool] = {0: False, 1: False}
        for tid in (0, 1):
            if self._ensure_active_alive(ctx, tid, reason="TURN_START"):
                # pet was replaced => skip that team's action this round
                skip_team[tid] = True

        # Resolve ordering
        first, second = self._order(ctx, action0, action1)

        # Persist round ordering for order-conditional opcodes (e.g., Prop233/234).
        # This enables correct "attacks last" detection beyond simple speed comparisons.
        from types import SimpleNamespace
        if not hasattr(ctx, "btl") or ctx.btl is None:
            ctx.btl = SimpleNamespace()
        try:
            ctx.btl.round_no = int(self.round_no)
            ctx.btl.round_first_team_id = int(first)
            ctx.btl.round_second_team_id = int(second)
            ctx.btl.round_first_actor_id = int(ctx.teams.active_pet_id(first))
            ctx.btl.round_second_actor_id = int(ctx.teams.active_pet_id(second))
            # Per-round transient state for opcodes that depend on "was struck first".
            ctx.btl.phase = ""
            ctx.btl.round_second_was_struck_first = 0
            ctx.btl.struck_before_action_ids = set()
        except Exception:
            pass

        # Execute in order
        try:
            ctx.btl.phase = "FIRST_ACTION"
        except Exception:
            pass
        self._exec_if_not_skipped(ctx, team_id=first, action=(action0 if first == 0 else action1), pets=pets, skip_team=skip_team)
        # If the second team's active died due to first action, it should be replaced; in WoW this forfeits the action.
        if self._ensure_active_alive(ctx, second, reason="AFTER_FIRST_ACTION"):
            skip_team[second] = True
        try:
            ctx.btl.phase = "SECOND_ACTION"
        except Exception:
            pass
        self._exec_if_not_skipped(ctx, team_id=second, action=(action0 if second == 0 else action1), pets=pets, skip_team=skip_team)

        try:
            ctx.btl.phase = ""
        except Exception:
            pass

        self.ex.on_turn_end(ctx, pets)

        # Racial passive: on_round_end
        racial = getattr(ctx, "racial", None)
        if racial is not None and hasattr(racial, "on_round_end"):
            try:
                racial.on_round_end(ctx, pets)
            except Exception:
                pass

        winner = self._winner(ctx)
        return RoundOutcome(
            round_no=self.round_no,
            team0_action=action0,
            team1_action=action1,
            first_team_id=first,
            winner_team_id=winner,
        )

    # ---------------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------------
    def _pet_alive(self, pet: Any) -> bool:
        # Also consider undead immortality phase as "alive"
        return bool(getattr(pet, "alive", True)) and int(getattr(pet, "hp", 1)) > 0

    def _check_and_handle_death(self, ctx: Any, pet: Any) -> bool:
        """Check if pet should die and handle racial passive resurrections.

        Returns True if pet was revived by a racial passive, False otherwise.
        """
        if pet is None:
            return False
        if int(getattr(pet, "hp", 0)) > 0:
            return False
        if not bool(getattr(pet, "alive", True)):
            return False

        # Pet HP is 0 and still marked alive - trigger racial passive death check
        racial = getattr(ctx, "racial", None)
        if racial is not None and hasattr(racial, "on_pet_death"):
            try:
                revived = racial.on_pet_death(ctx, pet)
                if revived:
                    return True
            except Exception:
                pass

        # No revive - mark as dead
        try:
            pet.alive = False
        except Exception:
            pass
        return False

    def _get_selected_abilities(self, pet: Any) -> List[Tuple[int, int]]:
        """Return list[(slot_index, ability_id)] in stable slot order.

        Supported shapes:
          - pet.selected_abilities: list[int] length >= 3
          - pet.ability_slots: dict[int->int] (1..3)
          - pet.abilities: dict slot names -> ability_id (best-effort)
        """
        if hasattr(pet, "selected_abilities") and isinstance(getattr(pet, "selected_abilities"), list):
            lst = [int(x) for x in getattr(pet, "selected_abilities")]
            out = []
            for i in range(3):
                out.append((i + 1, int(lst[i]) if i < len(lst) else 0))
            return out

        if hasattr(pet, "ability_slots") and isinstance(getattr(pet, "ability_slots"), dict):
            mp = getattr(pet, "ability_slots")
            return [(1, int(mp.get(1, 0))), (2, int(mp.get(2, 0))), (3, int(mp.get(3, 0)))]

        # Best-effort fallback: treat pet.abilities as already-selected mapping
        if hasattr(pet, "abilities") and isinstance(getattr(pet, "abilities"), dict):
            mp = getattr(pet, "abilities")
            # allow either {1:..} or {"slot1":..}
            def g(k1, k2):
                if k1 in mp:
                    return int(mp.get(k1) or 0)
                if k2 in mp:
                    return int(mp.get(k2) or 0)
                return 0

            return [(1, g(1, "slot1")), (2, g(2, "slot2")), (3, g(3, "slot3"))]

        return [(1, 0), (2, 0), (3, 0)]

    def _legal_swaps_only(self, ctx: Any, team_id: int, *, note: str = "") -> List[BattleAction]:
        team_id = int(team_id)
        t = ctx.teams.teams[team_id]
        active_idx = int(t.active_index)

        acts: List[BattleAction] = []
        for idx, pid in enumerate(t.pet_ids):
            pid = int(pid)
            if idx == active_idx:
                continue
            pet = ctx.pets.get(pid)
            if pet is None:
                continue
            if not self._pet_alive(pet):
                continue
            if not ctx.teams.can_swap_in(pid, ctx):
                continue
            acts.append(BattleAction(kind=ActionKind.SWAP, swap_index=int(idx), note=(note or None)))
        if not acts:
            return [BattleAction(kind=ActionKind.PASS, note="NO_SWAP_CAND")]
        return acts

    def _ensure_active_alive(self, ctx: Any, team_id: int, *, reason: str) -> bool:
        """Ensure the active pet is alive.

        Returns True if a replacement occurred.
        """
        team_id = int(team_id)
        active_id = int(ctx.teams.active_pet_id(team_id))
        pet = ctx.pets.get(active_id)
        if pet is None:
            return False

        # Check for death and handle racial passives (Undead/Mechanical resurrect)
        if int(getattr(pet, "hp", 0)) <= 0 and bool(getattr(pet, "alive", True)):
            revived = self._check_and_handle_death(ctx, pet)
            if revived:
                # Pet was revived by racial passive, no swap needed
                return False

        if self._pet_alive(pet):
            return False

        t = ctx.teams.teams[team_id]
        # Death replacement should not be blocked by swap-out lock (pet is dead).
        for idx, pid in enumerate(t.pet_ids):
            pid = int(pid)
            if pid == active_id:
                continue
            cand = ctx.pets.get(pid)
            if cand is None:
                continue
            if not self._pet_alive(cand):
                continue
            # Prefer respecting swap-in lock, but if none available, we will bypass.
            if ctx.teams.can_swap_in(pid, ctx):
                t.active_index = int(idx)
                if hasattr(ctx, "log"):
                    ctx.log.swap(team_id, active_id, pid, forced=True, reason=reason)
                return True

        # Bypass swap-in lock as a last resort (keeps the battle progressing).
        for idx, pid in enumerate(t.pet_ids):
            pid = int(pid)
            if pid == active_id:
                continue
            cand = ctx.pets.get(pid)
            if cand is None:
                continue
            if not self._pet_alive(cand):
                continue
            t.active_index = int(idx)
            if hasattr(ctx, "log"):
                ctx.log.swap(team_id, active_id, pid, forced=True, reason=f"{reason}:BYPASS_SWAPIN")
            return True

        return False

    def _effective_speed(self, ctx: Any, pet_id: int) -> int:
        pet_id = int(pet_id)
        pet = ctx.pets.get(pet_id)
        if pet is None:
            return 0

        # Prefer StatsResolver if present (keeps battle loop consistent with
        # damage/heal pipelines and aura/state semantics).
        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "effective_speed"):
            try:
                return int(stats.effective_speed(ctx, pet_id))
            except Exception:
                pass

        base = int(getattr(pet, "speed", 0))

        # Sum Mod_SpeedPercent from:
        #   - StateManager values (Prop31)
        #   - Aura meta bindings (ScriptDB ability_states)
        pct = 0
        if hasattr(ctx, "states"):
            pct += int(ctx.states.get(pet_id, STATE_MOD_SPEED_PERCENT, 0))

        if hasattr(ctx, "aura") and hasattr(ctx, "scripts") and ctx.scripts is not None:
            # Aura meta may include state_id=25 with value in state_binds.
            for aura in ctx.aura.list_owner(pet_id).values():
                meta = getattr(aura, "meta", {}) or {}
                binds = meta.get("state_binds") or []
                if isinstance(binds, list):
                    for b in binds:
                        if not isinstance(b, dict):
                            continue
                        try:
                            sid = int(b.get("state_id") or 0)
                            val = int(b.get("value") or 0)
                        except Exception:
                            continue
                        if sid == STATE_MOD_SPEED_PERCENT:
                            pct += int(val)

        # Clamp to avoid negative/degenerate speeds
        sp = int(base * (100 + pct) / 100)
        if sp < 1:
            sp = 1
        return sp

    def _order(self, ctx: Any, action0: BattleAction, action1: BattleAction) -> Tuple[int, int]:
        """Return (first_team_id, second_team_id)."""
        a0 = action0
        a1 = action1

        # Priority marker (Prop116) override
        pr = int(getattr(getattr(ctx, "btl", None), "priority_actor_id", 0) or 0)
        if pr != 0:
            p0 = int(ctx.teams.active_pet_id(0))
            p1 = int(ctx.teams.active_pet_id(1))
            if pr == p0 and pr != p1:
                # One-shot priority marker: consume.
                if hasattr(ctx, "btl"):
                    ctx.btl.priority_actor_id = 0
                return 0, 1
            if pr == p1 and pr != p0:
                if hasattr(ctx, "btl"):
                    ctx.btl.priority_actor_id = 0
                return 1, 0

        # Swap actions execute before ability actions by default.
        def pri(a: BattleAction) -> int:
            if a.kind == ActionKind.SWAP:
                return 0
            if a.kind == ActionKind.USE_ABILITY:
                return 1
            return 2

        p0 = pri(a0)
        p1 = pri(a1)
        if p0 != p1:
            return (0, 1) if p0 < p1 else (1, 0)

        s0 = self._effective_speed(ctx, int(ctx.teams.active_pet_id(0)))
        s1 = self._effective_speed(ctx, int(ctx.teams.active_pet_id(1)))
        if s0 != s1:
            return (0, 1) if s0 > s1 else (1, 0)

        # Deterministic tie-break
        r = float(getattr(ctx, "rng").rand_gate()) if hasattr(getattr(ctx, "rng", None), "rand_gate") else 0.0
        return (0, 1) if r < 0.5 else (1, 0)

    def _exec_if_not_skipped(self, ctx: Any, *, team_id: int, action: BattleAction, pets: List[Any], skip_team: Dict[int, bool]) -> None:
        team_id = int(team_id)
        if skip_team.get(team_id, False):
            return

        # Re-validate the action at execution-time.
        legal = self.legal_actions(ctx, team_id)
        use = action
        if not self._action_is_legal(action, legal):
            use = legal[0]

        if use.kind == ActionKind.PASS:
            return

        if use.kind == ActionKind.SWAP:
            before = int(ctx.teams.active_pet_id(team_id))
            ok, reason = ctx.teams.swap(team_id, int(use.swap_index), ctx)
            after = int(ctx.teams.active_pet_id(team_id))
            if hasattr(ctx, "log"):
                ctx.log.swap(team_id, before, after, forced=False, reason=("OK" if ok else reason))
            return

        # USE_ABILITY
        actor_id = int(ctx.teams.active_pet_id(team_id))
        opp_id = int(ctx.teams.active_pet_id(1 - team_id))
        actor = ctx.pets.get(actor_id)
        target = ctx.pets.get(opp_id)
        if actor is None or target is None:
            return
        self.ex.use_ability_id(ctx, actor, target, int(use.ability_id), slot_index=int(use.slot_index))

    def _action_is_legal(self, a: BattleAction, legal: List[BattleAction]) -> bool:
        if a.kind == ActionKind.PASS:
            return True
        for x in legal:
            if a.kind != x.kind:
                continue
            if a.kind == ActionKind.SWAP and int(a.swap_index) == int(x.swap_index):
                return True
            if a.kind == ActionKind.USE_ABILITY and int(a.ability_id) == int(x.ability_id) and int(a.slot_index) == int(x.slot_index):
                return True
        return False

    def _winner(self, ctx: Any) -> Optional[int]:
        alive_team = {0: False, 1: False}
        for tid in (0, 1):
            t = ctx.teams.teams[int(tid)]
            for pid in t.pet_ids:
                pet = ctx.pets.get(int(pid))
                if pet is not None and self._pet_alive(pet):
                    alive_team[tid] = True
        if alive_team[0] and alive_team[1]:
            return None
        if alive_team[0] and not alive_team[1]:
            return 0
        if alive_team[1] and not alive_team[0]:
            return 1
        return None
