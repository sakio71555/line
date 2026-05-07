# LINE Transport Matching

LINEグループ投稿を案件データとして保存し、LIFFアプリで案件確認・条件登録・個別通知を行う運送案件マッチングシステムです。

## Phase 1で実装済みの内容

- FastAPIによるLINE Webhook受信API
- LINE Webhook署名検証
- LINEグループ、またはルームに投稿されたテキストメッセージの受信
- `source_group_id`, `source_user_id`, `source_message_id`, `raw_text` のSupabase保存
- `.env.example`
- Supabase用SQL

## Phase 2で実装済みの内容

- `jobs.raw_text` をOpenAIで案件情報へ構造化
- 厳格なJSON Schema形式でLLM出力をパース
- 不明項目を `null` と `missing_fields` に保存
- `confidence`, `review_required`, `analysis_status` による手動確認前提の状態管理
- 既存jobsの未解析レコードを1件解析するCLI
- 任意の `raw_text` を保存せず解析確認するCLI

## Phase 3で実装済みの内容

- React / Vite / TypeScript のLIFF対応フロントエンド
- LIFF初期化とLINEプロフィール取得
- LINEアプリ外ブラウザでの開発確認継続
- Supabase Publishable Keyによる公開案件一覧取得
- 出発地、到着地、車種、ステータス、確認待ちの絞り込み
- スマホ前提のカードUI
- 管理者向け簡易一覧タブ

## Phase 3.5で実装済みの内容

- 管理者向け案件一覧の強化
- 管理者用FastAPI更新API
- 案件編集フォーム
- 確認完了処理
- 非公開処理
- `analysis_status = 'verified'` の状態追加

## Phase 2.5〜3.7で実装済みの内容

- LINEイベント原本を `line_messages` に保存
- ルールベースの `message_type` 分類
- 投稿種別に応じた `jobs`, `vehicle_availabilities`, `job_status_updates` への分岐保存
- 終了・完了報告を自動反映せず、管理者確認候補として保存
- 管理者によるステータス適用と `job_status_history` への履歴保存
- LIFF内の案件投稿フォーム
- LIFF内の空車登録フォーム
- canonical status: `needs_review`, `open`, `negotiating`, `assigned`, `in_progress`, `completed`, `cancelled`, `hidden`

## 投稿者・連絡先管理で実装済みの内容

- LINE投稿者を `line_users` にupsert
- Messaging APIプロフィール取得による `display_name` / `picture_url` 補完
- 案件投稿者、連絡先、連絡先未設定フラグの保存
- 終了報告者と案件投稿者の本人判定
- 管理画面で投稿者・会社名・担当者・電話番号・連絡方法を表示

## LINE個別チャットのリッチメニュー

推奨運用では、個別チャットに常設リッチメニューを設定し、ユーザーはそこからLIFFを開きます。グループは案件投稿、完了報告、通知の場として使い、操作メニューは個別チャット側に寄せます。

リッチメニューはLINE Messaging APIで作成します。画像はあらかじめ `2500 x 1686` px のPNGまたはJPEGを用意し、標準では `assets/line-rich-menu.png` に配置します。

6分割の割り当て:

```text
1. 案件を投稿   -> https://liff.line.me/{LIFF_ID}?tab=post
2. 空車を登録   -> https://liff.line.me/{LIFF_ID}?tab=vehicle
3. 案件一覧     -> https://liff.line.me/{LIFF_ID}?tab=list
4. 管理画面     -> https://liff.line.me/{LIFF_ID}?tab=admin
5. 使い方       -> message action: 使い方
6. 企業検索     -> https://liff.line.me/{LIFF_ID}?tab=companies
```

API送信せずにJSONだけ確認する場合:

```bash
cd /Users/sakio/Documents/New\ project
python3 scripts/create_line_rich_menu.py --dry-run
```

`--dry-run` の出力では、`.env` の値を表示しないためLIFF URLをマスクします。

実際に作成し、画像をアップロードし、デフォルトリッチメニューに設定する場合:

```bash
cd /Users/sakio/Documents/New\ project
python3 scripts/create_line_rich_menu.py
```

