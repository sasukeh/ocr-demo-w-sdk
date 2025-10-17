#!/bin/bash

# Japan East Computer Vision デプロイメントスクリプト
# 同一リージョン内の負荷分散・フォールバックテスト用

set -e  # エラー時に停止

# デフォルト値
SUBSCRIPTION_ID=""
RESOURCE_GROUP_NAME="rg-ocr-demo-japan-east"
LOCATION="japaneast"
COMPUTER_VISION_BASE_NAME="cv-ocr-demo-je"
WHAT_IF=false
FORCE=false

# 使用法表示
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -s, --subscription-id ID     Azure サブスクリプション ID"
    echo "  -g, --resource-group NAME    リソースグループ名 (default: rg-ocr-demo-japan-east)"
    echo "  -l, --location LOCATION      デプロイメント先リージョン (default: japaneast)"
    echo "  -n, --base-name NAME         Computer Vision ベース名 (default: cv-ocr-demo-je)"
    echo "  -w, --what-if                What-If モード（実際にはデプロイしない）"
    echo "  -f, --force                  確認をスキップ"
    echo "  -h, --help                   このヘルプを表示"
    echo ""
    echo "Example:"
    echo "  $0 --subscription-id 12345678-1234-1234-1234-123456789012"
    echo "  $0 --what-if  # デプロイ確認のみ"
}

# パラメータ解析
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--subscription-id)
            SUBSCRIPTION_ID="$2"
            shift 2
            ;;
        -g|--resource-group)
            RESOURCE_GROUP_NAME="$2"
            shift 2
            ;;
        -l|--location)
            LOCATION="$2"
            shift 2
            ;;
        -n|--base-name)
            COMPUTER_VISION_BASE_NAME="$2"
            shift 2
            ;;
        -w|--what-if)
            WHAT_IF=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            show_usage >&2
            exit 1
            ;;
    esac
done

# 色付きメッセージ用の関数
print_info() { echo -e "\033[0;32m$1\033[0m"; }
print_warn() { echo -e "\033[0;33m$1\033[0m"; }
print_error() { echo -e "\033[0;31m$1\033[0m" >&2; }
print_cyan() { echo -e "\033[0;36m$1\033[0m"; }

print_info "🚀 Japan East Computer Vision デプロイメント開始"
print_info "================================"

# Azure CLI の確認
if ! command -v az &> /dev/null; then
    print_error "Azure CLI が見つかりません。https://aka.ms/azure-cli からインストールしてください。"
    exit 1
fi
print_info "✓ Azure CLI 確認完了"

# Azure ログイン確認
if ! az account show &> /dev/null; then
    print_warn "Azure にログインしています..."
    az login
fi
print_info "✓ Azure ログイン確認完了"

# サブスクリプション設定
if [[ -n "$SUBSCRIPTION_ID" ]]; then
    az account set --subscription "$SUBSCRIPTION_ID"
    print_info "✓ サブスクリプション設定完了: $SUBSCRIPTION_ID"
else
    CURRENT_SUB=$(az account show --query name -o tsv)
    print_info "✓ 現在のサブスクリプションを使用: $CURRENT_SUB"
fi

# Bicepテンプレートのパス確認
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BICEP_TEMPLATE="$SCRIPT_DIR/japan-computer-vision.bicep"

if [[ ! -f "$BICEP_TEMPLATE" ]]; then
    print_error "Bicepテンプレートが見つかりません: $BICEP_TEMPLATE"
    exit 1
fi

# デプロイメント情報表示
print_cyan "📋 デプロイメント情報:"
echo "   リソースグループ: $RESOURCE_GROUP_NAME"
echo "   リージョン: $LOCATION"
echo "   Computer Vision ベース名: $COMPUTER_VISION_BASE_NAME"
echo "   エンドポイント数: 3個 (Primary, Secondary, Tertiary)"

# 確認
if [[ "$FORCE" != true ]]; then
    echo ""
    read -p "続行しますか? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warn "デプロイメントをキャンセルしました。"
        exit 0
    fi
fi

# デプロイメント名生成
DEPLOYMENT_NAME="ocr-demo-japan-east-$(date +%Y%m%d-%H%M%S)"

# デプロイメントパラメータ
DEPLOYED_BY="${USER:-unknown}"
DEPLOYED_AT=$(date +%Y-%m-%d-%H-%M)

print_warn "🔄 デプロイメント実行中..."

# What-If または実際のデプロイ
if [[ "$WHAT_IF" == true ]]; then
    print_warn "What-If モードでデプロイメントを確認しています..."
    
    az deployment sub what-if \
        --name "$DEPLOYMENT_NAME" \
        --location "$LOCATION" \
        --template-file "$BICEP_TEMPLATE" \
        --parameters \
            resourceGroupName="$RESOURCE_GROUP_NAME" \
            computerVisionBaseName="$COMPUTER_VISION_BASE_NAME" \
            location="$LOCATION" \
            tags="{\"project\":\"ocr-demo\",\"scenario\":\"japan-east-loadbalancing\",\"environment\":\"demo\",\"deployedBy\":\"$DEPLOYED_BY\",\"deployedAt\":\"$DEPLOYED_AT\"}"
