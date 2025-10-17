"""
シナリオA: クライアント側フォールバック実装

Azure Computer Vision OCR API の複数エンドポイント間での
フォールバック機能を提供するパッケージ。
"""

from client import OCRClient, create_client
from endpoints import Endpoint, EndpointPool
from fallback_policy import FallbackPolicy
from metrics import MetricsCollector

__all__ = [
    'OCRClient',
    'create_client', 
    'Endpoint',
    'EndpointPool',
    'FallbackPolicy',
    'MetricsCollector'
]