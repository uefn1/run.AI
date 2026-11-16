"""Self-chaining AI game dev: call the API, write files into files/, log to DEVLOG.md.

Iteration 1 (files/ is empty): implement the game from prompt.txt.
Iteration 2+ (files/ has content): find bugs and add features.
The workflow commits the result, launches the next process, and exits.
"""

import json
import os
import sys
from pathlib import Path

from gemma import generate

REPO = Path(__file__).resolve().parent
FILES_DIR = REPO / "files"
DEVLOG = REPO / "DEVLOG.md"
SPEC = REPO / "prompt.txt"
ITERATION = int(os.environ.get("ITERATION", "1"))
MAX_FILE_CHARS = 20000
MAX_TOTAL_CHARS = 60000
MAX_DEVLOG_CHARS = 8000

SYSTEM = (
    "あなたはブラウザゲームの開発者です。指示に従い、単一の JSON オブジェクトだけを"
    "出力してください。説明文・コードフェンス・JSON 以外のテキストは一切出力しないでください。"
)


def read_spec() -> str:
    if not SPEC.exists():
        sys.exit("ERROR: prompt.txt が見つかりません。")
    return SPEC.read_text(encoding="utf-8").strip()


def collect_files() -> dict[str, str]:
    if not FILES_DIR.is_dir():
        return {}
    out = {}
    total = 0
    for path in sorted(FILES_DIR.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > MAX_FILE_CHARS:
            text = text[:MAX_FILE_CHARS] + "\n... (省略) ..."
        total += len(text)
        if total > MAX_TOTAL_CHARS:
            out[rel] = "... (文字数制限により省略) ..."
            continue
        out[rel] = text
    return out


def build_prompt(spec: str, current: dict[str, str]) -> str:
    if not current:
        return (
            "以下の仕様に従って、ブラウザで動作するゲームを開発してください。\n\n"
            f"# 仕様\n{spec}\n\n"
            "# 要件\n"
            "- すべてのファイルは files/ フォルダ内に作成する(例: files/index.html, files/style.css, files/game.js)\n"
            "- 依存ライブラリなし・ビルド不要で、files/index.html を開けば遊べること\n"
            "- 完成度の高い実装にする\n\n"
            "# 出力形式(この形式の JSON オブジェクト 1 個だけを出力)\n"
            '{"summary": "実装内容の要約(日本語)", "files": {"files/index.html": "<ファイルの全文>", ...}}'
        )
    files_text = "\n\n".join(
        f"## {name}\n```{content}```" for name, content in current.items()
    )
    devlog = ""
    if DEVLOG.exists():
        devlog_text = DEVLOG.read_text(encoding="utf-8")
        devlog = "\n\n# 開発ログ(参考)\n" + devlog_text[-MAX_DEVLOG_CHARS:]
    return (
        "以下の仕様と現在のコードを確認し、バグを発見して修正し、仕様に対する不足があれば機能を追加してください。\n\n"
        f"# 仕様\n{spec}\n\n"
        f"# 現在の files/ の内容\n{files_text}{devlog}\n\n"
        "# ルール\n"
        "- バグ修正と機能追加の両方を行う。必ず具体的な改善を少なくとも 1 つ行うこと。\n"
        "- 変更が必要なファイルのみ、更新後の全文を出力する。\n"
        "- 新規ファイルも files/ の下に作成する。\n\n"
        "# 出力形式(この形式の JSON オブジェクト 1 個だけを出力)\n"
        '{"summary": "発見したバグと修正・追加内容(日本語)", "files": {"files/xxx.html": "<更新後の全文>", ...}}'
    )


def extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
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
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return None


def target_path(name: str) -> Path:
    name = str(name).strip().replace("\\", "/")
    while name.startswith("./"):
        name = name[2:]
    name = name.lstrip("/")
    if not name.startswith("files/"):
        name = f"files/{name}"
    path = (REPO / name).resolve()
    if not path.is_relative_to(FILES_DIR) or path == FILES_DIR.resolve():
        raise ValueError(f"invalid file path: {name}")
    return path


def write_files(files: dict) -> list[str]:
    written = []
    for name, content in files.items():
        path = target_path(str(name))
        if not isinstance(content, str):
            raise ValueError(f"file content must be a string: {name}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path.relative_to(REPO).as_posix())
    return written


def append_devlog(mode: str, summary: str, written: list[str]) -> None:
    entry = (
        f"\n## イテレーション {ITERATION} ({mode})\n"
        f"- {summary.strip() or '(要約なし)'}\n"
        f"- 更新ファイル: {', '.join(written)}\n"
    )
    with DEVLOG.open("a", encoding="utf-8") as f:
        f.write(entry)


def main() -> None:
    spec = read_spec()
    current = collect_files()
    mode = "初期開発" if not current else "バグ修正・機能追加"
    print(f"iteration {ITERATION} | mode: {mode} | 既存ファイル: {len(current)}", flush=True)

    text = generate(
        build_prompt(spec, current),
        system_instruction=SYSTEM,
        thinking_level=os.environ.get("DEV_THINKING", "minimal"),
    )
    data = extract_json(text)
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict) or not data["files"]:
        sys.exit(f"ERROR: モデルの応答から files を取得できませんでした: {text[:300]}")

    written = write_files(data["files"])
    summary = str(data.get("summary", ""))
    append_devlog(mode, summary, written)
    print(f"written: {', '.join(written)}")
    print(f"summary: {summary}")


if __name__ == "__main__":
    main()
