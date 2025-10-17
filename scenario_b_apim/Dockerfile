# シナリオB: APIM経由OCR用Dockerfile
FROM python:3.11-slim

LABEL maintainer="OCR Demo Team"
LABEL description="Scenario B: APIM-based circuit breaker for Azure Computer Vision OCR"

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
COPY . /app/scenario_b_apim/
COPY ../scripts /app/scripts/

# 出力ディレクトリ作成
RUN mkdir -p /app/out /app/samples

# 環境変数設定
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import scenario_b_apim; print('OK')" || exit 1

# デフォルトのエントリーポイント
ENTRYPOINT ["python", "-m", "scenario_b_apim.load_test"]

# デフォルト引数（上書き可能）
CMD ["--images", "/app/samples", "--rps", "2", "--duration", "60"]