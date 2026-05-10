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
    * CI/CD Github Actions
    * GCP Google App Engine (GAE)

## Quick Start

* uv: https://docs.astral.sh/uv/getting-started/installation/
* gcloud: https://docs.cloud.google.com/sdk/docs/downloads-homebrew?hl=ja
* `.env` に `LINE_CHANNEL_ACCESS_TOKEN` `LINE_CHANNEL_SECRET` を指定

```bash
uv sync
uv run pytest -v
uv run fastapi dev main.py
```

## GAE Deploy

* まずは、ターミナル上から `gcloud app deploy` でデプロイできるようにする
* `env_variables.yaml` を作成
    * 参照→ https://stackoverflow.com/a/54055525
* LINE Developers > Messaging API設定 から値を取得する
```yaml
env_variables:
  LINE_CHANNEL_ACCESS_TOKEN: '*****'
  LINE_CHANNEL_SECRET: '*****'
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
gcloud services enable *****
# 例 (多くの場合はデフォルトで入っていて不要と思われる)
gcloud services enable appengine.googleapis.com cloudbuild.googleapis.com storage.googleapis.com

# リージョン（場所）を選択して作成（東京なら asia-northeast1）
gcloud app create --region=asia-northeast1
gcloud app describe

# デプロイするファイルを確認 (.gcloudignore が意図通りの効果かを確認)
gcloud meta list-files-for-upload

# 初回のデプロイは権限不足でエラーになるので、下記参照で権限を追加する
gcloud app deploy
# Deployed service [default] to [https://*****.an.r.appspot.com]
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
* エラーが出る度にログを見て、権限の不足分を追加していく
* 最近デフォルトの権限が変更されたらしく、公式docを超えて、動くまで試行錯誤が必要

> Error Response: [13] Failed to create cloud build:
> service account PROJECT_ID@appspot.gserviceaccount.com
> does not have access to the bucket

```bash
PROJECT_ID=$(gcloud config get-value project)
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')

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
    --role="roles/cloudbuild.builds.editor"
```

以下、`gcloud app deploy` する度にエラーが出るので、
順次ログの表示に従って権限を追加していく

```bash
# The service account running this build projects/*****/serviceAccounts/*****@appspot.gserviceaccount.com does not have permission to write logs to Cloud Logging.
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

## GAE Deploy by Github Actions

* Github Actions の workflow を設定: `.github/workflows/main.yaml`
    * CI: ruff の linter formatter と pytest 実行
    * CD: GCP の Google AppEngine に自動デプロイする
* Workload Identity 連携を使って認証する
    * `google-github-actions/auth@v3`
    * `google-github-actions/deploy-appengine@v3`
* (参考) サービスアカウントキーを用いずにGitHub ActionsからGoogle Cloudと認証する
    * https://dev.classmethod.jp/articles/google-cloud-auth-with-workload-identity/

### 1. 変数のセット

```bash
PROJECT_ID=$(gcloud config get-value project)
SERVICE_ACCOUNT_NAME="github-deploy-sa"
SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
GITHUB_REPO="USER_NAME/REPO_NAME" # 例: myname/line-bot-repo

# 任意の名前でOK
POOL_NAME="github-actions-pool"
PROVIDER_NAME="github-actions-oidc"
```

### 2. サービスアカウントの作成

* 公式doc
    * https://github.com/google-github-actions/deploy-appengine#authorization
* 必要な Role は5つ
    * `roles/appengine.appAdmin`
    * `roles/storage.admin`
    * `roles/cloudbuild.builds.editor`
    * `roles/artifactregistry.reader`
    * `roles/iam.serviceAccountUser`

```bash
# サービスアカウント作成
gcloud iam service-accounts create ${SERVICE_ACCOUNT_NAME} \
    --project="${PROJECT_ID}" --display-name="GitHub Action Deployer"

# デプロイに必要な権限（App Engine管理、ストレージ書き込み、ビルド権限など）を付与
# ※最小権限に絞ることも可能ですが、まずはデプロイを確実に通すためのセットです
for role in "roles/appengine.appAdmin" "roles/storage.admin" "roles/cloudbuild.builds.editor" "roles/artifactregistry.reader" "roles/iam.serviceAccountUser"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
      --member="serviceAccount:${SA_EMAIL}" \
      --role="${role}"
done

# 一覧で確認
gcloud iam service-accounts list

# projects get-iam-policy 一覧コマンド (再掲)
gcloud projects get-iam-policy $(gcloud config get-value project) \
    --flatten="bindings[].members" \
    --format="table(bindings.members, bindings.role)" \
    --sort-by="bindings.members"
```

