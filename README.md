# WoW Pet Battle Engine Skeleton (Prop24 example)

## Run
```bash
python -m pip install -U pytest
pytest -q
```


## Opcode semantics pack

- `effect_properties_semantic.yml` is the human-oriented semantic catalog.
- `effect_properties_semantic.json` is the runtime-loaded semantic pack (no YAML dependency).

Runtime:
- `engine/effects/semantic_registry.py` loads the JSON pack and normalizes handler args.
- `engine/effects/dispatcher.py` distinguishes unknown opcodes from known-but-unimplemented opcodes.

Tools:
- `python tools/compile_semantics.py` (requires pyyaml) regenerates JSON from YAML.
- `python tools/gen_missing_handlers.py --out engine/effects/handlers_generated` generates stub handlers for missing opcodes.


## Ability pack (JSON)

This repository can also load periodic-aura scripts and aura meta directly from the
generated **petbattle ability pack** (strict JSON).

- Runtime API: `ScriptDB.from_ability_pack_json("data/petbattle_ability_pack.v1.release.json")`
- The `*.debug.jsonc` variant is for humans (contains comments) and is not loaded by default.
