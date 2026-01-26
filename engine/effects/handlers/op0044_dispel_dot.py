from __future__ import annotations

from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(44)
class H_Prop44_DispelDOT:
    """Prop44: Dispel a harmful periodic aura (DOT) from target.

    In this ability pack, opcode 44 appears paired with a heal effect on:
      - 168 Healing Flame
      - 173 Cauterize
      - 1078 Bandage
      - 1933 Rewind Time

    The DB2 param schema is (Points, Accuracy). The observed Points is
    always 50 in this pack and is not required to model a basic "cleanse"
    mechanic, therefore we treat opcode 44 as:

      - Perform a hit check using Accuracy.
      - Remove up to one harmful periodic aura (DOT) from the target.

    This is a conservative, evolvable implementation:
      - It prefers auras that actually carry periodic payloads.
      - It considers a periodic aura harmful if any periodic opcode is not
        a known healing opcode (23/100).
    """

    PROP_ID = 44

    _HEAL_OPS = {23, 100}

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        hit, reason = ctx.hitcheck.compute(
            ctx,
            actor,
            target,
            accuracy=args.get("accuracy", 1),
            dont_miss=bool(getattr(ctx.acc_ctx, "dont_miss", False)),
        )
        if not hit:
            ctx.log.effect_result(effect_row, actor, target, code="MISS", reason=reason)
            return EffectResult(executed=False)

        # Identify candidate DOT auras
        owner_map = ctx.aura.list_owner(getattr(target, "id", 0))
        candidates = []
        for aura_id, inst in owner_map.items():
            if self._is_harmful_periodic(inst):
                # prefer finite duration and higher remaining duration
                rd = getattr(inst, "remaining_duration", 0)
                finite = 0 if rd == -1 else 1
                candidates.append((finite, int(rd if rd != -1 else 10**9), int(aura_id)))

        if not candidates:
            ctx.log.dispel(effect_row, actor, target, removed_count=0, reason="NO_DOT")
            return EffectResult(executed=False, notes={"removed": 0})

        # Choose the most persistent harmful periodic aura (deterministic)
        candidates.sort(reverse=True)
        _, _, aura_id = candidates[0]
        ctx.aura.remove(getattr(target, "id", 0), int(aura_id))
        ctx.log.aura_remove(getattr(target, "id", 0), int(aura_id), reason="DISPEL_DOT")
        ctx.log.dispel(effect_row, actor, target, removed_count=1, reason="OK")

        stats = getattr(ctx, "stats", None)
        if stats is not None and hasattr(stats, "sync_pet"):
            try:
                stats.sync_pet(ctx, target)
            except Exception:
                pass
        return EffectResult(executed=True, notes={"removed": 1, "aura_id": int(aura_id)})

    def _is_harmful_periodic(self, aura_inst) -> bool:
        # Preferred payloads
        payloads = getattr(aura_inst, "periodic_payloads", None)
        if isinstance(payloads, dict) and payloads:
            for _, rows in payloads.items():
                for r in rows or []:
                    try:
                        op = int(getattr(r, "prop_id", getattr(r, "opcode_id", 0)) or 0)
                    except Exception:
                        op = 0
                    if op and op not in self._HEAL_OPS:
                        return True
            return False

        # Backward-compatible single list
        rows = getattr(aura_inst, "periodic_effect_rows", None)
        if rows:
            for r in rows:
                try:
                    op = int(getattr(r, "prop_id", getattr(r, "opcode_id", 0)) or 0)
                except Exception:
                    op = 0
                if op and op not in self._HEAL_OPS:
                    return True
        return False
