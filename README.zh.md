# Azure Computer Vision OCR - 延迟优化、故障转移和负载均衡演示

**其他语言版本:** [English](README.md) | 简体中文 | [日本語](README.ja.md)

这是一个全面演示 Azure Computer Vision OCR 服务延迟优化和 429 错误(速率限制)缓解的故障转移和负载均衡系统。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Azure](https://img.shields.io/badge/Azure-Computer%20Vision-0078D4)](https://azure.microsoft.com/services/cognitive-services/computer-vision/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub](https://img.shields.io/badge/GitHub-sasukeh%2Focr--demo--w--sdk-181717?logo=github)](https://github.com/sasukeh/ocr-demo-w-sdk)

> **🎉 SDK迁移完成**: 该项目已从基于 httpx 的实现迁移到 Azure 官方 SDK (azure-ai-vision-imageanalysis)。详情请参阅 [SDK_MIGRATION.md](docs/zh/SDK_MIGRATION.md)。

---

## 📋 目录

- [项目概述](#-项目概述)
- [架构](#-架构)
- [主要功能](#-主要功能)
- [快速开始](#-快速开始)
- [场景执行](#-场景执行)
- [部署](#-部署)
- [文档](#-文档)
- [项目结构](#-项目结构)
- [故障排除](#-故障排除)

---

## 🎯 项目概述

该系统允许您比较和验证 Azure Computer Vision OCR 的两种方法:

### 场景 A: 客户端故障转移和负载均衡 (Azure SDK) ✅

**实现方式:**

- 使用 **Azure Computer Vision SDK** (`azure-ai-vision-imageanalysis`)
- 通过官方 SDK 实现稳定性和类型安全
- 简化的错误处理

**特性:**

- 跨多个 Computer Vision 端点的自动负载均衡
- 基于延迟的智能端点选择
- 使用指数退避处理 429 错误
- 动态端点健康监控

**适用场景:**

- 轻量级应用程序
- 不使用 APIM 的简单架构
- 客户端完整的负载均衡
- 直接访问 Computer Vision 端点

### 场景 B: APIM (API Management) 断路器 (HTTP Client) ✅

**实现方式:**

- 使用 **httpx** HTTP 客户端
- 与 APIM 自定义标头和策略灵活集成

**特性:**

- 使用 Azure API Management 的集中式故障转移
- 集中式速率限制和断路器功能
- 支持 Image Analysis v4 API
- 高级断路器策略(5次失败后打开60秒)
- 通过 APIM 自定义标头提供详细诊断 (`X-Served-By-Backend` 等)

**适用场景:**

- 企业应用程序
- 需要集中管理的系统
- 来自多个客户端的访问
- 利用 APIM 自定义策略的环境

> **💡 实现区分:**
>
> - **场景 A**: 使用 Azure SDK 直接访问端点。实现简单且易于维护。
> - **场景 B**: 通过 APIM 自定义网关访问,使用 HTTP 客户端灵活实现。需要与 APIM 策略集成。

---

## 🏗 架构

### 场景 A: 客户端实现 (Azure SDK)

```text
┌─────────────────────────────┐
│   客户端                     │
│   (使用 Azure SDK)          │
└──────┬──────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ 端点池                       │
│ - 负载均衡                   │
│ - 健康监控                   │
│ - 惩罚管理                   │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Computer Vision API          │
│ ├─ je-primary   (日本东部)   │
│ ├─ je-secondary (日本东部)   │
│ └─ je-tertiary  (日本东部)   │
└──────────────────────────────┘
```

### 场景 B: APIM 实现

```text
┌─────────────────────────────┐
│   客户端 (httpx)            │
└──────┬──────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ API Management               │
│ ├─ 断路器策略                │
│ ├─ 速率限制                  │
│ └─ 后端池管理                │
└──────┬───────────────────────┘
       │
       ├──► 主端点
       ├──► 次端点
       └──► 第三端点
```

---

## ✨ 主要功能

### 高级故障转移

- **延迟监控**: 使用 EWMA(指数加权移动平均)跟踪每个端点的响应时间
- **基于惩罚的选择**: 降低慢速或失败端点的优先级
- **断路器**: 临时阻止持续失败的端点(场景 B)
- **指数退避**: 智能重试,延迟递增

### 图像处理优化

- **自动调整大小**: 自动优化大图像(符合4MB限制)
- **格式处理**: 支持 JPEG、PNG、BMP 等
- **Base64编码**: APIM 场景的自动转换

### 全面的监控和分析

- **详细指标**: 延迟、成功率、端点分布统计
- **实时仪表板**: CSV/JSON 格式结果输出
- **负载测试**: 内置负载测试工具
- **性能分析**: P50/P95/P99 延迟指标

### Azure 最佳实践实现

- **IaC (基础设施即代码)**: Bicep 模板
- **安全性**: 无硬编码凭据,Key Vault 集成
- **CI/CD**: GitHub Actions 工作流
- **成本优化**: 按需资源利用

---

## 🚀 快速开始

### 前提条件

- Python 3.11+
- Azure 订阅
- Azure Computer Vision 资源(建议3个以上用于负载均衡)
- Azure CLI (`az`)

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

### 4. 环境配置

```bash
cp .env.example .env
# 编辑 .env 并配置您的 Azure Computer Vision 端点
```

所需环境变量:

```bash
# 场景 A: 客户端负载均衡
CV_ENDPOINT_PRIMARY=https://your-primary.cognitiveservices.azure.com/
CV_KEY_PRIMARY=your_primary_key
CV_ENDPOINT_SECONDARY=https://your-secondary.cognitiveservices.azure.com/
CV_KEY_SECONDARY=your_secondary_key

# 场景 B: APIM
APIM_GATEWAY_URL=https://your-apim.azure-api.net
APIM_SUBSCRIPTION_KEY=your_apim_subscription_key
```

---

## 🎬 场景执行

### 场景 A: 基于 SDK 的客户端负载均衡

```bash
# 基本测试
python -m scenario_a_client.test_sdk

# 负载测试(10 RPS 持续 60 秒)
python -m scenario_a_client.load_test \
  --images test_images \
  --rps 10 \
  --duration 60
```

### 场景 B: APIM 断路器

```bash
# 基本测试
cd scenario_b_apim && python test_httpx.py

# 负载测试
python -m scenario_b_apim.load_test \
  --images test_images \
  --rps 10 \
  --duration 60
```

---

## 📚 文档

- [English Documentation](docs/en/)
- [日本語ドキュメント](docs/ja/)
- [中文文档](docs/zh/)
  - [最佳实践](docs/zh/BEST_PRACTICES.md)
  - [实现摘要](docs/zh/IMPLEMENTATION_SUMMARY.md)
  - [扩展策略](docs/zh/SCALING_STRATEGY.md)

---

## 📁 项目结构

```text
ocr-demo-w-sdk/
├── scenario_a_client/      # 场景 A: Azure SDK 实现
│   ├── client.py           # 基于 SDK 的 OCR 客户端
│   ├── endpoints.py        # 端点池管理
│   ├── fallback_policy.py  # 故障转移逻辑
│   └── load_test.py        # 负载测试工具
├── scenario_b_apim/        # 场景 B: APIM 实现
│   ├── apim_client.py      # APIM 客户端 (httpx)
│   ├── load_test.py        # 负载测试工具
│   └── apim/               # APIM 策略定义
├── infrastructure/         # 基础设施即代码
│   ├── apim/              # APIM Bicep 模板
│   └── modules/           # 可重用的 Bicep 模块
├── docs/                  # 文档
│   ├── en/               # 英文文档
│   ├── ja/               # 日文文档
│   └── zh/               # 中文文档
└── .github/workflows/     # CI/CD 管道
```

---

## 🛠 故障排除

### 常见问题

**429 速率限制错误**

- 增加 Computer Vision 资源数量
- 调整 RPS(每秒请求数)设置
- 验证 APIM 策略配置

**响应时间慢**

- 检查端点延迟指标
- 验证区域选择(建议选择更近的区域)
- 检查网络连接

**SDK 导入错误**

```bash
pip install --upgrade azure-ai-vision-imageanalysis
```

---

## 🤝 贡献

有关贡献指南,请参阅 [CONTRIBUTING.md](CONTRIBUTING.zh.md)。

---

## 📄 许可证

该项目根据 MIT 许可证授权 - 有关详细信息,请参阅 [LICENSE](LICENSE) 文件。

---

## 🔒 安全

有关安全漏洞报告,请参阅 [SECURITY.md](SECURITY.zh.md)。

---

## 📞 支持

- [GitHub Issues](https://github.com/sasukeh/ocr-demo-w-sdk/issues)
- [Azure Computer Vision 文档](https://docs.microsoft.com/zh-cn/azure/cognitive-services/computer-vision/)

---

**为 Azure 开发者用 ❤️ 制作**
