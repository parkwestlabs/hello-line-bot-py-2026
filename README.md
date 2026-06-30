# Hello LINE bot Python/FastAPI 2026

2026年5月時点における Python/FastAPI による LINE bot の Hello World サンプルコード

* `line-bot-sdk` を利用して、スタンプ付けておうむ返しするbot
* Tech Stack
    * Python 3.14
    * FastAPI (Flaskではない)
    * line-bot-sdk V3
    * 非同期を活用 `AsyncApiClient`/`AsyncMessagingApi`
    * uv/ruff
    * pytest
    * CI/CD Github Actions
    * GCP Google App Engine (GAE)
    * GCP Workload Identity (OIDC) 連携によるデプロイ
    * Terraform

## Overview

送られてくる主なイベントの種類と、この bot で扱う対象についての全体像

* トーク関連
    * MessageEvent
        * UserSource
            * TextMessageContent ← このbotはUserから来たTextを扱う
            * ImageMessageContent
            * StickerMessageContent
            * ...
        * GroupSource
        * RoomSource
        * UnsendEvent
    * FollowEvent
    * UnfollowEvent
* グループ関連
    * JoinEvent
    * LeaveEvent
    * MemberJoinedEvent
    * MemberLeftEvent
* アクション・通知関連
    * PostbackEvent
    * ...

## Quick Start

* uv: https://docs.astral.sh/uv/getting-started/installation/
* gcloud: https://docs.cloud.google.com/sdk/docs/downloads-homebrew?hl=ja
* `.env` に `LINE_CHANNEL_ACCESS_TOKEN` `LINE_CHANNEL_SECRET` を指定

```bash
uv sync
uv run pytest -v
uv run fastapi dev main.py
```

## Quick Deploy

GCP Google AppEngine (GAE) に terraform でデプロイする手順

### (1) Manual Deploy

* まずは、ターミナル上から `gcloud app deploy` でデプロイできるようにする
* 最初に project は手動で作成する
* (参考) Organizations ID が取得できる場合は project 作成自体も terraform 化できるらしい
    * `gcloud organizations list` で Organizations の有無を確認

```bash
# gcloud CLI 用ログイン
gcloud auth login

gcloud projects create [好きなプロジェクトID] --name="[好きなプロジェクトNAME]"
gcloud projects list    # PROJECT_NUMBER を確認
```

* `terraform-gcp/terraform.tfvars.sample` に基づき `terraform-gcp/terraform.tfvars` を作成する

```bash
# その他ツール用ログイン - ADC (Application Default Credentials)
gcloud auth application-default login

terraform-gcp/

terraform init
terraform plan
terraform apply
```

* `main.tf` にある AppEngine の土台のみが作成されているはず
* LINE Developers > Messaging API設定 から必要な値を取得する
    * https://developers.line.biz/ja/
* `env_variables.yaml.sample` に基づき `env_variables.yaml` を作成する
    * 参照→ https://stackoverflow.com/a/54055525
* ターミナル上から python のコードを deploy できるはず

```bash
gcloud app deploy
```

* 出力される app_url に `/callback` を付けて LINE Developers > Messaging API設定 > Webhook URL に登録

### (2) Github Actions Deploy

Github Actions から自動 Deploy する設定