このスクリプトは以下を順に実行します。

```text
POST https://api.line.me/v2/bot/richmenu
POST https://api-data.line.me/v2/bot/richmenu/{richMenuId}/content
POST https://api.line.me/v2/bot/user/all/richmenu/{richMenuId}
```

アクセストークンはバックエンド側の `.env` から読み込みますが、ターミナルには表示しません。

## LINEグループ内メニュー導線

LINEグループ画面では、個別トークのような常時固定のリッチメニューは表示できません。通常操作は個別チャットのリッチメニューを使い、グループの「メニュー」投稿は補助機能として扱います。グループにFlexメニューを直接返信すると参加者全員に通知されるため、グループではBotにメニューキーワードを投稿した送信者本人へ、個別チャットでLIFFへのボタン付きメッセージをPushします。

個別チャットで同じキーワードを送った場合は、そのチャット内でFlexメニューを返信します。送信者がBotを友だち追加していない場合、個別Pushに失敗することがあります。その場合もWebhook処理は失敗扱いにせず、Botを友だち追加してから個別チャットでメニューを開く運用にしてください。

対応キーワード:

```text
メニュー
案件投稿
空車登録
案件一覧
フォーム
企業検索
```

これらの投稿は `line_messages` に `message_type = 'menu_request'` として保存されます。`jobs`, `vehicle_availabilities`, `job_status_updates` は作成しません。グループ起点の場合は `line_liff_sessions` に `source_group_id` を持つ `session_id` を作成し、個別チャットへ送るLIFF URLへ付与します。

Botが送るボタンは以下のLIFF URLを開きます。グループ起点では末尾に `session_id` が付きます。

```text
案件投稿フォーム: https://liff.line.me/{LIFF_ID}?tab=post
空車登録フォーム: https://liff.line.me/{LIFF_ID}?tab=vehicle
案件一覧: https://liff.line.me/{LIFF_ID}?tab=list
管理画面: https://liff.line.me/{LIFF_ID}?tab=admin
企業検索: https://liff.line.me/{LIFF_ID}?tab=companies
```

バックエンド側では `LIFF_BASE_URL` が設定されていればそれを優先し、未設定の場合は `LIFF_ID` から `https://liff.line.me/{LIFF_ID}` を生成します。個別トークではLINE公式アカウントのリッチメニューも使えます。

## ディレクトリ構成

```text
.
├── apps/
│   ├── api/
│   │   ├── app/
│   │   │   ├── core/
│   │   │   ├── routers/
│   │   │   ├── schemas/
│   │   │   └── services/
│   │   └── requirements.txt
│   └── web/
│       ├── src/
│       │   ├── components/
│       │   ├── hooks/
│       │   ├── lib/
│       │   └── pages/
│       └── package.json
├── scripts/
│   ├── create_line_rich_menu.py
│   └── import_line_history.py
├── supabase/
│   └── migrations/
│       ├── 001_phase1_jobs.sql
│       ├── 002_phase2_job_analysis.sql
│       ├── 003_phase3_jobs_public_read.sql
│       ├── 004_phase35_admin_update.sql
│       ├── 005_phase25_line_classification_form_status.sql
│       ├── 006_line_users_contact_owner.sql
│       ├── 007_liff_sessions_and_line_notify.sql
│       └── 008_line_history_import.sql
├── .env.example
└── README.md
```

## Supabaseテーブル作成

Supabase SQL Editorで以下のSQLを実行してください。

```text
supabase/migrations/001_phase1_jobs.sql
supabase/migrations/002_phase2_job_analysis.sql
supabase/migrations/003_phase3_jobs_public_read.sql
supabase/migrations/004_phase35_admin_update.sql
supabase/migrations/005_phase25_line_classification_form_status.sql
supabase/migrations/006_line_users_contact_owner.sql
supabase/migrations/007_liff_sessions_and_line_notify.sql
supabase/migrations/008_line_history_import.sql
```

