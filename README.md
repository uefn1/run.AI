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

`gemma-4-31b-it` は無料枠で共有されているため、高需要時に `503 UNAVAILABLE` や `500 Internal error` が返ることがあります。
`gemma.py` は 429 と 5xx 系エラーを指数バックオフで自動リトライし（既定 6 回、最大 5→10→20→40→60 秒待機）、
それでも失敗した場合は `gemma-4-26b-a4b-it` に自動フォールバックします。
フォールバックを無効にしたい場合は `--fallback-model ""` を指定してください。

## CI

`.github/workflows/smoke-test.yml` は手動実行（workflow_dispatch）で `gemma-4-31b-it` への疎通確認を行います。Secret `GEMINI_API_KEY` の登録後に **Actions → Gemma 4 31B smoke test → Run workflow** から実行できます。

## AI開発ループ

`.github/workflows/ai-dev.yml` が次の流れを自動で繰り返します。

```
APIを呼び出す(dev.py が Gemma 4 31B に指示)
  → 生成物を files/ フォルダ内に書き出し、DEVLOG.md に記録してコミット
  → 次のプロセス(バグ修正・機能追加)を gh workflow run で起動
  → 現在のプロセスを終了
```

- 1回目: `prompt.txt` の仕様から新規開発
- 2回目以降: `prompt.txt` + `files/` の現在のコード + `DEVLOG.md` を参照してバグ発見・修正・機能追加
- 起動: **Actions → AI Game Dev Loop → Run workflow**(`max_iterations` で自動停止、既定10)
- 停止: 進行中の run を Cancel し、次の run を起動しない
- 開発内容を変えるには `prompt.txt` を編集してコミット
- 生成物は `files/` 以下のみに書き込まれる(パス検証済み)
