#!/bin/bash
# Gastown Endless Mode Monitor
# 用法: ./monitor_endless.sh

echo "=============================================="
echo "Gastown Endless Mode - Monitor"
echo "=============================================="
echo "Time: $(date)"
echo ""

# 检查进程
CLAUDE_PID=$(pgrep -f "endless_claude.py")
CODEX_PID=$(pgrep -f "endless_codex.py")

echo "=== Agent Status ==="
if [ -n "$CLAUDE_PID" ]; then
    echo "ClaudeCode: Running (PID: $CLAUDE_PID)"
else
    echo "ClaudeCode: NOT RUNNING"
fi

if [ -n "$CODEX_PID" ]; then
    echo "Codex: Running (PID: $CODEX_PID)"
else
    echo "Codex: NOT RUNNING"
fi

echo ""
echo "=== Latest Output ==="

echo ""
echo "--- ClaudeCode ---"
tail -15 /home/yarizakurahime/engine/wow_claude/logs/endless_claude.log 2>/dev/null | head -15

echo ""
echo "--- Codex ---"
tail -15 /home/yarizakurahime/engine/wow_claude/logs/endless_codex.log 2>/dev/null | head -15

echo ""
echo "=== Quick Stats ==="
if [ -f /home/yarizakurahime/engine/wow_claude/logs/codex_report_round.json ]; then
    echo "Codex Round Report:"
    cat /home/yarizakurahime/engine/wow_claude/logs/codex_report_round.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'  Round: {d.get(\"round\", \"?\")}')"
fi

echo ""
echo "=== Git Status ==="
cd /home/yarizakurahime/engine/wow_claude
git status --short 2>/dev/null | head -5

echo ""
echo "=============================================="
echo "Press Ctrl+C to exit"
echo "=============================================="
