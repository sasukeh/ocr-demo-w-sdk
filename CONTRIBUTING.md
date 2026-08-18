# Contributing to OCR Demo with Azure SDK# Contributing to OCR Demo with Azure SDK



**Read this in other languages:** English | [简体中文](CONTRIBUTING.zh.md) | [日本語](CONTRIBUTING.ja.md)このプロジェクトへのコントリビューションを歓迎します！ 🎉



We welcome contributions to this project! 🎉## 📋 目次



## 📋 Table of Contents- [行動規範](#行動規範)

- [開発環境のセットアップ](#開発環境のセットアップ)

- [Code of Conduct](#code-of-conduct)- [コントリビューション方法](#コントリビューション方法)

- [Development Environment Setup](#development-environment-setup)- [プルリクエストのガイドライン](#プルリクエストのガイドライン)

- [How to Contribute](#how-to-contribute)- [コーディング規約](#コーディング規約)

- [Pull Request Guidelines](#pull-request-guidelines)- [テスト](#テスト)

- [Coding Standards](#coding-standards)- [ドキュメント](#ドキュメント)

- [Testing](#testing)

- [Documentation](#documentation)---



---## 行動規範



## Code of Conductこのプロジェクトは、すべての参加者に対して尊重と協力を期待しています。以下の行動を遵守してください:



This project expects respect and cooperation from all participants. Please adhere to the following conduct:- 建設的なフィードバックを提供する

- 異なる視点や経験を尊重する

- Provide constructive feedback- 他の参加者への嫌がらせや差別は許容しない

- Respect different perspectives and experiences

- Harassment and discrimination against other participants are not tolerated---



---## 開発環境のセットアップ



## Development Environment Setup### 必須要件



### Prerequisites- Python 3.11以上

- Azure CLI (`az`)

- Python 3.11 or higher- Azureサブスクリプション

- Azure CLI (`az`)- Git

- Azure subscription

- Git### 1. リポジトリのクローン



### 1. Clone the Repository```bash

git clone https://github.com/sasukeh/ocr-demo-w-sdk.git

```bashcd ocr-demo-w-sdk

git clone https://github.com/sasukeh/ocr-demo-w-sdk.git```

cd ocr-demo-w-sdk

```### 2. 仮想環境の作成



### 2. Create Virtual Environment```bash

python -m venv .venv

```bashsource .venv/bin/activate  # Windowsの場合: .venv\Scripts\activate

python -m venv .venv```

source .venv/bin/activate  # Windows: .venv\Scripts\activate

```### 3. 依存関係のインストール



### 3. Install Dependencies```bash

pip install --upgrade pip

```bashpip install -r requirements.txt

pip install -r requirements.txt```

```

### 4. 環境変数の設定

### 4. Azure Resource Setup

```bash

Create Azure Computer Vision resources:# .env.exampleをコピー

cp .env.example .env

```bash

# Login to Azure# .envファイルを編集して、Azure Computer Visionの情報を設定

az login# OCR_ENDPOINTS=https://your-cv-endpoint1.cognitiveservices.azure.com/,...

# OCR_KEYS=your-key1,your-key2,...

# Create resource group```

az group create --name ocr-demo-rg --location japaneast

### 5. Azureリソースのデプロイ (オプション)

# Create Computer Vision resources

az cognitiveservices account create \```bash

  --name ocr-demo-cv-primary \# シナリオA用のComputer Visionリソース

  --resource-group ocr-demo-rg \cd infrastructure

  --kind ComputerVision \./deploy-japan-east.sh

  --sku S1 \

  --location japaneast# シナリオB用のAPIMリソース

```cd infrastructure/apim

./deploy-apim.sh

### 5. Environment Configuration```



```bash---

cp .env.example .env

# Edit .env and configure your endpoints and keys## コントリビューション方法

```

### イシューの報告

---

バグを見つけた場合や機能リクエストがある場合は、[GitHub Issues](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/issues)で報告してください。

## How to Contribute

**バグレポートに含めるべき情報:**

### Reporting Bugs- 問題の説明

- 再現手順

Use [GitHub Issues](https://github.com/sasukeh/ocr-demo-w-sdk/issues) to report bugs. Include:- 期待される動作

- 実際の動作

- Detailed description of the issue- 環境情報 (OS, Python バージョン, Azure SDK バージョン)

- Steps to reproduce- エラーログ (該当する場合)

- Expected behavior vs actual behavior

- Environment information (OS, Python version, etc.)**機能リクエストに含めるべき情報:**

- Error messages and logs- 機能の説明

- ユースケース

### Feature Requests- 期待される動作

- 代替案 (あれば)

Feature requests are also welcome via Issues. Please include:

### コードの変更

- Description of the feature

- Use cases1. **フォークしてブランチを作成**

- Expected benefits

- Example implementation (if applicable)   ```bash

   # リポジトリをフォーク

### Code Contributions   gh repo fork YOUR_USERNAME/ocr-demo-w-sdk --clone

   

1. **Fork the repository**   # 新しいブランチを作成

2. **Create a feature branch**   git checkout -b feature/your-feature-name

   ```

   ```bash

   git checkout -b feature/your-feature-name2. **変更を実装**

   ```

   - コーディング規約に従う (後述)

3. **Make your changes**   - テストを追加/更新

4. **Write tests**   - ドキュメントを更新

5. **Run tests and linters**

3. **ローカルテスト**

   ```bash

   # Run tests   ```bash

   pytest   # シナリオAのテスト

   cd scenario_a_client

   # Format code   python test_sdk.py

   black .   

      # シナリオBのテスト

   # Check with flake8   cd scenario_b_apim

   flake8 .   python test_httpx.py

   ```   ```



6. **Commit**4. **コミットしてプッシュ**



   ```bash   ```bash

   git commit -m "Add: Description of your changes"   git add .

   ```   git commit -m "feat: add new feature description"

   git push origin feature/your-feature-name

7. **Push to your fork**   ```



   ```bash5. **プルリクエストを作成**

   git push origin feature/your-feature-name

   ```   GitHub上でプルリクエストを作成し、変更内容を説明してください。



8. **Create Pull Request**---



---## プルリクエストのガイドライン



## Pull Request Guidelines### PRタイトル



### PR TitleConventional Commits形式を使用:



Use clear and descriptive titles:- `feat:` 新機能

- `fix:` バグ修正

- `Add: New feature description`- `docs:` ドキュメントのみの変更

- `Fix: Bug fix description`- `style:` コードの意味に影響しない変更 (フォーマット、セミコロンなど)

- `Update: Update description`- `refactor:` バグ修正でも機能追加でもないコード変更

- `Docs: Documentation changes`- `test:` テストの追加や修正

- `Refactor: Code refactoring`- `chore:` ビルドプロセスやツールの変更



### PR Description**例:**

```

Include the following in your PR description:feat: add rate limiting support for Scenario A

fix: resolve 429 error handling in APIM client

- **Purpose**: What does this PR accomplish?docs: update SDK migration guide

- **Changes**: What changes were made?```

- **Testing**: How was it tested?

- **Screenshots**: If UI-related, include screenshots### PR説明

- **Related Issues**: Link related issues

PRには以下の情報を含めてください:

### Review Process

```markdown

1. Automated checks (CI/CD) must pass## 変更内容

2. At least one code review approval required- 何を変更したか

3. Address all review comments

4. Update documentation if necessary## 動機

- なぜこの変更が必要か

---

## テスト

## Coding Standards- どのようにテストしたか

- テストケースの追加/変更

### Python

## スクリーンショット (該当する場合)

- **PEP 8**: Follow Python style guide

- **Type Hints**: Use type hints for all functions## チェックリスト

- [ ] コードがコーディング規約に準拠している

  ```python- [ ] テストが追加/更新されている

  def process_image(image_path: str, endpoint: str) -> dict:- [ ] ドキュメントが更新されている

      # Implementation- [ ] 全てのテストが通過している

      pass```

  ```

### レビュープロセス

- **Docstrings**: Write docstrings for all public functions and classes

1. 自動チェック (CI/CD) が通過すること

  ```python2. 少なくとも1人のメンテナーからの承認

  def analyze_image(image_data: bytes) -> dict:3. マージ前にコンフリクトを解決

      """

      Analyze image using Azure Computer Vision.---

      

      Args:## コーディング規約

          image_data: Binary image data

          ### Python

      Returns:

          dict: Analysis results including OCR text- **PEP 8** スタイルガイドに従う

          - **Type Hints** を使用 (Python 3.11+)

      Raises:- **Docstrings** を関数/クラスに追加 (Google形式)

          ValueError: If image_data is invalid

      """**例:**

      pass

  ``````python

from typing import Optional, Dict, Any

- **Error Handling**: Use appropriate exceptions

async def ocr_with_fallback(

  ```python    self,

  try:    image_data: bytes,

      result = ocr_client.analyze(image)    max_retries: int = 3

  except HttpResponseError as e:) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:

      logger.error(f"OCR failed: {e}")    """

      raise    OCR処理をフォールバック機能付きで実行

  ```    

    Args:

### Naming Conventions        image_data: 画像データのバイト列

        max_retries: 最大リトライ回数

- **Variables**: `snake_case`        

- **Functions**: `snake_case`    Returns:

- **Classes**: `PascalCase`        Tuple[OCR結果, メタデータ]

- **Constants**: `UPPER_SNAKE_CASE`        

    Raises:

```python        ValueError: image_dataが空の場合

MAX_RETRY_COUNT = 3    """

    if not image_data:

class OCRClient:        raise ValueError("image_data cannot be empty")

    def __init__(self):    

        self.retry_count = 0    # 実装...

    ```

    def analyze_image(self, image_path: str) -> dict:

        pass### ファイル構成

```

```

### Code Structureプロジェクトルート/

├── scenario_a_client/     # シナリオA (Azure SDK)

- Keep functions small and focused│   ├── client.py         # メインクライアント

- One class per file (unless closely related)│   ├── endpoints.py      # エンドポイント管理

- Use meaningful variable and function names│   ├── fallback_policy.py # フォールバックロジック

- Add comments for complex logic│   └── test_sdk.py       # SDKテスト

├── scenario_b_apim/       # シナリオB (httpx + APIM)

---│   ├── client_via_apim.py # APIMクライアント

│   └── test_httpx.py     # httpxテスト

## Testing├── infrastructure/        # Bicepテンプレート

├── docs/                  # ドキュメント

### Running Tests└── tests/                 # 統合テスト (将来追加)

```

```bash

# Run all tests### コミットメッセージ

pytest

```

# Run specific test file<type>(<scope>): <subject>

pytest tests/test_client.py

<body>

# Run with coverage

pytest --cov=scenario_a_client --cov=scenario_b_apim<footer>

``````



### Writing Tests**例:**

```

- Write unit tests for all new featuresfeat(scenario_a): add exponential backoff for SDK retry

- Test both success and error cases

- Use meaningful test names- Implement jittered exponential backoff

- Add configurable max_backoff_seconds parameter

```python- Update tests to verify backoff behavior

def test_ocr_client_success():

    """Test OCR client with valid image."""Closes #123

    client = OCRClient(endpoint, key)```

    result = client.analyze("test_images/sample.jpg")

    assert result["status"] == "success"---



def test_ocr_client_invalid_image():## テスト

    """Test OCR client with invalid image."""

    client = OCRClient(endpoint, key)### 単体テスト

    with pytest.raises(ValueError):

        client.analyze("invalid.jpg")```bash

```# pytest を使用 (将来的に追加予定)

pytest tests/

### Load Testing

# 特定のテストファイル

Test performance under load:pytest tests/test_client.py -v

```

```bash

python -m scenario_a_client.load_test \### 統合テスト

  --images test_images \

  --rps 10 \```bash

  --duration 60# シナリオAの統合テスト

```cd scenario_a_client

python test_sdk.py

---

# シナリオBの統合テスト

## Documentationcd scenario_b_apim

python test_httpx.py

### Code Documentation```



- Add docstrings to all public APIs### 負荷テスト

- Include usage examples

- Document parameters and return values```bash

# シナリオAの負荷テスト

### README Updatescd scenario_a_client

python load_test.py --workers 10 --duration 60

- Update README.md when adding new features

- Include usage examples# シナリオBの負荷テスト

- Update table of contentscd scenario_b_apim

python load_test.py --workers 5 --duration 60

### Multi-language Documentation```



- Update all language versions (EN, JA, ZH)---

- Keep translations synchronized

- Use clear and concise language## ドキュメント



---### ドキュメントの更新



## Development Workflowコード変更に伴い、以下のドキュメントを更新してください:



### Branch Strategy- `README.md` - プロジェクト概要、セットアップ手順

- `docs/IMPLEMENTATION_SUMMARY.md` - 実装詳細

- `main`: Stable production-ready code- `docs/SDK_MIGRATION.md` - SDK移行ガイド

- `develop`: Integration branch for features- `docs/SCALING_STRATEGY.md` - スケーリング戦略

- `feature/*`: Feature branches- `docs/BEST_PRACTICES.md` - ベストプラクティス

- `fix/*`: Bug fix branches

### ドキュメントのフォーマット

### Commit Messages

- Markdown形式

Use clear commit messages:- コードブロックには言語指定 (\`\`\`python, \`\`\`bash)

- 見出しの階層構造を維持

```bash- スクリーンショットは `docs/images/` に配置

Add: Implement retry logic for failed requests

Fix: Resolve timeout issue in APIM client---

Update: Improve error handling in OCR client

Docs: Add usage examples to README## 質問・サポート

```

- **イシュー**: [GitHub Issues](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/issues)

### Version Management- **ディスカッション**: [GitHub Discussions](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/discussions)

- **セキュリティ**: [SECURITY.md](SECURITY.md) を参照

- Follow [Semantic Versioning](https://semver.org/)

- Update `CHANGELOG.md` for significant changes---

- Tag releases appropriately

## ライセンス

---

このプロジェクトへのコントリビューションは、[MIT License](LICENSE) のもとで公開されます。

## Getting Help

---

- **Questions**: Open a [GitHub Discussion](https://github.com/sasukeh/ocr-demo-w-sdk/discussions)

- **Bugs**: Report via [GitHub Issues](https://github.com/sasukeh/ocr-demo-w-sdk/issues)**ハッピーコーディング！** 🚀

- **Security**: See [SECURITY.md](SECURITY.md)

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing! 🙏
