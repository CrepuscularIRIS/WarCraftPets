from typing import Dict, Optional, Protocol, Any

class IEffectHandler(Protocol):
    PROP_ID: int
    def apply(self, ctx: Any, actor: Any, target: Any, effect_row: Any, args: dict) -> Any: ...

_HANDLERS: Dict[int, IEffectHandler] = {}

def register_handler(prop_id: int):
    def deco(cls):
        _HANDLERS[prop_id] = cls()
        return cls
    return deco

def get_handler(prop_id: int) -> Optional[IEffectHandler]:
    return _HANDLERS.get(prop_id)
