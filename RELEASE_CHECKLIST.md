# GitHub公開前 最終チェックリスト ✅# GitHub公開前 最終チェックリスト ✅# 🚀 GitHub公開リリース - 最終チェックリスト



## ✅ 完了済み項目



### 1. セキュリティこのチェックリストは、リポジトリをGitHubに公開する前に確認すべき項目です。**プロジェクト名:** Azure Computer Vision OCR Demo with SDK  



- [x] ハードコードされたAPIキー・シークレットを削除**リリース日:** 2025-10-17  

- [x] `infrastructure/apim/image-analysis-v4-policy-with-retry.xml` のキーをプレースホルダー化

- [x] `setup-apim-api.sh` のハードコードされたキーを削除## ✅ 完了済み項目**バージョン:** v1.0.0

- [x] `.gitignore` で環境ファイル (`.env*`) を除外

- [x] `.env.example` と `.env.japan-east.template` のみを含める

- [x] テスト成果物 (`out/`) を除外

### セキュリティ---

### 2. ドキュメント



- [x] `LICENSE` (MIT License) を作成

- [x] `README.md` を更新- [x] ハードコードされたAPIキー・シークレットを削除## ✅ 完了した準備作業

- [x] リポジトリ情報を反映 (sasukeh/ocr-demo-w-sdk)

- [x] バッジを追加  - [x] `infrastructure/apim/image-analysis-v4-policy-with-retry.xml` のキーをプレースホルダー化

- [x] `CONTRIBUTING.md` を作成

- [x] リポジトリURLを更新  - [x] `setup-apim-api.sh` のハードコードされたキーを削除### 1. セキュリティとプライバシー

- [x] `SECURITY.md` を作成

- [x] `docs/` ディレクトリに詳細ドキュメントを配置- [x] `.gitignore` で環境ファイル (`.env*`) を除外



### 3. CI/CD- [x] `.env.example` と `.env.japan-east.template` のみを含める- [x] **機密情報の削除**



- [x] GitHub Actions ワークフローを作成- [x] テスト成果物 (`out/`) を除外  - [x] ハードコードされたAPIキーを削除 (`infrastructure/apim/image-analysis-v4-policy-with-retry.xml`)

- [x] `.github/workflows/ci.yml` (lint, test, security)

- [x] Markdown linting 設定 (`.markdownlint.json`)  - [x] ハードコードされたAPIキーを削除 (`setup-apim-api.sh`)

- [x] リンクチェック設定 (`.markdown-link-check.json`)

### ドキュメント  - [x] サブスクリプションキーの表示を削除 (`setup-apim-api.sh`)

### 4. コード品質

  - [x] `.gitignore` で `.env*` ファイルを除外 (テンプレート除く)

- [x] Python コードが PEP 8 に準拠

- [x] Type hints を使用- [x] `LICENSE` (MIT License) を作成

- [x] Docstrings を記載

- [x] 不要なファイルを削除- [x] `README.md` を更新- [x] **環境変数の確認**



### 5. テスト  - [x] リポジトリ情報を反映 (sasukeh/ocr-demo-w-sdk)  - [x] `.env.example` が最新



- [x] Scenario B の動作テスト (test_httpx.py)  - [x] バッジを追加  - [x] すべてのシークレットが環境変数経由で取得される

- [x] Scenario B の負荷テスト実行 (600リクエスト, 100%成功)

  - [x] クイックスタートガイドを記載

## 📝 プッシュ前の最終確認

- [x] `CONTRIBUTING.md` を作成### 2. ライセンスとコントリビューション

### リモートリポジトリ確認

  - [x] リポジトリURLを更新

```bash

git remote -v- [x] `SECURITY.md` を作成- [x] **LICENSEファイル**

# origin  git@github.com:sasukeh/ocr-demo-w-sdk.git (fetch)

# origin  git@github.com:sasukeh/ocr-demo-w-sdk.git (push)- [x] `docs/` ディレクトリに詳細ドキュメントを配置  - [x] MIT Licenseを作成

```

  - [x] 著作権年度: 2025

### ステージング確認

### CI/CD

```bash

git status- [x] **CONTRIBUTING.md**

```

