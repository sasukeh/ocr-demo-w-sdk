# Japan East Computer Vision デプロイメント手順

このガイドでは、Japan Eastリージョンに3つのComputer Visionエンドポイントをデプロイして、同一リージョン内での負荷分散・フォールバック機能をテストする手順を説明します。

## 📋 概要

- **目的**: 同一リージョン内での負荷分散とフォールバック効果の測定
- **リージョン**: Japan East (japaneast)
- **エンドポイント数**: 3個 (Primary, Secondary, Tertiary)
- **テストシナリオ**: 高負荷時の自動負荷分散とフォールバック

## 🚀 デプロイメント手順

### 1. 前提条件

- Azure CLI または Azure PowerShell がインストール済み
- Azureにログイン済み
- 適切なサブスクリプション権限（Computer Visionリソース作成権限）

#### Azure CLI の場合
```bash
# Azure CLI のインストール確認
az --version

# Azureにログイン
az login

# サブスクリプション確認
az account show
```

#### Azure PowerShell の場合
```powershell
# Azure PowerShell モジュール確認
Get-Module Az -ListAvailable

# Azureにログイン
Connect-AzAccount

# サブスクリプション確認
Get-AzContext
```

### 2. デプロイメント実行

#### 🐧 Linux/macOS (Bash)

```bash
# リポジトリのinfrastructureディレクトリに移動
cd infrastructure/

# デプロイメント実行
./deploy-japan-east.sh

# オプション付きで実行する場合
./deploy-japan-east.sh --subscription-id YOUR_SUBSCRIPTION_ID --force

# What-If モード（デプロイ確認のみ）
./deploy-japan-east.sh --what-if
```

#### 🪟 Windows (PowerShell)

```powershell
# リポジトリのinfrastructureディレクトリに移動
cd infrastructure\

# デプロイメント実行
.\deploy-japan-east.ps1

# オプション付きで実行する場合
.\deploy-japan-east.ps1 -SubscriptionId "YOUR_SUBSCRIPTION_ID" -Force

# What-If モード（デプロイ確認のみ）
.\deploy-japan-east.ps1 -WhatIf
```

### 3. APIキーの取得

デプロイメント完了後、各Computer VisionリソースのAPIキーを取得します：

```bash
# リソースグループ名（デフォルト: rg-ocr-demo-japan-east）
RESOURCE_GROUP="rg-ocr-demo-japan-east"

# 各エンドポイントのキー取得
az cognitiveservices account keys list \
    --name cv-ocr-demo-je-primary \
    --resource-group $RESOURCE_GROUP \
    --query key1 -o tsv

az cognitiveservices account keys list \
    --name cv-ocr-demo-je-secondary \
    --resource-group $RESOURCE_GROUP \
    --query key1 -o tsv

az cognitiveservices account keys list \
    --name cv-ocr-demo-je-tertiary \
    --resource-group $RESOURCE_GROUP \
    --query key1 -o tsv
```

### 4. 環境変数設定

1. 生成された `.env.japan-east` ファイルを確認
2. `OCR_KEYS` に上記で取得したAPIキーを設定

```bash
# 環境変数ファイル編集
vi .env.japan-east

# または
code .env.japan-east
```

設定例：
```bash
OCR_KEYS=your_primary_key_here,your_secondary_key_here,your_tertiary_key_here
```

## 🧪 テスト実行

### 基本的な動作確認

```bash
# 単一画像でのOCRテスト
python scripts/ocr_reader.py \
    --image ./samples/handwritten_text.jpg \
    --env-file .env.japan-east

# 複数エンドポイントの動作確認
python scripts/ocr_reader.py \
    --image ./samples/printed_text.jpg \
    --env-file .env.japan-east \
    --format rich
```

### 負荷分散・フォールバックテスト

```bash
# Japan East 専用負荷テスト（5分間、10並行）
python scripts/japan_east_load_test.py \
    --env-file .env.japan-east \
    --concurrency 10 \
    --duration 300

# より高負荷なテスト（20並行、10分間）
python scripts/japan_east_load_test.py \
    --env-file .env.japan-east \
    --concurrency 20 \
    --duration 600 \
    --output results_japan_east.json
```

## 📊 期待される結果

### 正常時
- Primary エンドポイントが主に使用される
- 低レイテンシーで高いスループット
- フォールバック発生は最小限

### 高負荷時
- 自動的にSecondary、Tertiaryエンドポイントに負荷分散
- レイテンシー閾値超過時のフォールバック
- 全体的なパフォーマンス向上

### 障害シミュレーション時
- 障害エンドポイントの自動隔離
- 健全エンドポイントへの迅速な切り替え
- サービス継続性の確保

## 🔧 設定調整

### フォールバック閾値の調整

`.env.japan-east` で以下の設定を調整できます：

```bash
# 単発リクエストの閾値 (ms)
FALLBACK_SINGLE_MS=2000

# EWMA P95レイテンシーの閾値 (ms) 
EWMA_P95_MS=2500

# EWMA重み係数
EWMA_ALPHA=0.2

# クールダウン期間 (秒)
COOLDOWN_SEC=60
```

### 負荷テスト設定

```bash
# 負荷テストの並行性
LOAD_TEST_CONCURRENCY=10

# 負荷テストの持続時間 (秒)
LOAD_TEST_DURATION=300

# 負荷テストの対象画像
LOAD_TEST_IMAGE_PATH=./samples/handwritten_text.jpg
```

## 🗑️ リソース削除

テスト完了後、リソースを削除する場合：

```bash
# リソースグループ全体を削除
az group delete --name rg-ocr-demo-japan-east --yes --no-wait

# 確認
az group show --name rg-ocr-demo-japan-east
```

## 🚨 トラブルシューティング

### デプロイメント失敗

1. **権限不足**: Computer Vision リソース作成権限を確認
2. **リージョン制限**: Japan East でのComputer Vision利用可否を確認
3. **クォータ不足**: サブスクリプションのクォータ制限を確認

### テスト失敗

1. **APIキー未設定**: `.env.japan-east` のOCR_KEYS設定を確認
2. **ネットワーク問題**: Azure接続とレイテンシーを確認
3. **画像ファイル**: テスト画像の存在と形式を確認

### パフォーマンス問題

1. **閾値設定**: フォールバック閾値の見直し
2. **並行数調整**: 負荷テストの並行数を調整
3. **画像サイズ**: テスト画像のサイズを最適化

## 📞 サポート

問題や質問がある場合は、以下を参照してください：

- [Azure Computer Vision ドキュメント](https://docs.microsoft.com/azure/cognitive-services/computer-vision/)
- [Azure CLI リファレンス](https://docs.microsoft.com/cli/azure/)
- プロジェクトの他のREADMEファイル