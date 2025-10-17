#!/bin/bash

# デプロイ設定
LOCATION="japaneast"
RESOURCE_GROUP="rg-ocr-demo-japan-east"
DEPLOYMENT_NAME="apim-cv-deployment-$(date +%Y%m%d-%H%M%S)"

# パラメータ設定
NAME_PREFIX="ocr-demo"
ENVIRONMENT="dev"
PUBLISHER_NAME="OCR Demo"
PUBLISHER_EMAIL="admin@example.com"
APIM_SKU="Developer"

echo "🚀 Azure API Management デプロイを開始します..."
echo "リソースグループ: $RESOURCE_GROUP"
echo "場所: $LOCATION"
echo "デプロイ名: $DEPLOYMENT_NAME"

# Azure CLI ログイン確認
if ! az account show > /dev/null 2>&1; then
    echo "❌ Azure CLI にログインしていません。ログインしてください。"
    az login
fi

# リソースグループの存在確認（既存のComputer Visionリソースが必要）
if ! az group show --name "$RESOURCE_GROUP" > /dev/null 2>&1; then
    echo "❌ リソースグループ $RESOURCE_GROUP が見つかりません。"
    echo "まず Computer Vision リソースをデプロイしてください。"
    exit 1
fi

# Computer Vision リソースの存在確認
echo "📋 Computer Vision リソースの確認中..."
CV_PRIMARY="cv-ocr-demo-je-primary"
CV_SECONDARY="cv-ocr-demo-je-secondary" 
CV_TERTIARY="cv-ocr-demo-je-tertiary"

for cv_name in "$CV_PRIMARY" "$CV_SECONDARY" "$CV_TERTIARY"; do
    if ! az cognitiveservices account show --name "$cv_name" --resource-group "$RESOURCE_GROUP" > /dev/null 2>&1; then
        echo "❌ Computer Vision リソース $cv_name が見つかりません。"
        echo "まず Computer Vision リソースをデプロイしてください。"
        exit 1
    fi
done

echo "✅ すべての Computer Vision リソースが確認できました。"

# Bicep テンプレートのデプロイ
echo "🔧 API Management をデプロイしています..."

az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --template-file "/Users/kyoheim/src/ocr-demo/infrastructure/apim/apim-computer-vision.bicep" \
    --parameters \
        location="$LOCATION" \
        namePrefix="$NAME_PREFIX" \
        environment="$ENVIRONMENT" \
        publisherName="$PUBLISHER_NAME" \
        publisherEmail="$PUBLISHER_EMAIL" \
        apimSku="$APIM_SKU" \
    --name "$DEPLOYMENT_NAME" \
    --verbose

if [ $? -eq 0 ]; then
    echo "✅ API Management デプロイが完了しました！"
    
    # デプロイ結果の取得
    APIM_NAME="${NAME_PREFIX}-apim-${ENVIRONMENT}"
    
    echo "📊 デプロイ結果:"
    echo "  API Management名: $APIM_NAME"
    
    # Gateway URLの取得
    GATEWAY_URL=$(az apim show --name "$APIM_NAME" --resource-group "$RESOURCE_GROUP" --query "gatewayUrl" -o tsv)
    echo "  Gateway URL: $GATEWAY_URL"
    
    # サブスクリプションキーの取得
    echo "🔑 サブスクリプションキーを取得しています..."
    
    # デフォルトサブスクリプションの確認
    SUBSCRIPTION_ID=$(az apim subscription list --service-name "$APIM_NAME" --resource-group "$RESOURCE_GROUP" --query "[?displayName=='Built-in all-access subscription'].name" -o tsv)
    
    if [ -n "$SUBSCRIPTION_ID" ]; then
        PRIMARY_KEY=$(az apim subscription show --service-name "$APIM_NAME" --resource-group "$RESOURCE_GROUP" --subscription-id "$SUBSCRIPTION_ID" --query "primaryKey" -o tsv)
        echo "  プライマリキー: $PRIMARY_KEY"
    else
        echo "⚠️  デフォルトサブスクリプションが見つかりません。手動でサブスクリプションを作成してください。"
    fi
    
    # 環境設定ファイルの作成
    ENV_FILE=".env.apim"
    echo "📝 環境設定ファイル $ENV_FILE を作成しています..."
    
    cat > "$ENV_FILE" << EOF
# Azure API Management Configuration
# Generated on $(date)

# API Management Settings
APIM_NAME=$APIM_NAME
APIM_GATEWAY_URL=$GATEWAY_URL
APIM_SUBSCRIPTION_KEY=$PRIMARY_KEY

# API Endpoints
APIM_OCR_ENDPOINT=$GATEWAY_URL/vision/v3.2/read/analyze
APIM_OCR_RESULT_ENDPOINT=$GATEWAY_URL/vision/v3.2/read/analyzeResults

# Resource Group
RESOURCE_GROUP=$RESOURCE_GROUP
LOCATION=$LOCATION
EOF
    
    echo "✅ 環境設定ファイル $ENV_FILE が作成されました。"
    echo ""
    echo "🔧 次のステップ:"
    echo "1. $ENV_FILE ファイルを確認してください"
    echo "2. Scenario B のクライアントでテストを実行してください"
    echo ""
    echo "📌 API Management の準備が完了しました！"
    
else
    echo "❌ API Management のデプロイに失敗しました。"
    echo "エラーの詳細を確認してください。"
    exit 1
fi