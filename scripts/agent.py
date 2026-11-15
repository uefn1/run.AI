#!/usr/bin/env python3
"""AI agent for the self-chaining GitHub Actions game-dev loop.

Iteration 1: read prompt.txt and implement the game from scratch.
Iteration 2+: read prompt.txt + DEVLOG.md + the previous commit, find and fix bugs.

Talks to any OpenAI-compatible chat endpoint (default: Google AI Studio's
gemma-4-26b-a4b-it via the Gemini API) using a JSON-in-text ReAct protocol,
stdlib only.
"""

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE = os.environ.get(
    "LLM_BASE", "https://generativelanguage.googleapis.com/v1beta/openai"
).rstrip("/")
API_KEY = os.environ.get("LLM_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "gemma-4-26b-a4b-it")
MAX_TURNS = int(os.environ.get("LLM_MAX_TURNS", "60"))
MAX_RESULT = int(os.environ.get("LLM_MAX_RESULT", "12000"))
ITERATION = int(os.environ.get("ITERATION", "1"))
REQUEST_INTERVAL = float(os.environ.get("LLM_REQUEST_INTERVAL", "2"))

SYSTEM_PROMPT = """あなたはリポジトリ内で自律的に作業するゲーム開発エージェントです。

# 実行プロトコル(厳守)
- 毎回の応答は、説明文を含めず JSON オブジェクト 1 個だけにする。
- 形式: {"tool": "<ツール名>", "args": { ... }}
- 1 回の応答で呼べるツールは 1 個。結果は次の user メッセージに {"tool_result": "..."} で返る。
- すべての作業が完了したら {"tool": "finish", "args": {"report": "作業報告(日本語)"}} で終了する。

# ツール一覧
- list_files: args {"path": "."}            … ファイル一覧を表示
- read_file: args {"path": "..."}           … ファイルを読む
- write_file: args {"path": "...", "content": "..."} … ファイルを新規作成/上書き
- edit_file: args {"path": "...", "old": "...", "new": "..."} … 完全一致置換(old は一意であること)
- run_command: args {"command": "..."}      … リポジトリのルートでシェルコマンドを実行
- finish: args {"report": "..."}

# ルール
- パスはすべてリポジトリルートからの相対パス。.git 以下は触らない。
- git push やネットワーク操作は禁止。コミットはシステム側が行う。
- コードを書いたら run_command で検証してから終わる(例: node --check game/game.js)。
- 小さく確実に: 一度に大量の変更をせず、動く状態を維持する。
"""


# ---------------------------------------------------------------- API layer

def http_json(method: str, url: str, payload=None):
    headers = {"Content-Type": "application/json", "User-Agent": "run.AI-agent/1.0"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    data = json.dumps(payload).encode() if payload is not None else None
    last_error = None
    for attempt in range(10):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:500]
            retry_after = e.headers.get("Retry-After") if e.headers else None
            if e.code == 429:
                wait = float(retry_after) if retry_after and retry_after.isdigit() else 10.0
                print(f"  rate limited, waiting {wait}s ...", flush=True)
                time.sleep(min(wait, 60))
                last_error = RuntimeError(f"429: {body}")
                continue
            if e.code == 401:
                sys.exit(
                    f"ERROR 401 from {url}: {body}\n"
                    "APIキーが無効です。シークレット GEMINI_API_KEY に\n"
                    "Google AI Studio (https://aistudio.google.com/apikey) の API キーを設定してください。"
                )
            if e.code >= 500:
                time.sleep(5 * (attempt + 1))
                last_error = RuntimeError(f"{e.code}: {body}")
                continue
            sys.exit(f"ERROR {e.code} from {url}: {body}")
        except urllib.error.URLError as e:
            time.sleep(5 * (attempt + 1))
            last_error = e
    sys.exit(f"ERROR: API retries exhausted: {last_error}")


def discover_model() -> str:
    if MODEL:
        return MODEL
    data = http_json("GET", f"{BASE}/models")
    ids = [m.get("id") for m in data.get("data", []) if m.get("id")]
    if not ids:
        sys.exit(f"ERROR: /v1/models returned no model ids: {str(data)[:300]}")
    print(f"discovered model: {ids[0]}", flush=True)
    return ids[0]


def chat(messages, model: str) -> str:
    time.sleep(REQUEST_INTERVAL)
    data = http_json(
        "POST",
        f"{BASE}/chat/completions",
        {"model": model, "messages": messages, "temperature": 0.2},
    )
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError):
        sys.exit(f"ERROR: unexpected API response: {str(data)[:500]}")


# ---------------------------------------------------------------- tool layer

def safe_path(p: str) -> Path:
    path = (REPO / p).resolve()
    if not path.is_relative_to(REPO):
        raise ValueError(f"path outside repository: {p}")
    if ".git" in path.relative_to(REPO).parts:
        raise ValueError(f"refusing to touch .git: {p}")
    return path


def tool_list_files(args):
    base = safe_path(args.get("path", "."))
    if base.is_file():
        base = base.parent
    out = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__")]
        rel = Path(root).relative_to(REPO)
        for name in sorted(files):
            out.append(str(rel / name) if str(rel) != "." else name)
        if len(out) > 500:
            break
    return "\n".join(sorted(out)) or "(empty)"


def tool_read_file(args):
    path = safe_path(args["path"])
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:MAX_RESULT]


