import math
import random
import time
from typing import Tuple, Optional
from endpoints import EndpointPool, Endpoint
from rich.console import Console

console = Console()


class FallbackPolicy:
    """
    フォールバック判定ポリシーを管理するクラス。
    レイテンシー、エラーレート、EWMA P95に基づいてフォールバック判定を行う。
    """
    
    def __init__(self, pool: EndpointPool, single_ms: int, ewma_p95_ms: int, alpha: float):
        self.pool = pool
        self.single_ms = single_ms  # 単発リクエストの閾値
        self.ewma_p95_ms = ewma_p95_ms  # EWMA P95の閾値
        self.alpha = alpha  # EWMA の重み
        
        console.print(f"[green]フォールバックポリシー初期化: 単発閾値={single_ms}ms, P95閾値={ewma_p95_ms}ms, alpha={alpha}[/green]")

    def update_latency(self, ep: Endpoint, ms: int):
        """エンドポイントのレイテンシー統計を更新"""
        # EWMA 更新
        if ep.ewma_ms == 0:
            ep.ewma_ms = float(ms)
        else:
            ep.ewma_ms = (1 - self.alpha) * ep.ewma_ms + self.alpha * ms
        
        # サンプル追加（最大200個保持）
        ep.lat_samples.append(ms)
        if len(ep.lat_samples) > 200:
            ep.lat_samples.pop(0)
        
        console.print(f"[dim]レイテンシー更新: {ep.region} {ms}ms (EWMA: {ep.ewma_ms:.1f}ms)[/dim]")

    def should_fallback(self, ep: Endpoint, ms: int, status: Optional[int]) -> Tuple[bool, str]:
        """
        フォールバックすべきかを判定
        
        Returns:
            Tuple[bool, str]: (フォールバック要否, 理由)
        """
        # 1. HTTPステータスコードによる判定
        if status is not None:
            if status == 429:
                return True, "429_RATE_LIMIT"
            elif status >= 500:
                return True, f"5XX_ERROR_{status}"
        
        # 2. 単発レイテンシーによる判定
        if ms >= self.single_ms:
            return True, f"SLOW_SINGLE_{ms}ms"
        
        # 3. EWMA P95による判定（十分なサンプルがある場合のみ）
        if len(ep.lat_samples) >= 20:
            p95 = ep.get_p95_latency()
            if p95 is not None and p95 >= self.ewma_p95_ms:
                return True, f"EWMA_P95_{p95:.1f}ms"
        
        return False, "OK"

    def handle_request_result(self, ep: Endpoint, ms: int, status: Optional[int], success: bool) -> bool:
        """
        リクエスト結果を処理し、フォールバックが必要かを判定
        
        Returns:
            bool: フォールバックが必要な場合True
        """
        if success:
            ep.add_success(ms)
            self.update_latency(ep, ms)
        else:
            ep.add_failure()
        
        should_fallback, reason = self.should_fallback(ep, ms, status)
        
        if should_fallback:
            self.pool.penalize(ep, reason)
            console.print(f"[red]フォールバック発動: {ep.region} - {reason}[/red]")
            return True
        else:
            console.print(f"[green]成功: {ep.region} - {ms}ms[/green]")
            return False

    def get_statistics(self) -> dict:
        """統計情報を取得"""
        stats = {}
        for ep in self.pool.endpoints:
            stats[ep.region] = {
                'requests': ep.request_count,
                'success_rate': ep.success_rate(),
                'ewma_ms': ep.ewma_ms,
                'p95_ms': ep.get_p95_latency(),
                'healthy': ep.healthy(),
                'samples_count': len(ep.lat_samples)
            }
        return stats