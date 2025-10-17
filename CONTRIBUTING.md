# Contributing to OCR Demo with Azure SDK

このプロジェクトへのコントリビューションを歓迎します！ 🎉

## 📋 目次

- [行動規範](#行動規範)
- [開発環境のセットアップ](#開発環境のセットアップ)
- [コントリビューション方法](#コントリビューション方法)
- [プルリクエストのガイドライン](#プルリクエストのガイドライン)
- [コーディング規約](#コーディング規約)
- [テスト](#テスト)
- [ドキュメント](#ドキュメント)

---

## 行動規範

このプロジェクトは、すべての参加者に対して尊重と協力を期待しています。以下の行動を遵守してください:

- 建設的なフィードバックを提供する
- 異なる視点や経験を尊重する
- 他の参加者への嫌がらせや差別は許容しない

---

## 開発環境のセットアップ

### 必須要件

- Python 3.11以上
- Azure CLI (`az`)
- Azureサブスクリプション
- Git

### 1. リポジトリのクローン

```bash
git clone https://github.com/sasukeh/ocr-demo-w-sdk.git
cd ocr-demo-w-sdk
```

### 2. 仮想環境の作成

```bash
python -m venv .venv
source .venv/bin/activate  # Windowsの場合: .venv\Scripts\activate
```

### 3. 依存関係のインストール

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. 環境変数の設定

```bash
# .env.exampleをコピー
cp .env.example .env

# .envファイルを編集して、Azure Computer Visionの情報を設定
# OCR_ENDPOINTS=https://your-cv-endpoint1.cognitiveservices.azure.com/,...
# OCR_KEYS=your-key1,your-key2,...
```

### 5. Azureリソースのデプロイ (オプション)

```bash
# シナリオA用のComputer Visionリソース
cd infrastructure
./deploy-japan-east.sh

# シナリオB用のAPIMリソース
cd infrastructure/apim
./deploy-apim.sh
```

---

## コントリビューション方法

### イシューの報告

バグを見つけた場合や機能リクエストがある場合は、[GitHub Issues](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/issues)で報告してください。

**バグレポートに含めるべき情報:**
- 問題の説明
- 再現手順
- 期待される動作
- 実際の動作
- 環境情報 (OS, Python バージョン, Azure SDK バージョン)
- エラーログ (該当する場合)

**機能リクエストに含めるべき情報:**
- 機能の説明
- ユースケース
- 期待される動作
- 代替案 (あれば)

### コードの変更

1. **フォークしてブランチを作成**

   ```bash
   # リポジトリをフォーク
   gh repo fork YOUR_USERNAME/ocr-demo-w-sdk --clone
   
   # 新しいブランチを作成
   git checkout -b feature/your-feature-name
   ```

2. **変更を実装**

   - コーディング規約に従う (後述)
   - テストを追加/更新
   - ドキュメントを更新

3. **ローカルテスト**

   ```bash
   # シナリオAのテスト
   cd scenario_a_client
   python test_sdk.py
   
   # シナリオBのテスト
   cd scenario_b_apim
   python test_httpx.py
   ```

4. **コミットしてプッシュ**

   ```bash
   git add .
   git commit -m "feat: add new feature description"
   git push origin feature/your-feature-name
   ```

5. **プルリクエストを作成**

   GitHub上でプルリクエストを作成し、変更内容を説明してください。

---

## プルリクエストのガイドライン

### PRタイトル

Conventional Commits形式を使用:

- `feat:` 新機能
- `fix:` バグ修正
- `docs:` ドキュメントのみの変更
- `style:` コードの意味に影響しない変更 (フォーマット、セミコロンなど)
- `refactor:` バグ修正でも機能追加でもないコード変更
- `test:` テストの追加や修正
- `chore:` ビルドプロセスやツールの変更

**例:**
```
feat: add rate limiting support for Scenario A
fix: resolve 429 error handling in APIM client
docs: update SDK migration guide
```

### PR説明

PRには以下の情報を含めてください:

```markdown
## 変更内容
- 何を変更したか

## 動機
- なぜこの変更が必要か

## テスト
- どのようにテストしたか
- テストケースの追加/変更

## スクリーンショット (該当する場合)

## チェックリスト
- [ ] コードがコーディング規約に準拠している
- [ ] テストが追加/更新されている
- [ ] ドキュメントが更新されている
- [ ] 全てのテストが通過している
```

### レビュープロセス

1. 自動チェック (CI/CD) が通過すること
2. 少なくとも1人のメンテナーからの承認
3. マージ前にコンフリクトを解決

---

## コーディング規約

### Python

- **PEP 8** スタイルガイドに従う
- **Type Hints** を使用 (Python 3.11+)
- **Docstrings** を関数/クラスに追加 (Google形式)

**例:**

```python
from typing import Optional, Dict, Any

async def ocr_with_fallback(
    self,
    image_data: bytes,
    max_retries: int = 3
) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    OCR処理をフォールバック機能付きで実行
    
    Args:
        image_data: 画像データのバイト列
        max_retries: 最大リトライ回数
        
    Returns:
        Tuple[OCR結果, メタデータ]
        
    Raises:
        ValueError: image_dataが空の場合
    """
    if not image_data:
        raise ValueError("image_data cannot be empty")
    
    # 実装...
```

### ファイル構成

```
プロジェクトルート/
├── scenario_a_client/     # シナリオA (Azure SDK)
│   ├── client.py         # メインクライアント
│   ├── endpoints.py      # エンドポイント管理
│   ├── fallback_policy.py # フォールバックロジック
│   └── test_sdk.py       # SDKテスト
├── scenario_b_apim/       # シナリオB (httpx + APIM)
│   ├── client_via_apim.py # APIMクライアント
│   └── test_httpx.py     # httpxテスト
├── infrastructure/        # Bicepテンプレート
├── docs/                  # ドキュメント
└── tests/                 # 統合テスト (将来追加)
```

### コミットメッセージ

```
<type>(<scope>): <subject>

<body>

<footer>
```

**例:**
```
feat(scenario_a): add exponential backoff for SDK retry

- Implement jittered exponential backoff
- Add configurable max_backoff_seconds parameter
- Update tests to verify backoff behavior

Closes #123
```

---

## テスト

### 単体テスト

```bash
# pytest を使用 (将来的に追加予定)
pytest tests/

# 特定のテストファイル
pytest tests/test_client.py -v
```

### 統合テスト

```bash
# シナリオAの統合テスト
cd scenario_a_client
python test_sdk.py

# シナリオBの統合テスト
cd scenario_b_apim
python test_httpx.py
```

### 負荷テスト

```bash
# シナリオAの負荷テスト
cd scenario_a_client
python load_test.py --workers 10 --duration 60

# シナリオBの負荷テスト
cd scenario_b_apim
python load_test.py --workers 5 --duration 60
```

---

## ドキュメント

### ドキュメントの更新

コード変更に伴い、以下のドキュメントを更新してください:

- `README.md` - プロジェクト概要、セットアップ手順
- `docs/IMPLEMENTATION_SUMMARY.md` - 実装詳細
- `docs/SDK_MIGRATION.md` - SDK移行ガイド
- `docs/SCALING_STRATEGY.md` - スケーリング戦略
- `docs/BEST_PRACTICES.md` - ベストプラクティス

### ドキュメントのフォーマット

- Markdown形式
- コードブロックには言語指定 (\`\`\`python, \`\`\`bash)
- 見出しの階層構造を維持
- スクリーンショットは `docs/images/` に配置

---

## 質問・サポート

- **イシュー**: [GitHub Issues](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/issues)
- **ディスカッション**: [GitHub Discussions](https://github.com/YOUR_USERNAME/ocr-demo-w-sdk/discussions)
- **セキュリティ**: [SECURITY.md](SECURITY.md) を参照

---

## ライセンス

このプロジェクトへのコントリビューションは、[MIT License](LICENSE) のもとで公開されます。

---

**ハッピーコーディング！** 🚀