### 3. Workload Identity プールとプロバイダの作成

```bash
# プールの作成
gcloud iam workload-identity-pools create "${POOL_NAME}" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --display-name="GitHub Actions Pool"

# プロバイダの作成（GitHubからの接続を許可する設定）
gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_NAME}" \
    --project="${PROJECT_ID}" \
    --location="global" \
    --workload-identity-pool="${POOL_NAME}" \
    --display-name="GitHub Actions Provider" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository"

# 一覧
gcloud iam workload-identity-pools list --location="global"
gcloud iam workload-identity-pools providers list \
  --location="global" --workload-identity-pool=$POOL_NAME

# 作成した $POOL_NAME のIDを変数に設定
WORKLOAD_IDENTITY_POOL_ID=$(gcloud iam workload-identity-pools describe $POOL_NAME \
  --project="${PROJECT_ID}" \
  --location="global" \
  --format="value(name)")
```

### 4. サービスアカウントとGitHubリポジトリの紐付け

```bash
gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
    --project="${PROJECT_ID}" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/${GITHUB_REPO}"

gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
    --project="${PROJECT_ID}" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --member="principalSet://iam.googleapis.com/${WORKLOAD_IDENTITY_POOL_ID}/attribute.repository/${GITHUB_REPO}"

# 確認
gcloud iam service-accounts get-iam-policy "${SA_EMAIL}"
```

### 5. GitHub Secrets に登録する

* Settings > Secrets and variables > Actions > Repository secrets に登録する
    * `GCP_PROJECT_ID`
    * `WIF_PROVIDER`
    * `WIF_SERVICE_ACCOUNT`
    * `LINE_CHANNEL_ACCESS_TOKEN`
    * `LINE_CHANNEL_SECRET`

```bash
# GCP_PROJECT_ID として登録する値
echo $PROJECT_ID

# WIF_PROVIDER として登録する値
gcloud iam workload-identity-pools providers describe $PROVIDER_NAME \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool=$POOL_NAME \
  --format='value(name)'

# WIF_SERVICE_ACCOUNT として登録する値
echo $SA_EMAIL
```

## Init Project Notes

```bash
uv init . --app
uv add "fastapi[standard]" line-bot-sdk python-dotenv
uv export --format requirements.txt -o requirements.txt

uv add --dev ruff pyright pytest pytest-mock pytest-asyncio pytest-cov
```

## Reference

* [無料][2024年版] LINE Messaging API v3 + Python(Flask) でボットを作る
    * https://qiita.com/nozomiyamada/items/dff5f240e8c936d731fd
* (参考) Gemi兄の解説 - なぜ SDK V3 は分かりにくいのか。以下は引用です。

> 現在の SDK v3 がこれほど「ややこしい」抽象的な設計になっているのには、いくつか理由（というか苦肉の策）があります。

### なぜこうなったのか？

1. 自動生成の弊害: LINE SDK v3 は、OpenAPI (Swagger) という定義ファイルから機械的にコードを生成（Auto-generated）しています。そのため、人間が書くような「気が利いたクラス分け」よりも、仕様書の構造をそのままクラスに落とし込んでしまっているのです。
2. 型安全への極端な振り切り: 「どんなイベントが飛んできても、型定義でエラーを出さない」ことを優先した結果、Source や MessageContent といった抽象的な親クラスを介さざるを得なくなりました。
3. 柔軟性とのトレードオフ: グループ内でのユーザー特定など、複雑な組み合わせを一つの MessageEvent で表現しようとしたため、中身を開けてみないと正体がわからない「福袋」のようなオブジェクトになってしまいました。

### 開発者としての向き合い方

この「ライブラリの不便さ」をコードに持ち込みすぎないためには、やはり自分専用のラッパー（ラップ関数）を作ってしまうのが一番の防衛策です。
