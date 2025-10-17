# Japan East Computer Vision デプロイメントスクリプト
# 同一リージョン内の負荷分散・フォールバックテスト用

param(
    [Parameter(Mandatory=$false)]
    [string]$SubscriptionId = $null,
    
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroupName = "rg-ocr-demo-japan-east",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "japaneast",
    
    [Parameter(Mandatory=$false)]
    [string]$ComputerVisionBaseName = "cv-ocr-demo-je",
    
    [Parameter(Mandatory=$false)]
    [switch]$WhatIf = $false,
    
    [Parameter(Mandatory=$false)]
    [switch]$Force = $false
)

# エラーハンドリング
$ErrorActionPreference = "Stop"

Write-Host "🚀 Japan East Computer Vision デプロイメント開始" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# Azure PowerShellモジュールの確認
try {
    Import-Module Az -Force -ErrorAction Stop
    Write-Host "✓ Azure PowerShell モジュール読み込み完了" -ForegroundColor Green
} catch {
    Write-Error "Azure PowerShell モジュールが見つかりません。Install-Module Az を実行してください。"
    exit 1
}

# Azure ログイン確認
try {
    $context = Get-AzContext
    if (-not $context) {
        Write-Host "Azure にログインしています..." -ForegroundColor Yellow
        Connect-AzAccount
    }
    Write-Host "✓ Azure ログイン確認完了" -ForegroundColor Green
} catch {
    Write-Error "Azure ログインに失敗しました: $_"
    exit 1
}

# サブスクリプション設定
if ($SubscriptionId) {
    try {
        Set-AzContext -SubscriptionId $SubscriptionId
        Write-Host "✓ サブスクリプション設定完了: $SubscriptionId" -ForegroundColor Green
    } catch {
        Write-Error "サブスクリプション設定に失敗しました: $_"
        exit 1
    }
} else {
    $currentContext = Get-AzContext
    Write-Host "✓ 現在のサブスクリプションを使用: $($currentContext.Subscription.Name)" -ForegroundColor Green
}

# デプロイメント情報表示
Write-Host "`n📋 デプロイメント情報:" -ForegroundColor Cyan
Write-Host "   リソースグループ: $ResourceGroupName"
Write-Host "   リージョン: $Location"
Write-Host "   Computer Vision ベース名: $ComputerVisionBaseName"
Write-Host "   エンドポイント数: 3個 (Primary, Secondary, Tertiary)"

if (-not $Force) {
    $confirmation = Read-Host "`n続行しますか? (y/N)"
    if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
        Write-Host "デプロイメントをキャンセルしました。" -ForegroundColor Yellow
        exit 0
    }
}

# Bicepテンプレートのパス
$bicepTemplate = Join-Path $PSScriptRoot "japan-computer-vision.bicep"
if (-not (Test-Path $bicepTemplate)) {
    Write-Error "Bicepテンプレートが見つかりません: $bicepTemplate"
    exit 1
}

# デプロイメントパラメータ
$deploymentParams = @{
    resourceGroupName = $ResourceGroupName
    computerVisionBaseName = $ComputerVisionBaseName
    location = $Location
    tags = @{
        project = "ocr-demo"
        scenario = "japan-east-loadbalancing"
        environment = "demo"
        deployedBy = $env:USERNAME
        deployedAt = (Get-Date -Format "yyyy-MM-dd-HH-mm")
    }
}

try {
    Write-Host "`n🔄 デプロイメント実行中..." -ForegroundColor Yellow
    
    $deploymentName = "ocr-demo-japan-east-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    
    if ($WhatIf) {
        Write-Host "What-If モードでデプロイメントを確認しています..." -ForegroundColor Yellow
        $result = New-AzSubscriptionDeployment `
            -Name $deploymentName `
            -Location $Location `
            -TemplateFile $bicepTemplate `
            -TemplateParameterObject $deploymentParams `
            -WhatIf
    } else {
        $result = New-AzSubscriptionDeployment `
            -Name $deploymentName `
            -Location $Location `
            -TemplateFile $bicepTemplate `
            -TemplateParameterObject $deploymentParams `
            -Verbose
    }
    
    if ($result.ProvisioningState -eq "Succeeded" -or $WhatIf) {
        Write-Host "`n✅ デプロイメント完了!" -ForegroundColor Green
        
        if (-not $WhatIf) {
            # 出力情報を表示
            Write-Host "`n📊 デプロイメント結果:" -ForegroundColor Cyan
            Write-Host "   リソースグループ: $($result.Outputs.resourceGroupName.Value)"
            
            $endpoints = $result.Outputs.computerVisionEndpoints.Value
            Write-Host "   Computer Vision エンドポイント数: $($endpoints.Count)"
            
            foreach ($endpoint in $endpoints) {
                Write-Host "   - $($endpoint.endpointType): $($endpoint.name)" -ForegroundColor White
                Write-Host "     エンドポイント: $($endpoint.endpoint)" -ForegroundColor Gray
            }
            
            # 環境変数ファイル生成
            Write-Host "`n📝 環境変数ファイルを生成しています..." -ForegroundColor Yellow
            $envFile = Join-Path $PSScriptRoot "..\\.env.japan-east"
            
            $envContent = @"
# Japan East Computer Vision エンドポイント設定
# 生成日時: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# リソース情報
RESOURCE_GROUP_NAME=$($result.Outputs.resourceGroupName.Value)
LOCATION=$Location

# Computer Vision エンドポイント (カンマ区切り)
OCR_ENDPOINTS=$($endpoints | ForEach-Object { $_.endpoint } | Join-String -Separator ',')

# Computer Vision キー (後で手動設定が必要)
# 以下のコマンドで取得できます:
"@

            foreach ($endpoint in $endpoints) {
                $envContent += "`n# az cognitiveservices account keys list --name $($endpoint.name) --resource-group $($result.Outputs.resourceGroupName.Value) --query key1 -o tsv"
            }
            
            $envContent += "`n`nOCR_KEYS=YOUR_KEY_1,YOUR_KEY_2,YOUR_KEY_3"
            
            $envContent | Out-File -FilePath $envFile -Encoding UTF8
            Write-Host "   環境変数ファイル生成完了: $envFile" -ForegroundColor Green
            
            # キー取得のヘルプ
            Write-Host "`n🔑 次のステップ: APIキーの取得" -ForegroundColor Magenta
            Write-Host "以下のコマンドでAPIキーを取得してください:" -ForegroundColor Yellow
            
            foreach ($endpoint in $endpoints) {
                Write-Host "az cognitiveservices account keys list --name $($endpoint.name) --resource-group $($result.Outputs.resourceGroupName.Value) --query key1 -o tsv" -ForegroundColor White
            }
            
            Write-Host "`n取得したキーを $envFile の OCR_KEYS に設定してください。" -ForegroundColor Yellow
        }
        
    } else {
        Write-Error "デプロイメントに失敗しました: $($result.ProvisioningState)"
        exit 1
    }
    
} catch {
    Write-Error "デプロイメント中にエラーが発生しました: $_"
    exit 1
}

Write-Host "`n🎉 Japan East Computer Vision デプロイメント完了!" -ForegroundColor Green
Write-Host "同一リージョン内での負荷分散・フォールバックテストの準備ができました。" -ForegroundColor Green