- [x] GitHub Actions ワークフローを作成  - [x] コントリビューションガイドライン

## 🚀 GitHubへのプッシュ

  - [x] `.github/workflows/ci.yml` (lint, test, security)  - [x] 開発環境セットアップ手順

```bash

# 初回コミット  - [x] `.github/workflows/deploy-infrastructure.yml`  - [x] PRガイドライン

git commit -m "Initial commit: Azure Computer Vision OCR Demo

  - [x] `.github/workflows/load-test.yml`  - [x] コーディング規約

- Scenario A: Azure SDK-based client-side load balancing

- Scenario B: APIM + httpx circuit breaker implementation- [x] Markdown linting 設定 (`.markdownlint.json`)

- Comprehensive documentation and CI/CD pipelines

- Security-hardened configuration- [x] リンクチェック設定 (`.markdown-link-check.json`)- [x] **SECURITY.md**

- MIT License"

  - [x] 脆弱性報告プロセス

# プッシュ

git push -u origin main### コード品質  - [x] サポートバージョン

```

  - [x] セキュリティベストプラクティス

## 📊 公開後の作業

- [x] Python コードが PEP 8 に準拠

### GitHub リポジトリ設定

- [x] Type hints を使用### 3. ドキュメント

- [ ] リポジトリの説明を追加

- [ ] トピック/タグを追加 (azure, computer-vision, ocr, python, sdk)- [x] Docstrings を記載

- [ ] README.md がデフォルトで表示されることを確認

- [x] 不要なファイルを削除- [x] **README.md**

### GitHub Secrets設定 (CI/CD用)

  - [x] `__pycache__/` ディレクトリ  - [x] プロジェクト概要

- [ ] `AZURE_CREDENTIALS`

- [ ] `AZURE_SUBSCRIPTION_ID`  - [x] `.pyc` ファイル  - [x] バッジ追加 (License, Python version, Azure, Code style)



---  - [x] ログファイル  - [x] SDK Migration完了の通知



🎉 **リリース準備完了!**  - [x] 一時ファイル  - [x] クイックスタート手順


  - [x] アーキテクチャ図

### テスト  - [x] シナリオ別実行方法



- [x] 基本的な動作確認- [x] **技術ドキュメント**

  - [x] Scenario A の動作テスト  - [x] `docs/SDK_MIGRATION.md` - SDK移行ガイド

  - [x] Scenario B の動作テスト (test_httpx.py)  - [x] `docs/SCALING_STRATEGY.md` - 2000リクエスト/分対応戦略

  - [x] Scenario B の負荷テスト実行 (600リクエスト, 100%成功)  - [x] `docs/IMPLEMENTATION_SUMMARY.md` - 実装サマリー

  - [x] `docs/BEST_PRACTICES.md` - ベストプラクティス

## 📝 最終確認事項

### 4. CI/CD

### リポジトリ設定

- [x] **GitHub Actions**

- [ ] リモートリポジトリが正しく設定されている  - [x] `.github/workflows/ci.yml` - CI/CDパイプライン

  ```bash    - [x] Lint (flake8, black)

  git remote -v    - [x] Test (pytest)

  # origin  git@github.com:sasukeh/ocr-demo-w-sdk.git (fetch)    - [x] Security scan (safety, bandit)

  # origin  git@github.com:sasukeh/ocr-demo-w-sdk.git (push)    - [x] Documentation validation (markdownlint)

  ```  

- [x] **設定ファイル**

### コミット前の確認  - [x] `.markdownlint.json` - Markdown lint設定

  - [x] `.markdown-link-check.json` - リンクチェック設定

- [ ] ステージングされたファイルを確認

  ```bash### 5. コード品質

  git status

  ```- [x] **テストコード**

- [ ] 差分を最終確認  - [x] `scenario_a_client/test_sdk.py` - Scenario A SDKテスト

  ```bash  - [x] `scenario_b_apim/test_httpx.py` - Scenario B httpxテスト

  git diff --cached  - [x] 両方のテストが正常動作確認済み

  ```

- [x] **依存関係**

### プッシュ前の確認  - [x] `requirements.txt` が最新

  - [x] Azure SDK dependencies追加