Phase 1ではFastAPIバックエンドが `SUPABASE_SECRET_KEY` を使って `jobs` テーブルへ保存します。既存環境との互換性のため、`SUPABASE_SERVICE_ROLE_KEY` もバックエンド専用キーとして読み込めるようにしています。
Phase 2では `notes`, `analysis_status`, `analysis_error`, `analysis_model`, `analysis_completed_at`, `review_required` を追加します。
Phase 3ではReact/LIFFアプリから公開案件を読めるように、`anon` / `authenticated` に `select` 権限とRLS policyを追加します。
Phase 3.5では管理者確認済みを表す `analysis_status = 'verified'` を許可します。
Phase 2.5〜3.7では原本保存・分類分岐用テーブルを追加し、既存の日本語statusを英語のcanonical statusへ変換します。一般案件一覧では `open`, `negotiating`, `assigned`, `in_progress` のみを読めるRLS policyに更新します。
LIFFフォームのグループ通知では `line_liff_sessions` を追加し、グループIDをURLに直接出さずに `session_id` で投稿元グループへ紐付けます。
過去ログ取込では `posted_at`, `pickup_date`, `schedule_text`, `import_batch_id`, `history_message_hash` などを追加し、Webhookではない履歴データを `source_type = 'line_history_import'` として扱います。

### Phase 2.5〜3.7で追加するテーブル

```text
line_messages
line_users
line_liff_sessions
vehicle_availabilities
job_status_updates
job_status_history
```

### Phase 2.5〜3.7でjobsへ追加する主なカラム

```text
source_type
source_line_message_id
job_category
vehicle_count
delivery_date
tax_type
fee_note
highway_fee_note
budget_note
company_name
contact_name
phone_numbers
created_by_line_user_id
created_by_display_name
assigned_at
in_progress_at
completed_at
cancelled_at
status_updated_at
status_updated_by
closed_reason
contact_line_user_id
contact_display_name
contact_phone
contact_method
contact_missing
closed_reported_by_line_user_id
closed_reported_at
posted_at
pickup_date
pickup_time_text
delivery_time_text
schedule_text
date_confidence
date_needs_review
recurring
import_batch_id
history_message_hash
```

## LINE過去ログ一括取込

LINEの過去ログをテキストファイルから取り込み、`line_messages` に原本保存したうえで、既存の分類ロジックを使って `jobs`, `vehicle_availabilities`, `job_status_updates` に分岐保存できます。

対応する基本形式:

```text
2026.05.01 金曜日
09:27 タカオ お世話になります。
本日、大阪府枚方市積み→5月2日埼玉県日高市下ろし
4t 低予算に対応出来る方いませんか？
```

dry-run:

```bash
cd /Users/sakio/Documents/New\ project
python3 scripts/import_line_history.py data/line_history.txt --dry-run
```

本取込:

```bash
cd /Users/sakio/Documents/New\ project
python3 scripts/import_line_history.py data/line_history.txt
```

dry-runではDB保存せず、1メッセージごとの分類と以下の件数サマリーを表示します。

```text
messages
jobs
vehicle_availabilities
status_updates
ignored_events
duplicates
```

日付はログの日付行を基準に解釈します。`本日` は投稿日、`明日` は投稿日の翌日、`5/2` や `5月2日` はログ年を使って保存します。`5月下旬`, `決まり次第`, `毎週月曜` のような曖昧・定期表現は無理に日付確定せず、`schedule_text` に残して `date_needs_review = true` にします。

同じ `history_date + history_time + sender_name + raw_text` は `history_message_hash` で重複扱いにし、二重保存を避けます。一括取込ごとに `import_batch_id` を発行するため、後から取込単位で確認できます。

## 環境変数

`.env.example` を `.env` にコピーし、値を設定してください。

```bash
cp .env.example .env
```

`.env` は `.gitignore` に含めています。APIキー、LINE Channel Secret、Supabase Secret Keyなどのシークレット値はコミットしないでください。`.env` の中身はターミナル出力、README、ログ、エラー文、コミット差分に表示しない前提です。

### バックエンド用

これらはPython/FastAPI側だけで読み込みます。React/Vite側へ渡さないでください。

