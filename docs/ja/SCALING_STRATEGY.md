# 分間2000リクエスト対応スケーリング戦略

## 📊 目標要件

- **目標スループット**: 2000リクエスト/分 = 約33.3リクエスト/秒 (TPS)
- **現在の制限**: 各Computer Vision S1リソース = 10 TPS (デフォルト)
- **必要な対応**: スケールアップ + スケールアウト戦略

---

## 🎯 推奨アーキテクチャ

### オプション1: マルチリージョン + クォータ増加 (推奨)

```
┌─────────────────────────────────────────────────────────┐
│ クライアントアプリケーション (Scenario A または B)       │
│ - 並行処理: asyncio (Python), Promise.all (Node.js)    │
│ - 接続プール: 50-100並行接続                             │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 負荷分散レイヤー (Scenario Aクライアント内蔵)           │
│ - EWMA-based endpoint selection                         │
│ - Exponential backoff with jitter                       │
│ - Circuit breaker (cooldown 60s)                        │
└────┬──────────────┬──────────────┬──────────────────────┘
     │              │              │
     ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Region 1 │  │ Region 2 │  │ Region 3 │
│ East US  │  │Japan East│  │West EU   │
│ 20 TPS   │  │ 20 TPS   │  │ 20 TPS   │
└──────────┘  └──────────┘  └──────────┘
     ↓              ↓              ↓
[Computer Vision] [Computer Vision] [Computer Vision]
   S1 + Quota       S1 + Quota       S1 + Quota
   Increase         Increase         Increase
```

**スループット計算:**
- 3リージョン × 20 TPS (クォータ増加後) = **60 TPS**
- **余裕率**: 60 TPS ÷ 33.3 TPS (目標) = **1.8倍** ✅

---

### オプション2: APIM + 複数Computer Visionインスタンス

```
┌─────────────────────────────────────────────────────────┐
│ クライアントアプリケーション (Scenario B)                │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ Azure API Management (Premium tier)                     │
│ - Rate limiting policy (per-backend)                    │
│ - Circuit breaker policy                                │
│ - Load balancer with weighted round-robin               │
│ - 429エラー時のリトライ + フォールバック                 │
└────┬─────┬──────┬──────┬──────┬──────────────────────┘
     │     │      │      │      │
     ▼     ▼      ▼      ▼      ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
│CV-1 JE ││CV-2 JE ││CV-3 JE ││CV-4 EU ││CV-5 US │
│10 TPS  ││10 TPS  ││10 TPS  ││10 TPS  ││10 TPS  │
└────────┘└────────┘└────────┘└────────┘└────────┘
```

**スループット計算:**
- 5インスタンス × 10 TPS (デフォルト) = **50 TPS**
- **余裕率**: 50 TPS ÷ 33.3 TPS = **1.5倍** ✅

---

## 📋 実装手順

### ステップ1: Computer Vision クォータ増加リクエスト

#### 1.1 Azureサポートチケット作成

Azure Portalで各Computer Visionリソースに対してサポートチケットを起票:

```plaintext
件名: Computer Vision API - TPS増加リクエスト
問題の種類: クォータ/サブスクリプション
サービスの種類: Cognitive Services - Computer Vision

必要情報:
1. 使用ケース: 高頻度OCR処理 (レシート/請求書処理システム)
2. 現在の制限: 10 TPS
3. 希望する制限: 20 TPS (または 30 TPS)
4. 影響を受けるリソース:
   - ocr-test-a-cv-eastus (East US)
   - ocr-test-a-cv-japaneast (Japan East)
   - ocr-test-a-cv-westeurope (West Europe)
5. スロットリング頻度: 現在ピーク時に429エラー発生
6. 使用履歴: Azure Portal メトリクスで確認済み
```

**承認期間**: 通常2-5営業日

#### 1.2 代替案: S0 → S1確認

S0とS1の違いを確認:

| Tier | Default TPS | 増加可能? | 価格 (概算) |
|------|-------------|----------|-------------|
| S0 (Standard) | 10 TPS | はい (最大50 TPS) | 低 |
| S1 (Enterprise) | 10 TPS | はい (最大50+ TPS) | 高 |

現在のBicepでは `sku: 'S1'` を使用しているため、クォータ増加申請が可能です。

---

### ステップ2: インフラストラクチャのスケーリング

#### 2.1 追加リージョンのデプロイ (オプショナル)

同一リージョン内で複数インスタンスをデプロイする場合:

**Bicep修正例** (`infrastructure/japan-computer-vision.bicep`):

