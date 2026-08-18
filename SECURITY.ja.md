# Security Policy

## Supported Versions

現在サポートされているバージョン:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

---

## Reporting a Vulnerability

セキュリティ上の脆弱性を発見した場合は、**公開のイシュートラッカーには投稿せず**、以下の手順に従って報告してください。

### 報告方法

1. **GitHub Security Advisory** を使用 (推奨)
   - リポジトリの "Security" タブ → "Report a vulnerability"
   - または [こちら](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/security/advisories/new)

2. **メールでの報告**
   - 送信先: security@your-domain.com
   - 件名: [SECURITY] OCR Demo Vulnerability Report

### 報告に含めるべき情報

- **脆弱性の種類** (例: 認証バイパス、情報漏洩、コード実行)
- **影響を受けるコンポーネント** (ファイル名、関数名など)
- **再現手順** (できるだけ詳細に)
- **影響範囲** (どのような攻撃が可能か)
- **PoC (概念実証コード)** (オプション)
- **提案する修正方法** (あれば)

### 例

```markdown
## 脆弱性の概要
Azure Computer Vision APIキーがログに出力される

## 影響を受けるコンポーネント
scenario_a_client/client.py, Line 123

## 再現手順
1. DEBUG=trueで実行
2. ログファイルを確認
3. APIキーが平文で記録されている

## 影響範囲
攻撃者がログファイルにアクセスできる場合、APIキーを取得可能

## 提案する修正
ログ出力時にAPIキーをマスク (例: "***...last4chars")
```

---

## 対応プロセス

### 1. 確認 (24時間以内)

報告を受領したことを確認し、初期評価を行います。

### 2. 調査 (3営業日以内)

- 脆弱性の再現
- 影響範囲の特定
- 深刻度の評価 (CVSS v3.1スコア)

### 3. 修正 (深刻度による)

| 深刻度 | 対応目標 |
|--------|----------|
| Critical (CVSS 9.0-10.0) | 24時間以内 |
| High (CVSS 7.0-8.9) | 7日以内 |
| Medium (CVSS 4.0-6.9) | 30日以内 |
| Low (CVSS 0.1-3.9) | 90日以内 |

### 4. リリース

- パッチバージョンをリリース
- セキュリティアドバイザリを公開
- 影響を受けるユーザーに通知

---

## セキュリティのベストプラクティス

### 環境変数の管理

**❌ ハードコードしない:**
```python
# 悪い例
api_key = "be20989c82b241d9b92e74f9f9d7c786"
```

**✅ 環境変数を使用:**
```python
# 良い例
import os
api_key = os.getenv('OCR_KEY')
if not api_key:
    raise ValueError("OCR_KEY environment variable is required")
```

### .env ファイルの保護

**必ず `.gitignore` に追加:**
```gitignore
# Environment files
.env
.env.*
!.env.example
!.env*.template
```

**テンプレートのみをコミット:**
```bash
# .env.example (コミット可)
OCR_ENDPOINTS=https://your-endpoint.cognitiveservices.azure.com/
OCR_KEYS=your-key-here

# .env (コミット禁止)
OCR_ENDPOINTS=https://actual-endpoint.cognitiveservices.azure.com/
OCR_KEYS=be20989c82b241d9b92e74f9f9d7c786
```

### Azure リソースのセキュリティ

1. **ネットワークアクセス制限**
   ```bicep
   networkAcls: {
     defaultAction: 'Deny'
     ipRules: [
       {
         value: 'YOUR_IP_ADDRESS'
       }
     ]
   }
   ```

2. **マネージドID の使用**
   ```python
   from azure.identity import DefaultAzureCredential
   credential = DefaultAzureCredential()
   ```

3. **APIキーのローテーション**
   - 定期的にキーを再生成 (90日ごと推奨)
   - Azure Key Vault での管理を検討

### ログのセキュリティ

**機密情報をマスク:**
```python
import logging

def mask_key(key: str) -> str:
    """APIキーの最後の4文字以外をマスク"""
    if len(key) <= 4:
        return "****"
    return f"****{key[-4:]}"

logging.info(f"Using API key: {mask_key(api_key)}")
```

### 依存関係の管理

**定期的なアップデート:**
```bash
# 脆弱性スキャン
pip install safety
safety check --json

# 依存関係のアップデート
pip install --upgrade -r requirements.txt
```

---

## 既知の制限事項

### 1. APIキーの保護

このプロジェクトは、Azure Computer Vision APIキーを環境変数で管理しています。本番環境では、以下のいずれかの方法を推奨します:

- **Azure Key Vault** を使用
- **マネージドID** を使用 (Azure内でのデプロイ時)
- **GitHub Secrets** (CI/CDパイプライン)

### 2. ネットワークセキュリティ

デフォルト設定では、Computer Visionエンドポイントはパブリックアクセスを許可しています。本番環境では:

- **Private Endpoint** を設定
- **Virtual Network** 統合を検討
- **IP制限** を有効化

### 3. レート制限

429エラー (Too Many Requests) を適切に処理していますが、DDoS攻撃への完全な対策ではありません。本番環境では:

- **Azure Front Door** または **API Management** でレート制限
- **Azure Monitor** でアラート設定

---

## セキュリティアップデート

セキュリティアップデートは、以下の方法で通知されます:

1. **GitHub Security Advisories** ([購読はこちら](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/security/advisories))
2. **GitHub Releases** (セキュリティタグ付き)
3. **README.md** のバナー (Critical/High の場合)

---

## 連絡先

セキュリティに関する質問:
- **GitHub Security Advisory**: [こちら](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/security/advisories)
- **Email**: security@your-domain.com

一般的な質問:
- **GitHub Issues**: [こちら](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/issues)
- **GitHub Discussions**: [こちら](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/discussions)

---

## 謝辞

セキュリティ上の脆弱性を責任を持って報告していただいた方々に感謝いたします。

---

**最終更新: 2025-10-17**
