# Security Policy# Security Policy



**Read this in other languages:** English | [简体中文](SECURITY.zh.md) | [日本語](SECURITY.ja.md)## Supported Versions



## Reporting a Vulnerability現在サポートされているバージョン:



We take the security of this project seriously. If you discover a security vulnerability, please report it responsibly.| Version | Supported          |

| ------- | ------------------ |

### How to Report| 1.0.x   | :white_check_mark: |



**Do not** create public GitHub issues for security vulnerabilities.---



Instead, please report vulnerabilities through one of the following methods:## Reporting a Vulnerability



1. **GitHub Security Advisories** (Recommended)セキュリティ上の脆弱性を発見した場合は、**公開のイシュートラッカーには投稿せず**、以下の手順に従って報告してください。

   - Go to the [Security tab](https://github.com/sasukeh/ocr-demo-w-sdk/security/advisories)

   - Click "Report a vulnerability"### 報告方法

   - Fill out the form with details

1. **GitHub Security Advisory** を使用 (推奨)

2. **Direct Email**   - リポジトリの "Security" タブ → "Report a vulnerability"

   - Send details to the maintainers   - または [こちら](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/security/advisories/new)

   - Include "SECURITY" in the subject line

   - Encrypt sensitive information if possible2. **メールでの報告**

   - 送信先: security@your-domain.com

### What to Include   - 件名: [SECURITY] OCR Demo Vulnerability Report



When reporting a vulnerability, please include:### 報告に含めるべき情報



- **Description**: Detailed description of the vulnerability- **脆弱性の種類** (例: 認証バイパス、情報漏洩、コード実行)

- **Impact**: Potential impact and severity- **影響を受けるコンポーネント** (ファイル名、関数名など)

- **Reproduction Steps**: Step-by-step instructions to reproduce- **再現手順** (できるだけ詳細に)

- **Affected Versions**: Which versions are affected- **影響範囲** (どのような攻撃が可能か)

- **Proof of Concept**: Code or screenshots demonstrating the issue (if applicable)- **PoC (概念実証コード)** (オプション)

- **Suggested Fix**: If you have ideas for mitigation (optional)- **提案する修正方法** (あれば)



### Response Timeline### 例



- **Initial Response**: Within 48 hours```markdown

- **Status Update**: Within 5 business days## 脆弱性の概要

- **Fix Timeline**: Depends on severityAzure Computer Vision APIキーがログに出力される

  - Critical: Within 7 days

  - High: Within 14 days## 影響を受けるコンポーネント

  - Medium: Within 30 daysscenario_a_client/client.py, Line 123

  - Low: Within 90 days

## 再現手順

---1. DEBUG=trueで実行

2. ログファイルを確認

## Security Best Practices3. APIキーが平文で記録されている



### API Key Management## 影響範囲

攻撃者がログファイルにアクセスできる場合、APIキーを取得可能

**Never commit API keys or secrets to the repository.**

## 提案する修正

✅ **DO:**ログ出力時にAPIキーをマスク (例: "***...last4chars")

- Store credentials in environment variables```

- Use `.env` files (add to `.gitignore`)

- Use Azure Key Vault for production---

- Rotate keys regularly

## 対応プロセス

```bash

# .env file (never commit this)### 1. 確認 (24時間以内)

AZURE_CV_ENDPOINT=https://your-resource.cognitiveservices.azure.com/

AZURE_CV_KEY=your-api-key-here報告を受領したことを確認し、初期評価を行います。

```

### 2. 調査 (3営業日以内)

❌ **DON'T:**

- Hardcode credentials in source code- 脆弱性の再現

- Commit `.env` files to Git- 影響範囲の特定

- Share credentials in public channels- 深刻度の評価 (CVSS v3.1スコア)

- Use the same key across multiple environments

### 3. 修正 (深刻度による)

### Azure Resource Security

| 深刻度 | 対応目標 |

#### Network Security|--------|----------|

| Critical (CVSS 9.0-10.0) | 24時間以内 |

```bash| High (CVSS 7.0-8.9) | 7日以内 |

# Restrict access by IP| Medium (CVSS 4.0-6.9) | 30日以内 |

az cognitiveservices account network-rule add \| Low (CVSS 0.1-3.9) | 90日以内 |

  --resource-group ocr-demo-rg \

  --name ocr-demo-cv \### 4. リリース

  --ip-address "YOUR_IP_ADDRESS"

- パッチバージョンをリリース

# Enable private endpoints for production- セキュリティアドバイザリを公開

az network private-endpoint create \- 影響を受けるユーザーに通知

  --resource-group ocr-demo-rg \

  --name cv-private-endpoint \---

  --vnet-name ocr-vnet \

  --subnet default \## セキュリティのベストプラクティス

  --private-connection-resource-id "/subscriptions/.../cognitiveservices/accounts/ocr-demo-cv" \

  --connection-name cv-connection### 環境変数の管理

```

**❌ ハードコードしない:**

#### Managed Identity```python

# 悪い例

Use Managed Identity instead of API keys when possible:api_key = "be20989c82b241d9b92e74f9f9d7c786"

```

```python

from azure.identity import DefaultAzureCredential**✅ 環境変数を使用:**

from azure.ai.vision.imageanalysis import ImageAnalysisClient```python

# 良い例

credential = DefaultAzureCredential()import os

client = ImageAnalysisClient(api_key = os.getenv('OCR_KEY')

    endpoint=endpoint,if not api_key:

    credential=credential    raise ValueError("OCR_KEY environment variable is required")

)```

```

### .env ファイルの保護

### Application Security

**必ず `.gitignore` に追加:**

#### Input Validation```gitignore

# Environment files

Always validate input data:.env

.env.*

```python!.env.example

def validate_image(image_data: bytes) -> bool:!.env*.template

    """Validate image data before processing."""```

    # Check file size (max 20MB)

    if len(image_data) > 20 * 1024 * 1024:**テンプレートのみをコミット:**

        raise ValueError("Image too large")```bash

    # .env.example (コミット可)

    # Check image formatOCR_ENDPOINTS=https://your-endpoint.cognitiveservices.azure.com/

    allowed_formats = [b'\xFF\xD8\xFF', b'\x89PNG', b'GIF89a']OCR_KEYS=your-key-here

    if not any(image_data.startswith(fmt) for fmt in allowed_formats):

        raise ValueError("Invalid image format")# .env (コミット禁止)

    OCR_ENDPOINTS=https://actual-endpoint.cognitiveservices.azure.com/

    return TrueOCR_KEYS=be20989c82b241d9b92e74f9f9d7c786

``````



#### Rate Limiting### Azure リソースのセキュリティ



Implement rate limiting to prevent abuse:1. **ネットワークアクセス制限**

   ```bicep

```python   networkAcls: {

from functools import wraps     defaultAction: 'Deny'

from time import time, sleep     ipRules: [

       {

def rate_limit(max_calls: int, period: int):         value: 'YOUR_IP_ADDRESS'

    """Rate limiting decorator."""       }

    calls = []     ]

       }

    def decorator(func):   ```

        @wraps(func)

        def wrapper(*args, **kwargs):2. **マネージドID の使用**

            now = time()   ```python

            calls[:] = [c for c in calls if c > now - period]   from azure.identity import DefaultAzureCredential

               credential = DefaultAzureCredential()

            if len(calls) >= max_calls:   ```

                sleep_time = period - (now - calls[0])

                sleep(sleep_time)3. **APIキーのローテーション**

               - 定期的にキーを再生成 (90日ごと推奨)

            calls.append(time())   - Azure Key Vault での管理を検討

            return func(*args, **kwargs)

        return wrapper### ログのセキュリティ

    return decorator

**機密情報をマスク:**

@rate_limit(max_calls=10, period=60)```python

def process_ocr_request(image_path: str):import logging

    # Process request

    passdef mask_key(key: str) -> str:

```    """APIキーの最後の4文字以外をマスク"""

    if len(key) <= 4:

#### Error Handling        return "****"

    return f"****{key[-4:]}"

Avoid leaking sensitive information in error messages:

logging.info(f"Using API key: {mask_key(api_key)}")

```python```

try:

    result = ocr_client.analyze(image)### 依存関係の管理

except HttpResponseError as e:

    # DON'T expose internal details**定期的なアップデート:**

    # logger.error(f"Failed with key: {api_key}")```bash

    # 脆弱性スキャン

    # DO log safelypip install safety

    logger.error(f"OCR request failed: {e.status_code}")safety check --json

    raise RuntimeError("Image analysis failed")

```# 依存関係のアップデート

pip install --upgrade -r requirements.txt

### Dependency Security```



#### Regular Updates---



Keep dependencies up to date:## 既知の制限事項



```bash### 1. APIキーの保護

# Check for outdated packages

pip list --outdatedこのプロジェクトは、Azure Computer Vision APIキーを環境変数で管理しています。本番環境では、以下のいずれかの方法を推奨します:



# Update packages- **Azure Key Vault** を使用

pip install --upgrade -r requirements.txt- **マネージドID** を使用 (Azure内でのデプロイ時)

- **GitHub Secrets** (CI/CDパイプライン)

# Use pip-audit for vulnerability scanning

pip install pip-audit### 2. ネットワークセキュリティ

pip-audit

```デフォルト設定では、Computer Visionエンドポイントはパブリックアクセスを許可しています。本番環境では:



#### Vulnerability Scanning- **Private Endpoint** を設定

- **Virtual Network** 統合を検討

Enable GitHub Dependabot:- **IP制限** を有効化



1. Go to repository Settings → Security & analysis### 3. レート制限

2. Enable "Dependabot alerts"

3. Enable "Dependabot security updates"429エラー (Too Many Requests) を適切に処理していますが、DDoS攻撃への完全な対策ではありません。本番環境では:



---- **Azure Front Door** または **API Management** でレート制限

- **Azure Monitor** でアラート設定

## Security Checklist

---

### Before Deployment

## セキュリティアップデート

- [ ] All API keys stored in environment variables or Key Vault

- [ ] No secrets committed to repositoryセキュリティアップデートは、以下の方法で通知されます:

- [ ] Network security rules configured

- [ ] Managed Identity enabled (if applicable)1. **GitHub Security Advisories** ([購読はこちら](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/security/advisories))

- [ ] Rate limiting implemented2. **GitHub Releases** (セキュリティタグ付き)

- [ ] Input validation in place3. **README.md** のバナー (Critical/High の場合)

- [ ] Error handling doesn't expose sensitive data

- [ ] Dependencies scanned for vulnerabilities---

- [ ] HTTPS enforced for all endpoints

- [ ] Logging configured (without sensitive data)## 連絡先



### Regular Maintenanceセキュリティに関する質問:

- **GitHub Security Advisory**: [こちら](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/security/advisories)

- [ ] Review and rotate API keys quarterly- **Email**: security@your-domain.com

- [ ] Update dependencies monthly

- [ ] Review access permissions quarterly一般的な質問:

- [ ] Check security advisories weekly- **GitHub Issues**: [こちら](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/issues)

- [ ] Audit logs for suspicious activity monthly- **GitHub Discussions**: [こちら](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/discussions)

- [ ] Test disaster recovery procedures quarterly

---

---

## 謝辞

## Known Security Considerations

セキュリティ上の脆弱性を責任を持って報告していただいた方々に感謝いたします。

### Rate Limiting

---

Azure Computer Vision has default rate limits:

- Free tier: 20 calls/minute**最終更新: 2025-10-17**

- S1 tier: 10 calls/second

Implement client-side rate limiting to stay within these limits and prevent service disruption.

### Data Privacy

**Important:** OCR processing may involve sensitive data (PII, financial information, etc.)

- Ensure compliance with data protection regulations (GDPR, CCPA, etc.)
- Implement data retention policies
- Use Azure Private Link for sensitive workloads
- Consider data residency requirements
- Document data flows and processing

### Multi-Region Deployment

When using multiple regions for high availability:
- Each region should have its own API keys
- Implement secure failover mechanisms
- Ensure consistent security policies across regions
- Monitor all endpoints for suspicious activity

---

## Security Resources

### Azure Security Documentation

- [Azure Security Best Practices](https://learn.microsoft.com/azure/security/fundamentals/best-practices-and-patterns)
- [Cognitive Services Security](https://learn.microsoft.com/azure/cognitive-services/security-features)
- [Azure Key Vault](https://learn.microsoft.com/azure/key-vault/)
- [Managed Identity](https://learn.microsoft.com/azure/active-directory/managed-identities-azure-resources/)

### Tools

- [pip-audit](https://github.com/pypa/pip-audit) - Python dependency vulnerability scanner
- [Bandit](https://github.com/PyCQA/bandit) - Python security linter
- [Safety](https://github.com/pyupio/safety) - Dependency vulnerability checker

### Security Training

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Azure Security Center](https://learn.microsoft.com/azure/defender-for-cloud/)

---

## Contact

For security concerns, please use:
- GitHub Security Advisories (preferred)
- Direct contact with maintainers

**Do not discuss security issues in public channels.**

---

## Acknowledgments

We appreciate security researchers and contributors who help keep this project secure. Responsible disclosure is valued and acknowledged.

---

Thank you for helping keep this project secure! 🔒
