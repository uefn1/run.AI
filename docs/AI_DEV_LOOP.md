# AI開発ループの使い方

GitHub Actions 上で UncloseAI が自律的にゲーム開発を行う自己連鎖型ワークフローです。

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
| Secret | `UNCLOSE_API_KEY` | `permacomputer` | UncloseAI の API キー |
| Variable | `UNCLOSE_BASE` | `https://hermes.ai.unturf.com/v1` | OpenAI 互換 API のベース URL |
| Variable | `UNCLOSE_MODEL` | (自動検出) | モデル ID。空なら `/v1/models` から自動検出 |

## 重要な注意

検証時点で、uncloseai.com の公開ベータはクローズしており、API キー登録も停止しています
(`{"type":"public_beta_closed"}` エラー)。このワークフローを動かすには:

- UncloseAI の API キーを入手できるのを待つ、または
- `vars.UNCLOSE_BASE` を自分で立てた llama-server / vLLM など OpenAI 互換エンドポイントに向ける

どちらの場合も `scripts/agent.py` は無変更で動作します(標準ライブラリのみ使用)。

## 動作要件

- ランナーに `python3`(標準搭載)と `node`(構文チェック用、標準搭載)のみで動作します。
- 依存パッケージのインストールは不要です。