```bicep
// 3インスタンス → 5インスタンスに増加
var endpoints = [
  { name: 'primary', displayName: 'Primary Endpoint', suffix: 'primary' }
  { name: 'secondary', displayName: 'Secondary Endpoint', suffix: 'secondary' }
  { name: 'tertiary', displayName: 'Tertiary Endpoint', suffix: 'tertiary' }
  { name: 'quaternary', displayName: 'Quaternary Endpoint', suffix: 'quaternary' }  // 追加
  { name: 'quinary', displayName: 'Quinary Endpoint', suffix: 'quinary' }  // 追加
]
```

**デプロイコマンド:**

```bash
# Japan Eastリージョンに5インスタンスデプロイ
cd infrastructure
./deploy-japan-east.sh

# または手動で
az deployment sub create \
  --location japaneast \
  --template-file japan-computer-vision.bicep \
  --parameters resourceGroupName=rg-ocr-demo-japan-east \
               computerVisionBaseName=cv-ocr-demo-je
```

---

### ステップ3: クライアントアプリケーションの最適化

#### 3.1 Scenario A: 並行処理の最適化

**`scenario_a_client/client.py` 修正:**

```python
# 並行接続数を増やす
async def batch_process_images(
    self,
    image_data_list: List[bytes],
    max_concurrent: int = 50  # 10 → 50に増加
) -> List[Tuple[Optional[Dict], Dict]]:
    """複数画像を並行処理"""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_semaphore(image_data):
        async with semaphore:
            return await self.ocr_with_fallback(image_data)
    
    return await asyncio.gather(*[
        process_with_semaphore(img) for img in image_data_list
    ])
```

**環境変数調整** (`.env`):

```bash
# タイムアウト設定
GLOBAL_TIMEOUT_MS=15000  # 12000 → 15000に増加 (高負荷時のバッファ)

# リトライ設定
MAX_RETRIES_PER_REQUEST=3  # 2 → 3に増加

# フォールバックしきい値
FALLBACK_SINGLE_MS=2000  # 1800 → 2000に緩和
```

#### 3.2 Scenario B: APIM負荷分散ポリシー最適化

**`infrastructure/apim/policies/ocr-load-balancer-policy.xml` 修正:**

```xml
<policies>
    <inbound>
        <base />
        <!-- ラウンドロビン + 重み付け負荷分散 -->
        <set-variable name="backendIndex" value="@(context.RequestId.GetHashCode() % 5)" />
        <choose>
            <when condition="@((int)context.Variables[&quot;backendIndex&quot;] == 0)">
                <set-backend-service backend-id="cv-primary" />
            </when>
            <when condition="@((int)context.Variables[&quot;backendIndex&quot;] == 1)">
                <set-backend-service backend-id="cv-secondary" />
            </when>
            <when condition="@((int)context.Variables[&quot;backendIndex&quot;] == 2)">
                <set-backend-service backend-id="cv-tertiary" />
            </when>
            <when condition="@((int)context.Variables[&quot;backendIndex&quot;] == 3)">
                <set-backend-service backend-id="cv-quaternary" />
            </when>
            <otherwise>
                <set-backend-service backend-id="cv-quinary" />
            </otherwise>
        </choose>
    </inbound>
    
    <backend>
        <!-- 429エラー時のリトライ: 別のバックエンドへフォールバック -->
        <retry condition="@(context.Response.StatusCode == 429)" 
               count="4" 
               interval="0.5" 
               delta="0.5">
            <!-- 次のバックエンドを試行 -->
            <set-variable name="backendIndex" 
                value="@((int)context.Variables[&quot;backendIndex&quot;] + 1) % 5" />
            <choose>
                <when condition="@((int)context.Variables[&quot;backendIndex&quot;] == 0)">
                    <set-backend-service backend-id="cv-primary" />
                </when>
                <!-- ... 他のバックエンド ... -->
            </choose>
            <base />
        </retry>
    </backend>
    
    <outbound>
        <base />
        <set-header name="X-Backend-Used" exists-action="override">
            <value>@("backend-" + context.Variables["backendIndex"])</value>
        </set-header>
    </outbound>
</policies>
```

---

### ステップ4: 負荷テストと検証

#### 4.1 ローカル負荷テスト

**新規テストスクリプト作成** (`scripts/high_load_test.py`):

