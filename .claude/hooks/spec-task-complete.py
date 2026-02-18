#!/usr/bin/env python3
"""
spec-task-complete.py
======================
spec-workflow MCP タスク完了フック

テスト全通過時に、アクティブな spec-workflow タスクの完了を通知します。
Claude Code の PostToolUse フックとして使用。

環境変数:
  ACTIVE_SPEC_ID   - 現在実装中のスペック ID
  ACTIVE_TASK_ID   - 現在実装中のタスク ID

使い方 (.claude/settings.json):
  {
    "hooks": {
      "PostToolUse": [
        {
          "matcher": "Bash",
          "hooks": [{"type": "command", "command": "python3 .claude/hooks/spec-task-complete.py"}]
        }
      ]
    }
  }
"""

import json
import os
import subprocess
import sys
from datetime import datetime


def run_tests() -> tuple[bool, str]:
    """テストを実行して結果を返す"""
    result = subprocess.run(
        ["uv", "run", "pytest", "--tb=short", "-q"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.returncode == 0, result.stdout + result.stderr


def log_completion(spec_id: str, task_id: str, test_output: str) -> None:
    """実装ログを記録"""
    log_dir = ".spec-workflow/logs"
    os.makedirs(log_dir, exist_ok=True)

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "spec_id": spec_id,
        "task_id": task_id,
        "status": "completed",
        "test_output_summary": test_output[:500],
    }

    log_file = os.path.join(log_dir, "task-completions.jsonl")
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def main():
    spec_id = os.environ.get("ACTIVE_SPEC_ID")
    task_id = os.environ.get("ACTIVE_TASK_ID")

    if not spec_id or not task_id:
        # スペックタスクが設定されていない場合は何もしない
        return

    # テスト実行
    try:
        all_passed, output = run_tests()
    except subprocess.TimeoutExpired:
        print("⚠️  テスト実行タイムアウト", file=sys.stderr)
        return
    except FileNotFoundError:
        # pytest が見つからない場合はスキップ
        return

    if all_passed:
        print("\n✅ 全テスト通過!")
        print(f"   Spec: {spec_id} / Task: {task_id}")
        print("\n📋 次のアクション:")
        print(
            "   spec-workflow ダッシュボード(http://localhost:5000)でタスクを完了マークしてください"
        )
        print(
            f"   または Claude に 'タスク {task_id} を完了マークして' と伝えてください\n"
        )

        # ログ記録
        log_completion(spec_id, task_id, output)
    else:
        # テスト失敗時は何もしない（通常のTDDフローに任せる）
        pass


if __name__ == "__main__":
    main()
