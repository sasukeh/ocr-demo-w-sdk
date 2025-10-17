# Azure OCR デモ - ベストプラクティスと推奨事項

本ドキュメントでは、本プロジェクトに実装されているベストプラクティスと、将来的な拡張に向けた推奨事項をまとめます。

---

## ✅ 実装済みベストプラクティス

### 1. インフラストラクチャ as Code (IaC)

#### **Bicep テンプレート**
- ✅ 宣言的なインフラ定義
- ✅ パラメータ化による再利用性
- ✅ モジュール化による保守性向上

```bicep
// モジュールの例
module computerVision './modules/computer-vision.bicep' = {
  name: 'cv-${location}'
  params: {
    location: location
    computerVisionName: cvName
    sku: 'S1'
  }
}
```

#### **命名規則**
Azure の推奨パターンを採用:
- `cv-{name}-{region}` - Computer Vision
- `{prefix}-apim-{environment}` - API Management
- `{prefix}-log-{environment}` - Log Analytics

### 2. エラーハンドリングとリトライロジック

#### **APIM ポリシーレベル**
```xml
<retry condition="@(context.Response.StatusCode == 429 || context.Response.StatusCode >= 500)" 
       count="3" 
       interval="2" 
       max-interval="10" 
       delta="2">
    <base />
</retry>
```

#### **クライアントレベル**
```python
async def process_image(self, image_data: bytes, max_retries: int = 3):
    retry_count = 0
    while retry_count <= max_retries:
        try:
            # リクエスト実行
            if response.status_code == 429:
                wait_time = min(2 ** retry_count, 10)
                await asyncio.sleep(wait_time)
                retry_count += 1
                continue
```

**特徴:**
- デュアルレイヤー (APIM + クライアント)
- 指数バックオフ
- レート制限 (429) への特別対応

### 3. 診断設定とログ管理

#### **Log Analytics Workspace**
```bicep
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${namePrefix}-log-${environment}'
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}
```

#### **リソース診断設定**
- **APIM**: GatewayLogs, WebSocketConnectionLogs, AllMetrics
- **Computer Vision**: Audit, RequestResponse, AllMetrics
- **保持期間**: 30日間

**ログクエリ例:**
```kusto
// APIM ゲートウェイエラー
ApiManagementGatewayLogs
| where ResponseCode >= 500
| summarize Count=count() by BackendId, ResponseCode
| order by Count desc

// Computer Vision レート制限
AzureDiagnostics
| where Category == "RequestResponse"
| where httpStatusCode_d == 429
| summarize Count=count() by bin(TimeGenerated, 5m)
```

### 4. 高度なサーキットブレーカー

#### **実装場所**
`infrastructure/apim/policies/advanced-circuit-breaker-policy.xml`

#### **機能:**
1. **状態管理**: CLOSED → OPEN → HALF_OPEN
2. **失敗カウント**: 5回連続失敗で OPEN
3. **自動回復**: 60秒後に HALF_OPEN
4. **バックエンド選択**: Primary → Secondary → Tertiary

#### **キャッシュキー:**
- `circuit-state-{backend}`: サーキット状態
- `{backend}-failure-count`: 失敗カウント

#### **デバッグヘッダー:**
- `X-Served-By-Backend`: 使用されたバックエンド
- `X-Circuit-State-Primary/Secondary/Tertiary`: 各バックエンドの状態

### 5. コスト最適化タグ

#### **リソースタグ戦略**
```bicep
tags: {
  environment: 'dev'           // 環境識別
  project: 'ocr-demo'          // プロジェクト識別
  costCenter: 'Engineering'    // コストセンター
  owner: publisherEmail        // リソース所有者
  managedBy: 'Bicep'          // 管理方法
  purpose: 'OCR Load Balancing' // 用途
}
```

**活用方法:**
```bash
# タグによるコスト分析
az consumption usage list \
  --query "[?tags.project=='ocr-demo']" \
  --output table

# タグによるリソース一覧
az resource list \
  --tag project=ocr-demo \
  --output table
```

### 6. 負荷テストの自動化

#### **GitHub Actions ワークフロー**
`.github/workflows/load-test.yml`

**トリガー:**
- 手動実行 (workflow_dispatch)
- スケジュール実行 (毎日 9:00 JST)
- コード変更時 (push on main)

**テストシナリオ:**
- Scenario A: 直接クライアント
- Scenario B: APIM 経由
- 両方の比較分析

**成功基準:**
- Scenario B 成功率 ≥ 90%

#### **使用方法:**
```bash
# GitHub Actions から手動実行
# Actions タブ → "OCR Load Testing" → "Run workflow"
# - scenario: scenario-a / scenario-b / both
# - total_requests: 1000
# - workers: 5
```

### 7. メトリクスと可視化

#### **Rich コンソール出力**
```python
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

# プログレスバー
with Progress() as progress:
    task = progress.add_task("[cyan]リクエスト実行中...", total=total)
    
# テーブル表示
table = Table(title="総合統計")
table.add_column("メトリクス")
table.add_column("値", justify="right")
table.add_row("総リクエスト数", f"{stats['total']:,}")
table.add_row("成功率", f"{stats['success_rate']:.1f}%")
```

