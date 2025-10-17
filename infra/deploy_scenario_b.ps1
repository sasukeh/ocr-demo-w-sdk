#!/usr/bin/env pwsh
# シナリオB用のAzureリソースをデプロイするPowerShellスクリプト

param(
    [Parameter(Mandatory=$false)]
    [string]$SubscriptionId = "",
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "rg-ocr-demo-scenario-b",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastus",
    
    [Parameter(Mandatory=$false)]
    [string]$ProjectName = "ocr-demo-b",
    
    [Parameter(Mandatory=$false)]
    [string]$CognitiveServicesSku = "S1",
    
    [Parameter(Mandatory=$false)]
    [string]$ApimSku = "Developer"
)

# エラー時に停止
$ErrorActionPreference = "Stop"

Write-Host "=== シナリオB用Azureリソースデプロイ ===" -ForegroundColor Blue

# サブスクリプション設定
if ($SubscriptionId) {
    Write-Host "サブスクリプション設定: $SubscriptionId" -ForegroundColor Yellow
    az account set --subscription $SubscriptionId
}

# 現在のサブスクリプション確認
$currentSub = az account show --query "name" -o tsv
Write-Host "使用中のサブスクリプション: $currentSub" -ForegroundColor Cyan

# リソースグループ作成
Write-Host "リソースグループ作成: $ResourceGroupName ($Location)" -ForegroundColor Yellow
az group create --name $ResourceGroupName --location $Location

# Computer Vision サービス用の複数リージョン（APIM バックエンド用）
$locations = @("eastus", "japaneast", "westeurope")
$cvServices = @()

foreach ($loc in $locations) {
    $serviceName = "$ProjectName-cv-$loc"
    
    Write-Host "Computer Vision サービス作成: $serviceName ($loc)" -ForegroundColor Yellow
    
    az cognitiveservices account create `
        --name $serviceName `
        --resource-group $ResourceGroupName `
        --kind ComputerVision `
        --sku $CognitiveServicesSku `
        --location $loc `
        --custom-domain $serviceName `
        --tags Project=$ProjectName Scenario=B Environment=Demo Region=$loc
    
    # エンドポイントとキー取得
    $endpoint = az cognitiveservices account show `
        --name $serviceName `
        --resource-group $ResourceGroupName `
        --query "properties.endpoint" -o tsv
    
    $key = az cognitiveservices account keys list `
        --name $serviceName `
        --resource-group $ResourceGroupName `
        --query "key1" -o tsv
    
    $cvServices += @{
        Name = $serviceName
        Location = $loc
        Endpoint = $endpoint
        Key = $key
    }
    
    Write-Host "  エンドポイント: $endpoint" -ForegroundColor Cyan
    Write-Host "  キー: $($key.Substring(0, 8))..." -ForegroundColor Cyan
}

# API Management インスタンス作成
$apimName = "$ProjectName-apim"
Write-Host "`nAPI Management インスタンス作成: $apimName" -ForegroundColor Yellow
Write-Host "注意: APIMインスタンスの作成には30-40分程度かかります..." -ForegroundColor Red

az apim create `
    --name $apimName `
    --resource-group $ResourceGroupName `
    --location $Location `
    --publisher-name "OCR Demo Publisher" `
    --publisher-email "demo@example.com" `
    --sku-name $ApimSku `
    --tags Project=$ProjectName Scenario=B Environment=Demo

# APIM ゲートウェイURL取得
$apimGateway = az apim show `
    --name $apimName `
    --resource-group $ResourceGroupName `
    --query "gatewayUrl" -o tsv

Write-Host "APIM ゲートウェイURL: $apimGateway" -ForegroundColor Cyan

# APIM Named Values (秘密の設定)
Write-Host "`nAPIM Named Values 設定..." -ForegroundColor Yellow

foreach ($service in $cvServices) {
    $namedValueName = "$($service.Location.Replace('us','').Replace('europe','eu'))-ocr-key"
    
    az apim nv create `
        --resource-group $ResourceGroupName `
        --service-name $apimName `
        --named-value-id $namedValueName `
        --display-name $namedValueName `
        --value $service.Key `
        --secret true
    
    Write-Host "  Named Value 作成: $namedValueName" -ForegroundColor Cyan
}

# APIM API 作成
$apiId = "ocr-demo-api"
Write-Host "`nAPIM API 作成: $apiId" -ForegroundColor Yellow

az apim api create `
    --resource-group $ResourceGroupName `
    --service-name $apimName `
    --api-id $apiId `
    --display-name "OCR Demo API" `
    --path "ocr" `
    --protocols https `
    --service-url $cvServices[0].Endpoint

# サブスクリプション作成
Write-Host "APIサブスクリプション作成..." -ForegroundColor Yellow
$subscriptionKey = az apim subscription create `
    --resource-group $ResourceGroupName `
    --service-name $apimName `
    --subscription-id "ocr-demo-subscription" `
    --display-name "OCR Demo Subscription" `
    --scope "/apis/$apiId" `
    --query "primaryKey" -o tsv

Write-Host "サブスクリプションキー: $($subscriptionKey.Substring(0, 8))..." -ForegroundColor Cyan

Write-Host "`n=== デプロイ完了 ===" -ForegroundColor Green

# 環境変数設定の出力
$apimGatewayPath = "$apimGateway/ocr"

Write-Host "`n=== 環境変数設定 (.env) ===" -ForegroundColor Magenta
Write-Host "# Scenario B: APIM Gateway"
Write-Host "APIM_GATEWAY=$apimGatewayPath"
Write-Host "APIM_SUBSCRIPTION_KEY=$subscriptionKey"

# .env.local ファイルとして保存
$envContent = @"
# Scenario B: APIM Gateway (Generated: $(Get-Date))
APIM_GATEWAY=$apimGatewayPath
APIM_SUBSCRIPTION_KEY=$subscriptionKey

# Thresholds
FALLBACK_SINGLE_MS=1800
EWMA_ALPHA=0.2
EWMA_P95_MS=2000
COOLDOWN_SEC=60
MAX_RETRIES_PER_REQUEST=2
GLOBAL_TIMEOUT_MS=12000

# Test settings
TEST_RPS=5
TEST_DURATION=120
"@

$envPath = ".env.scenario_b"
$envContent | Out-File -FilePath $envPath -Encoding UTF8
Write-Host "`n環境変数ファイル作成: $envPath" -ForegroundColor Green

Write-Host "`n=== 作成されたリソース ===" -ForegroundColor Magenta
az resource list --resource-group $ResourceGroupName --query "[].{Name:name, Type:type, Location:location}" -o table

Write-Host "`n=== 重要な手動設定 ===" -ForegroundColor Red
Write-Host "1. APIM ポリシー設定が必要です:"
Write-Host "   - scenario_b_apim/apim/policy.xml をAPIM Portalで適用"
Write-Host "   - Named Values の設定確認"
Write-Host ""
Write-Host "2. バックエンドURL設定:"
foreach ($service in $cvServices) {
    Write-Host "   - $($service.Location): $($service.Endpoint)"
}

Write-Host "`n=== 次のステップ ===" -ForegroundColor Yellow
Write-Host "1. 環境変数設定: cp $envPath .env"
Write-Host "2. APIMポータルでポリシー設定を手動適用"
Write-Host "3. 依存関係インストール: pip install -r requirements.txt"
Write-Host "4. サンプル画像ダウンロード: python scripts/seed_test_images/download_samples.py"
Write-Host "5. テスト実行: python -m scenario_b_apim.load_test --images ./samples"
Write-Host "`n6. クリーンアップ: az group delete --name $ResourceGroupName --yes --no-wait"