# Hello LINE bot Python/FastAPI 2026

2026年5月時点における Python/FastAPI による LINE bot の Hello World サンプルコード

* `line-bot-sdk` を利用しておうむ返しするbot
* Tech Stack
    * Python 3.14
    * FastAPI (Flaskではない)
    * line-bot-sdk V3
    * 非同期を活用 `AsyncApiClient`/`AsyncMessagingApi`
    * uv/ruff
    * pytest
    * GCP Google App Engine (GAE)

## Quick Start

* uv: https://docs.astral.sh/uv/getting-started/installation/
* gcloud: https://docs.cloud.google.com/sdk/docs/downloads-homebrew?hl=ja

```bash
uv sync
uv run pytest -v
./start_devserver.sh
```

## GAE Deploy

* `env_variables.yaml` を作成
    * 参照→ https://stackoverflow.com/a/54055525
```yaml
env_variables:
  LINE_CHANNEL_ACCESS_TOKEN: 'xxx'
  LINE_CHANNEL_SECRET: 'xxx'
```

* `gcloud` で各種設定とデプロイ

```bash
# 最初に auth login と config set project を
# 対話形式でまとめてできる初期コマンド
gcloud init

# 1. Googleアカウントでログイン（ブラウザが開きます）
gcloud auth login

# 2. プロジェクト一覧を表示して、使いたいプロジェクトIDを確認
gcloud projects list
# またはプロジェクト作成
gcloud projects create [好きなプロジェクトID]

# 3. デプロイ先のプロジェクトを設定
gcloud config set project [あなたのプロジェクトID]

# 選択したプロジェクトIDを確認
gcloud config get-value project

# 事前に不足している service を確認
gcloud services list --enabled

# 必要な場合に service を有効化
gcloud services enable xxx
# 例 (多くの場合はデフォルトで入っていて不要と思われる)
gcloud services enable appengine.googleapis.com cloudbuild.googleapis.com storage.googleapis.com

# リージョン（場所）を選択して作成（東京なら asia-northeast1）
gcloud app create --region=asia-northeast1
gcloud app describe

# デプロイするファイルを確認 (.gcloudignore が意図通りの効果かを確認)
gcloud meta list-files-for-upload

# 初回のデプロイは権限不足でエラーになるので、下記参照で権限を追加する
gcloud app deploy
# Deployed service [default] to [https://xxx.an.r.appspot.com]
# You can stream logs from the command line by running:
#   $ gcloud app logs tail -s default
# To view your application in the web browser run:
#   $ gcloud app browse
```

### Troubleshooting

* デバッグ用一覧コマンド

```bash
# 有効化された service 一覧
gcloud services list --enabled

# 権限一覧コマンド
gcloud projects get-iam-policy $(gcloud config get-value project) \
    --flatten="bindings[].members" \
    --format="table(bindings.members, bindings.role)" \
    --sort-by="bindings.members"
```

* (公式doc) 新しいプロジェクトのデプロイに失敗する
    * https://docs.cloud.google.com/appengine/docs/standard/troubleshooter/deployment?hl=ja

> Error Response: [13] Failed to create cloud build:
> service account PROJECT_ID@appspot.gserviceaccount.com
> does not have access to the bucket

```bash
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='get(projectNumber)')

# (注) GCP初期からある appspot だけ例外で PROJECT_ID@appspot になる
GAE_SA="${PROJECT_ID}@appspot.gserviceaccount.com"
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# まずは公式docの説明の通り、デフォルトのサービス アカウントに
# ストレージ管理者（roles/storage.admin）のロールを付与します。
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$GAE_SA" \
    --role="roles/storage.admin"

# cloudbuild も設定する必要があるらしい
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$CB_SA" \
    --role="roles/storage.admin"
```

以下、`gcloud app deploy` する度にエラーが出るので、
順次ログの表示に従って権限を追加していく

```bash
# The service account running this build projects/xxx/serviceAccounts/xxx@appspot.gserviceaccount.com does not have permission to write logs to Cloud Logging.
# To fix this, grant the Logs Writer (roles/logging.logWriter) role to the service account.

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$GAE_SA" \
    --role="roles/logging.logWriter"

# ERROR: failed to initialize analyzer:
# validating registry read access: failed to ensure registry read access
# DENIED: Permission 'artifactregistry.repositories.downloadArtifacts' denied on resource

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$GAE_SA" \
    --role="roles/artifactregistry.reader"

# ERROR: failed to initialize analyzer:
# validating registry write access: failed to ensure registry read/write access
# DENIED: Permission 'artifactregistry.repositories.uploadArtifacts' denied on resource

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$GAE_SA" \
    --role="roles/artifactregistry.writer"
```

* (オプション) デプロイ成功後、「最小権限の原則」に沿った設定にする場合

```bash
# 1. 強い方の権限 (admin) を削除
gcloud projects remove-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$GAE_SA" \
    --role="roles/storage.admin"

# 2. 適切な権限 (objectAdmin) を付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$GAE_SA" \
    --role="roles/storage.objectAdmin"
```

## Init Project Notes

```bash
uv init . --app
uv add "fastapi[standard]" line-bot-sdk python-dotenv
uv export --format requirements.txt -o requirements.txt

uv add --dev ruff pyright pytest pytest-mock pytest-asyncio pytest-cov
```
