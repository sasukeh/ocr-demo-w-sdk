"""
Scenario A: Azure Computer Vision SDK を使ったクライアント側フォールバック実装
"""
import asyncio
import time
import random
from typing import Optional, Dict, Any, Tuple
import os
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import (
    HttpResponseError,
    ServiceRequestError,
    ServiceResponseError
)
from endpoints import EndpointPool
from fallback_policy import FallbackPolicy
from image_utils import ImageProcessor
from rich.console import Console

console = Console()


class OCRClient:
    """
    Azure Computer Vision OCR SDK クライアント。
    複数エンドポイント間でのフォールバック機能を提供。
    """
    
    def __init__(self, pool: EndpointPool, policy: FallbackPolicy, global_timeout_ms: int = 12000):
        self.pool = pool
        self.policy = policy
        self.global_timeout = global_timeout_ms / 1000.0  # 秒に変換
        self.max_retries = int(os.getenv('MAX_RETRIES_PER_REQUEST', '2'))
        
        console.print(f"[green]OCRクライアント初期化 (Azure SDK): タイムアウト={self.global_timeout}s, 最大リトライ={self.max_retries}[/green]")

    def _create_client(self, endpoint) -> ImageAnalysisClient:
        """
        指定されたエンドポイントに対してSDKクライアントを作成
        
        Args:
            endpoint: Endpointオブジェクト
            
        Returns:
            ImageAnalysisClient インスタンス
        """
        # URLからベースエンドポイントを抽出（/vision/... を除く）
        endpoint_url = endpoint.url
        if '/vision/' in endpoint_url:
            endpoint_url = endpoint_url.split('/vision/')[0]
        
        return ImageAnalysisClient(
            endpoint=endpoint_url,
            credential=AzureKeyCredential(endpoint.key)
        )

    async def _analyze_image_with_sdk(self, endpoint, image_data: bytes) -> Tuple[Optional[Dict[str, Any]], int, int, Optional[int]]:
        """
        Azure Computer Vision SDK を使って画像解析（OCR）を実行
        
        Args:
            endpoint: Endpointオブジェクト
            image_data: 画像データ（バイト列）
            
        Returns:
            Tuple[結果, ステータスコード, レイテンシー(ms), Retry-After秒数]
        """
        start_time = time.time()
        
        try:
            # SDKクライアントを作成
            client = self._create_client(endpoint)
            
            # 画像解析を実行（同期的に）
            # SDKは内部で適切なタイムアウト処理を行う
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: client.analyze(
                    image_data=image_data,
                    visual_features=[VisualFeatures.READ],
                    language="ja"
                )
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 結果を辞書形式に変換
            response_dict = {
                'readResult': {
                    'blocks': []
                }
            }
            
            if result.read and result.read.blocks:
                for block in result.read.blocks:
                    block_dict = {
                        'lines': []
                    }
                    for line in block.lines:
                        line_dict = {
                            'text': line.text,
                            'boundingPolygon': [
                                {'x': p.x, 'y': p.y} for p in line.bounding_polygon
                            ] if line.bounding_polygon else [],
                            'words': []
                        }
                        for word in line.words:
                            word_dict = {
                                'text': word.text,
                                'boundingPolygon': [
                                    {'x': p.x, 'y': p.y} for p in word.bounding_polygon
                                ] if word.bounding_polygon else [],
                                'confidence': word.confidence
                            }
                            line_dict['words'].append(word_dict)
                        block_dict['lines'].append(line_dict)
                    response_dict['readResult']['blocks'].append(block_dict)
            
            return response_dict, 200, latency_ms, None
            
        except HttpResponseError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            status_code = e.status_code if hasattr(e, 'status_code') else 500
            
            # Retry-Afterヘッダーを取得
            retry_after = None
            if hasattr(e, 'response') and e.response and hasattr(e.response, 'headers'):
                retry_after_header = e.response.headers.get('Retry-After') or e.response.headers.get('retry-after')
                if retry_after_header:
                    try:
                        retry_after = int(retry_after_header)
                    except ValueError:
                        pass
            
            console.print(f"[red]HTTP エラー: {status_code} - {str(e)}[/red]")
            return None, status_code, latency_ms, retry_after
            
        except (ServiceRequestError, ServiceResponseError) as e:
            latency_ms = int((time.time() - start_time) * 1000)
            console.print(f"[red]サービスエラー: {str(e)}[/red]")
            return None, 500, latency_ms, None
            
        except asyncio.TimeoutError:
            latency_ms = int(self.global_timeout * 1000)
            console.print(f"[red]タイムアウト: {self.global_timeout}秒[/red]")
            return None, 408, latency_ms, None
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            console.print(f"[red]予期しないエラー: {str(e)}[/red]")
            return None, 500, latency_ms, None

    async def ocr_with_fallback(self, image_data: bytes) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        フォールバック機能付きOCR実行
        
        Args:
            image_data: 画像データ
            
        Returns:
            Tuple[結果, メタデータ]
        """
        # 画像前処理（リサイズ・圧縮）
        processed_image_data, processing_info = ImageProcessor.process_image(image_data)
        
        attempts = []
        fallback_count = 0
        
        for attempt in range(self.max_retries + 1):
            endpoint = self.pool.choose()
            
            try:
                console.print(f"[blue]試行 {attempt + 1}: {endpoint.region} (Azure SDK使用)[/blue]")
                
                # SDKを使って画像解析を実行
                result, status, latency_ms, retry_after = await self._analyze_image_with_sdk(
                    endpoint, 
                    processed_image_data
                )
                
                success = result is not None and status == 200
                
                attempt_info = {
                    'endpoint': endpoint.region,
                    'status': status,
                    'latency_ms': latency_ms,
                    'success': success,
                    'attempt': attempt + 1,
                    'retry_after': retry_after,
                    'method': 'Azure SDK'
                }
                attempts.append(attempt_info)
                
                # フォールバック判定
                need_fallback = self.policy.handle_request_result(endpoint, latency_ms, status, success)
                
                if success and not need_fallback:
                    # 成功！
                    metadata = {
                        'attempts': attempts,
                        'fallback_count': fallback_count,
                        'final_endpoint': endpoint.region,
                        'total_attempts': len(attempts),
                        'image_processing': processing_info,
                        'client_type': 'Azure SDK'
                    }
                    return result, metadata
                
                if need_fallback:
                    fallback_count += 1
                    
                # 最後の試行でない場合は継続
                if attempt < self.max_retries:
                    # Retry-Afterがある場合はそれを尊重、なければ指数バックオフ + ジッター
                    if retry_after and retry_after > 0:
                        delay = min(retry_after, 10.0)  # 最大10秒に制限
                        console.print(f"[yellow]Retry-Afterにより{delay:.2f}秒待機後にリトライ[/yellow]")
                    else:
                        delay = min(2 ** attempt + random.uniform(0, 1), 5.0)
                        console.print(f"[yellow]指数バックオフで{delay:.2f}秒待機後にリトライ[/yellow]")
                    
                    await asyncio.sleep(delay)
                
            except Exception as e:
                console.print(f"[red]予期しないエラー: {e}[/red]")
                attempt_info = {
                    'endpoint': endpoint.region,
                    'status': 500,
                    'latency_ms': 0,
                    'success': False,
                    'attempt': attempt + 1,
                    'error': str(e),
                    'method': 'Azure SDK'
                }
                attempts.append(attempt_info)
                fallback_count += 1
        
        # 全ての試行が失敗
        metadata = {
            'attempts': attempts,
            'fallback_count': fallback_count,
            'final_endpoint': None,
            'total_attempts': len(attempts),
            'image_processing': processing_info,
            'client_type': 'Azure SDK'
        }
        return None, metadata


async def create_client() -> OCRClient:
    """環境変数からOCRクライアントを作成"""
    pool = EndpointPool.from_env()
    
    single_ms = int(os.getenv('FALLBACK_SINGLE_MS', '1800'))
    ewma_p95_ms = int(os.getenv('EWMA_P95_MS', '2000'))
    alpha = float(os.getenv('EWMA_ALPHA', '0.2'))
    global_timeout = int(os.getenv('GLOBAL_TIMEOUT_MS', '12000'))
    
    policy = FallbackPolicy(pool, single_ms, ewma_p95_ms, alpha)
    client = OCRClient(pool, policy, global_timeout)
    
    return client
