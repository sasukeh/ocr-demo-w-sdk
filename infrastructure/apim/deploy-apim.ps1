# Deploy API Management for Computer Vision OCR Demo
# PowerShell version

param(
    [string]$Location = "japaneast",
    [string]$ResourceGroup = "rg-ocr-demo-japan-east",
    [string]$NamePrefix = "ocr-demo", 
    [string]$Environment = "dev",
    [string]$PublisherName = "OCR Demo",
    [string]$PublisherEmail = "admin@example.com",
    [string]$ApimSku = "Developer"
)

$DeploymentName = "apim-cv-deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

Write-Host "🚀 Azure API Management デプロイを開始します..." -ForegroundColor Green
Write-Host "リソースグループ: $ResourceGroup"
Write-Host "場所: $Location"
Write-Host "デプロイ名: $DeploymentName"

# Azure CLI ログイン確認
try {
    az account show | Out-Null
}
catch {
    Write-Host "❌ Azure CLI にログインしていません。ログインしてください。" -ForegroundColor Red
    az login
}

# リソースグループの存在確認
try {
    az group show --name $ResourceGroup | Out-Null
}
catch {
    Write-Host "❌ リソースグループ $ResourceGroup が見つかりません。" -ForegroundColor Red
    Write-Host "まず Computer Vision リソースをデプロイしてください。"
    exit 1
}

# Computer Vision リソースの存在確認
Write-Host "📋 Computer Vision リソースの確認中..." -ForegroundColor Yellow
$CvPrimary = "$NamePrefix-cv-je-primary"
$CvSecondary = "$NamePrefix-cv-je-secondary"
$CvTertiary = "$NamePrefix-cv-je-tertiary"

foreach ($cvName in @($CvPrimary, $CvSecondary, $CvTertiary)) {
    try {
        az cognitiveservices account show --name $cvName --resource-group $ResourceGroup | Out-Null
    }
    catch {
        Write-Host "❌ Computer Vision リソース $cvName が見つかりません。" -ForegroundColor Red
        Write-Host "まず Computer Vision リソースをデプロイしてください。"
        exit 1
    }
}

Write-Host "✅ すべての Computer Vision リソースが確認できました。" -ForegroundColor Green

# Bicep テンプレートのデプロイ
Write-Host "🔧 API Management をデプロイしています..." -ForegroundColor Yellow

$deployResult = az deployment group create `
    --resource-group $ResourceGroup `
    --template-file "./apim-computer-vision.bicep" `
    --parameters `
        location=$Location `
        namePrefix=$NamePrefix `
        environment=$Environment `
        publisherName=$PublisherName `
        publisherEmail=$PublisherEmail `
        apimSku=$ApimSku `
    --name $DeploymentName `
    --verbose 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ API Management デプロイが完了しました！" -ForegroundColor Green
    
    # デプロイ結果の取得
    $ApimName = "$NamePrefix-apim-$Environment"
    
    Write-Host "📊 デプロイ結果:" -ForegroundColor Cyan
    Write-Host "  API Management名: $ApimName"
    
    # Gateway URLの取得
    $GatewayUrl = az apim show --name $ApimName --resource-group $ResourceGroup --query "gatewayUrl" -o tsv
    Write-Host "  Gateway URL: $GatewayUrl"
    
    # サブスクリプションキーの取得
    Write-Host "🔑 サブスクリプションキーを取得しています..." -ForegroundColor Yellow
    
    # デフォルトサブスクリプションの確認
    $SubscriptionId = az apim subscription list --service-name $ApimName --resource-group $ResourceGroup --query "[?displayName=='Built-in all-access subscription'].name" -o tsv
    
    if ($SubscriptionId) {
        $PrimaryKey = az apim subscription show --service-name $ApimName --resource-group $ResourceGroup --subscription-id $SubscriptionId --query "primaryKey" -o tsv
        Write-Host "  プライマリキー: $PrimaryKey"
    }
    else {
        Write-Host "⚠️  デフォルトサブスクリプションが見つかりません。手動でサブスクリプションを作成してください。" -ForegroundColor Yellow
        $PrimaryKey = ""
    }
    
    # 環境設定ファイルの作成
    $EnvFile = ".env.apim"
    Write-Host "📝 環境設定ファイル $EnvFile を作成しています..." -ForegroundColor Yellow
    
    $envContent = @"
# Azure API Management Configuration
# Generated on $(Get-Date)

# API Management Settings
APIM_NAME=$ApimName
APIM_GATEWAY_URL=$GatewayUrl
APIM_SUBSCRIPTION_KEY=$PrimaryKey

# API Endpoints
APIM_OCR_ENDPOINT=$GatewayUrl/vision/v3.2/read/analyze
APIM_OCR_RESULT_ENDPOINT=$GatewayUrl/vision/v3.2/read/analyzeResults

# Resource Group
RESOURCE_GROUP=$ResourceGroup
LOCATION=$Location
"@
    
    $envContent | Out-File -FilePath $EnvFile -Encoding utf8
    
    Write-Host "✅ 環境設定ファイル $EnvFile が作成されました。" -ForegroundColor Green
    Write-Host ""
    Write-Host "🔧 次のステップ:" -ForegroundColor Cyan
    Write-Host "1. $EnvFile ファイルを確認してください"
    Write-Host "2. Scenario B のクライアントでテストを実行してください"
    Write-Host ""
    Write-Host "📌 API Management の準備が完了しました！" -ForegroundColor Green
}
else {
    Write-Host "❌ API Management のデプロイに失敗しました。" -ForegroundColor Red
    Write-Host "エラーの詳細を確認してください。"
    Write-Host $deployResult
    exit 1
}