- [ ] 初回コミットを作成  - [x] バージョン固定 (セキュリティ考慮)

  ```bash

  git commit -m "Initial commit: Azure Computer Vision OCR Demo with SDK"---

  ```

- [ ] GitHubにプッシュ## 📝 GitHub公開前の最終確認

  ```bash

  git push -u origin main### リポジトリ設定

  ```

- [ ] **リポジトリ名**: `ocr-demo-w-sdk` (または適切な名前)

## 🚀 公開後の作業- [ ] **公開設定**: Public

- [ ] **トピック追加**:

- [ ] GitHub リポジトリ設定  - [ ] `azure`

  - [ ] リポジトリの説明を追加  - [ ] `computer-vision`

  - [ ] トピック/タグを追加 (azure, computer-vision, ocr, python, sdk)  - [ ] `ocr`

  - [ ] README.md がデフォルトで表示されることを確認  - [ ] `python`

- [ ] GitHub Secrets を設定 (CI/CD用)  - [ ] `azure-sdk`

  - [ ] `AZURE_CREDENTIALS`  - [ ] `load-balancing`

  - [ ] `AZURE_SUBSCRIPTION_ID`  - [ ] `api-management`

- [ ] Issues/Pull Requests テンプレートを作成 (オプション)

- [ ] GitHub Pages を有効化 (オプション)### リポジトリ説明文



## 📊 リリースノート例```

Azure Computer Vision OCR with SDK-based load balancing, failover, and APIM integration demo

```markdown```

# v1.0.0 - Initial Release

### READMEの更新 (GitHubアップロード後)

## 🎉 主な機能

以下のプレースホルダーを実際のURLに置き換える:

- Azure Computer Vision OCR の2つの実装アプローチを提供

  - Scenario A: Azure SDK ベースのクライアント側負荷分散- [ ] `YOUR_USERNAME` → 実際のGitHubユーザー名

  - Scenario B: APIM + httpx によるサーキットブレーカー実装- [ ] リンクの動作確認

- レイテンシー監視とインテリジェントなエンドポイント選択

- 429エラーハンドリングとリトライロジック### GitHub設定

- 包括的なメトリクス収集・分析

- Bicep による Infrastructure as Code- [ ] **About セクション**

- GitHub Actions CI/CD パイプライン  - [ ] Description: 上記の説明文

  - [ ] Website: (デモサイトのURL、あれば)

## 📦 デプロイメント  - [ ] Topics: 上記のトピック



詳細は [README.md](README.md) を参照してください。- [ ] **Features**

  - [ ] ✅ Issues

## 🔒 セキュリティ  - [ ] ✅ Discussions (オプション)

  - [ ] ✅ Wikis (オプション)

セキュリティ上の問題を発見した場合は、[SECURITY.md](SECURITY.md) を参照してください。  - [ ] ✅ Sponsors (オプション)



## 🤝 コントリビューション- [ ] **Security**

  - [ ] Security policy (SECURITY.md) が表示される

