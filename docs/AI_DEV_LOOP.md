# AI開発ループの使い方

GitHub Actions 上で Google AI Studio の **Gemma 4 26B**(`gemma-4-26b-a4b-it`)が自律的にゲーム開発を行う自己連鎖型ワークフローです。

## 仕組み

```
手動起動 (Actions → AI Game Dev Loop → Run workflow)
   │
   ▼
[イテレーション 1] prompt.txt を読んで新規開発
   → コミット & push
   → 次のプロセスを起動 (gh workflow run) → 現在のプロセス終了
   │
   ▼
[イテレーション 2..N] prompt.txt + DEVLOG.md + 直前のコミットを参照
   → バグを発見して修正
   → コミット & push
   → 次のプロセスを起動 → 現在のプロセス終了
   │
   ▼
[max_iterations 到達] ループ終了
```

- 各プロセスは `concurrency` グループで直列化されるため、同時に走りません。
- 開発内容は `DEVLOG.md` に蓄積され、次回プロセスの文脈として使われます。
- ループは `main` ブランチに直接コミットします。

## 開発の指示を変える

`prompt.txt` を編集してコミットしてください。次回起動時から新しい仕様で動作します。

## 事前準備(必須)

1. [Google AI Studio](https://aistudio.google.com/apikey) で API キーを発行する
2. リポジトリの **Settings → Secrets and variables → Actions → Secrets** に
   `GEMINI_API_KEY` という名前で登録する

キーが未設定の場合、ワークフローは最初のステップで明確なエラーメッセージを出して停止します(次のプロセスは起動されません)。

## 起動方法

1. GitHub の **Actions** タブ → **AI Game Dev Loop**
2. **Run workflow** → 必要なら `iteration` / `max_iterations` を変更
3. **Run workflow** を実行

## 停止方法

- 何もしなければ `max_iterations`(既定 10)で自動停止します。
- 途中で止めるには、進行中の run を **Cancel workflow** し、次の run を再起動しないでください。
- 再開したいときは `iteration` に続きの番号を入れて手動起動します。

## 設定(リポジトリの Settings → Secrets and variables → Actions)

| 種別 | 名前 | 既定値 | 説明 |
| --- | --- | --- | --- |
| Secret | `GEMINI_API_KEY` | (必須) | Google AI Studio の API キー |
| Variable | `LLM_BASE` | `https://generativelanguage.googleapis.com/v1beta/openai` | OpenAI 互換 API のベース URL |
| Variable | `LLM_MODEL` | `gemma-4-26b-a4b-it` | モデル ID |

## モデルやエンドポイントの変更

`vars.LLM_MODEL` と `vars.LLM_BASE` を設定すれば、他のモデル・エンドポイントに差し替えできます。
`scripts/agent.py` は OpenAI 互換の chat/completions に標準ライブラリのみで接続するため、
Gemini API だけでなくローカル llama-server / vLLM / OpenRouter などでも無変更で動作します。

- Gemma 4 31B: `LLM_MODEL` を `gemma-4-31b-it` に変更
- OpenRouter 経由: `LLM_BASE` を `https://openrouter.ai/api/v1`、`LLM_MODEL` を `google/gemma-4-26b-a4b-it:free` に変更(キーは `GEMINI_API_KEY` の代わりに OpenRouter のキーを登録)

## 動作要件

- ランナーに `python3`(標準搭載)と `node`(構文チェック用、標準搭載)のみで動作します。
- 依存パッケージのインストールは不要です。
- Gemma 4 は無料枠で利用できますが、レート制限があります(エージェントは 429 を Retry-After に従って待機してリトライします)。