```python
"""
2000リクエスト/分 (33 TPS) 負荷テスト
"""
import asyncio
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scenario_a_client"))
from client import OCRClient

async def load_test_33tps():
    """33 TPSで60秒間負荷テスト"""
    client = OCRClient()
    
    # テスト画像準備
    test_image_path = Path(__file__).parent.parent / "test_images" / "printed_text.jpg"
    with open(test_image_path, 'rb') as f:
        image_data = f.read()
    
    total_requests = 2000  # 60秒で2000リクエスト
    duration = 60  # 秒
    target_tps = total_requests / duration  # 33.33 TPS
    
    results = {
        'success': 0,
        'failed': 0,
        'rate_limited': 0,
        'latencies': []
    }
    
    print(f"🚀 負荷テスト開始: {target_tps:.1f} TPS × {duration}秒")
    print(f"   総リクエスト数: {total_requests}")
    
    start_time = time.time()
    
    async def send_request(request_num):
        """単一リクエスト送信"""
        try:
            req_start = time.time()
            result, metadata = await client.ocr_with_fallback(image_data)
            latency = (time.time() - req_start) * 1000
            
            if result:
                results['success'] += 1
                results['latencies'].append(latency)
            else:
                if metadata.get('status_code') == 429:
                    results['rate_limited'] += 1
                else:
                    results['failed'] += 1
            
            if request_num % 100 == 0:
                print(f"   Progress: {request_num}/{total_requests} requests")
                
        except Exception as e:
            results['failed'] += 1
            print(f"   Error at request {request_num}: {e}")
    
    # バッチ処理: 33リクエストを1秒ごとに送信
    batch_size = int(target_tps)
    for batch_num in range(duration):
        batch_start = time.time()
        
        # 並行実行
        tasks = [send_request(batch_num * batch_size + i) for i in range(batch_size)]
        await asyncio.gather(*tasks)
        
        # タイミング調整
        elapsed = time.time() - batch_start
        if elapsed < 1.0:
            await asyncio.sleep(1.0 - elapsed)
    
    total_time = time.time() - start_time
    
    # 結果サマリー
    print(f"\n📊 負荷テスト完了")
    print(f"   実行時間: {total_time:.2f}秒")
    print(f"   成功: {results['success']} ({results['success']/total_requests*100:.1f}%)")
    print(f"   失敗: {results['failed']}")
    print(f"   レート制限: {results['rate_limited']}")
    print(f"   実効TPS: {results['success']/total_time:.2f}")
    
    if results['latencies']:
        latencies = sorted(results['latencies'])
        print(f"\n   レイテンシー:")
        print(f"     平均: {sum(latencies)/len(latencies):.0f}ms")
        print(f"     中央値: {latencies[len(latencies)//2]:.0f}ms")
        print(f"     P95: {latencies[int(len(latencies)*0.95)]:.0f}ms")
        print(f"     P99: {latencies[int(len(latencies)*0.99)]:.0f}ms")

if __name__ == "__main__":
    asyncio.run(load_test_33tps())
```

**実行:**

```bash
# 仮想環境アクティブ化
source .venv/bin/activate

# 負荷テスト実行
python scripts/high_load_test.py
```

#### 4.2 Azure Load Testing (推奨)

Azure Load Testingサービスを使用した本格的な負荷テスト:

```bash
# Azure Load Testing リソース作成
az load create \
  --name ocr-load-test \
  --resource-group rg-ocr-demo-japan-east \
  --location japaneast

# JMeterテストプラン実行
az load test-run create \
  --test-id ocr-high-load-test \
  --load-test-resource ocr-load-test \
  --resource-group rg-ocr-demo-japan-east \
  --test-plan ./load_test_plan.jmx \
  --engine-instances 5 \
  --parameters threads=200 duration=300
```

---

## 💰 コスト見積もり

### Computer Vision API (S1 tier)

| 構成 | インスタンス数 | TPS/インスタンス | 月額コスト (概算) |
|------|---------------|-----------------|------------------|
| **現在** | 3 (マルチリージョン) | 10 TPS | ~¥30,000 |
| **オプション1** | 3 (クォータ増加) | 20 TPS | ~¥30,000 (同額) |
| **オプション2** | 5 (追加インスタンス) | 10 TPS | ~¥50,000 |
| **オプション3** | 5 (追加+クォータ増加) | 20 TPS | ~¥50,000 |

