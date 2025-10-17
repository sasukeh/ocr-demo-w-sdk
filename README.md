# Azure Computer Vision OCR - レイテンシー・フォールバック・負荷分散デモ

Azure Computer Vision OCR サービスのレイテンシー最適化と 429 エラー (Rate Limiting) 緩和のためのフォールバック・負荷分散システムの包括的なデモンストレーションです。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Azure](https://img.shields.io/badge/Azure-Computer%20Vision-0078D4)](https://azure.microsoft.com/services/cognitive-services/computer-vision/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub](https://img.shields.io/badge/GitHub-sasukeh%2Focr--demo--w--sdk-181717?logo=github)](https://github.com/sasukeh/ocr-demo-w-sdk)

> **🎉 SDK Migration完了**: このプロジェクトは、httpxベースの実装からAzure公式SDK (azure-ai-vision-imageanalysis) に移行しました。詳細は [SDK_MIGRATION.md](docs/SDK_MIGRATION.md) を参照してください。

---

## 📋 目次

- [プロジェクト概要](#-プロジェクト概要)
- [アーキテクチャ](#️-アーキテクチャ)
- [主な機能](#-主な機能)
- [クイックスタート](#-クイックスタート)
- [シナリオ別実行方法](#-シナリオ別実行方法)
- [デプロイメント方法](#-デプロイメント方法)
- [ドキュメント](#-ドキュメント)
- [プロジェクト構造](#-プロジェクト構造)
- [トラブルシューティング](#-トラブルシューティング)

---

## 🎯 プロジェクト概要

本システムでは、Azure Computer Vision OCR の 2 つのアプローチを比較・検証できます:

### Scenario A: クライアント側フォールバック・負荷分散 (Azure SDK) ✅

**実装方式:**
- **Azure Computer Vision SDK** (`azure-ai-vision-imageanalysis`) を使用
- 公式SDKによる安定した実装と型安全性
- エラーハンドリングの簡略化

**特徴:**
- 複数の Computer Vision エンドポイント間での自動負荷分散
- レイテンシーベースのインテリジェント・エンドポイント選択
- 指数バックオフによる 429 エラー対応
- 動的エンドポイント健全性監視

**適用シーン:**
- 軽量なアプリケーション
- APIM を使わないシンプルなアーキテクチャ
- クライアント側で完結する負荷分散
- 直接Computer Visionエンドポイントにアクセス可能な環境

### Scenario B: APIM (API Management) サーキットブレーカー (HTTP Client) ✅

**実装方式:**
- **httpx** HTTP クライアントを使用
- APIMカスタムヘッダー・ポリシーとの柔軟な連携

**特徴:**
- Azure API Management を使用した集約型フォールバック
- 一元化されたレート制限・サーキットブレーカー機能
- Image Analysis v4 API 対応
- 高度なサーキットブレーカーポリシー (5 回失敗で 60 秒 OPEN)
- APIMカスタムヘッダー（`X-Served-By-Backend` など）による詳細な診断

**適用シーン:**
- エンタープライズアプリケーション
- 集中管理が必要なシステム
- 複数のクライアントからのアクセス
- APIMのカスタムポリシーを活用したい環境

> **💡 実装の使い分け:**
> - **シナリオA**: Azure SDKを活用し、直接エンドポイントにアクセス。シンプルで保守性の高い実装。
> - **シナリオB**: APIMのカスタムゲートウェイ経由でアクセスするため、HTTPクライアントで柔軟に実装。APIMポリシーとの連携が必要。

---

## 🏗️ アーキテクチャ

### Scenario A: クライアント側実装 (Azure SDK)

```
┌─────────────────────────────┐
│   クライアント                │
│   (Azure SDK使用)            │
└──────┬──────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ エンドポイントプール           │
│ - 負荷分散                    │
│ - 健全性監視                  │
│ - ペナルティ管理              │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Computer Vision API          │
│ ├─ je-primary   (Japan East) │
│ ├─ je-secondary (Japan East) │
│ └─ je-tertiary  (Japan East) │
└──────────────────────────────┘
```

### Scenario B: APIM 実装 (HTTP Client)

```
┌─────────────────────────────┐
│   クライアント                │
│   (httpx使用)                │
└──────┬──────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Azure API Management         │
│ ├─ リトライポリシー (429/5xx) │
│ ├─ サーキットブレーカー        │
│ ├─ カスタムヘッダー追加        │
│ └─ 負荷分散                   │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Computer Vision API          │
│ ├─ cv-primary   (CLOSED/OPEN)│
│ ├─ cv-secondary (CLOSED/OPEN)│
│ └─ cv-tertiary  (CLOSED/OPEN)│
└──────────────────────────────┘
```

---

## 🚀 主な機能

### 高度なフォールバック機能
- **レイテンシー監視**: 各エンドポイントのレスポンス時間を EWMA (指数移動平均) で追跡
- **動的ペナルティ**: 遅延やエラーが発生したエンドポイントの一時的隔離
- **指数バックオフ**: リトライ時の段階的遅延増加 (2^n, 最大 10 秒)
- **健全性回復**: ペナルティエンドポイントの自動復帰 (60 秒)
- **サーキットブレーカー**: 5 回連続失敗で 60 秒間 OPEN、自動回復

### 画像処理最適化
- **自動リサイズ**: 大きな画像の自動最適化 (4MB 制限対応)
- **アスペクト比保持**: 画質を保ったままファイルサイズ削減
- **メモリ効率**: ストリーミング処理による低メモリフットプリント

### 包括的監視・分析
- **詳細メトリクス**: レイテンシー、成功率、エンドポイント分散統計
- **リアルタイム表示**: Rich UI による美しいプログレス表示
- **結果出力**: JSON 形式での詳細レポート生成
- **診断設定**: Log Analytics による集中ログ管理

### Azure ベストプラクティス実装
- **IaC (Infrastructure as Code)**: Bicep テンプレート
- **デュアルレイヤーリトライ**: APIM + クライアント側
- **診断設定**: Log Analytics (30 日保持)
- **コスト最適化タグ**: リソース追跡・分析
- **CI/CD 自動化**: GitHub Actions ワークフロー

---

## ⚡ クイックスタート

### 前提条件

- **Python**: 3.10 以上
- **Azure CLI**: 最新版
- **Azure サブスクリプション**: Computer Vision リソース作成権限

### 1. リポジトリのクローンとセットアップ

```bash
# リポジトリクローン
git clone <repository-url>
cd ocr-demo

# 仮想環境作成・アクティベート
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 依存関係インストール
pip install -r requirements.txt
```

### 2. 環境設定ファイルの準備

#### オプション A: テンプレートからコピー (推奨)

```bash
# Scenario A 用
cp .env.example .env.scenario_a
# エディタで .env.scenario_a を編集し、Azure リソース情報を入力

# Scenario B 用
cp .env.example .env.apim
# エディタで .env.apim を編集し、APIM 情報を入力
```

#### オプション B: Azure リソースを自動デプロイ

詳細は [デプロイメント方法](#-デプロイメント方法) を参照してください。

### 3. クイックテスト

#### Scenario A: クライアント側負荷分散

```bash
# 100 リクエスト、5 並行
python scenario_a_client/load_test.py \
  --images test_images \
  --duration 60 \
  --workers 5
```

#### Scenario B: APIM 経由

```bash
# 100 リクエスト、5 ワーカー
python scenario_b_apim/load_test_count.py \
  --total-requests 100 \
  --workers 5
```

---

## 🎮 シナリオ別実行方法

### Scenario A: クライアント側フォールバック

#### 基本的な負荷テスト

```bash
# 軽負荷: 5 並行、60 秒
python scenario_a_client/load_test.py \
  --images test_images \
  --duration 60 \
  --workers 5

# 中負荷: 10 並行、120 秒
python scenario_a_client/load_test.py \
  --images test_images \
  --duration 120 \
  --workers 10

# 高負荷: 15 並行、300 秒
python scenario_a_client/load_test.py \
  --images test_images \
  --duration 300 \
  --workers 15
```

#### カスタム設定

```bash
# 特定の画像ディレクトリを使用
python scenario_a_client/load_test.py \
  --images ./my_test_images \
  --duration 120 \
  --workers 10

# 結果を CSV で出力
python scenario_a_client/load_test.py \
  --images test_images \
  --duration 60 \
  --workers 5 \
  --output results.csv
```

#### 期待される結果

```
📊 Scenario A 負荷テスト結果
════════════════════════════════
              総合統計
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ メトリクス       ┃             値 ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ 総リクエスト数   │            280 │
│ 成功             │    277 (98.9%) │
│ 失敗             │       3 (1.1%) │
│ 実行時間         │        51.76秒 │
│ スループット     │     5.41 req/s │
│ 平均レイテンシー │         1175ms │
└──────────────────┴────────────────┘

🌐 エンドポイント使用状況:
  • je-primary: 65 回 (23.2%)
  • je-secondary: 114 回 (40.7%)
  • je-tertiary: 98 回 (35.0%)
```

### Scenario B: APIM サーキットブレーカー

#### 基本的な負荷テスト

```bash
# 軽負荷: 100 リクエスト、5 ワーカー
python scenario_b_apim/load_test_count.py \
  --total-requests 100 \
  --workers 5

# 中負荷: 500 リクエスト、10 ワーカー
python scenario_b_apim/load_test_count.py \
  --total-requests 500 \
  --workers 10

# 高負荷: 1000 リクエスト、5 ワーカー (推奨)
python scenario_b_apim/load_test_count.py \
  --total-requests 1000 \
  --workers 5
```

#### サーキットブレーカー動作確認

```bash
# 高負荷でサーキットブレーカーをテスト
python scenario_b_apim/load_test_count.py \
  --total-requests 1000 \
  --workers 20

# レスポンスヘッダーでサーキット状態を確認
# X-Circuit-State-Primary: CLOSED/OPEN
# X-Circuit-State-Secondary: CLOSED/OPEN
# X-Circuit-State-Tertiary: CLOSED/OPEN
```

#### 期待される結果

```
╭───────────────────────────╮
│ Scenario B 負荷テスト開始 │
│ 総リクエスト数: 1000      │
│ 最大並行数: 5             │
╰───────────────────────────╯

  リクエスト実行中... ━━━━━━━━━━━━━━━━━━━━ 100% 1000/1000

============================================================
📊 Scenario B 負荷テスト結果
============================================================
              総合統計
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ メトリクス       ┃             値 ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ 総リクエスト数   │          1,000 │
│ 成功             │ 1,000 (100.0%) │
│ 失敗             │              0 │
│ 実行時間         │        82.00秒 │
│ スループット     │    12.19 req/s │
│ 平均レイテンシー │          398ms │
└──────────────────┴────────────────┘

🏠 バックエンド使用状況:
  • cv-primary-direct: 1,000回 (100.0%)
```

### シナリオ比較

```bash
# 両方のシナリオを実行して結果を比較
./compare_scenarios.sh
```

**比較のポイント:**

| 項目 | Scenario A | Scenario B |
|------|-----------|-----------|
| **成功率** | 98-99% | 99-100% |
| **平均レイテンシー** | 1000-1500ms | 400-600ms |
| **スループット** | 5-8 req/s | 10-15 req/s |
| **429 エラー対応** | クライアント側リトライ | APIM + クライアント |
| **サーキットブレーカー** | ペナルティ機能 | 高度なサーキットブレーカー |
| **運用複雑度** | 低 | 中 (APIM 必要) |

---

## 🚀 デプロイメント方法

### 方法 1: ローカル環境変数 + スクリプト実行 (推奨)

#### Step 1: 環境変数ファイルの準備

```bash
# テンプレートをコピー
cp .env.example .env.scenario_a
cp .env.example .env.apim
```

#### Step 2: 環境変数を編集

**`.env.scenario_a`** (Scenario A 用):
```bash
CV_PRIMARY_ENDPOINT=https://cv-ocr-demo-je-primary.cognitiveservices.azure.com/
CV_PRIMARY_KEY=your-primary-key-here
CV_SECONDARY_ENDPOINT=https://cv-ocr-demo-je-secondary.cognitiveservices.azure.com/
CV_SECONDARY_KEY=your-secondary-key-here
CV_TERTIARY_ENDPOINT=https://cv-ocr-demo-je-tertiary.cognitiveservices.azure.com/
CV_TERTIARY_KEY=your-tertiary-key-here
```

**`.env.apim`** (Scenario B 用):
```bash
APIM_GATEWAY_URL=https://ocr-demo-apim-dev.azure-api.net
APIM_SUBSCRIPTION_KEY=your-apim-subscription-key
APIM_OCR_ENDPOINT=/computer-vision/imageanalysis:analyze?api-version=2024-02-01&features=read
```

#### Step 3: Azure リソースをデプロイ

```bash
# Scenario A: Computer Vision リソース x3
cd infrastructure
./deploy-japan-east.sh

# Scenario B: APIM + Computer Vision
cd infrastructure/apim
az deployment group create \
  --resource-group rg-ocr-demo \
  --template-file apim-computer-vision.bicep \
  --parameters publisherEmail=your@email.com
```

#### Step 4: テスト実行

```bash
# Scenario A
python scenario_a_client/load_test.py --images test_images --duration 60 --workers 5

# Scenario B
python scenario_b_apim/load_test_count.py --total-requests 100 --workers 5
```

---

### 方法 2: GitHub Actions (CI/CD)

GitHub Actions を使った自動デプロイとテストの実行方法です。

#### ワークフロー一覧

| ワークフロー | 説明 | トリガー |
|------------|------|---------|
| **Deploy Azure Infrastructure** | Azure リソースのデプロイ | 手動実行 |
| **OCR Load Testing** | 負荷テストの実行 | 手動 / スケジュール / Push |

---

#### A. インフラストラクチャのデプロイ

##### Step 1: Azure 認証情報の設定

リポジトリの Settings → Secrets and variables → Actions で以下を設定:

**Azure 認証用 (デプロイに必須):**

1. Azure でサービスプリンシパルを作成:
   ```bash
   az ad sp create-for-rbac \
     --name "github-actions-ocr-demo" \
     --role contributor \
     --scopes /subscriptions/{subscription-id} \
     --sdk-auth
   ```

2. 出力された JSON を GitHub Secret に保存:
   - Secret 名: `AZURE_CREDENTIALS`
   - 値: JSON 全体をコピー

3. サブスクリプション ID も追加:
   - Secret 名: `AZURE_SUBSCRIPTION_ID`
   - 値: サブスクリプション ID (GUID)

##### Step 2: デプロイワークフローの実行

1. GitHub リポジトリの **Actions** タブを開く
2. **"Deploy Azure Infrastructure"** ワークフローを選択
3. **"Run workflow"** をクリック
4. パラメータを設定:
   - **scenario**: `scenario-a` / `scenario-b` / `both` (デフォルト: `both`)
   - **environment**: `dev` / `prod` (デフォルト: `dev`)
   - **resource_group**: リソースグループ名 (空欄の場合は自動生成)
   - **region**: `japaneast` / `eastus` / `westeurope` (デフォルト: `japaneast`)
5. **"Run workflow"** を実行

##### Step 3: デプロイ結果の確認

- **Summary タブ**: デプロイされたリソースの概要
- **Artifacts**: 
  - `scenario-a-outputs` - Scenario A のデプロイ結果
  - `scenario-b-outputs` - Scenario B のデプロイ結果
  - `deployment-env-template` - 環境変数テンプレート

##### Scenario B の追加設定

APIM のデプロイ後、手動で以下を実施:

1. **Named Values の設定** (Azure Portal)
   - `cv-primary-endpoint`, `cv-primary-key`
   - `cv-secondary-endpoint`, `cv-secondary-key`
   - `cv-tertiary-endpoint`, `cv-tertiary-key`

2. **Circuit Breaker Policy のアップロード**
   ```bash
   cd infrastructure/apim
   ./setup-apim-api.sh
   ```

---

#### B. 負荷テストの実行

##### Step 1: テスト用 GitHub Secrets の設定

リポジトリの Settings → Secrets and variables → Actions で以下を設定:

**Scenario A 用:**
- `CV_PRIMARY_ENDPOINT`
- `CV_PRIMARY_KEY`
- `CV_SECONDARY_ENDPOINT`
- `CV_SECONDARY_KEY`
- `CV_TERTIARY_ENDPOINT`
- `CV_TERTIARY_KEY`

**Scenario B 用:**
- `APIM_GATEWAY_URL`
- `APIM_SUBSCRIPTION_KEY`
- `APIM_OCR_ENDPOINT`

##### Step 2: 負荷テストワークフローの実行

1. GitHub リポジトリの **Actions** タブを開く
2. **"OCR Load Testing"** ワークフローを選択
3. **"Run workflow"** をクリック
4. パラメータを設定:
   - **scenario**: `scenario-a` / `scenario-b` / `both`
   - **total_requests**: `1000` (デフォルト)
   - **workers**: `5` (デフォルト)
5. **"Run workflow"** を実行

##### Step 3: 結果の確認

- ワークフロー実行ログでリアルタイム結果を確認
- 完了後、Artifacts から結果 JSON をダウンロード
- Summary タブで成功率などの概要を確認

##### 自動スケジュール実行

デフォルトで毎日 9:00 JST (00:00 UTC) に自動実行されます。

```yaml
# .github/workflows/load-test.yml
schedule:
  - cron: '0 0 * * *'  # 毎日 9:00 JST
```

---

#### GitHub Actions の利点

| 項目 | メリット |
|------|---------|
| **自動化** | スケジュール実行で定期的な監視が可能 |
| **チーム共有** | 全メンバーが同じ環境でテスト可能 |
| **履歴管理** | すべてのデプロイとテスト結果が記録される |
| **CI/CD統合** | コード変更時の自動テストが可能 |
| **セキュリティ** | 認証情報を GitHub Secrets で安全に管理 |

---

## 📚 ドキュメント

### 主要ドキュメント

| ドキュメント | 説明 |
|------------|------|
| **[BEST_PRACTICES.md](docs/BEST_PRACTICES.md)** | Azure ベストプラクティスの詳細ガイド<br>- 実装済みベストプラクティス詳細<br>- 将来的な推奨事項 (Key Vault, App Insights, マネージドID, マルチリージョン)<br>- コスト見積もり<br>- セキュリティチェックリスト |
| **[IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md)** | 実装内容のサマリー<br>- 診断設定<br>- サーキットブレーカー<br>- コスト最適化タグ<br>- 負荷テスト自動化 |
| **[receipt_guide.md](docs/receipt_guide.md)** | レシート OCR の実装ガイド<br>- レシート特有の最適化<br>- フィールド抽出方法 |

### クイックリンク

- **[Azure ベストプラクティス実装状況](#-ベストプラクティス実装状況)** - 実装済み機能とスコア
- **[トラブルシューティング](#-トラブルシューティング)** - よくある問題と解決方法
- **[プロジェクト構造](#-プロジェクト構造)** - ファイル構成の詳細

---

## 📊 ベストプラクティス実装状況

### ✅ 実装済み (スコア: 92/100)
- リクエスト間隔の調整
- エンドポイント数の増加検討

#### 4. 画像処理エラー
```bash
# 画像フォーマット・サイズ確認
python scripts/ocr_reader.py --image problem_image.jpg --verbose
```

## 🔮 今後の拡張予定

### Phase 2: APIM統合
- Azure API Management サーキットブレーカー実装
- 集約型レート制限・監視
- Scenario A vs Scenario B 性能比較

### Phase 3: マルチリージョン対応
- 地理的分散エンドポイント
- レイテンシーベース地域選択
- 災害復旧・高可用性対応

### Phase 4: 高度な分析機能
- Machine Learning ベース予測
- 動的負荷調整
- コスト最適化分析

---

## � ベストプラクティス実装状況

### ✅ 実装済み (スコア: 92/100)

| カテゴリ | 実装内容 | スコア |
|---------|---------|--------|
| **IaC** | Bicep テンプレート、モジュール化 | 100% |
| **エラーハンドリング** | デュアルレイヤーリトライ (APIM + クライアント) | 100% |
| **診断・ログ** | Log Analytics (30 日保持) | 100% |
| **サーキットブレーカー** | キャッシュベース状態管理 | 100% |
| **コスト最適化** | リソースタグによる追跡・分析 | 100% |
| **CI/CD** | GitHub Actions 自動テスト | 100% |
| **セキュリティ** | API キー管理 (Key Vault 推奨) | 75% |
| **高可用性** | 単一リージョン (マルチリージョン推奨) | 70% |

### 📄 推奨事項 (将来拡張)

以下は [`docs/BEST_PRACTICES.md`](docs/BEST_PRACTICES.md) に詳細記載:

- **Key Vault 統合**: API キーの一元管理とローテーション
- **Application Insights**: 分散トレーシングとリアルタイムメトリクス
- **マネージドID**: ゼロトラストセキュリティモデル
- **マルチリージョン**: 災害復旧と高可用性

詳細は **[ベストプラクティスガイド](docs/BEST_PRACTICES.md)** を参照してください。

---

## 📁 プロジェクト構造

```
ocr-demo/
├── .github/
│   └── workflows/
│       └── load-test.yml           # GitHub Actions ワークフロー
│
├── docs/                           # ドキュメント
│   ├── BEST_PRACTICES.md          # Azure ベストプラクティス詳細
│   ├── IMPLEMENTATION_SUMMARY.md  # 実装サマリー
│   └── receipt_guide.md           # レシート OCR ガイド
│
├── infrastructure/                 # Azure インフラストラクチャ (IaC)
│   ├── apim/                      # APIM 関連
│   │   ├── apim-computer-vision.bicep
│   │   ├── deploy-apim.sh
│   │   └── policies/
│   │       └── advanced-circuit-breaker-policy.xml
│   ├── modules/
│   │   └── computer-vision.bicep  # Computer Vision モジュール
│   ├── japan-computer-vision.bicep
│   └── deploy-japan-east.sh       # 自動デプロイスクリプト
│
├── scenario_a_client/             # Scenario A: クライアント側実装
│   ├── client.py                  # メインクライアント
│   ├── endpoints.py               # エンドポイント管理
│   ├── fallback_policy.py         # フォールバックロジック
│   ├── image_utils.py             # 画像最適化
│   ├── metrics.py                 # メトリクス収集
│   └── load_test.py               # 負荷テストツール
│
├── scenario_b_apim/               # Scenario B: APIM 実装
│   ├── apim_client.py             # APIM クライアント
│   ├── load_test_count.py         # 負荷テストツール (リクエスト数指定)
│   ├── load_tester.py             # 負荷テストコア
│   └── metrics.py                 # メトリクス収集
│
├── test_images/                   # テスト画像ディレクトリ
│
├── .env.example                   # 環境変数テンプレート
├── .gitignore                     # Git 除外設定
├── requirements.txt               # Python 依存関係
├── compare_scenarios.sh           # シナリオ比較スクリプト
└── README.md                      # 本ファイル
```

---

## 🚨 トラブルシューティング

### よくある問題と解決方法

#### 1. API キー関連エラー

**エラーメッセージ:**
```
401 Unauthorized: Access denied due to invalid subscription key
```

**解決方法:**
```bash
# Azure ポータルで API キーを確認
az cognitiveservices account keys list \
  --name cv-ocr-demo-je-primary \
  --resource-group rg-ocr-demo

# .env ファイルを更新
# CV_PRIMARY_KEY=<新しいキー>
```

#### 2. 429 エラー頻発

**エラーメッセージ:**
```
429 Too Many Requests: Rate limit exceeded
```

**解決方法:**
- **Scenario A**: 並行数を削減 (`--workers 5` → `--workers 3`)
- **Scenario B**: ワーカー数を削減 (`--workers 10` → `--workers 5`)
- Computer Vision の SKU を S1 から S2/S3 にアップグレード

#### 3. 高レイテンシー

**症状:**
- 平均レイテンシーが 2000ms を超える
- P95 レイテンシーが 5000ms を超える

**解決方法:**
```bash
# タイムアウト値を増加
export COMPUTER_VISION_TIMEOUT_SEC=15.0

# ペナルティ閾値を調整 (.env ファイル)
FALLBACK_SINGLE_THRESHOLD_MS=3000
FALLBACK_P95_THRESHOLD_MS=4000
```

#### 4. 画像サイズエラー

**エラーメッセージ:**
```
Request entity too large
```

**解決方法:**
- 自動リサイズが有効になっているか確認
- `MAX_IMAGE_SIZE_MB=4.0` が設定されているか確認
- 手動でリサイズ: `python scenario_a_client/image_utils.py --resize <image>`

#### 5. APIM 接続エラー (Scenario B)

**エラーメッセージ:**
```
Connection refused: APIM_GATEWAY_URL not reachable
```

**解決方法:**
```bash
# APIM エンドポイントを確認
az apim show \
  --name ocr-demo-apim-dev \
  --resource-group rg-ocr-demo \
  --query "gatewayUrl" -o tsv

# .env.apim を更新
APIM_GATEWAY_URL=https://<your-apim>.azure-api.net

# APIM サブスクリプションキーを確認
az apim subscription show \
  --resource-group rg-ocr-demo \
  --service-name ocr-demo-apim-dev \
  --sid master
```

#### 6. GitHub Actions 実行エラー

**症状:**
- ワークフローが失敗する
- シークレットが見つからない

**解決方法:**
1. リポジトリの **Settings** → **Secrets and variables** → **Actions** を開く
2. 必要なシークレットが全て設定されているか確認:
   - `CV_PRIMARY_ENDPOINT`
   - `CV_PRIMARY_KEY`
   - `APIM_GATEWAY_URL`
   - `APIM_SUBSCRIPTION_KEY`
   - その他
3. シークレット名が正確か確認 (大文字小文字を区別)

---

## 🤝 貢献

本プロジェクトへの貢献を歓迎します！

### 貢献方法

1. リポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチをプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

### コーディング規約

- **Python**: PEP 8 に準拠
- **Bicep**: Azure の推奨スタイルガイドに従う
- **コミットメッセージ**: [Conventional Commits](https://www.conventionalcommits.org/) 形式

---

## 📚 参考リンク

- [Azure Computer Vision ドキュメント](https://learn.microsoft.com/azure/cognitive-services/computer-vision/)
- [Azure API Management ドキュメント](https://learn.microsoft.com/azure/api-management/)
- [Bicep ドキュメント](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [本プロジェクトのベストプラクティスガイド](docs/BEST_PRACTICES.md)

---

## 📝 ライセンス

このプロジェクトは MIT ライセンスのもとで公開されています。

---

<div align="center">

**💡 このデモを通じて、Azure Computer Vision OCR サービスの性能最適化と信頼性向上のベストプラクティスを実際に体験できます。**

**⭐ このプロジェクトが役立った場合は、スターをつけてください！⭐**

Made with ❤️ using Azure Computer Vision

**Last Updated:** 2025-10-16 | **Version:** 2.0

</div>
