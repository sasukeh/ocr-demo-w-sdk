"""
シナリオB: APIM経由OCR実装

Azure API Management経由でComputer Vision OCR APIを呼び出し、
サーキットブレーカーとフォールバック機能を提供するパッケージ。
"""

from .client_via_apim import APIMClient, create_apim_client
from .metrics import APIMMetricsCollector

__all__ = [
    'APIMClient',
    'create_apim_client',
    'APIMMetricsCollector'
]