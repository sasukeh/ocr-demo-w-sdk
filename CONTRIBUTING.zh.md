# 贡献指南

**其他语言版本:** [English](CONTRIBUTING.md) | 简体中文 | [日本語](CONTRIBUTING.ja.md)

我们欢迎为本项目做出贡献! 🎉

## 📋 目录

- [行为准则](#行为准则)
- [开发环境设置](#开发环境设置)
- [如何贡献](#如何贡献)
- [拉取请求指南](#拉取请求指南)
- [编码标准](#编码标准)
- [测试](#测试)
- [文档](#文档)

---

## 行为准则

本项目期望所有参与者相互尊重和合作。请遵守以下行为准则:

- 提供建设性的反馈
- 尊重不同的观点和经验
- 不容忍对其他参与者的骚扰和歧视

---

## 开发环境设置

### 前提条件

- Python 3.11 或更高版本
- Azure CLI (`az`)
- Azure 订阅
- Git

### 1. 克隆仓库

```bash
git clone https://github.com/sasukeh/ocr-demo-w-sdk.git
cd ocr-demo-w-sdk
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 设置 Azure 资源

创建 Azure Computer Vision 资源:

```bash
# 登录到 Azure
az login

# 创建资源组
az group create --name ocr-demo-rg --location japaneast

# 创建 Computer Vision 资源
az cognitiveservices account create \
  --name ocr-demo-cv-primary \
  --resource-group ocr-demo-rg \
  --kind ComputerVision \
  --sku S1 \
  --location japaneast
```

### 5. 配置环境

```bash
cp .env.example .env
# 编辑 .env 并配置您的端点和密钥
```

---

## 如何贡献

### 报告错误

使用 [GitHub Issues](https://github.com/sasukeh/ocr-demo-w-sdk/issues) 报告错误。请包含:

- 问题的详细描述
- 重现步骤
- 预期行为与实际行为对比
- 环境信息 (操作系统、Python 版本等)
- 错误消息和日志

### 功能请求

也欢迎通过 Issues 提出功能请求。请包含:

- 功能描述
- 用例
- 预期收益
- 示例实现 (如果适用)

### 代码贡献

1. **Fork 仓库**
2. **创建功能分支**

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **进行更改**
4. **编写测试**
5. **运行测试和代码检查工具**

   ```bash
   # 运行测试
   pytest

   # 格式化代码
   black .
   
   # 使用 flake8 检查
   flake8 .
   ```

6. **提交**

   ```bash
   git commit -m "Add: 您的更改描述"
   ```

7. **推送到您的 fork**

   ```bash
   git push origin feature/your-feature-name
   ```

8. **创建拉取请求**

---

## 拉取请求指南

### PR 标题

使用清晰且描述性的标题:

- `Add: 新功能描述`
- `Fix: 错误修复描述`
- `Update: 更新描述`
- `Docs: 文档更改`
- `Refactor: 代码重构`

### PR 描述

在 PR 描述中包含以下内容:

- **目的**: 此 PR 完成了什么?
- **更改**: 进行了哪些更改?
- **测试**: 如何测试?
- **截图**: 如果与 UI 相关,请包含截图
- **相关问题**: 链接相关问题

### 审查流程

1. 自动检查 (CI/CD) 必须通过
2. 至少需要一次代码审查批准
3. 解决所有审查意见
4. 如有必要更新文档

---

## 编码标准

### Python

- **PEP 8**: 遵循 Python 风格指南
- **类型提示**: 为所有函数使用类型提示

  ```python
  def process_image(image_path: str, endpoint: str) -> dict:
      # 实现
      pass
  ```

- **文档字符串**: 为所有公共函数和类编写文档字符串

  ```python
  def analyze_image(image_data: bytes) -> dict:
      """
      使用 Azure Computer Vision 分析图像。
      
      Args:
          image_data: 二进制图像数据
          
      Returns:
          dict: 分析结果,包括 OCR 文本
          
      Raises:
          ValueError: 如果 image_data 无效
      """
      pass
  ```

- **错误处理**: 使用适当的异常

  ```python
  try:
      result = ocr_client.analyze(image)
  except HttpResponseError as e:
      logger.error(f"OCR 失败: {e}")
      raise
  ```

### 命名约定

- **变量**: `snake_case`
- **函数**: `snake_case`
- **类**: `PascalCase`
- **常量**: `UPPER_SNAKE_CASE`

```python
MAX_RETRY_COUNT = 3

class OCRClient:
    def __init__(self):
        self.retry_count = 0
    
    def analyze_image(self, image_path: str) -> dict:
        pass
```

### 代码结构

- 保持函数小而专注
- 每个文件一个类 (除非关系密切)
- 使用有意义的变量和函数名
- 为复杂逻辑添加注释

---

## 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_client.py

# 运行并生成覆盖率报告
pytest --cov=scenario_a_client --cov=scenario_b_apim
```

### 编写测试

- 为所有新功能编写单元测试
- 测试成功和错误情况
- 使用有意义的测试名称

```python
def test_ocr_client_success():
    """测试 OCR 客户端与有效图像。"""
    client = OCRClient(endpoint, key)
    result = client.analyze("test_images/sample.jpg")
    assert result["status"] == "success"

def test_ocr_client_invalid_image():
    """测试 OCR 客户端与无效图像。"""
    client = OCRClient(endpoint, key)
    with pytest.raises(ValueError):
        client.analyze("invalid.jpg")
```

### 负载测试

测试负载下的性能:

```bash
python -m scenario_a_client.load_test \
  --images test_images \
  --rps 10 \
  --duration 60
```

---

## 文档

### 代码文档

- 为所有公共 API 添加文档字符串
- 包含使用示例
- 记录参数和返回值

### README 更新

- 添加新功能时更新 README.md
- 包含使用示例
- 更新目录

### 多语言文档

- 更新所有语言版本 (EN, JA, ZH)
- 保持翻译同步
- 使用清晰简洁的语言

---

## 开发工作流程

### 分支策略

- `main`: 稳定的生产就绪代码
- `develop`: 功能集成分支
- `feature/*`: 功能分支
- `fix/*`: 错误修复分支

### 提交消息

使用清晰的提交消息:

```bash
Add: 实现失败请求的重试逻辑
Fix: 解决 APIM 客户端的超时问题
Update: 改进 OCR 客户端的错误处理
Docs: 向 README 添加使用示例
```

### 版本管理

- 遵循 [语义版本控制](https://semver.org/)
- 为重大更改更新 `CHANGELOG.md`
- 适当标记发布版本

---

## 获取帮助

- **问题**: 开启 [GitHub Discussion](https://github.com/sasukeh/ocr-demo-w-sdk/discussions)
- **错误**: 通过 [GitHub Issues](https://github.com/sasukeh/ocr-demo-w-sdk/issues) 报告
- **安全**: 参见 [SECURITY.md](SECURITY.zh.md)

---

## 许可证

通过贡献,您同意您的贡献将根据 MIT 许可证进行许可。

---

感谢您的贡献! 🙏
