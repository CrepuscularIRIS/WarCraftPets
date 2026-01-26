from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Mapping, Tuple

import pandas as pd
import json
from pathlib import Path

from engine.core.events import Event
from engine.model.effect_row import EffectRow


@dataclass(frozen=True)
class ScriptDBConfig:
    # Map DB2 EventTypeEnum integer -> Event string ("TURN_START"/"TURN_END")
    event_type_map: Dict[int, str]

    @staticmethod
    def default() -> "ScriptDBConfig":
        return ScriptDBConfig(event_type_map={
            6: Event.TURN_START.value,  # v4 demo convention
            7: Event.TURN_END.value,
        })


class ScriptDB:
    def __init__(self, config: Optional[ScriptDBConfig] = None):
        self.config = config or ScriptDBConfig.default()

        # aura_ability_id -> event -> rows
        self._aura_periodic: Dict[int, Dict[str, List[EffectRow]]] = {}

        # aura_ability_id -> metadata dict (raw, data-driven)
        self._aura_meta: Dict[int, Dict[str, Any]] = {}

        # ability_id -> base info (cooldown, type, etc)
        self._ability_info: Dict[int, Dict[str, Any]] = {}

        # ability_id -> cast turns (each turn is a list of EffectRow)
        self._ability_cast: Dict[int, List[List[EffectRow]]] = {}

    def get_aura_periodic(self, aura_ability_id: int) -> Dict[str, List[EffectRow]]:
        return dict(self._aura_periodic.get(int(aura_ability_id), {}))

    def get_aura_meta(self, aura_ability_id: int) -> Dict[str, Any]:
        return dict(self._aura_meta.get(int(aura_ability_id), {}))

    def get_ability_info(self, ability_id: int) -> Dict[str, Any]:
        return dict(self._ability_info.get(int(ability_id), {}))

    def get_ability_cooldown(self, ability_id: int) -> int:
        info = self._ability_info.get(int(ability_id), {})
        try:
            return int(info.get("cooldown", 0))
        except Exception:
            return 0

    def get_ability_cast_turns(self, ability_id: int) -> List[List[EffectRow]]:
        turns = self._ability_cast.get(int(ability_id), [])
        return [list(rows) for rows in turns]

    def attach_periodic_to_aura(self, aura_instance: Any) -> None:
        aura_id = int(getattr(aura_instance, "aura_id", 0))
        payloads = self.get_aura_periodic(aura_id)
        if not payloads:
            return
        aura_instance.periodic_payloads.update(payloads)

    def attach_meta_to_aura(self, aura_instance: Any) -> None:
        aura_id = int(getattr(aura_instance, "aura_id", 0))
        meta = self.get_aura_meta(aura_id)
        if not meta:
            return
        aura_instance.meta.update(meta)

    @staticmethod
    def from_xlsx(path: str, *, config: Optional[ScriptDBConfig] = None) -> "ScriptDB":
        ability_turn = pd.read_excel(path, sheet_name="BattlePetAbilityTurn")
        ability_eff = pd.read_excel(path, sheet_name="BattlePetAbilityEffect")
        eff_props = pd.read_excel(path, sheet_name="BattlePetEffectProperties")

        # Optional sheets (not always present)
        ability_state = None
        state = None
        try:
            ability_state = pd.read_excel(path, sheet_name="BattlePetAbilityState")
        except Exception:
            pass
        try:
            state = pd.read_excel(path, sheet_name="BattlePetState")
        except Exception:
            pass

        return ScriptDB.from_frames(
            ability_turn=ability_turn,
            ability_effect=ability_eff,
            effect_properties=eff_props,
            ability_state=ability_state,
            state=state,
            config=config,
        )

    @staticmethod
    def from_ability_pack_json(
        path: str | Path,
        *,
        config: Optional[ScriptDBConfig] = None,
        periodic_default_event_type: int = 6,
        attach_cast_is_periodic: bool = True,
    ) -> "ScriptDB":
        """Load aura periodic scripts and aura meta from a petbattle ability pack JSON.

        This integrates with the data-driven ability pack we generate:
          abilities[].cast.turns[].effects[].params_raw
          abilities[].triggers.by_event[EventTypeEnum].turns[].effects[].params_raw

        Policy (conservative, runtime-friendly):
          - Trigger turns (TurnType=TRIGGER) are attached based on event_type_map.
          - Additionally, for aura abilities that have no trigger turns, we may attach
            any cast effects with an "IsPeriodic" param set to 1 to the default tick event.
            (This matches the common DOT/HOT modeling where the aura's cast defines its tick.)

        The pack file must be strict JSON. (The debug JSONC contains comments and is for humans.)
        """
        p = Path(path)
        obj = json.loads(p.read_text(encoding="utf-8"))
        return ScriptDB.from_ability_pack_obj(
            obj,
            config=config,
            periodic_default_event_type=periodic_default_event_type,
            attach_cast_is_periodic=attach_cast_is_periodic,
        )

    @staticmethod
    def from_ability_pack_obj(
        obj: Dict[str, Any],
        *,
        config: Optional[ScriptDBConfig] = None,
        periodic_default_event_type: int = 6,
        attach_cast_is_periodic: bool = True,
    ) -> "ScriptDB":
        """Same as from_ability_pack_json, but accepts an already-loaded pack object."""
        db = ScriptDB(config=config)

        # --- opcode_id -> param_label (best-effort) ---
        opcode_schema = {}
        for op in (obj.get("opcodes") or []):
            if not isinstance(op, dict):
                continue
            try:
                pid = int(op.get("opcode_id") or 0)
            except Exception:
                continue
            schema = op.get("param_schema") or []
            if not isinstance(schema, list):
                schema = []
            # Build tokens by position (preserve gaps); trim trailing empties.
            max_pos = 0
            toks: Dict[int, str] = {}
            for it in schema:
                if not isinstance(it, dict):
                    continue
                try:
                    pos = int(it.get("pos") or 0)
                except Exception:
                    continue
                if pos <= 0 or pos > 6:
                    continue
                max_pos = max(max_pos, pos)
                k = str(it.get("k") or "")
                toks[pos] = k
            out = []
            for pos in range(1, max_pos + 1):
                out.append(toks.get(pos, ""))
            # trim trailing empties
            while out and out[-1] == "":
                out.pop()
            opcode_schema[pid] = ",".join(out)

        # --- quick lookup for IsPeriodic position per opcode ---
        is_periodic_pos: Dict[int, int] = {}
        for op in (obj.get("opcodes") or []):
            if not isinstance(op, dict):
                continue
            try:
                pid = int(op.get("opcode_id") or 0)
            except Exception:
                continue
            schema = op.get("param_schema") or []
            if not isinstance(schema, list):
                continue
            for it in schema:
                if not isinstance(it, dict):
                    continue
                if str(it.get("k") or "") == "IsPeriodic":
                    try:
                        is_periodic_pos[pid] = int(it.get("pos") or 0)
                    except Exception:
                        pass

        # --- state flags map (optional) ---
        state_flags: Dict[int, int] = {}
        for st in (obj.get("states") or []):
            if not isinstance(st, dict):
                continue
            try:
                sid = int(st.get("state_id") or 0)
            except Exception:
                continue
            if sid <= 0:
                continue
            try:
                state_flags[sid] = int(st.get("flags") or 0)
            except Exception:
                state_flags[sid] = 0

        def map_event_type(evt_type: int) -> Optional[str]:
            return db.config.event_type_map.get(int(evt_type))

        default_ev = map_event_type(int(periodic_default_event_type))

        # --- build periodic scripts + meta ---
        abilities = obj.get("abilities") or []
        if not isinstance(abilities, list):
            return db

        for ab in abilities:
            if not isinstance(ab, dict):
                continue
            try:
                aura_id = int(ab.get("ability_id") or 0)
            except Exception:
                continue
            # Base ability info (for runtime execution)
            db._ability_info[aura_id] = {
                "kind": str(ab.get("kind") or ""),
                "pet_type_enum": int(ab.get("pet_type_enum") or 0),
                "cooldown": int(ab.get("cooldown") or 0),
                "flags": int(ab.get("flags") or 0),
                "visual_id": int(ab.get("visual_id") or 0),
            }

            # Cast turns (used by AbilityExecutor for active ability execution)
            cast = ab.get("cast")
            turns = None
            if isinstance(cast, dict):
                turns = cast.get("turns")
            if isinstance(turns, list) and turns:
                out_turns: List[List[EffectRow]] = []
                for t in turns:
                    if not isinstance(t, dict):
                        continue
                    turn_id = int(t.get("turn_id") or 0)
                    turn_order = int(t.get("turn_order_index") or 0)
                    effs = t.get("effects") or []
                    if not isinstance(effs, list) or not effs:
                        continue
                    rows: List[EffectRow] = []
                    for e in effs:
                        if not isinstance(e, dict):
                            continue
                        try:
                            prop_id = int(e.get("opcode_id") or 0)
                        except Exception:
                            continue
                        effect_id = int(e.get("effect_id") or 0)
                        eff_order = int(e.get("order") or 0)
                        params_raw = e.get("params_raw") or [0, 0, 0, 0, 0, 0]
                        if not isinstance(params_raw, list):
                            params_raw = [0, 0, 0, 0, 0, 0]
                        pr = [(int(x) if str(x).lstrip("-").isdigit() else 0) for x in (params_raw + [0]*6)[:6]]
                        param_label = opcode_schema.get(prop_id, "")
                        param_raw_s = ",".join(str(x) for x in pr)
                        aura_ref = int(e.get("aura_ability_id") or 0)
                        er = EffectRow(
                            ability_id=aura_id,
                            turn_id=turn_id,
                            effect_id=effect_id,
                            prop_id=prop_id,
                            order_index=turn_order * 100 + eff_order,
                            param_label=param_label,
                            param_raw=param_raw_s,
                            aura_ability_id=(aura_ref or None),
                        )
                        rows.append(er)
                    if rows:
                        out_turns.append(sorted(rows, key=lambda x: (x.order_index, x.effect_id)))
                if out_turns:
                    db._ability_cast[aura_id] = out_turns

            # Meta: ability_states (if present)
            binds = []
            sids = []
            svals = []
            sflags = []
            for bs in (ab.get("ability_states") or []):
                if not isinstance(bs, dict):
                    continue
                try:
                    sid = int(bs.get("state_id") or 0)
                except Exception:
                    continue
                if sid <= 0:
                    continue
                try:
                    val = int(bs.get("value") or 0)
                except Exception:
                    val = 0
                flg = int(state_flags.get(sid, 0))
                binds.append({"state_id": sid, "value": val, "flags": flg})
                sids.append(sid)
                svals.append(val)
                if flg != 0:
                    sflags.append(flg)

            if binds:
                db._aura_meta[aura_id] = {
                    "state_ids": sids,
                    "state_values": svals,
                    "state_flags": sflags,
                    "state_binds": binds,
                }

            # Periodic scripts from triggers (preferred)
            triggers = ab.get("triggers")
            by_event = None
            if isinstance(triggers, dict):
                be = triggers.get("by_event")
                if isinstance(be, dict):
                    by_event = be

            any_trigger_rows = False
            if by_event:
                for ev_str, turns in by_event.items():
                    try:
                        ev_type = int(ev_str)
                    except Exception:
                        continue
                    ev = map_event_type(ev_type)
                    if ev is None:
                        continue
                    if not isinstance(turns, list):
                        continue
                    for t in turns:
                        if not isinstance(t, dict):
                            continue
                        turn_id = int(t.get("turn_id") or 0)
                        turn_order = int(t.get("turn_order_index") or 0)
                        effs = t.get("effects") or []
                        if not isinstance(effs, list):
                            continue
                        for e in effs:
                            if not isinstance(e, dict):
                                continue
                            try:
                                prop_id = int(e.get("opcode_id") or 0)
                            except Exception:
                                continue
                            effect_id = int(e.get("effect_id") or 0)
                            eff_order = int(e.get("order") or 0)
                            params_raw = e.get("params_raw") or [0, 0, 0, 0, 0, 0]
                            if not isinstance(params_raw, list):
                                params_raw = [0, 0, 0, 0, 0, 0]
                            # ensure len 6
                            pr = [(int(x) if str(x).lstrip("-").isdigit() else 0) for x in (params_raw + [0]*6)[:6]]

                            param_label = opcode_schema.get(prop_id, "")
                            param_raw_s = ",".join(str(x) for x in pr)
                            aura_ref = int(e.get("aura_ability_id") or 0)
                            er = EffectRow(
                                ability_id=aura_id,
                                turn_id=turn_id,
                                effect_id=effect_id,
                                prop_id=prop_id,
                                order_index=turn_order * 100 + eff_order,
                                param_label=param_label,
                                param_raw=param_raw_s,
                                aura_ability_id=(aura_ref or None),
                            )
                            db._aura_periodic.setdefault(aura_id, {}).setdefault(ev, []).append(er)
                            any_trigger_rows = True

            # Periodic scripts from cast turn (fallback for DOT/HOT modeled in cast with IsPeriodic=1)
            if attach_cast_is_periodic and not any_trigger_rows and default_ev is not None:
                cast = ab.get("cast")
                turns = None
                if isinstance(cast, dict):
                    turns = cast.get("turns")
                if isinstance(turns, list):
                    for t in turns:
                        if not isinstance(t, dict):
                            continue
                        turn_id = int(t.get("turn_id") or 0)
                        turn_order = int(t.get("turn_order_index") or 0)
                        effs = t.get("effects") or []
                        if not isinstance(effs, list):
                            continue
                        for e in effs:
                            if not isinstance(e, dict):
                                continue
                            try:
                                prop_id = int(e.get("opcode_id") or 0)
                            except Exception:
                                continue
                            pos = int(is_periodic_pos.get(prop_id, 0) or 0)
                            if pos <= 0 or pos > 6:
                                continue
                            params_raw = e.get("params_raw") or [0, 0, 0, 0, 0, 0]
                            if not isinstance(params_raw, list):
                                continue
                            pr = [(int(x) if str(x).lstrip("-").isdigit() else 0) for x in (params_raw + [0]*6)[:6]]
                            if pr[pos - 1] == 0:
                                continue

                            effect_id = int(e.get("effect_id") or 0)
                            eff_order = int(e.get("order") or 0)
                            param_label = opcode_schema.get(prop_id, "")
                            param_raw_s = ",".join(str(x) for x in pr)
                            aura_ref = int(e.get("aura_ability_id") or 0)
                            er = EffectRow(
                                ability_id=aura_id,
                                turn_id=turn_id,
                                effect_id=effect_id,
                                prop_id=prop_id,
                                order_index=turn_order * 100 + eff_order,
                                param_label=param_label,
                                param_raw=param_raw_s,
                                aura_ability_id=(aura_ref or None),
                            )
                            db._aura_periodic.setdefault(aura_id, {}).setdefault(default_ev, []).append(er)

        # Ensure deterministic order
        for aura_id, mp in db._aura_periodic.items():
            for ev, rows in mp.items():
                mp[ev] = sorted(rows, key=lambda x: (x.order_index, x.effect_id))

        return db

    @staticmethod
    def from_frames(
        *,
        ability_turn: pd.DataFrame,
        ability_effect: pd.DataFrame,
        effect_properties: pd.DataFrame,
        ability_state: Optional[pd.DataFrame] = None,
        state: Optional[pd.DataFrame] = None,
        config: Optional[ScriptDBConfig] = None,
    ) -> "ScriptDB":
        db = ScriptDB(config=config)

        # Map PropID -> ParamLabel
        prop2label = {}
        if effect_properties is not None and len(effect_properties) > 0:
            for _, r in effect_properties.iterrows():
                try:
                    prop2label[int(r["ID"])] = str(r.get("ParamLabel", ""))
                except Exception:
                    continue

        # Join turn + effect
        t = ability_turn.rename(columns={
            "ID": "turn_id",
            "BattlePetAbilityID": "ability_id",
            "OrderIndex": "turn_order",
            "EventTypeEnum": "event_type",
        })
        e = ability_effect.rename(columns={
            "ID": "effect_id",
            "BattlePetAbilityTurnID": "turn_id",
            "OrderIndex": "effect_order",
            "BattlePetEffectPropertiesID": "prop_id",
            "AuraBattlePetAbilityID": "aura_ability_id",
            "Param": "param_raw",
        })

        joined = e.merge(t[["turn_id", "ability_id", "turn_order", "event_type"]], on="turn_id", how="left")

        def map_event(evt: Any) -> Optional[str]:
            try:
                ev = int(evt)
            except Exception:
                return None
            return db.config.event_type_map.get(ev)

        for _, r in joined.iterrows():
            event = map_event(r.get("event_type", None))
            if event is None:
                continue

            aura_ability_id = int(r.get("ability_id", 0))
            prop_id = int(r.get("prop_id", 0))
            turn_id = int(r.get("turn_id", 0))
            effect_id = int(r.get("effect_id", 0))

            turn_order = int(r.get("turn_order", 0))
            effect_order = int(r.get("effect_order", 0))
            compound_order = turn_order * 100 + effect_order

            param_label = prop2label.get(prop_id, "")
            param_raw = str(r.get("param_raw", "0,0,0,0,0,0"))

            er = EffectRow(
                ability_id=aura_ability_id,
                turn_id=turn_id,
                effect_id=effect_id,
                prop_id=prop_id,
                order_index=compound_order,
                param_label=param_label,
                param_raw=param_raw,
                aura_ability_id=(int(r.get("aura_ability_id", 0)) or None),
            )

            db._aura_periodic.setdefault(aura_ability_id, {}).setdefault(event, []).append(er)

        # Ensure deterministic order
        for aura_id, mp in db._aura_periodic.items():
            for ev, rows in mp.items():
                mp[ev] = sorted(rows, key=lambda x: (x.order_index, x.effect_id))

        # --- Aura metadata: raw state bindings (optional) ---
        if ability_state is not None and len(ability_state) > 0:
            # Expect columns: BattlePetAbilityID, BattlePetStateID (or similar)
            # We store raw state ids; flags can be joined if BattlePetState sheet exists.
            ab_col = "BattlePetAbilityID" if "BattlePetAbilityID" in ability_state.columns else None
            st_col = "BattlePetStateID" if "BattlePetStateID" in ability_state.columns else None
            if ab_col and st_col:
                # Build state_id -> flags mapping
                state_flags = {}
                if state is not None and len(state) > 0 and "ID" in state.columns and "Flags" in state.columns:
                    for _, sr in state.iterrows():
                        try:
                            state_flags[int(sr["ID"])] = int(sr.get("Flags", 0))
                        except Exception:
                            continue

                grouped = ability_state.groupby(ab_col)[st_col].apply(list).to_dict()
                for ability_id, state_ids in grouped.items():
                    sids = []
                    sflags = []
                    for sid in state_ids:
                        try:
                            sid_i = int(sid)
                        except Exception:
                            continue
                        sids.append(sid_i)
                        if sid_i in state_flags:
                            sflags.append(state_flags[sid_i])
                    db._aura_meta[int(ability_id)] = {
                        "state_ids": sids,
                        "state_flags": sflags,
                    }

        return db
