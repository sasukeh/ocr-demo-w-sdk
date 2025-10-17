#!/bin/bash
# シナリオA用のAzureリソースをデプロイするBashスクリプト

set -e  # エラー時に停止

# パラメータのデフォルト値
SUBSCRIPTION_ID=""
RESOURCE_GROUP_NAME="rg-ocr-demo-scenario-a"
LOCATION="eastus"
PROJECT_NAME="ocr-demo-a"
COGNITIVE_SERVICES_SKU="S1"

# 引数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --subscription)
            SUBSCRIPTION_ID="$2"
            shift 2
            ;;
        --resource-group)
            RESOURCE_GROUP_NAME="$2"
            shift 2
            ;;
        --location)
            LOCATION="$2"
            shift 2
            ;;
        --project-name)
            PROJECT_NAME="$2"
            shift 2
            ;;
        --sku)
            COGNITIVE_SERVICES_SKU="$2"
            shift 2
            ;;
        -h|--help)
            echo "使用法: $0 [オプション]"
            echo "オプション:"
            echo "  --subscription SUBSCRIPTION_ID    サブスクリプションID"
            echo "  --resource-group GROUP_NAME       リソースグループ名"
            echo "  --location LOCATION               リージョン"
            echo "  --project-name PROJECT_NAME       プロジェクト名"
            echo "  --sku SKU                        Cognitive Services SKU (S0/S1)"
            exit 0
            ;;
        *)
            echo "不明なオプション: $1"
            exit 1
            ;;
    esac
done

echo "=== シナリオA用Azureリソースデプロイ ==="

# サブスクリプション設定
if [[ -n "$SUBSCRIPTION_ID" ]]; then
    echo "サブスクリプション設定: $SUBSCRIPTION_ID"
    az account set --subscription "$SUBSCRIPTION_ID"
fi

# 現在のサブスクリプション確認
CURRENT_SUB=$(az account show --query "name" -o tsv)
echo "使用中のサブスクリプション: $CURRENT_SUB"

# リソースグループ作成
echo "リソースグループ作成: $RESOURCE_GROUP_NAME ($LOCATION)"
az group create --name "$RESOURCE_GROUP_NAME" --location "$LOCATION"

# Computer Vision サービス用の複数リージョン
LOCATIONS=("eastus" "japaneast" "westeurope")
ENDPOINTS=()
KEYS=()

for LOC in "${LOCATIONS[@]}"; do
    SERVICE_NAME="$PROJECT_NAME-cv-$LOC"
    
    echo "Computer Vision サービス作成: $SERVICE_NAME ($LOC)"
    
    az cognitiveservices account create \
        --name "$SERVICE_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --kind ComputerVision \
        --sku "$COGNITIVE_SERVICES_SKU" \
        --location "$LOC" \
        --custom-domain "$SERVICE_NAME" \
        --tags Project="$PROJECT_NAME" Scenario=A Environment=Demo Region="$LOC"
    
    # エンドポイントとキー取得
    ENDPOINT=$(az cognitiveservices account show \
        --name "$SERVICE_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --query "properties.endpoint" -o tsv)
    
    KEY=$(az cognitiveservices account keys list \
        --name "$SERVICE_NAME" \
        --resource-group "$RESOURCE_GROUP_NAME" \
        --query "key1" -o tsv)
    
    ENDPOINTS+=("${ENDPOINT}vision/v3.2/read/analyze")
    KEYS+=("$KEY")
    
    echo "  エンドポイント: $ENDPOINT"
    echo "  キー: ${KEY:0:8}..."
done

echo ""
echo "=== デプロイ完了 ==="

# 環境変数設定の出力
ENV_ENDPOINTS=$(IFS=,; echo "${ENDPOINTS[*]}")
ENV_KEYS=$(IFS=,; echo "${KEYS[*]}")

echo ""
echo "=== 環境変数設定 (.env) ==="
echo "# Scenario A: Computer Vision endpoints"
echo "OCR_ENDPOINTS=$ENV_ENDPOINTS"
echo "OCR_KEYS=$ENV_KEYS"

# .env.scenario_a ファイルとして保存
ENV_FILE=".env.scenario_a"
cat > "$ENV_FILE" << EOF
# Scenario A: Computer Vision endpoints (Generated: $(date))
OCR_ENDPOINTS=$ENV_ENDPOINTS
OCR_KEYS=$ENV_KEYS

# Thresholds
FALLBACK_SINGLE_MS=1800
EWMA_ALPHA=0.2
EWMA_P95_MS=2000
COOLDOWN_SEC=60
MAX_RETRIES_PER_REQUEST=2
GLOBAL_TIMEOUT_MS=12000

# OCR API settings
USE_SYNC_API=false

# Test settings
TEST_RPS=5
TEST_DURATION=120
EOF

echo ""
echo "環境変数ファイル作成: $ENV_FILE"

echo ""
echo "=== 作成されたリソース ==="
az resource list --resource-group "$RESOURCE_GROUP_NAME" --query "[].{Name:name, Type:type, Location:location}" -o table

echo ""
echo "=== 次のステップ ==="
echo "1. 環境変数設定: cp $ENV_FILE .env"
echo "2. 依存関係インストール: pip install -r requirements.txt"
echo "3. サンプル画像ダウンロード: python scripts/seed_test_images/download_samples.py"
echo "4. テスト実行: python -m scenario_a_client.load_test --images ./samples"
echo ""
echo "5. クリーンアップ: az group delete --name $RESOURCE_GROUP_NAME --yes --no-wait"