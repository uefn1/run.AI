"""Self-chaining AI game dev: call the API, write files into files/, verify behavior.

Iteration 1 (files/ is empty): implement the game from prompt.txt.
Iteration 2+ (files/ has content): find bugs and add features, guided by the
previous browser test result.

The model also writes a Playwright test script (tests/test_game.py) that
operates the game in a real browser and asserts it behaves as specified.
The workflow runs that test, records the result, commits, launches the next
process, and exits.

TPM is only 16K: prompts are capped hard, and 429/5xx are retried forever
with a fixed 10s interval (see gemma.generate).
"""

import json
import os
import sys
import time
from pathlib import Path

from gemma import generate

REPO = Path(__file__).resolve().parent
FILES_DIR = REPO / "files"
TESTS_DIR = REPO / "tests"
DEVLOG = REPO / "DEVLOG.md"
SPEC = REPO / "prompt.txt"
ITERATION = int(os.environ.get("ITERATION", "1"))

MAX_FILE_CHARS = 12000
MAX_TOTAL_CHARS = 30000
MAX_DEVLOG_CHARS = 4000
MAX_TEST_CHARS = 8000
MAX_RESULT_CHARS = 4000
MAX_RESPONSE_ATTEMPTS = 3  # re-asks when the model returns unparseable output

SYSTEM = (
    "あなたはブラウザゲームの開発者です。指示に従い、単一の JSON オブジェクトだけを"
    "出力してください。説明文・コードフェンス・JSON 以外のテキストは一切出力しないでください。"
)

DEFAULT_TEST = '''from pathlib import Path

from playwright.sync_api import sync_playwright

GAME = (Path(__file__).resolve().parents[1] / "files" / "index.html").as_uri()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    problems = []
    page.on("console", lambda m: problems.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
    page.goto(GAME)
    page.wait_for_timeout(1500)
    assert page.content(), "page is empty"
    assert not problems, "errors: " + "\\n".join(problems)
    print("smoke OK")
    browser.close()
'''

TEST_RULES = '''- "test" キーには、ゲームが仕様どおりに「動作するか」を実際に操作して確認する Python (Playwright) テストスクリプトの全文を入れる。
  - from playwright.sync_api import sync_playwright を使用し、スクリプト単体で実行可能にする(依存は playwright のみ)
  - files/index.html を file:// URL で開く: (Path(__file__).resolve().parents[1] / "files" / "index.html").as_uri()
  - エラーが出ないことの確認に留まらず、実際にクリック・キーボード操作を行い、画面の状態(盤面・スコア・メッセージ・ターン表示など)を assert で検証する
  - console error と pageerror を検知したら失敗扱いにする
  - テストは確実に通ることを重視し、実装と整合する操作・セレクタを使う
'''


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


def read_test() -> str:
    path = TESTS_DIR / "test_game.py"
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:MAX_TEST_CHARS]


def read_last_result() -> str:
    path = TESTS_DIR / "last_result.txt"
    if not path.exists():
        return "(まだテストを実行していません)"
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    return text[:MAX_RESULT_CHARS] if text else "(出力なし)"


