from engine.effects.registry import register_handler
from engine.effects.types import EffectResult


@register_handler(246)
class H_Prop246_CooldownModifierBySlot:
    """Set a per-slot cooldown modifier on the target pet.

    Ability-pack param schema:
      - Index (1..3): ability slot index
      - CooldownModification: integer modifier

    Observed usage:
      - Bend Time aura toggles this to 1 while active, then back to 0 when expiring.

    Engine integration:
      - AbilityExecutor applies ctx.cooldown_mods[(pet_id, slot_index)] when setting cooldowns.
    """

    PROP_ID = 246

    def apply(self, ctx, actor, target, effect_row, args) -> EffectResult:
        # This opcode exists in the ability-pack schema, but may not be present in
        # effect_properties_semantic.yml yet. Therefore, ParamParser keys can be
        # lowercase (index, cooldown_modification). Accept both forms.
        idx = int(args.get("Index") or args.get("index") or 0)
        mod = int(args.get("CooldownModification") or args.get("cooldown_modification") or 0)

        if idx <= 0:
            ctx.log.effect_result(effect_row, actor, target, code="NOOP", reason="BAD_INDEX")
            return EffectResult(executed=True)

        # Ensure storage exists.
        if not hasattr(ctx, "cooldown_mods") or ctx.cooldown_mods is None:
            ctx.cooldown_mods = {}

        key = (int(getattr(target, "id", 0)), int(idx))
        if mod == 0:
            ctx.cooldown_mods.pop(key, None)
            ctx.log.effect_result(effect_row, actor, target, code="OK", reason=f"CDMOD_CLEAR_SLOT_{idx}")
            return EffectResult(executed=True)

        ctx.cooldown_mods[key] = int(mod)
        ctx.log.effect_result(effect_row, actor, target, code="OK", reason=f"CDMOD_SET_SLOT_{idx}:{mod}")
        return EffectResult(executed=True)