* `gha_deploy.tf` にある Workload Identity の設定もされているはず
* Github に secrets を設定する
    * 下記 5. [GitHub Secrets に登録する](#5-github-secrets-に登録する) 参照
* workflow の `google-github-actions/deploy-appengine@v3` が `gcloud app deploy` してくれる

-----

以下は、Terraform 化の前提となる CLI の作業手順の記録

## GAE Deploy

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
gcloud projects create [好きなプロジェクトID] --name="[好きなプロジェクトNAME]"

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

* 最後に表示された URL に `/callback` を付けて Webhook URL に登録する
    * LINE Developers > Messaging API設定

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

# まずは公式docの説明の通り、デフォルトのサービス アカウントに
# ストレージ管理者（roles/storage.admin）のロールを付与します。
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$GAE_SA" \
    --role="roles/storage.admin"
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
* Workload Identity (OIDC) 連携を使って認証する
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

## Terraform

* 上記の gcloud CLI による作業を Terraform を使って自動化・スクリプト化する

```bash
cd terraform-gcp/

# 最初の一回だけ初期化
terraform init
# .terraform/ が作成される

gcloud auth application-default login
```

* ブラウザが開き、以下が出てくるので、両方チェックして続ける
    * Google Cloud のデータの参照、編集、設定、削除、Google アカウントのメールアドレスの参照
    * Google Cloud SQL インスタンスを参照してログインする
* `~/.config/gcloud/application_default_credentials.json` が作成され、自動で利用される
    * `provider "google"` に `credentials` や `access_token` は不要

### 先に gcloud CLI で作成したリソースを管理下に置く

* `terraform import` の代わりに generate (importブロック) を使う
    * `imports.tf` に import ブロックを書く
    * `-generate-config-out` オプションで `generated.tf` が生成される
    * `generated.tf` の中を変数に置き換えて整理整頓
    * `terraform plan` で `Plan: 15 to import...` と出れば成功
    * `terraform apply` で State ファイルに書き込み terraform の管理下に入る
        * `terraform.tfstate` は一旦 local 管理として `.gitignore` に入れる
        * リモートバックエンド (GCSバケット) が望ましい
    * `terraform plan` を再度実行して `No changes.` と出ることを確認
    * `generated.tf` から整頓後のコードを `main.tf` に移動して `generated.tf` は削除
    * `imports.tf` も作業後に削除する。(参考用に `imports.tf.backup` として保持している)
* `imports.tf` に入れるのはユーザー管理のもののみを対象にする
    * `SERVICE_ACCOUNT_NAME@PROJECT_ID.iam.gserviceaccount.com` を管理対象にする
    * `PROJECT_ID@appspot.gserviceaccount.com` (Google管理 / デフォルト) 自体は対象外
        * 追加された権限のみを対象にする (参考: `imports.tf.backup`)

```bash
# imports.tf から generated.tf を生成
terraform plan -generate-config-out=generated.tf

# 整理整頓後
terraform plan
terraform apply

# format
terraform fmt
```

### role 追加など、同じことの繰り返しは DRY にできる

generateではリソースを個別に生成するしかないが、後から配列化する方法

* `locals` に role を配列として定義する
* 重複したコードをその配列を使って `for_each` `toset` `each.key` で DRY にする
* `moved` で移動前後のリソース名を指定する (一時的なものなのでどこに書いてもよい)
* `terraform plan` で `Plan: 0 to add, 0 to change, 0 to destroy.` と出れば成功
* `terraform apply` を実行し `Apply complete! Resources: 0 added, 0 changed, 0 destroyed.` で成功
* `moved` は配列化に限らず、リソースの rename 全般に便利に利用できる

```bash
# moved で個別指定から配列への rename を指定する例
moved {
  from = google_project_iam_member.default_sa_artifactregistry_reader_role
  to   = google_project_iam_member.gae_sys_sa_roles["roles/artifactregistry.reader"]
}
moved {
  from = google_project_iam_member.default_sa_artifactregistry_writer_role
  to   = google_project_iam_member.gae_sys_sa_roles["roles/artifactregistry.writer"]
}
# ... (これを配列の全要素分繰り返す)
```

### Clean Up

```bash
# 全削除
terraform destroy

# 削除されたことを確認
terraform state list
# タイミング問題もあり得るので、もし何か残っていたら、もう一度 terraform destroy してみるとよい

# 大量の出力がされるが、ほぼsystemが管理しているものでスルーでOKなはず
gcloud asset search-all-resources --scope="projects/YOUR_PROJECT_ID" --format="table(assetType, displayName)"

# project 全体を削除すれば課金も確実にされなくなる
gcloud projects delete YOUR_PROJECT_ID

# sys で始まるPROJECT_IDはsystem用なので課金もされず無視してOK
gcloud projects list
```

### Tips

* GCP のnamingは、idは番号ではなく文字、数字のidはnumberが別にあり、またdisplay_nameとして人間用の文字がある
* google_project_iam_member: プロジェクト内のリソースを操作できるmember (例: サービスアカウント)
* google_service_account_iam_member: サービスアカウントを操作できるmember (例: GitHub Actions)

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