```env
API_ENV=
APP_BASE_URL=
SUPABASE_URL=
SUPABASE_SECRET_KEY=
SUPABASE_SERVICE_ROLE_KEY=
OPENAI_API_KEY=
OPENAI_MODEL=
MAPS_API_KEY=
LINE_CHANNEL_SECRET=
LINE_CHANNEL_ACCESS_TOKEN=
LINE_LOGIN_CHANNEL_ID=
LINE_LOGIN_CHANNEL_SECRET=
LIFF_ID=
LIFF_BASE_URL=
RICH_MENU_IMAGE_PATH=assets/line-rich-menu.png
```

| 変数名 | 用途 |
| --- | --- |
| `API_ENV` | APIの実行環境名です。ローカル、ステージング、本番などの切り替えに使います。 |
| `APP_BASE_URL` | FastAPIのベースURLです。Webhook URLやサーバー側で生成するURLの基準に使います。 |
| `SUPABASE_URL` | Supabase Project SettingsのAPI URLです。FastAPIからSupabaseへ接続するために使います。 |
| `SUPABASE_SECRET_KEY` | Supabaseの新しい `sb_secret` 形式のSecret keyです。FastAPIがDBへ保存・更新するために使います。バックエンド専用で、React/Vite側へ絶対に出さないでください。 |
| `SUPABASE_SERVICE_ROLE_KEY` | 旧形式や既存コードとの互換用のService Role Keyです。設定されている場合でもバックエンド専用で、React/Vite側へ絶対に出さないでください。 |
| `OPENAI_API_KEY` | OpenAI Platformで発行するAPI keyです。LLM抽出処理で使います。バックエンド専用です。 |
| `OPENAI_MODEL` | LLM抽出に使うOpenAIモデル名です。 |
| `MAPS_API_KEY` | Google Maps / Distance Matrix APIなどで走行距離を取得するためのAPI keyです。バックエンド専用です。未設定でも案件投稿は可能です。 |
| `LINE_CHANNEL_SECRET` | LINE DevelopersのMessaging APIチャネルで取得するChannel secretです。Webhook署名検証に使います。バックエンド専用です。 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE DevelopersのMessaging APIチャネルで発行するChannel access tokenです。Push通知などに使います。バックエンド専用です。 |
| `LINE_LOGIN_CHANNEL_ID` | LINE DevelopersのLINE Loginチャネルで取得するChannel IDです。LIFFログインやID token検証のために使います。 |
| `LINE_LOGIN_CHANNEL_SECRET` | LINE DevelopersのLINE Loginチャネルで取得するChannel secretです。バックエンド専用です。 |
| `LIFF_ID` | Botが個別チャットへ送るLIFFリンク生成に使うLIFF IDです。バックエンド側でURL生成に使います。 |
| `LIFF_BASE_URL` | Botが送るLIFF URLのベースです。設定されている場合は `LIFF_ID` より優先されます。 |
| `RICH_MENU_IMAGE_PATH` | Messaging APIでアップロードするリッチメニュー画像のパスです。標準は `assets/line-rich-menu.png` です。 |

### フロントエンド用

これらはReact/Vite側で使う値です。`VITE_` で始まる値はビルド後のブラウザコードから参照できます。Secret key、OpenAI API key、LINE Channel Secret、LINE Channel Access Tokenは絶対に入れないでください。

```env
VITE_API_BASE_URL=
VITE_SUPABASE_URL=
VITE_SUPABASE_PUBLISHABLE_KEY=
VITE_LIFF_ID=
```

| 変数名 | 用途 |
| --- | --- |
| `VITE_API_BASE_URL` | LIFFアプリからFastAPIを呼ぶ場合のAPIベースURLです。 |
| `VITE_SUPABASE_URL` | Supabase Project SettingsのAPI URLです。通常はバックエンド用の `SUPABASE_URL` と同じURLです。 |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Supabaseの新しい `sb_publishable` 形式のPublishable keyです。フロントエンドからSupabaseへ接続するために使います。Secret keyは絶対に入れないでください。 |
| `VITE_LIFF_ID` | LINE Developersで発行したLIFF IDです。 |

## ローカル起動

### FastAPI