def tool_write_file(args):
    path = safe_path(args["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args["content"], encoding="utf-8")
    return f"wrote {args['path']} ({len(args['content'])} bytes)"


def tool_edit_file(args):
    path = safe_path(args["path"])
    text = path.read_text(encoding="utf-8")
    old, new = args["old"], args["new"]
    count = text.count(old)
    if count == 0:
        return "ERROR: old string not found (read the file again and copy it exactly)"
    if count > 1:
        return f"ERROR: old string matches {count} places; include more surrounding text to make it unique"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return f"edited {args['path']}"


FORBIDDEN = ("git push", "sudo", "rm -rf /", "mkfs", "shutdown", "reboot", "gh workflow")


def tool_run_command(args):
    cmd = args["command"]
    if any(f in cmd for f in FORBIDDEN):
        return f"ERROR: forbidden command: {cmd}"
    try:
        proc = subprocess.run(
            ["bash", "-c", cmd], cwd=REPO, capture_output=True, text=True, timeout=180
        )
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out after 180s"
    out = (proc.stdout + ("\n[stderr]\n" + proc.stderr if proc.stderr else "")).strip()
    return f"exit code: {proc.returncode}\n{out[:MAX_RESULT]}"


TOOLS = {
    "list_files": tool_list_files,
    "read_file": tool_read_file,
    "write_file": tool_write_file,
    "edit_file": tool_edit_file,
    "run_command": tool_run_command,
}


def dispatch(tool, args):
    if tool == "finish":
        return None
    if tool not in TOOLS:
        return f"ERROR: unknown tool '{tool}'. Available: {', '.join(TOOLS)}, finish"
    try:
        return TOOLS[tool](args)
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"


def parse_action(text: str):
    text = re.sub(r"```(?:json)?", "", text).strip().strip("`")
    start = text.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
                    tool = obj.get("tool") or obj.get("name")
                    args = obj.get("args") or obj.get("arguments") or {}
                    if isinstance(tool, str) and isinstance(args, dict):
                        return tool, args
                    break
        start = text.find("{", start + 1)
    return None


# ---------------------------------------------------------------- task layer

def read_repo_file(name: str) -> str:
    path = REPO / name
    return path.read_text(encoding="utf-8") if path.exists() else "(ファイルが存在しません)"


def previous_development() -> str:
    parts = []
    log = subprocess.run(
        ["git", "log", "--oneline", "-5"], cwd=REPO, capture_output=True, text=True
    )
    parts.append("## 最近のコミット\n" + (log.stdout or "(なし)"))
    diff = subprocess.run(
        ["git", "show", "--stat", "HEAD"], cwd=REPO, capture_output=True, text=True
    )
    parts.append("## 直前のコミットの変更概要\n" + (diff.stdout or "(なし)"))
    return "\n\n".join(parts)


def build_task() -> str:
    spec = read_repo_file("prompt.txt")
    common = f"# ゲーム制作仕様 (prompt.txt)\n{spec}\n\n# 制約\n- ゲームのコードは game/ ディレクトリに置く(index.html, style.css, game.js など)。\n- ビルド不要・依存ゼロで、index.html をブラウザで開けば動く構成にする。\n"
    if ITERATION <= 1:
        return (
            common
            + "\n# あなたのタスク(イテレーション 1: 新規開発)\n"
            "1. prompt.txt の仕様を読み、ゲームを完全に実装する。\n"
            "2. run_command で `node --check game/game.js` を実行し、構文エラーがないことを確認する。\n"
            "3. DEVLOG.md を作成し、`## イテレーション 1` の見出しで実装内容・実装済み機能・既知の問題・次回確認ポイントを記録する。\n"
            "4. finish で報告する。\n"
        )
    devlog = read_repo_file("DEVLOG.md")
    prev = previous_development()
    return (
        common
        + f"\n# 前回までの開発内容 (DEVLOG.md)\n{devlog[:MAX_RESULT]}\n\n{prev[:MAX_RESULT]}\n\n"
        + "# あなたのタスク(イテレーション "
        + str(ITERATION)
        + ": バグ発見と修正)\n"
        "1. prompt.txt の仕様、DEVLOG.md、直前のコミット内容を参照する。\n"
        "2. game/ のコードを丁寧に読み、バグや仕様との不一致(ロジック誤り、境界ケース、イベント処理、状態管理、タイポ等)を探す。\n"
        "3. 見つけたバグを修正する。バグが見つからない場合は、仕様をより正確に満たす改善やコード品質の修正を行う。\n"
        "4. run_command で `node --check game/game.js` を実行し、検証する。\n"
        "5. DEVLOG.md に `## イテレーション "
        + str(ITERATION)
        + "` の見出しで、発見したバグ・修正内容・残る懸念を追記する。\n"
        "6. finish で報告する。\n"
    )


# ---------------------------------------------------------------- main loop

def main() -> int:
    if not API_KEY:
        sys.exit(
            "ERROR: LLM_API_KEY is empty.\n"
            "リポジトリの Settings > Secrets and variables > Actions で\n"
            "シークレット GEMINI_API_KEY を設定してから再実行してください。"
        )
    model = discover_model()
    task = build_task()
    print(f"iteration {ITERATION} | base={BASE} | model={model}", flush=True)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    for turn in range(1, MAX_TURNS + 1):
        content = chat(messages, model)
        print(f"--- turn {turn} ---\n{content[:600]}", flush=True)
        messages.append({"role": "assistant", "content": content})

        action = parse_action(content)
        if action is None:
            messages.append(
                {
                    "role": "user",
                    "content": '応答を解釈できませんでした。説明文を書かず、JSON オブジェクト 1 個だけを返してください: {"tool": "...", "args": {...}}',
                }
            )
            continue

        tool, args = action
        if tool == "finish":
            print(f"\n=== agent report ===\n{args.get('report', '(no report)')}")
            return 0

        result = dispatch(tool, args)
        print(f"    -> {str(result)[:200]}", flush=True)
        messages.append(
            {"role": "user", "content": json.dumps({"tool_result": str(result)[:MAX_RESULT]}, ensure_ascii=False)}
        )

    print("ERROR: max turns reached without finish", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
