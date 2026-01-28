# WarCraftPets Logs

## Folder Structure
```
/home/yarizakurahime/engine/wow_claude/logs/
├── battle_logs/           # Raw battle_log_*.txt moved here
├── by_pet/                # One log per pet
├── by_skill/              # One log per skill (when a pet can cast it)
├── events/                # JSONL event logs
│   ├── by_pet/
│   └── by_skill/
├── reports/
│   └── log_traversal_summary.json
│   └── special_ability_audit.json
│   └── event_diff_report.json
├── battle_simulation_log_001.md
├── pet_stats_detailed_log_001.md
├── damage_formula_log_001.md
├── aura_system_log_001.md
├── healing_formula_log_001.md
├── state_machine_log_001.md
├── hit_accuracy_log_001.md
├── cooldown_tracking_log_001.md
├── weather_effects_log_001.md
└── race_passives_log_001.md
```

## Notes
- `battle_log_traversal.py` generates per-pet/per-skill logs and writes a summary report.
- `reports/log_traversal_summary.json` lists missing skills that are not assigned to any pet.
- Missing skills are force-mapped to a dummy pet for logging.
- `reports/special_ability_audit.json` lists abilities with non-damage opcodes (likely unsupported in main.py).
- `reports/event_diff_report.json` lists event-diff issues found in JSONL logs.
