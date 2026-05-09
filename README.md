# Daily Auto Poster — X & Instagram

毎日21:00 (JST) に Claude API でモチベーション系の投稿文を生成し、Pillowで画像化して X と Instagram に自動投稿するアプリ。GitHub Actions の cron で動くのでサーバー不要・無料。

## 仕組み

```
GitHub Actions (cron 21:00 JST)
   │
   ├─ prepare:  Claude API → 投稿文 → Pillowで画像生成
   │            posts/YYYY-MM-DD.png と posts/YYYY-MM-DD.json を保存
   │
   ├─ commit:   生成物を main にコミット & push
   │            （IGに渡す画像URLを raw.githubusercontent.com で配信するため）
   │
   └─ post:     X (tweepy v1.1+v2) と Instagram (Graph API) に投稿
```

## セットアップ

### 1. リポジトリを GitHub に push

このリポジトリをGitHubの**パブリックリポジトリ**として push してください（IGがGitHubの raw URLから画像を取得するため）。

### 2. 各種APIキーを取得

#### Anthropic (Claude)
- https://console.anthropic.com/ でAPIキーを発行

#### X (Twitter)
- https://developer.x.com/ でDeveloper登録
- 「User authentication settings」で OAuth1.0a を有効にし、permissions を **Read and Write** に設定（重要：Read-onlyだと投稿不可）
- 必要なキー4つ:
  - API Key
  - API Secret
  - Access Token
  - Access Token Secret

#### Instagram (Graph API)
これが一番ハードルが高いです。手順:

1. Instagram アカウントを **ビジネス or クリエイター** に切り替え
2. Facebookページを作成して Instagram と連携
3. https://developers.facebook.com/ でアプリを作成
4. アプリに「Instagram Graph API」を追加
5. https://developers.facebook.com/tools/explorer/ で **長期トークン** を取得
   - 必要な権限: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, `business_management`
6. `IG_USER_ID`（Instagram Business Account ID）を取得:
   ```
   GET https://graph.facebook.com/v21.0/me/accounts?access_token=XXX
   → page_id を取得
   GET https://graph.facebook.com/v21.0/{page_id}?fields=instagram_business_account&access_token=XXX
   → instagram_business_account.id が IG_USER_ID
   ```

> **注意**: 長期トークンも60日で切れます。本番運用するなら定期的に更新するか、トークン更新ジョブを追加してください。

### 3. GitHub Secrets に登録

リポジトリの **Settings → Secrets and variables → Actions → New repository secret** から以下を登録:

| Secret 名 | 値 |
|----------|----|
| `ANTHROPIC_API_KEY` | Claude のAPIキー |
| `X_API_KEY` | X の API Key |
| `X_API_SECRET` | X の API Secret |
| `X_ACCESS_TOKEN` | X の Access Token |
| `X_ACCESS_TOKEN_SECRET` | X の Access Token Secret |
| `IG_ACCESS_TOKEN` | Instagram の長期アクセストークン |
| `IG_USER_ID` | Instagram Business Account ID |

### 4. 動作確認

GitHub上で **Actions タブ → Daily Auto Post → Run workflow** から手動実行できます。

## ローカルでテストする

```bash
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # macOS/Linux

pip install -r requirements.txt
copy .env.example .env           # Windows
# cp .env.example .env           # macOS/Linux
# .env に各キーを記入
```

### 投稿せず生成内容だけ確認

```bash
# 投稿文と画像だけ生成（posts/ に保存される）
python -m src.main prepare

# 生成済みコンテンツを使ってドライラン（投稿はしない）
set DRY_RUN=true && python -m src.main post   # Windows
# DRY_RUN=true python -m src.main post        # macOS/Linux
```

### 各モジュール単体テスト

```bash
# Claude APIで投稿文だけ生成
python -m src.content_generator

# サンプル画像だけ生成（posts/local/sample.png）
python -m src.image_generator
```

## カスタマイズ

### テーマを変える
[src/content_generator.py](src/content_generator.py) の `SYSTEM_PROMPT` と `USER_PROMPT_TEMPLATE` を編集してください。

### 投稿時刻を変える
[.github/workflows/daily-post.yml](.github/workflows/daily-post.yml) の cron を変更:
- `0 12 * * *` = UTC 12:00 = JST 21:00
- `0 23 * * *` = UTC 23:00 = JST 翌 8:00（朝投稿）
- `0 3 * * *` = UTC 03:00 = JST 12:00（昼投稿）

### 画像のデザインを変える
[src/image_generator.py](src/image_generator.py) の `GRADIENTS` で背景色、`_fit_text` でフォントサイズを調整できます。

### Xだけ・IGだけにしたい
GitHub Actions の env で `POST_TO_X` か `POST_TO_INSTAGRAM` を `false` に。

## トラブルシューティング

| 症状 | 原因 |
|------|------|
| `日本語フォントが見つかりません` | Ubuntuなら `apt install fonts-noto-cjk`、Windowsならデフォルトで入っているはず |
| X で 403 Forbidden | アプリの permissions が Read のみ → Read and Write に変更後、Access Token を**再発行** |
| IG で `Media not ready` | 画像URLに公開アクセスできていない。GitHubがパブリックリポか確認 |
| IG で `OAuthException` | 長期トークン切れ（60日）。再取得が必要 |
| 投稿が同じ内容になる | Claude が同じ案を返している。`SYSTEM_PROMPT` でランダム性を促す指示を追加 |

## 構成ファイル

```
.
├── .github/workflows/daily-post.yml   # GitHub Actions cron
├── src/
│   ├── main.py                        # prepare / post / all
│   ├── content_generator.py           # Claude API
│   ├── image_generator.py             # Pillow
│   ├── x_poster.py                    # tweepy
│   └── instagram_poster.py            # Graph API
├── posts/                             # 生成された画像とJSON
├── requirements.txt
├── .env.example
└── README.md
```