```bash
cd /Users/sakio/Documents/New\ project
python3 -m venv .venv
source .venv/bin/activate
pip install -r apps/api/requirements.txt
uvicorn apps.api.app.main:app --reload --host 0.0.0.0 --port 8000
```

ヘルスチェック:

```bash
curl http://localhost:8000/health
```

LINE DevelopersのWebhook URLには、ngrokなどで公開したURLを指定してください。

```text
https://<your-domain>/line/webhook
```

## curlでWebhook署名付きテスト

`.env` を読み込んだ状態で、署名付きのテストリクエストを送れます。

```bash
source .env

BODY='{"events":[{"type":"message","message":{"type":"text","id":"test-message-001","text":"5/10 東京港から大阪市 4t 冷凍食品 8万円"},"source":{"type":"group","groupId":"Cxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx","userId":"Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},"timestamp":1714546800000}]}'

SIGNATURE=$(printf "%s" "$BODY" | openssl dgst -sha256 -hmac "$LINE_CHANNEL_SECRET" -binary | openssl base64)

curl -i -X POST http://localhost:8000/line/webhook \
  -H "Content-Type: application/json" \
  -H "X-Line-Signature: $SIGNATURE" \
  -d "$BODY"
```

成功すると以下のようなレスポンスになります。

```json
{
  "ok": true,
  "received": 1,
  "saved": 1,
  "processed": 1,
  "skipped": 0,
  "errors": 0
}
```

署名が間違っている場合は `401 Invalid LINE signature` を返します。

## Phase 3: React / LIFF 案件一覧

フロントエンドは `apps/web` にあります。React/Vite側では `VITE_` で始まる環境変数だけを参照します。`SUPABASE_SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`, `LINE_CHANNEL_ACCESS_TOKEN` はフロントエンドコードでは使いません。

### 起動

```bash
cd /Users/sakio/Documents/New\ project/apps/web
npm install
npm run dev
```

開発サーバー:

```text
http://localhost:5173
```

### ビルド確認

```bash
cd /Users/sakio/Documents/New\ project/apps/web
npm run typecheck
npm run build
```

### 画面確認

- LINEアプリ内では、LIFF URLから開いて `VITE_LIFF_ID` で `liff.init()` します。
- LINEアプリ外のブラウザでは、LIFF初期化に失敗しても案件一覧の開発確認は続行できます。
- 案件一覧では `public.jobs` から公開案件を取得します。
- 検索条件は出発地、到着地、車種、ステータス、確認待ちのみです。
- 案件投稿タブでは、LIFFフォームから `jobs` に `source_type = 'liff_form'`, `analysis_status = 'form_submitted'`, `review_required = false`, `status = 'open'` で保存します。
- 空車登録タブでは、LIFFフォームから `vehicle_availabilities` に保存します。
- 案件一覧タブ内の「空車一覧」では、登録済みの `vehicle_availabilities` を新しい順に表示します。
- 管理タブではFastAPI経由で案件の確認、編集、非公開化、終了報告候補の適用ができます。MVPではローカル開発前提の管理APIです。本番公開前に管理者認証を追加してください。
- 企業検索タブでは、`data/BusinessCards_Export.csv` を使い、会社名、氏名、電話番号、メール、住所などを検索します。CSVが未配置の場合もAPIは落ちず、企業データCSVが見つからない旨を返します。
- LIFF URLに `?tab=list`, `?tab=vehicles`, `?tab=vehicle_availabilities`, `?tab=post`, `?tab=vehicle`, `?tab=admin`, `?tab=companies` を付けると、対応する画面を初期表示します。

### Cloudflare TunnelでReactを一時公開する

LIFFの実機確認でローカルReact画面を一時的に公開する場合は、Viteを外部アクセス可能なhostで起動し、Cloudflare TunnelなどのHTTPS URLをLIFF Endpoint URLに設定します。

```bash
cd /Users/sakio/Documents/New\ project/apps/web
npm run dev -- --host 0.0.0.0 --port 5173
cloudflared tunnel --url http://localhost:5173
```

発行されたHTTPS URLをLINE DevelopersのLIFF Endpoint URLへ設定してください。LINE Webhook用のFastAPIは別途ngrok、Cloudflare Tunnel、本番環境などで `https://<your-domain>/line/webhook` として公開します。