def build_prompt(spec: str, current: dict[str, str]) -> str:
    if not current:
        return (
            "以下の仕様に従って、ブラウザで動作するゲームを開発してください。\n\n"
            f"# 仕様\n{spec}\n\n"
            "# 要件\n"
            "- すべてのファイルは files/ フォルダ内に作成する(例: files/index.html, files/style.css, files/game.js)\n"
            "- 依存ライブラリなし・ビルド不要で、files/index.html を開けば遊べること\n"
            "- 完成度の高い実装にする。ただしコードは簡潔に保ち、不必要に長くしない(応答サイズの制約が厳しいため)\n\n"
            "# テスト\n" + TEST_RULES +
            "\n# 出力形式(この形式の JSON オブジェクト 1 個だけを、閉じられて完結した状態で出力)\n"
            '{"summary": "実装内容の要約(日本語)", '
            '"files": {"files/index.html": "<ファイルの全文>", ...}, '
            '"test": "<テストスクリプトの全文>"}'
        )
    files_text = "\n\n".join(
        f"## {name}\n```{content}```" for name, content in current.items()
    )
    devlog = ""
    if DEVLOG.exists():
        devlog_text = DEVLOG.read_text(encoding="utf-8")
        devlog = "\n\n# 開発ログ(参考)\n" + devlog_text[-MAX_DEVLOG_CHARS:]
    test_text = read_test()
    test_section = f"\n\n# 現在のテストスクリプト (tests/test_game.py)\n```{test_text}```" if test_text else ""
    return (
        "以下を確認し、前回のテスト結果を踏まえてバグを修正し、仕様に対する不足があれば機能を追加してください。\n\n"
        f"# 仕様\n{spec}\n\n"
        f"# 前回のブラウザテスト結果(失敗している場合は最優先で修正)\n{read_last_result()}\n\n"
        f"# 現在の files/ の内容\n{files_text}{test_section}{devlog}\n\n"
        "# ルール\n"
        "- 前回のテストが失敗していたら、その原因を最優先で修正する。\n"
        "- バグ修正と機能追加の両方を行う。必ず具体的な改善を少なくとも 1 つ行うこと。\n"
        "- テストも実装の変更に合わせて更新する(テスト自体のバグも修正してよい)。\n"
        "- 変更が必要なファイルのみ、更新後の全文を出力する。新規ファイルも files/ の下に作成する。\n"
        "- コードは簡潔に保ち、不必要に長くしない(応答サイズの制約が厳しいため)。\n\n"
        "# テスト\n" + TEST_RULES +
        "\n# 出力形式(この形式の JSON オブジェクト 1 個だけを、閉じられて完結した状態で出力)\n"
        '{"summary": "発見したバグと修正・追加内容(日本語)", '
        '"files": {"files/xxx.html": "<更新後の全文>", ...}, '
        '"test": "<更新後のテストスクリプトの全文>"}'
    )


def _scan_json(text: str):
    """Find the first balanced {...} in text and json.loads it, else None."""
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


def extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
    data = _scan_json(text)
    if data is None:
        # Some models emit full-width/typographic quotes as JSON delimiters.
        fixed = text.translate(
            str.maketrans({"\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"'})
        )
        if fixed != text:
            data = _scan_json(fixed)
    return data


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
        path = target_path(name)
        if not isinstance(content, str):
            raise ValueError(f"file content must be a string: {name}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path.relative_to(REPO).as_posix())
    return written


def write_test(test: str) -> str | None:
    if not isinstance(test, str) or not test.strip():
        return None
    TESTS_DIR.mkdir(parents=True, exist_ok=True)
    (TESTS_DIR / "test_game.py").write_text(test, encoding="utf-8")
    return "tests/test_game.py"


def ensure_test_exists() -> None:
    if not (TESTS_DIR / "test_game.py").exists():
        TESTS_DIR.mkdir(parents=True, exist_ok=True)
        (TESTS_DIR / "test_game.py").write_text(DEFAULT_TEST, encoding="utf-8")


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

    prompt = build_prompt(spec, current)
    data = None
    text = ""
    for attempt in range(1, MAX_RESPONSE_ATTEMPTS + 1):
        text = generate(
            prompt,
            system_instruction=SYSTEM,
            thinking_level=os.environ.get("DEV_THINKING", "minimal"),
        )
        data = extract_json(text)
        if isinstance(data, dict) and isinstance(data.get("files"), dict) and data["files"]:
            break
        print(
            f"WARNING: モデルの応答から files を取得できませんでした "
            f"(attempt {attempt}/{MAX_RESPONSE_ATTEMPTS}): {text[:200]}",
            file=sys.stderr,
        )
        data = None
        if attempt < MAX_RESPONSE_ATTEMPTS:
            time.sleep(10)
    if data is None:
        sys.exit(f"ERROR: モデルの応答から files を取得できませんでした: {text[:300]}")

    written = write_files(data["files"])
    test_file = write_test(data.get("test", ""))
    if test_file:
        written.append(test_file)
    else:
        ensure_test_exists()

    summary = str(data.get("summary", ""))
    append_devlog(mode, summary, written)
    print(f"written: {', '.join(written)}")
    print(f"summary: {summary}")


if __name__ == "__main__":
    main()
