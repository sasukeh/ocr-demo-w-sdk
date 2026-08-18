from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
import time
import os
import random
from rich.console import Console

console = Console()

@dataclass
class Endpoint:
    """OCR API エンドポイント情報とヘルス状態を管理するクラス"""
    url: str
    key: str
    region: str
    penalty_until: float = 0.0
    ewma_ms: float = 0.0
    lat_samples: list[int] = field(default_factory=list)
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0

    def healthy(self) -> bool:
        """エンドポイントがヘルシーかどうかを判定"""
        return time.time() >= self.penalty_until

    def success_rate(self) -> float:
        """成功率を計算"""
        if self.request_count == 0:
            return 1.0
        return self.success_count / self.request_count

    def add_success(self, latency_ms: int):
        """成功記録を追加"""
        self.request_count += 1
        self.success_count += 1
        self.lat_samples.append(latency_ms)
        if len(self.lat_samples) > 200:
            self.lat_samples.pop(0)

    def add_failure(self):
        """失敗記録を追加"""
        self.request_count += 1
        self.failure_count += 1

    def get_p95_latency(self) -> Optional[float]:
        """P95レイテンシーを計算"""
        if len(self.lat_samples) < 5:
            return None
        sorted_samples = sorted(self.lat_samples)
        p95_index = int(0.95 * (len(sorted_samples) - 1))
        return sorted_samples[p95_index]


class EndpointPool:
    """複数のOCRエンドポイントを管理し、ヘルスベースでエンドポイントを選択するクラス"""
    
    def __init__(self, endpoints: List[Endpoint], cooldown_sec: int = 60):
        self.endpoints = endpoints
        self.cooldown = cooldown_sec
        self._selection_index = 0
        
        console.print(f"[green]初期化: {len(endpoints)} エンドポイント, クールダウン: {cooldown_sec}秒[/green]")

    @classmethod
    def from_env(cls) -> 'EndpointPool':
        """環境変数からエンドポイントプールを作成"""
        endpoints_str = os.getenv('OCR_ENDPOINTS', '')
        keys_str = os.getenv('OCR_KEYS', '')
        cooldown = int(os.getenv('COOLDOWN_SEC', '60'))
        
        if not endpoints_str or not keys_str:
            raise ValueError("OCR_ENDPOINTS と OCR_KEYS 環境変数が必要です")
        
        endpoint_urls = [url.strip() for url in endpoints_str.split(',')]
        endpoint_keys = [key.strip() for key in keys_str.split(',')]
        
        if len(endpoint_urls) != len(endpoint_keys):
            raise ValueError("エンドポイントURLとキーの数が一致しません")
        
        endpoints = []
        for i, (url, key) in enumerate(zip(endpoint_urls, endpoint_keys)):
            # Infer region from URL
            region = 'unknown'
            if 'eastus' in url:
                region = 'eastus'
            elif 'japaneast' in url:
                region = 'japaneast'
            elif 'japanwest' in url:
                region = 'japanwest'  
            elif 'koreacentral' in url:
                region = 'koreacentral'
            elif 'westeurope' in url:
                region = 'westeurope'
            elif 'southeastasia' in url:
                region = 'southeastasia'
            elif 'cv-ocr-demo-je-primary' in url:
                region = 'je-primary'
            elif 'cv-ocr-demo-je-secondary' in url:
                region = 'je-secondary'
            elif 'cv-ocr-demo-je-tertiary' in url:
                region = 'je-tertiary'
            
            endpoints.append(Endpoint(
                url=url,
                key=key,
                region=region
            ))
            
        return cls(endpoints, cooldown)

    def choose(self) -> Endpoint:
        """
        ヘルシーなエンドポイントを優先して選択。
        ヘルシーなものがない場合は全体からラウンドロビンで選択。
        """
        healthy_endpoints = [ep for ep in self.endpoints if ep.healthy()]
        
        if healthy_endpoints:
            # Randomly select from healthy endpoints (load balancing)
            endpoint = random.choice(healthy_endpoints)
            console.print(f"[blue]選択: {endpoint.region} (ヘルシー)[/blue]")
            return endpoint
        else:
            # Use round-robin if all endpoints are penalized
            self._selection_index = (self._selection_index + 1) % len(self.endpoints)
            endpoint = self.endpoints[self._selection_index]
            console.print(f"[yellow]選択: {endpoint.region} (ペナルティ中だが強制)[/yellow]")
            return endpoint

    def penalize(self, ep: Endpoint, reason: str = "unknown"):
        """エンドポイントにペナルティを設定"""
        ep.penalty_until = time.time() + self.cooldown
        console.print(f"[red]ペナルティ: {ep.region} ({reason}) - {self.cooldown}秒間隔離[/red]")

    def get_status(self) -> dict:
        """全エンドポイントの状態を取得"""
        status = {}
        for ep in self.endpoints:
            status[ep.region] = {
                'healthy': ep.healthy(),
                'penalty_until': ep.penalty_until,
                'request_count': ep.request_count,
                'success_rate': ep.success_rate(),
                'ewma_ms': ep.ewma_ms,
                'p95_ms': ep.get_p95_latency()
            }
        return status

    def get_healthy_count(self) -> int:
        """ヘルシーなエンドポイント数を取得"""
        return len([ep for ep in self.endpoints if ep.healthy()])