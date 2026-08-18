import asyncio
import httpx
import json
import time
import random
from typing import Optional, Dict, Any, Tuple
import os
from rich.console import Console

console = Console()


class APIMClient:
    """
    Azure API Management経由でOCR APIを呼び出すクライアント。
    サーキットブレーカーとフォールバックはAPIMポリシー側で処理。
    """
    
    def __init__(self, apim_gateway: str, subscription_key: str, global_timeout_ms: int = 12000):
        self.apim_gateway = apim_gateway.rstrip('/')
        self.subscription_key = subscription_key
        self.global_timeout = global_timeout_ms / 1000.0  # convert to seconds
        
        # HTTP/2 compatible client configuration
        self.client_config = {
            'http2': True,
            'timeout': httpx.Timeout(self.global_timeout),
            'limits': httpx.Limits(max_connections=20, max_keepalive_connections=10)
        }
        
        console.print(f"[green]APIMクライアント初期化: Gateway={apim_gateway}, タイムアウト={self.global_timeout}s[/green]")

    async def _make_request(self, method: str, url: str, headers: Dict[str, str], 
                          data: Optional[bytes] = None) -> Tuple[int, Dict[str, Any], int, Dict[str, str], Optional[int]]:
        """
        HTTPリクエストを実行し、レスポンス、レイテンシー、ヘッダー、Retry-Afterを返す
        
        Returns:
            Tuple[status_code, response_json, latency_ms, response_headers, retry_after_seconds]
        """
        start_time = time.time()
        
        async with httpx.AsyncClient(**self.client_config) as client:
            try:
                response = await client.request(method, url, headers=headers, content=data)
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Get response headers as dictionary
                response_headers = dict(response.headers)
                
                # Parse Retry-After header
                retry_after_seconds = None
                if 'Retry-After' in response_headers:
                    try:
                        retry_after_seconds = int(response_headers['Retry-After'])
                    except ValueError:
                        # Ignore date format (simplified)
                        retry_after_seconds = None
                
                # Process response body
                response_json = {}
                if response.content:
                    try:
                        response_json = response.json()
                    except json.JSONDecodeError:
                        response_json = {'text': response.text}
                
                return response.status_code, response_json, latency_ms, response_headers, retry_after_seconds
                    
            except asyncio.TimeoutError:
                latency_ms = int(self.global_timeout * 1000)
                return 408, {'error': 'Request timeout'}, latency_ms, {}, None
            except Exception as e:
                latency_ms = int((time.time() - start_time) * 1000)
                return 500, {'error': str(e)}, latency_ms, {}, None

    async def ocr_via_apim(self, image_data: bytes) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        APIM経由でOCR実行 (Image Analysis v4.0)
        
        Args:
            image_data: 画像データ
            
        Returns:
            Tuple[結果, メタデータ]
        """
        # Build APIM OCR endpoint URL (v4.0 imageanalysis:analyze)
        url = f"{self.apim_gateway}/vision/computervision/imageanalysis:analyze?api-version=2024-02-01&features=read"
        
        headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Content-Type': 'application/octet-stream'
        }
        
        try:
            console.print(f"[blue]APIM経由でOCR実行: {url}[/blue]")
            
            status, response, latency_ms, response_headers, retry_after = await self._make_request(
                'POST', url, headers, data=image_data
            )
            
            success = response is not None and status == 200
            
            # Extract metadata returned from APIM
            selected_endpoint = response_headers.get('X-OCR-Endpoint', 'unknown')
            apim_latency = response_headers.get('X-OCR-Latency-Ms')
            circuit_state = response_headers.get('X-OCR-Circuit')
            error_info = response_headers.get('X-OCR-Error')
            
            # Build metadata
            metadata = {
                'apim_gateway': self.apim_gateway,
                'selected_endpoint': selected_endpoint,
                'status_code': status,
                'client_latency_ms': latency_ms,
                'apim_latency_ms': int(apim_latency) if apim_latency else None,
                'circuit_state': circuit_state,
                'error_info': error_info,
                'success': success,
                'retry_after': retry_after,
                'response_headers': response_headers
            }
            
            if success:
                console.print(f"[green]成功: {selected_endpoint} ({latency_ms}ms)[/green]")
                return response, metadata
            else:
                error_msg = response.get('error', 'Unknown error')
                console.print(f"[red]失敗: {selected_endpoint} - {error_msg} ({status})[/red]")
                return None, metadata
                
        except Exception as e:
            console.print(f"[red]予期しないエラー: {e}[/red]")
            metadata = {
                'apim_gateway': self.apim_gateway,
                'selected_endpoint': 'unknown',
                'status_code': 500,
                'client_latency_ms': 0,
                'apim_latency_ms': None,
                'circuit_state': None,
                'error_info': str(e),
                'success': False,
                'retry_after': None,
                'response_headers': {}
            }
            return None, metadata


async def create_apim_client() -> APIMClient:
    """環境変数からAPIMクライアントを作成"""
    apim_gateway = os.getenv('APIM_GATEWAY')
    subscription_key = os.getenv('APIM_SUBSCRIPTION_KEY')
    global_timeout = int(os.getenv('GLOBAL_TIMEOUT_MS', '12000'))
    
    if not apim_gateway:
        raise ValueError("APIM_GATEWAY 環境変数が設定されていません")
    
    if not subscription_key:
        raise ValueError("APIM_SUBSCRIPTION_KEY 環境変数が設定されていません")
    
    client = APIMClient(apim_gateway, subscription_key, global_timeout)
    return client