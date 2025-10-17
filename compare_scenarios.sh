#!/bin/bash

# Scenario A と B の比較実行スクリプト

echo "🔍 OCR Demo: Scenario A vs B 比較分析"
echo "========================================"

# 仮想環境の確認
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Python仮想環境: $(basename $VIRTUAL_ENV)"
else
    echo "⚠️ 仮想環境が有効化されていません"
fi

# 必要なファイルの存在確認
echo ""
echo "📋 ファイル確認中..."

CLIENT_METRICS=$(ls client_metrics_*.json 2>/dev/null | tail -1)
APIM_METRICS=$(ls apim_metrics_*.json 2>/dev/null | tail -1)

if [[ -n "$CLIENT_METRICS" ]]; then
    echo "✅ Scenario A メトリクス: $CLIENT_METRICS"
else
    echo "❌ Scenario A のメトリクスファイルが見つかりません"
    echo "   先に scenario_a_client/client.py を実行してください"
    exit 1
fi

if [[ -n "$APIM_METRICS" ]]; then
    echo "✅ Scenario B メトリクス: $APIM_METRICS"
else
    echo "❌ Scenario B のメトリクスファイルが見つかりません"
    echo "   先に scenario_b_apim/apim_client.py を実行してください"
    exit 1
fi

echo ""
echo "📊 比較分析実行中..."
python scenario_b_apim/metrics_analyzer.py

echo ""
echo "✨ 比較分析が完了しました！"
echo ""
echo "🔗 次に実行できるコマンド:"
echo "  - scenario_a_client/client.py     # Scenario A 再実行"
echo "  - scenario_b_apim/apim_client.py  # Scenario B 再実行"  
echo "  - scenario_b_apim/load_tester.py  # APIM 負荷テスト"
echo "  - ./compare_scenarios.sh          # この比較分析"