コントリビューションガイドは [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。  - [ ] Private vulnerability reporting を有効化

```

### 初回リリース (v1.0.0)

---

- [ ] **リリースノート作成**

## ✅ チェックリスト完了  - [ ] タイトル: `v1.0.0 - Initial Release with Azure SDK`

  - [ ] 説明: 主要機能、セットアップ手順、既知の制限事項

すべての項目が完了したら、以下のコマンドでGitHubに公開できます:  - [ ] タグ: `v1.0.0`



```bash---

# 最終確認

git status## 🎯 リリースノートテンプレート



# コミット```markdown

git commit -m "Initial commit: Azure Computer Vision OCR Demo with SDK## 🎉 v1.0.0 - Initial Release



- Scenario A: Azure SDK-based client-side load balancingAzure Computer Vision OCRのフォールバック・負荷分散デモプロジェクトの初回リリースです。

- Scenario B: APIM + httpx circuit breaker implementation

- Comprehensive documentation and CI/CD pipelines### ✨ 主な機能

- Security-hardened configuration

- MIT License"**Scenario A: クライアント側フォールバック (Azure SDK)**

- Azure Computer Vision SDK (`azure-ai-vision-imageanalysis`) による直接エンドポイントアクセス

# プッシュ- EWMA-based health monitoring によるインテリジェントなエンドポイント選択

git push -u origin main- 指数バックオフリトライとフォールバックメカニズム

```- マルチリージョン対応 (East US, Japan East, West Europe)



🎉 **おめでとうございます!** リポジトリの公開準備が完了しました!**Scenario B: APIM統合 (httpx)**

- Azure API Management によるサーキットブレーカーとレート制限
- HTTP/2対応のhttpxクライアント
- カスタムポリシーによる高度なルーティング

### 📦 含まれるコンポーネント

- Python 3.11+ サポート
- Bicepテンプレート (インフラデプロイ自動化)
- 負荷テストツール
- 包括的なドキュメント

### 🔧 セットアップ

詳細は [README.md](README.md) を参照してください。

```bash
# クローン
git clone https://github.com/YOUR_USERNAME/ocr-demo-w-sdk.git

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .envを編集してAzureリソース情報を設定
```

### 📚 ドキュメント

- [SDK Migration Guide](docs/SDK_MIGRATION.md) - httpx → Azure SDK移行ガイド
- [Scaling Strategy](docs/SCALING_STRATEGY.md) - 2000リクエスト/分対応戦略
- [Best Practices](docs/BEST_PRACTICES.md) - ベストプラクティス
- [Contributing Guide](CONTRIBUTING.md) - コントリビューションガイド
- [Security Policy](SECURITY.md) - セキュリティポリシー

### ⚠️ 既知の制限事項

- Scenario Bは、APIM Developerティアで動作確認 (Premiumティアでの検証推奨)
- 単体テスト (pytest) は今後追加予定
- Windows環境での動作は未検証

### 🙏 謝辞

Azure Computer Vision SDKチームと、オープンソースコミュニティに感謝します。

---

**Full Changelog**: https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/commits/v1.0.0
```

---

## 🚢 GitHubへのアップロード手順

### 1. ローカルGitリポジトリ初期化

```bash
cd /Users/kyoheim/src/ocr-demo-w-sdk

# Gitリポジトリ初期化 (まだの場合)
git init

# すべてのファイルをステージング (.gitignoreが適用される)
git add .

# 初回コミット
git commit -m "feat: initial release with Azure SDK migration

- Migrate Scenario A from httpx to Azure SDK
- Add comprehensive documentation
- Add CI/CD with GitHub Actions
- Add LICENSE, CONTRIBUTING.md, SECURITY.md
- Clean up hardcoded secrets
"
```

### 2. GitHubリポジトリ作成

```bash
# GitHub CLIを使用 (推奨)
gh repo create ocr-demo-w-sdk --public --source=. --remote=origin

# または手動でGitHub Webから作成し、リモート追加
git remote add origin https://github.com/YOUR_USERNAME/ocr-demo-w-sdk.git
```

### 3. プッシュ

```bash
# メインブランチにプッシュ
git branch -M main
git push -u origin main
```

### 4. リリース作成

```bash
# GitHub CLIでリリース作成
gh release create v1.0.0 \
  --title "v1.0.0 - Initial Release with Azure SDK" \
  --notes-file RELEASE_NOTES.md

# または GitHub Webの "Releases" → "Create a new release"
```

---

## ✅ 最終確認項目

アップロード後、以下を確認:

- [ ] README.mdがGitHubで正しく表示される
- [ ] バッジ (License, Python, Azure) が機能している
- [ ] ドキュメントリンクが正常に動作
- [ ] GitHub Actions CIが自動実行される
- [ ] Issues/Discussions が有効化されている
- [ ] SECURITY.mdが "Security" タブに表示される
- [ ] CONTRIBUTINGリンクがPRテンプレートで表示される

---

## 📣 公開後のアクション

- [ ] Twitterでリリース告知 (オプション)
- [ ] LinkedInで共有 (オプション)
- [ ] Azure Tech Communityで共有 (オプション)
- [ ] ブログ記事作成 (オプション)

---

**準備完了！** 🎊

このチェックリストのすべての項目が完了したら、GitHubに公開する準備が整っています！