else
    # 実際のデプロイメント
    DEPLOYMENT_OUTPUT=$(az deployment sub create \
        --name "$DEPLOYMENT_NAME" \
        --location "$LOCATION" \
        --template-file "$BICEP_TEMPLATE" \
        --parameters \
            resourceGroupName="$RESOURCE_GROUP_NAME" \
            computerVisionBaseName="$COMPUTER_VISION_BASE_NAME" \
            location="$LOCATION" \
            tags="{\"project\":\"ocr-demo\",\"scenario\":\"japan-east-loadbalancing\",\"environment\":\"demo\",\"deployedBy\":\"$DEPLOYED_BY\",\"deployedAt\":\"$DEPLOYED_AT\"}" \
        --output json)

    if [[ $? -eq 0 ]]; then
        print_info "✅ デプロイメント完了!"
        
        # 結果の解析と表示
        print_cyan "📊 デプロイメント結果:"
        
        RESOURCE_GROUP=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.resourceGroupName.value')
        echo "   リソースグループ: $RESOURCE_GROUP"
        
        # エンドポイント情報の表示
        ENDPOINTS=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.computerVisionEndpoints.value')
        ENDPOINT_COUNT=$(echo "$ENDPOINTS" | jq length)
        echo "   Computer Vision エンドポイント数: $ENDPOINT_COUNT"
        
        # 各エンドポイントの詳細表示
        for i in $(seq 0 $((ENDPOINT_COUNT-1))); do
            ENDPOINT_TYPE=$(echo "$ENDPOINTS" | jq -r ".[$i].endpointType")
            ENDPOINT_NAME=$(echo "$ENDPOINTS" | jq -r ".[$i].name")
            ENDPOINT_URL=$(echo "$ENDPOINTS" | jq -r ".[$i].endpoint")
            
            echo "   - $ENDPOINT_TYPE: $ENDPOINT_NAME"
            echo "     エンドポイント: $ENDPOINT_URL"
        done
        
        # 環境変数ファイル生成
        print_warn "📝 環境変数ファイルを生成しています..."
        ENV_FILE="$SCRIPT_DIR/../.env.japan-east"
        
        # エンドポイントURLを抽出してカンマ区切りで結合
        ENDPOINT_URLS=$(echo "$ENDPOINTS" | jq -r '.[].endpoint' | tr '\n' ',' | sed 's/,$//')
        
        cat > "$ENV_FILE" << EOF
# Japan East Computer Vision エンドポイント設定
# 生成日時: $(date '+%Y-%m-%d %H:%M:%S')

# リソース情報
RESOURCE_GROUP_NAME=$RESOURCE_GROUP
LOCATION=$LOCATION

# Computer Vision エンドポイント (カンマ区切り)
OCR_ENDPOINTS=$ENDPOINT_URLS

# Computer Vision キー (後で手動設定が必要)
# 以下のコマンドで取得できます:
EOF

        # 実際にAPIキーを取得して設定
        print_warn "🔑 APIキーを自動取得しています..."
        
        API_KEYS=""
        for i in $(seq 0 $((ENDPOINT_COUNT-1))); do
            ENDPOINT_NAME=$(echo "$ENDPOINTS" | jq -r ".[$i].name")
            print_warn "   キー取得中: $ENDPOINT_NAME"
            
            # リトライ機能付きでキー取得
            for retry in {1..3}; do
                KEY=$(az cognitiveservices account keys list --name "$ENDPOINT_NAME" --resource-group "$RESOURCE_GROUP" --query key1 -o tsv 2>/dev/null)
                if [[ -n "$KEY" && "$KEY" != "null" ]]; then
                    if [[ -z "$API_KEYS" ]]; then
                        API_KEYS="$KEY"
                    else
                        API_KEYS="$API_KEYS,$KEY"
                    fi
                    print_info "     ✓ 取得成功"
                    break
                else
                    print_warn "     リトライ $retry/3..."
                    sleep 2
                fi
            done
            
            # バックアップとしてコマンドも記録
            echo "# az cognitiveservices account keys list --name $ENDPOINT_NAME --resource-group $RESOURCE_GROUP --query key1 -o tsv" >> "$ENV_FILE"
        done
        
        echo "" >> "$ENV_FILE"
        if [[ -n "$API_KEYS" ]]; then
            echo "OCR_KEYS=$API_KEYS" >> "$ENV_FILE"
            print_info "✅ APIキーの自動設定が完了しました"
        else
            echo "OCR_KEYS=YOUR_KEY_1,YOUR_KEY_2,YOUR_KEY_3" >> "$ENV_FILE"
            print_warn "⚠️  APIキーの自動取得に失敗しました。手動で設定してください。"
        fi
        
        print_info "   環境変数ファイル生成完了: $ENV_FILE"
        
        # キー取得のヘルプ
        print_cyan "🔑 次のステップ: APIキーの取得"
        print_warn "以下のコマンドでAPIキーを取得してください:"
        
        for i in $(seq 0 $((ENDPOINT_COUNT-1))); do
            ENDPOINT_NAME=$(echo "$ENDPOINTS" | jq -r ".[$i].name")
            echo "az cognitiveservices account keys list --name $ENDPOINT_NAME --resource-group $RESOURCE_GROUP --query key1 -o tsv"
        done
        
        print_warn ""
        print_warn "取得したキーを $ENV_FILE の OCR_KEYS に設定してください。"
        
    else
        print_error "デプロイメントに失敗しました。"
        exit 1
    fi
fi

print_info ""
print_info "🎉 Japan East Computer Vision デプロイメント完了!"
print_info "同一リージョン内での負荷分散・フォールバックテストの準備ができました。"