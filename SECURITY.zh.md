# 安全策略

**其他语言版本:** [English](SECURITY.md) | 简体中文 | [日本語](SECURITY.ja.md)

## 报告漏洞

我们非常重视本项目的安全性。如果您发现安全漏洞,请负责任地报告。

### 如何报告

**请勿**为安全漏洞创建公开的 GitHub issues。

请通过以下方法之一报告漏洞:

1. **GitHub 安全公告** (推荐)
   - 访问 [Security 标签页](https://github.com/sasukeh/ocr-demo-w-sdk/security/advisories)
   - 点击 "Report a vulnerability"
   - 填写详细信息表单

2. **直接电子邮件**
   - 向维护者发送详细信息
   - 在主题行中包含 "SECURITY"
   - 如果可能,加密敏感信息

### 应包含的内容

报告漏洞时,请包含:

- **描述**: 漏洞的详细描述
- **影响**: 潜在影响和严重性
- **重现步骤**: 重现问题的分步说明
- **受影响版本**: 哪些版本受到影响
- **概念验证**: 演示问题的代码或截图 (如适用)
- **建议修复**: 如果您有缓解措施的想法 (可选)

### 响应时间表

- **初始响应**: 48 小时内
- **状态更新**: 5 个工作日内
- **修复时间**: 取决于严重性
  - 严重: 7 天内
  - 高: 14 天内
  - 中等: 30 天内
  - 低: 90 天内

---

## 安全最佳实践

### API 密钥管理

**切勿将 API 密钥或机密提交到仓库。**

✅ **应该:**
- 将凭据存储在环境变量中
- 使用 `.env` 文件 (添加到 `.gitignore`)
- 在生产环境使用 Azure Key Vault
- 定期轮换密钥

```bash
# .env 文件 (切勿提交)
AZURE_CV_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_CV_KEY=your-api-key-here
```

❌ **不应该:**
- 在源代码中硬编码凭据
- 将 `.env` 文件提交到 Git
- 在公共渠道共享凭据
- 在多个环境中使用相同的密钥

### Azure 资源安全

#### 网络安全

```bash
# 通过 IP 限制访问
az cognitiveservices account network-rule add \
  --resource-group ocr-demo-rg \
  --name ocr-demo-cv \
  --ip-address "YOUR_IP_ADDRESS"

# 为生产环境启用专用端点
az network private-endpoint create \
  --resource-group ocr-demo-rg \
  --name cv-private-endpoint \
  --vnet-name ocr-vnet \
  --subnet default \
  --private-connection-resource-id "/subscriptions/.../cognitiveservices/accounts/ocr-demo-cv" \
  --connection-name cv-connection
```

#### 托管标识

尽可能使用托管标识而不是 API 密钥:

```python
from azure.identity import DefaultAzureCredential
from azure.ai.vision.imageanalysis import ImageAnalysisClient

credential = DefaultAzureCredential()
client = ImageAnalysisClient(
    endpoint=endpoint,
    credential=credential
)
```

### 应用程序安全

#### 输入验证

始终验证输入数据:

```python
def validate_image(image_data: bytes) -> bool:
    """在处理前验证图像数据。"""
    # 检查文件大小 (最大 20MB)
    if len(image_data) > 20 * 1024 * 1024:
        raise ValueError("图像太大")
    
    # 检查图像格式
    allowed_formats = [b'\xFF\xD8\xFF', b'\x89PNG', b'GIF89a']
    if not any(image_data.startswith(fmt) for fmt in allowed_formats):
        raise ValueError("无效的图像格式")
    
    return True
```

#### 速率限制

实施速率限制以防止滥用:

```python
from functools import wraps
from time import time, sleep

def rate_limit(max_calls: int, period: int):
    """速率限制装饰器。"""
    calls = []
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time()
            calls[:] = [c for c in calls if c > now - period]
            
            if len(calls) >= max_calls:
                sleep_time = period - (now - calls[0])
                sleep(sleep_time)
            
            calls.append(time())
            return func(*args, **kwargs)
        return wrapper
    return decorator

@rate_limit(max_calls=10, period=60)
def process_ocr_request(image_path: str):
    # 处理请求
    pass
```

#### 错误处理

避免在错误消息中泄露敏感信息:

```python
try:
    result = ocr_client.analyze(image)
except HttpResponseError as e:
    # 不要暴露内部详细信息
    # logger.error(f"失败,密钥: {api_key}")
    
    # 应该安全地记录
    logger.error(f"OCR 请求失败: {e.status_code}")
    raise RuntimeError("图像分析失败")
```

### 依赖项安全

#### 定期更新

保持依赖项更新:

```bash
# 检查过时的包
pip list --outdated

# 更新包
pip install --upgrade -r requirements.txt

# 使用 pip-audit 进行漏洞扫描
pip install pip-audit
pip-audit
```

#### 漏洞扫描

启用 GitHub Dependabot:

1. 进入仓库 Settings → Security & analysis
2. 启用 "Dependabot alerts"
3. 启用 "Dependabot security updates"

---

## 安全检查清单

### 部署前

- [ ] 所有 API 密钥存储在环境变量或 Key Vault 中
- [ ] 没有机密提交到仓库
- [ ] 配置网络安全规则
- [ ] 启用托管标识 (如适用)
- [ ] 实施速率限制
- [ ] 输入验证就位
- [ ] 错误处理不暴露敏感数据
- [ ] 依赖项已扫描漏洞
- [ ] 所有端点强制使用 HTTPS
- [ ] 配置日志记录 (不含敏感数据)

### 定期维护

- [ ] 每季度审查和轮换 API 密钥
- [ ] 每月更新依赖项
- [ ] 每季度审查访问权限
- [ ] 每周检查安全公告
- [ ] 每月审计日志以查找可疑活动
- [ ] 每季度测试灾难恢复程序

---

## 已知安全注意事项

### 速率限制

Azure Computer Vision 有默认速率限制:
- 免费层: 20 次调用/分钟
- S1 层: 10 次调用/秒

实施客户端速率限制以保持在这些限制内并防止服务中断。

### 数据隐私

**重要:** OCR 处理可能涉及敏感数据 (PII、财务信息等)

- 确保符合数据保护法规 (GDPR、CCPA 等)
- 实施数据保留策略
- 为敏感工作负载使用 Azure Private Link
- 考虑数据驻留要求
- 记录数据流和处理

### 多区域部署

使用多个区域实现高可用性时:
- 每个区域应有自己的 API 密钥
- 实施安全的故障转移机制
- 确保跨区域的一致安全策略
- 监控所有端点的可疑活动

---

## 安全资源

### Azure 安全文档

- [Azure 安全最佳实践](https://learn.microsoft.com/zh-cn/azure/security/fundamentals/best-practices-and-patterns)
- [认知服务安全](https://learn.microsoft.com/zh-cn/azure/cognitive-services/security-features)
- [Azure Key Vault](https://learn.microsoft.com/zh-cn/azure/key-vault/)
- [托管标识](https://learn.microsoft.com/zh-cn/azure/active-directory/managed-identities-azure-resources/)

### 工具

- [pip-audit](https://github.com/pypa/pip-audit) - Python 依赖项漏洞扫描器
- [Bandit](https://github.com/PyCQA/bandit) - Python 安全检查工具
- [Safety](https://github.com/pyupio/safety) - 依赖项漏洞检查器

### 安全培训

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Azure 安全中心](https://learn.microsoft.com/zh-cn/azure/defender-for-cloud/)

---

## 联系方式

对于安全问题,请使用:
- GitHub 安全公告 (首选)
- 直接联系维护者

**请勿在公共渠道讨论安全问题。**

---

## 致谢

我们感谢帮助保护本项目安全的安全研究人员和贡献者。我们重视并认可负责任的披露。

---

感谢您帮助保护本项目的安全! 🔒