---

## 📋 将来的な推奨事項 (デプロイ複雑化を避けるため未実装)

### 1. Azure Key Vault 統合

#### **目的:**
API キーやシークレットを Key Vault で一元管理

#### **実装案:**

**Key Vault 作成:**
```bicep
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'kv-ocr-demo'
  location: location
  properties: {
    sku: { family: 'A', name: 'standard' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
  }
}

// Computer Vision キーを保存
resource cvPrimaryKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'cv-primary-key'
  properties: {
    value: cvPrimary.listKeys().key1
  }
}
```

**APIM からの参照:**
```bicep
resource namedValueCvKey 'Microsoft.ApiManagement/service/namedValues@2023-05-01-preview' = {
  parent: apim
  name: 'cv-primary-key'
  properties: {
    displayName: 'cv-primary-key'
    keyVault: {
      secretIdentifier: '${keyVault.properties.vaultUri}secrets/cv-primary-key'
    }
    secret: true
  }
}
```

**メリット:**
- ✅ シークレットのローテーションが容易
- ✅ アクセス監査ログ
- ✅ RBAC による細かいアクセス制御

### 2. Application Insights 統合

#### **目的:**
深い可観測性と分散トレーシング

#### **実装案:**

**Application Insights 作成:**
```bicep
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-ocr-demo'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
  }
}
```

**APIM ロガー設定:**
```bicep
resource apimLogger 'Microsoft.ApiManagement/service/loggers@2023-05-01-preview' = {
  parent: apim
  name: 'appinsights-logger'
  properties: {
    loggerType: 'applicationInsights'
    credentials: {
      instrumentationKey: appInsights.properties.InstrumentationKey
    }
  }
}

resource diagnostics 'Microsoft.ApiManagement/service/apis/diagnostics@2023-05-01-preview' = {
  parent: computerVisionApi
  name: 'applicationinsights'
  properties: {
    loggerId: apimLogger.id
    alwaysLog: 'allErrors'
    sampling: {
      samplingType: 'fixed'
      percentage: 100
    }
  }
}
```

**Python クライアント統合:**
```python
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.trace.tracer import Tracer

# トレーサー設定
tracer = Tracer(
    exporter=AzureExporter(
        connection_string=f"InstrumentationKey={instrumentation_key}"
    ),
    sampler=ProbabilitySampler(1.0)
)

# OCR 処理のトレース
with tracer.span(name="process_image"):
    result = await client.process_image(image_data)
```

**メリット:**
- ✅ 分散トレーシング
- ✅ アプリケーションマップ
- ✅ リアルタイムメトリクス
- ✅ カスタムイベント追跡

### 3. マネージドID の使用

#### **目的:**
パスワードレス認証でセキュリティ向上

#### **実装案:**

**APIM にシステムマネージドID を付与:**
```bicep
resource apim 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: apimName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  // ...
}
```

**Key Vault アクセスポリシー:**
```bicep
resource keyVaultAccessPolicy 'Microsoft.KeyVault/vaults/accessPolicies@2023-07-01' = {
  name: 'add'
  parent: keyVault
  properties: {
    accessPolicies: [
      {
        tenantId: subscription().tenantId
        objectId: apim.identity.principalId
        permissions: {
          secrets: ['get', 'list']
        }
      }
    ]
  }
}
```

**Computer Vision への RBAC:**
```bicep
// Cognitive Services User ロール
var cognitiveServicesUserRole = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource cvPrimaryRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: cvPrimary
  name: guid(cvPrimary.id, apim.id, cognitiveServicesUserRole)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRole)
    principalId: apim.identity.principalId
    principalType: 'ServicePrincipal'
  }
}
```

**APIM ポリシーでマネージドID 使用:**
```xml
<authentication-managed-identity resource="https://cognitiveservices.azure.com" />
```

**メリット:**
- ✅ シークレット不要
- ✅ 自動ローテーション
- ✅ ゼロトラスト原則

### 4. マルチリージョン展開

#### **目的:**
高可用性と災害復旧

#### **実装案:**

**セカンダリリージョン (West Japan):**
```bicep
// West Japan の Computer Vision
module westJapanCV './modules/computer-vision.bicep' = {
  name: 'cv-west-japan'
  params: {
    location: 'westjapan'
    computerVisionName: 'cv-ocr-demo-wj-primary'
    sku: 'S1'
    tags: union(commonTags, { region: 'west-japan' })
  }
}

// APIM のマルチリージョン
resource apim 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: apimName
  location: 'japaneast'
  sku: {
    name: 'Premium' // Premium 必須
    capacity: 1
  }
  properties: {
    additionalLocations: [
      {
        location: 'westjapan'
        sku: {
          name: 'Premium'
          capacity: 1
        }
      }
    ]
  }
}
```

