#!/usr/bin/env pwsh
# シナリオA用のAzureリソースをデプロイするPowerShellスクリプト

param(
    [Parameter(Mandatory=$false)]
    [string]$SubscriptionId = "",
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "rg-ocr-demo-scenario-a",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastus",
    
    [Parameter(Mandatory=$false)]
    [string]$ProjectName = "ocr-demo-a",
    
    [Parameter(Mandatory=$false)]
    [string]$CognitiveServicesSku = "S1"
)

# エラー時に停止
$ErrorActionPreference = "Stop"

Write-Host "=== シナリオA用Azureリソースデプロイ ===" -ForegroundColor Green

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

# Computer Vision サービス用の複数リージョン
$locations = @("eastus", "japaneast", "westeurope")
$endpoints = @()
$keys = @()

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
        --tags Project=$ProjectName Scenario=A Environment=Demo Region=$loc
    
    # エンドポイントとキー取得
    $endpoint = az cognitiveservices account show `
        --name $serviceName `
        --resource-group $ResourceGroupName `
        --query "properties.endpoint" -o tsv
    
    $key = az cognitiveservices account keys list `
        --name $serviceName `
        --resource-group $ResourceGroupName `
        --query "key1" -o tsv
    
    $endpoints += "$endpoint" + "vision/v3.2/read/analyze"
    $keys += $key
    
    Write-Host "  エンドポイント: $endpoint" -ForegroundColor Cyan
    Write-Host "  キー: $($key.Substring(0, 8))..." -ForegroundColor Cyan
}

Write-Host "`n=== デプロイ完了 ===" -ForegroundColor Green

# 環境変数設定の出力
$envEndpoints = $endpoints -join ","
$envKeys = $keys -join ","

Write-Host "`n=== 環境変数設定 (.env) ===" -ForegroundColor Magenta
Write-Host "# Scenario A: Computer Vision endpoints"
Write-Host "OCR_ENDPOINTS=$envEndpoints"
Write-Host "OCR_KEYS=$envKeys"

# .env.local ファイルとして保存
$envContent = @"
# Scenario A: Computer Vision endpoints (Generated: $(Get-Date))
OCR_ENDPOINTS=$envEndpoints
OCR_KEYS=$envKeys

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
"@

$envPath = ".env.scenario_a"
$envContent | Out-File -FilePath $envPath -Encoding UTF8
Write-Host "`n環境変数ファイル作成: $envPath" -ForegroundColor Green

Write-Host "`n=== 作成されたリソース ===" -ForegroundColor Magenta
az resource list --resource-group $ResourceGroupName --query "[].{Name:name, Type:type, Location:location}" -o table

Write-Host "`n=== 次のステップ ===" -ForegroundColor Yellow
Write-Host "1. 環境変数設定: cp $envPath .env"
Write-Host "2. 依存関係インストール: pip install -r requirements.txt"  
Write-Host "3. サンプル画像ダウンロード: python scripts/seed_test_images/download_samples.py"
Write-Host "4. テスト実行: python -m scenario_a_client.load_test --images ./samples"
Write-Host "`n5. クリーンアップ: az group delete --name $ResourceGroupName --yes --no-wait"