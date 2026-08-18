# Azure Computer Vision OCR - Latency Optimization, Fallback & Load Balancing Demo

**Read this in other languages:** English | [简体中文](README.zh.md) | [日本語](README.ja.md)

A comprehensive demonstration of fallback and load balancing systems for Azure Computer Vision OCR service latency optimization and 429 error (Rate Limiting) mitigation.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Azure](https://img.shields.io/badge/Azure-Computer%20Vision-0078D4)](https://azure.microsoft.com/services/cognitive-services/computer-vision/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GitHub](https://img.shields.io/badge/GitHub-sasukeh%2Focr--demo--w--sdk-181717?logo=github)](https://github.com/sasukeh/ocr-demo-w-sdk)

> **🎉 SDK Migration Complete**: This project has been migrated from httpx-based implementation to Azure official SDK (azure-ai-vision-imageanalysis). See [SDK_MIGRATION.md](docs/en/SDK_MIGRATION.md) for details.

---

## 📋 Table of Contents

- [Project Overview](#-project-overview)
- [Architecture](#-architecture)
- [Key Features](#-key-features)
- [Quick Start](#-quick-start)
- [Scenario Execution](#-scenario-execution)
- [Deployment](#-deployment)
- [Documentation](#-documentation)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 Project Overview

This system allows you to compare and verify two approaches to Azure Computer Vision OCR:

### Scenario A: Client-Side Fallback & Load Balancing (Azure SDK) ✅

**Implementation:**

- Uses **Azure Computer Vision SDK** (`azure-ai-vision-imageanalysis`)
- Stable implementation and type safety with official SDK
- Simplified error handling

**Features:**

- Automatic load balancing across multiple Computer Vision endpoints
- Intelligent endpoint selection based on latency
- 429 error handling with exponential backoff
- Dynamic endpoint health monitoring

**Use Cases:**

- Lightweight applications
- Simple architecture without APIM
- Client-side complete load balancing
- Direct access to Computer Vision endpoints

### Scenario B: APIM (API Management) Circuit Breaker (HTTP Client) ✅

**Implementation:**

- Uses **httpx** HTTP client
- Flexible integration with APIM custom headers and policies

**Features:**

- Centralized fallback using Azure API Management
- Centralized rate limiting and circuit breaker functionality
- Image Analysis v4 API support
- Advanced circuit breaker policy (OPEN for 60s after 5 failures)
- Detailed diagnostics via APIM custom headers (`X-Served-By-Backend`, etc.)

**Use Cases:**

- Enterprise applications
- Systems requiring centralized management
- Access from multiple clients
- Environments leveraging APIM custom policies

> **💡 Implementation Differentiation:**
>
> - **Scenario A**: Uses Azure SDK for direct endpoint access. Simple and maintainable implementation.
> - **Scenario B**: Accesses via APIM custom gateway, flexibly implemented with HTTP client. Integration with APIM policies required.

---

## 🏗 Architecture

### Scenario A: Client-Side Implementation (Azure SDK)

```text
┌─────────────────────────────┐
│   Client                    │
│   (Using Azure SDK)         │
└──────┬──────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Endpoint Pool                │
│ - Load Balancing             │
│ - Health Monitoring          │
│ - Penalty Management         │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ Computer Vision API          │
│ ├─ je-primary   (Japan East) │
│ ├─ je-secondary (Japan East) │
│ └─ je-tertiary  (Japan East) │
└──────────────────────────────┘
```

### Scenario B: APIM Implementation

```text
┌─────────────────────────────┐
│   Client (httpx)            │
└──────┬──────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│ API Management               │
│ ├─ Circuit Breaker Policy   │
│ ├─ Rate Limiting             │
│ └─ Backend Pool Management   │
└──────┬───────────────────────┘
       │
       ├──► Primary Endpoint
       ├──► Secondary Endpoint
       └──► Tertiary Endpoint
```

---

## ✨ Key Features

### Advanced Fallback

- **Latency Monitoring**: Track response time for each endpoint using EWMA (Exponential Weighted Moving Average)
- **Penalty-Based Selection**: Deprioritize slow or failing endpoints
- **Circuit Breaker**: Temporarily block consistently failing endpoints (Scenario B)
- **Exponential Backoff**: Intelligent retry with increasing delays

### Image Processing Optimization

- **Auto-Resize**: Automatic optimization for large images (4MB limit compliance)
- **Format Handling**: Support for JPEG, PNG, BMP, etc.
- **Base64 Encoding**: Automatic conversion for APIM scenarios

### Comprehensive Monitoring & Analysis

- **Detailed Metrics**: Latency, success rate, endpoint distribution statistics
- **Real-time Dashboard**: CSV/JSON format result output
- **Load Testing**: Built-in load testing tools
- **Performance Analysis**: P50/P95/P99 latency metrics

### Azure Best Practices Implementation

- **IaC (Infrastructure as Code)**: Bicep templates
- **Security**: No hardcoded credentials, Key Vault integration
- **CI/CD**: GitHub Actions workflows
- **Cost Optimization**: On-demand resource utilization

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Azure subscription
- Azure Computer Vision resource (3+ recommended for load balancing)
- Azure CLI (`az`)

### 1. Clone Repository

```bash
git clone https://github.com/sasukeh/ocr-demo-w-sdk.git
cd ocr-demo-w-sdk
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

```bash
cp .env.example .env
# Edit .env and configure your Azure Computer Vision endpoints
```

Required environment variables:

```bash
# Scenario A: Client-side load balancing
CV_ENDPOINT_PRIMARY=https://your-primary.cognitiveservices.azure.com/
CV_KEY_PRIMARY=your_primary_key
CV_ENDPOINT_SECONDARY=https://your-secondary.cognitiveservices.azure.com/
CV_KEY_SECONDARY=your_secondary_key

# Scenario B: APIM
APIM_GATEWAY_URL=https://your-apim.azure-api.net
APIM_SUBSCRIPTION_KEY=your_apim_subscription_key
```

---

## 🎬 Scenario Execution

### Scenario A: SDK-Based Client-Side Load Balancing

```bash
# Basic test
python -m scenario_a_client.test_sdk

# Load test (10 RPS for 60 seconds)
python -m scenario_a_client.load_test \
  --images test_images \
  --rps 10 \
  --duration 60
```

### Scenario B: APIM Circuit Breaker

```bash
# Basic test
cd scenario_b_apim && python test_httpx.py

# Load test
python -m scenario_b_apim.load_test \
  --images test_images \
  --rps 10 \
  --duration 60
```

---

## 📚 Documentation

- [English Documentation](docs/en/)
  - [Best Practices](docs/en/BEST_PRACTICES.md)
  - [Implementation Summary](docs/en/IMPLEMENTATION_SUMMARY.md)
  - [Scaling Strategy](docs/en/SCALING_STRATEGY.md)
- [日本語ドキュメント](docs/ja/)
- [中文文档](docs/zh/)

---

## 📁 Project Structure

```text
ocr-demo-w-sdk/
├── scenario_a_client/      # Scenario A: Azure SDK implementation
│   ├── client.py           # SDK-based OCR client
│   ├── endpoints.py        # Endpoint pool management
│   ├── fallback_policy.py  # Fallback logic
│   └── load_test.py        # Load testing tool
├── scenario_b_apim/        # Scenario B: APIM implementation
│   ├── apim_client.py      # APIM client (httpx)
│   ├── load_test.py        # Load testing tool
│   └── apim/               # APIM policy definitions
├── infrastructure/         # Infrastructure as Code
│   ├── apim/              # APIM Bicep templates
│   └── modules/           # Reusable Bicep modules
├── docs/                  # Documentation
│   ├── en/               # English docs
│   ├── ja/               # Japanese docs
│   └── zh/               # Chinese docs
└── .github/workflows/     # CI/CD pipelines
```

---

## 🛠 Troubleshooting

### Common Issues

**429 Rate Limit Errors**

- Increase the number of Computer Vision resources
- Adjust RPS (requests per second) settings
- Verify APIM policy configuration

**Slow Response Times**

- Check endpoint latency metrics
- Verify region selection (closer regions recommended)
- Review network connectivity

**SDK Import Errors**

```bash
pip install --upgrade azure-ai-vision-imageanalysis
```

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.en.md) for contribution guidelines.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔒 Security

For security vulnerability reports, please see [SECURITY.md](SECURITY.en.md).

---

## 📞 Support

- [GitHub Issues](https://github.com/sasukeh/ocr-demo-w-sdk/issues)
- [Azure Computer Vision Documentation](https://docs.microsoft.com/azure/cognitive-services/computer-vision/)

---

**Made with ❤️ for Azure developers**