**Traffic Manager によるグローバル負荷分散:**
```bicep
resource trafficManagerProfile 'Microsoft.Network/trafficManagerProfiles@2022-04-01' = {
  name: 'tm-ocr-demo'
  location: 'global'
  properties: {
    profileStatus: 'Enabled'
    trafficRoutingMethod: 'Performance'
    dnsConfig: {
      relativeName: 'ocr-demo'
      ttl: 60
    }
    monitorConfig: {
      protocol: 'HTTPS'
      port: 443
      path: '/health'
      intervalInSeconds: 30
      timeoutInSeconds: 10
      toleratedNumberOfFailures: 3
    }
    endpoints: [
      {
        name: 'japan-east'
        type: 'Microsoft.Network/trafficManagerProfiles/azureEndpoints'
        properties: {
          targetResourceId: apim.id
          endpointStatus: 'Enabled'
          weight: 1
          priority: 1
        }
      }
      {
        name: 'west-japan'
        type: 'Microsoft.Network/trafficManagerProfiles/azureEndpoints'
        properties: {
          targetResourceId: apim.properties.additionalLocations[0].id
          endpointStatus: 'Enabled'
          weight: 1
          priority: 2
        }
      }
    ]
  }
}
```

**メリット:**
- ✅ リージョン障害時の自動フェイルオーバー
- ✅ レイテンシー最適化
- ✅ 99.99% SLA (Premium APIM)

---

## 🎯 実装優先順位

### 即座に実装可能 (既に実装済み)
- ✅ IaC (Bicep)
- ✅ エラーハンドリング・リトライ
- ✅ 診断設定
- ✅ 高度なサーキットブレーカー
- ✅ コスト最適化タグ
- ✅ 負荷テスト自動化

### 短期 (1-2週間)
1. **Key Vault 統合** - セキュリティ最優先
2. **Application Insights** - 可観測性向上

### 中期 (1-2ヶ月)
3. **マネージドID** - ゼロトラスト強化
4. **追加監視ダッシュボード** - Azure Workbooks

### 長期 (3ヶ月以上)
5. **マルチリージョン** - エンタープライズグレード高可用性
6. **CI/CD パイプライン拡張** - Blue/Green デプロイ

---

## 📊 コスト見積もり

### 現在の構成 (Japan East)
| リソース | SKU | 月額概算 (JPY) |
|---------|-----|---------------|
| APIM | Developer | ¥7,000 |
| Computer Vision x3 | S1 | ¥150 x 3 = ¥450 |
| Log Analytics | PerGB2018 | ¥500 (10GB/月) |
| **合計** | | **¥7,950** |

### Key Vault 追加時
| リソース | 追加コスト |
|---------|-----------|
| Key Vault | ¥65 (10,000 operations) |
| **新合計** | **¥8,015** |

### Application Insights 追加時
| リソース | 追加コスト |
|---------|-----------|
| App Insights | ¥800 (5GB ingestion) |
| **新合計** | **¥8,815** |

### マルチリージョン構成 (Premium APIM)
| リソース | SKU | 月額概算 |
|---------|-----|----------|
| APIM Premium x2 | 2 units | ¥350,000 |
| CV West Japan x3 | S1 | ¥450 |
| Traffic Manager | Standard | ¥700 |
| **合計** | | **¥351,150** |

> **注:** Premium APIM はコストが高額なため、エンタープライズ環境のみ推奨

---

## 🔒 セキュリティチェックリスト

### 実装済み
- ✅ HTTPS 通信
- ✅ API キーによる認証
- ✅ Named Values でのシークレット管理
- ✅ CORS 設定
- ✅ レート制限 (Computer Vision S1)

### 推奨事項
- ⬜ Key Vault 統合
- ⬜ マネージドID
- ⬜ APIM IP 制限
- ⬜ VNet 統合
- ⬜ Private Endpoint
- ⬜ Azure Defender for APIs

---

## 📚 参考リソース

### 公式ドキュメント
- [Azure API Management ベストプラクティス](https://learn.microsoft.com/azure/api-management/api-management-howto-deploy-multi-region)
- [Computer Vision ベストプラクティス](https://learn.microsoft.com/azure/cognitive-services/computer-vision/how-to/call-read-api)
- [Azure Monitor ベストプラクティス](https://learn.microsoft.com/azure/azure-monitor/best-practices)
- [Bicep ベストプラクティス](https://learn.microsoft.com/azure/azure-resource-manager/bicep/best-practices)

### アーキテクチャパターン
- [Circuit Breaker Pattern](https://learn.microsoft.com/azure/architecture/patterns/circuit-breaker)
- [Retry Pattern](https://learn.microsoft.com/azure/architecture/patterns/retry)
- [Health Endpoint Monitoring](https://learn.microsoft.com/azure/architecture/patterns/health-endpoint-monitoring)

---

## 🤝 貢献

改善提案や質問は Issue または Pull Request でお願いします。

---

**Last Updated:** 2025-10-16  
**Version:** 1.0  
**Author:** OCR Demo Team