### 管理API

管理画面は以下のFastAPI APIを使います。Supabase Secret Keyはバックエンド側だけで使い、React/Vite側には渡しません。
`scope=mine` ではLIFFのID tokenをバックエンドで検証し、検証済みLINE userIdと `jobs.created_by_line_user_id` が一致する案件だけを取得します。

```text
GET    /admin/jobs
GET    /admin/jobs?scope=mine
GET    /admin/jobs/{job_id}
PATCH  /admin/jobs/{job_id}
POST   /admin/jobs/{job_id}/verify
POST   /admin/jobs/{job_id}/hide
POST   /admin/jobs/{job_id}/status
GET    /admin/line-messages
GET    /admin/status-updates
POST   /admin/status-updates/{id}/apply
POST   /admin/status-updates/{id}/ignore
POST   /liff/jobs
POST   /liff/vehicle-availabilities
POST   /distance/measure
GET    /vehicle-availabilities
GET    /companies/search?q=検索語&limit=50
```

`/distance/measure` は積地・卸地から走行距離を取得し、軽貨物の場合は貨物軽自動車運賃表の距離制運賃で標準運賃目安を返します。`MAPS_API_KEY` が未設定の場合でも案件投稿は止めず、距離取得API未設定として安全に返します。

### LINE投稿分類

Webhook受信時は、まず `line_messages` に原本を保存し、ルールベースで次の `message_type` に分類します。

```text
job_request
regular_job
work_job
vehicle_availability
job_closed
job_completed
menu_request
attachment
member_event
note_event
unsend_event
irrelevant
```

`job_request`, `regular_job`, `work_job` は `jobs` に確認待ちとして保存します。
`vehicle_availability` は `vehicle_availabilities` に保存し、`jobs` には入れません。
`job_closed`, `job_completed` は `job_status_updates` に候補保存し、管理者が適用するまで `jobs.status` は更新しません。
`menu_request` はBotがLIFFメニューを案内するための投稿として扱い、`line_messages` にだけ保存します。グループでは送信者本人への個別Push、個別チャットではその場のreplyでメニューを返します。
添付ファイルは `line_messages` に `message_type = 'attachment'` として保存し、初期MVPでは本文解析しません。
送信取消は、対象 `source_message_id` が分かる場合に `line_messages.is_unsent = true` とし、関連 `jobs` は自動削除せず `hidden` として通常一覧から外します。

分類だけを確認する場合:

```bash
source .venv/bin/activate
python -m apps.api.app.cli.classify_message --text "富山県魚津市で軽バンが空車となりました。"
```

## Phase 2: OpenAI案件解析

OpenAI APIはFastAPI側、またはCLIからバックエンド専用に呼び出します。`OPENAI_API_KEY` はReact/Vite側に渡さず、ログやREADMEにも実値を書かないでください。

### raw_textを指定して解析だけ確認

Supabaseには保存せず、OpenAIのJSON抽出結果だけを確認します。

```bash
source .venv/bin/activate
python -m apps.api.app.cli.analyze_job \
  --raw-text "5/10 東京港から大阪市 4t 冷凍食品 8万円 午前積み"
```

### 未解析jobsを1件解析して保存

`analysis_status = 'pending'` の古いレコードを1件取得し、解析結果を `public.jobs` に保存します。

```bash
source .venv/bin/activate
python -m apps.api.app.cli.analyze_job --next-unparsed
```

### 指定したjobを解析して保存

```bash
source .venv/bin/activate
python -m apps.api.app.cli.analyze_job --job-id "<job-id>"
```

保存時は以下を更新します。

```text
pickup_location
delivery_location
pickup_prefecture
delivery_prefecture
scheduled_date
scheduled_time_text
vehicle_type
cargo_type
price
notes
confidence
missing_fields
analysis_status
analysis_error
analysis_model
analysis_completed_at
review_required
```

`confidence` が低い場合、または `missing_fields` がある場合は `review_required = true` になり、`analysis_status = 'needs_review'` になります。OpenAIの結果は自動確定ではなく、管理者の確認・修正を前提にしています。
