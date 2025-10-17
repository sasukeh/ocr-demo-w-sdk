# シナリオA: クライアント側フォールバック用Dockerfile
FROM python:3.11-slim

LABEL maintainer="OCR Demo Team"
LABEL description="Scenario A: Client-side failover for Azure Computer Vision OCR"

# 作業ディレクトリ設定
WORKDIR /app

# システムパッケージ更新
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をコピーしてインストール
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . /app/scenario_a_client/
COPY ../scripts /app/scripts/

# 出力ディレクトリ作成
RUN mkdir -p /app/out /app/samples

# 環境変数設定
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import scenario_a_client; print('OK')" || exit 1

# デフォルトのエントリーポイント
ENTRYPOINT ["python", "-m", "scenario_a_client.load_test"]

# デフォルト引数（上書き可能）
CMD ["--images", "/app/samples", "--rps", "2", "--duration", "60"]