**注**: 
- クォータ増加自体は無料 (使用量に応じた従量課金)
- 料金は実際のAPI呼び出し回数に基づく
- [Computer Vision価格ページ](https://azure.microsoft.com/pricing/details/cognitive-services/computer-vision/)

### APIM (Premium tier)

| 項目 | 月額コスト (概算) |
|------|------------------|
| APIM Premium (1 unit) | ~¥370,000/月 |
| APIM Developer (開発用) | ~¥5,000/月 |

**推奨**: Scenario Bは開発/テスト用にDeveloper tierを継続使用

---

## 🎯 推奨実装プラン

### フェーズ1: クォータ増加 (1週間)

1. ✅ Azureサポートチケット起票 (3リージョン × 20 TPS申請)
2. ✅ 承認待ち (2-5営業日)
3. ✅ 承認後、負荷テストで検証

**期待結果**: 60 TPS (3リージョン × 20 TPS)

### フェーズ2: クライアント最適化 (並行)

1. ✅ 並行接続数を50に増加
2. ✅ タイムアウト/リトライパラメータ調整
3. ✅ バッチ処理の実装

**期待結果**: クライアント側ボトルネック解消

### フェーズ3: 検証とモニタリング (1週間)

1. ✅ 33 TPS負荷テスト実行
2. ✅ Azure Monitorメトリクス確認:
   - `ProcessedImages` (成功数)
   - `ClientErrors` (429エラー数)
   - `Latency` (P50/P95/P99)
3. ✅ Application Insightsでエンドツーエンド追跡

---

## 📈 モニタリング設定

### Azure Monitor アラート設定

```bash
# 429エラー率が10%超えた場合にアラート
az monitor metrics alert create \
  --name ocr-rate-limit-alert \
  --resource-group rg-ocr-demo-japan-east \
  --scopes /subscriptions/{subscription-id}/resourceGroups/rg-ocr-demo-japan-east/providers/Microsoft.CognitiveServices/accounts/ocr-test-a-cv-eastus \
  --condition "avg ClientErrors where ResultType == 429 > 10" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action email admin@example.com
```

### Application Insights クエリ

```kusto
// レート制限発生状況
requests
| where timestamp > ago(1h)
| where resultCode == "429"
| summarize Count=count() by bin(timestamp, 1m), cloud_RoleName
| render timechart

// レイテンシー分布
requests
| where timestamp > ago(1h)
| where success == true
| summarize 
    P50=percentile(duration, 50),
    P95=percentile(duration, 95),
    P99=percentile(duration, 99)
    by bin(timestamp, 5m)
| render timechart
```

---

## 🔧 トラブルシューティング

### 問題1: 429エラーが継続発生

**症状**: クォータ増加後も429エラー

**原因候補**:
1. クォータ増加が反映されていない
2. 特定エンドポイントに負荷集中
3. リトライ処理が適切でない

**解決策**:
```bash
# クォータ確認
az cognitiveservices account show \
  --name ocr-test-a-cv-eastus \
  --resource-group rg-ocr-demo-japan-east \
  --query "properties.quotaLimit"

# 負荷分散確認 (Application Insights)
requests
| where timestamp > ago(10m)
| summarize Count=count() by customDimensions.endpoint
```

### 問題2: レイテンシー増加

**症状**: P95レイテンシーが3000ms超え

**原因候補**:
1. ネットワーク遅延 (リージョン間通信)
2. Computer Vision側の処理遅延
3. 大きな画像サイズ

**解決策**:
```python
# 画像圧縮処理追加
from scenario_a_client.image_utils import ImageProcessor

# 4MB超の画像を自動リサイズ
processed_data, metadata = ImageProcessor.process_image(image_data)
result, ocr_metadata = await client.ocr_with_fallback(processed_data)
```

---

## 📚 参考資料

- [Azure Computer Vision 価格](https://azure.microsoft.com/pricing/details/cognitive-services/computer-vision/)
- [Azure Computer Vision FAQ - TPS増加](https://learn.microsoft.com/azure/ai-services/computer-vision/faq#how-can-i-increase-the-transactions-per-second-tps-allowed-by-the-service)
- [Azure サポートチケット作成](https://azure.microsoft.com/support/create-ticket/)
- [Azure Load Testing ドキュメント](https://learn.microsoft.com/azure/load-testing/)
- [APIM 負荷分散ポリシー](https://learn.microsoft.com/azure/api-management/api-management-sample-flexible-throttling)

---

## ✅ チェックリスト

### 実装前
- [ ] 現在のAPI使用量を確認 (Azure Monitor)
- [ ] ピーク時のTPS測定
- [ ] コスト承認取得

### 実装中
- [ ] Computer Vision クォータ増加チケット起票
- [ ] クライアントコード修正 (並行処理)
- [ ] 環境変数調整

### 実装後
- [ ] 33 TPS負荷テスト実行
- [ ] 429エラー率 < 1%確認
- [ ] P95レイテンシー < 2500ms確認
- [ ] コスト監視設定
- [ ] アラート設定

---

**作成日**: 2025-01-16  
**更新日**: 2025-01-16  
**対象バージョン**: v1.0 (SDK Migration完了後)
