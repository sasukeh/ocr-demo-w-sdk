#!/bin/bash

# APIM に Computer Vision OCR API を手動作成

RESOURCE_GROUP="rg-ocr-demo-japan-east"
APIM_NAME="ocr-demo-apim-dev"
API_NAME="computer-vision-ocr"
CV_ENDPOINT="https://cv-ocr-demo-je-primary.cognitiveservices.azure.com"

# 環境変数から取得 (または引数で指定)
CV_KEY="${CV_KEY:-$(az cognitiveservices account keys list --resource-group $RESOURCE_GROUP --name cv-ocr-demo-je-primary --query 'key1' -o tsv)}"

echo "🔧 APIM に Computer Vision API を作成中..."

# API を作成
az rest --method PUT \
  --url "https://management.azure.com/subscriptions/8f4244ad-7467-4361-a52e-57052eb23ca2/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.ApiManagement/service/${APIM_NAME}/apis/${API_NAME}?api-version=2021-08-01" \
  --body "{
    \"properties\": {
      \"displayName\": \"Computer Vision OCR API\",
      \"description\": \"Direct proxy to Computer Vision Read API\",
      \"serviceUrl\": \"${CV_ENDPOINT}\",
      \"path\": \"vision\",
      \"protocols\": [\"https\"],
      \"subscriptionRequired\": true
    }
  }"

if [ $? -eq 0 ]; then
    echo "✅ API 作成完了"
    
    # OCR Read Operation を作成
    echo "🔧 OCR Read オペレーション作成中..."
    
    az rest --method PUT \
      --url "https://management.azure.com/subscriptions/8f4244ad-7467-4361-a52e-57052eb23ca2/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.ApiManagement/service/${APIM_NAME}/apis/${API_NAME}/operations/ocr-read?api-version=2021-08-01" \
      --body "{
        \"properties\": {
          \"displayName\": \"OCR Read\",
          \"method\": \"POST\",
          \"urlTemplate\": \"/vision/v3.2/read/analyze\",
          \"description\": \"Extract text from images\",
          \"request\": {
            \"headers\": [
              {
                \"name\": \"Content-Type\",
                \"type\": \"string\",
                \"required\": true,
                \"values\": [\"application/octet-stream\"]
              }
            ]
          },
          \"responses\": [
            {
              \"statusCode\": 202,
              \"description\": \"Accepted\",
              \"headers\": [
                {
                  \"name\": \"Operation-Location\",
                  \"type\": \"string\"
                }
              ]
            }
          ]
        }
      }"
    
    if [ $? -eq 0 ]; then
        echo "✅ OCR Read オペレーション作成完了"
        
        # ポリシーを設定（Computer Vision キーを追加）
        echo "🔧 ポリシー設定中..."
        
        POLICY='<policies>
            <inbound>
                <base />
                <set-header name="Ocp-Apim-Subscription-Key" exists-action="override">
                    <value>'${CV_KEY}'</value>
                </set-header>
                <set-header name="X-Forwarded-For" exists-action="skip" />
            </inbound>
            <backend>
                <base />
            </backend>
            <outbound>
                <base />
                <set-header name="X-Served-By-Backend" exists-action="override">
                    <value>cv-primary-direct</value>
                </set-header>
            </outbound>
            <on-error>
                <base />
            </on-error>
        </policies>'
        
        az rest --method PUT \
          --url "https://management.azure.com/subscriptions/8f4244ad-7467-4361-a52e-57052eb23ca2/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.ApiManagement/service/${APIM_NAME}/apis/${API_NAME}/operations/ocr-read/policies/policy?api-version=2021-08-01" \
          --body "{
            \"properties\": {
              \"value\": \"$(echo "$POLICY" | sed 's/"/\\"/g')\",
              \"format\": \"xml\"
            }
          }"
        
        if [ $? -eq 0 ]; then
            echo "✅ ポリシー設定完了"
            
            # OCR Result Operation も作成
            echo "🔧 OCR Result オペレーション作成中..."
            
            az rest --method PUT \
              --url "https://management.azure.com/subscriptions/8f4244ad-7467-4361-a52e-57052eb23ca2/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.ApiManagement/service/${APIM_NAME}/apis/${API_NAME}/operations/ocr-result?api-version=2021-08-01" \
              --body "{
                \"properties\": {
                  \"displayName\": \"Get OCR Result\",
                  \"method\": \"GET\",
                  \"urlTemplate\": \"/vision/v3.2/read/analyzeResults/{resultId}\",
                  \"description\": \"Get OCR analysis result\",
                  \"templateParameters\": [
                    {
                      \"name\": \"resultId\",
                      \"type\": \"string\",
                      \"required\": true
                    }
                  ],
                  \"responses\": [
                    {
                      \"statusCode\": 200,
                      \"description\": \"Success\"
                    }
                  ]
                }
              }"
            
            # Result オペレーションにも同じポリシーを適用
            az rest --method PUT \
              --url "https://management.azure.com/subscriptions/8f4244ad-7467-4361-a52e-57052eb23ca2/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.ApiManagement/service/${APIM_NAME}/apis/${API_NAME}/operations/ocr-result/policies/policy?api-version=2021-08-01" \
              --body "{
                \"properties\": {
                  \"value\": \"$(echo "$POLICY" | sed 's/"/\\"/g')\",
                  \"format\": \"xml\"
                }
              }"
            
            echo "✅ すべての設定が完了しました！"
            echo ""
            echo "📋 API エンドポイント:"
            echo "  OCR Analyze: https://ocr-demo-apim-dev.azure-api.net/vision/v3.2/read/analyze"
            echo "  OCR Result:  https://ocr-demo-apim-dev.azure-api.net/vision/v3.2/read/analyzeResults/{resultId}"
            echo ""
            echo "🔑 Subscription Key: (Azure Portal で確認してください)"
            
        else
            echo "❌ ポリシー設定に失敗しました"
        fi
    else
        echo "❌ OCR Read オペレーション作成に失敗しました"
    fi
else
    echo "❌ API 作成に失敗しました"
fi