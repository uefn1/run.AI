# run.AI

Google AI Studio（Gemini API）経由で **Gemma 4 31B**（`gemma-4-31b-it`）を使用するためのリポジトリです。

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## APIキー

- **ローカル**: `.env.example` を `.env` にコピーし、[Google AI Studio](https://aistudio.google.com/) で発行したAPIキーを `GEMINI_API_KEY` に設定して `source .env` してください（`.env` はコミットされません）。
- **GitHub Actions**: リポジトリの **Settings → Secrets and variables → Actions** に `GEMINI_API_KEY` という名前でシークレットを登録してください。ワークフローが自動的に読み込みます。

## 使い方

```bash
python gemma.py "こんにちは！自己紹介をしてください。"

# システム指示を付ける
python gemma.py "茶道の目的は？" --system "あなたは京都の茶道の師匠です。3文以内で答えてください。"

# 思考プロセスを有効化（高難度の推論タスク向け）
python gemma.py "この数学の証明を検証して" --thinking high

# モデルやリトライを指定
python gemma.py "こんにちは" --model gemma-4-26b-a4b-it --max-attempts 3 --fallback-model ""
```

### 高負荷時(429/503)の挙動

`gemma-4-31b-it` は無料枠で共有されているため、高需要時に `503 UNAVAILABLE` が返ることがあります。
`gemma.py` は指数バックオフで自動リトライし（既定 6 回、最大 5→10→20→40→60 秒待機）、
それでも失敗した場合は `gemma-4-26b-a4b-it` に自動フォールバックします。
フォールバックを無効にしたい場合は `--fallback-model ""` を指定してください。

## CI

`.github/workflows/smoke-test.yml` は手動実行（workflow_dispatch）で `gemma-4-31b-it` への疎通確認を行います。Secret `GEMINI_API_KEY` の登録後に **Actions → Gemma 4 31B smoke test → Run workflow** から実行できます。
