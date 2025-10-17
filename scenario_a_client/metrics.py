from typing import Dict, List, Optional
import time
import json
from dataclasses import dataclass, asdict
from collections import defaultdict
import statistics
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class RequestMetric:
    """個別リクエストのメトリクス"""
    timestamp: float
    endpoint: str
    success: bool
    status_code: Optional[int]
    latency_ms: int
    fallback_count: int
    attempt_count: int
    error_message: Optional[str] = None


class MetricsCollector:
    """メトリクス収集・集計クラス"""
    
    def __init__(self):
        self.requests: List[RequestMetric] = []
        self.start_time = time.time()
        
        # Prometheus メトリクス
        self.request_counter = Counter('ocr_requests_total', 'Total OCR requests', ['endpoint', 'status'])
        self.latency_histogram = Histogram('ocr_request_duration_seconds', 'Request duration', ['endpoint'])
        self.fallback_counter = Counter('ocr_fallbacks_total', 'Total fallbacks', ['from_endpoint', 'reason'])
        self.endpoint_health = Gauge('ocr_endpoint_health', 'Endpoint health status', ['endpoint'])

    def record_request(self, endpoint: str, success: bool, status_code: Optional[int], 
                      latency_ms: int, fallback_count: int, attempt_count: int, 
                      error_message: Optional[str] = None):
        """リクエスト結果を記録"""
        metric = RequestMetric(
            timestamp=time.time(),
            endpoint=endpoint,
            success=success,
            status_code=status_code,
            latency_ms=latency_ms,
            fallback_count=fallback_count,
            attempt_count=attempt_count,
            error_message=error_message
        )
        
        self.requests.append(metric)
        
        # Prometheusメトリクス更新
        status_label = str(status_code) if status_code else 'unknown'
        self.request_counter.labels(endpoint=endpoint, status=status_label).inc()
        self.latency_histogram.labels(endpoint=endpoint).observe(latency_ms / 1000.0)
        
        if fallback_count > 0:
            self.fallback_counter.labels(from_endpoint=endpoint, reason='failure').inc(fallback_count)

    def get_summary_stats(self) -> Dict:
        """サマリー統計を計算"""
        if not self.requests:
            return {}
        
        # 基本統計
        total_requests = len(self.requests)
        successful_requests = len([r for r in self.requests if r.success])
        success_rate = successful_requests / total_requests
        
        # レイテンシー統計
        latencies = [r.latency_ms for r in self.requests]
        p50_latency = statistics.median(latencies)
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
        p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
        avg_latency = statistics.mean(latencies)
        
        # エラー統計
        error_counts = defaultdict(int)
        for r in self.requests:
            if not r.success and r.status_code:
                error_counts[r.status_code] += 1
        
        # エンドポイント別統計
        endpoint_stats = defaultdict(lambda: {'requests': 0, 'successes': 0, 'latencies': []})
        for r in self.requests:
            stats = endpoint_stats[r.endpoint]
            stats['requests'] += 1
            if r.success:
                stats['successes'] += 1
            stats['latencies'].append(r.latency_ms)
        
        # フォールバック統計
        total_fallbacks = sum(r.fallback_count for r in self.requests)
        
        # 実行時間
        duration_sec = time.time() - self.start_time
        rps = total_requests / duration_sec if duration_sec > 0 else 0
        
        return {
            'summary': {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'success_rate': success_rate,
                'total_fallbacks': total_fallbacks,
                'duration_sec': duration_sec,
                'rps': rps
            },
            'latency': {
                'p50_ms': p50_latency,
                'p95_ms': p95_latency,
                'p99_ms': p99_latency,
                'avg_ms': avg_latency
            },
            'errors': dict(error_counts),
            'endpoints': {
                ep: {
                    'requests': stats['requests'],
                    'success_rate': stats['successes'] / stats['requests'],
                    'avg_latency_ms': statistics.mean(stats['latencies']) if stats['latencies'] else 0,
                    'p95_latency_ms': statistics.quantiles(stats['latencies'], n=20)[18] 
                                    if len(stats['latencies']) >= 20 else (max(stats['latencies']) if stats['latencies'] else 0)
                } for ep, stats in endpoint_stats.items()
            }
        }

    def print_summary(self):
        """サマリー統計をコンソールに表示"""
        stats = self.get_summary_stats()
        
        if not stats:
            console.print("[yellow]メトリクスデータがありません[/yellow]")
            return
        
        console.print("\n[bold green]═══ OCR 負荷テスト結果 ═══[/bold green]")
        
        # 全体統計
        summary = stats['summary']
        console.print(f"\n[bold]全体統計:[/bold]")
        console.print(f"  総リクエスト数: {summary['total_requests']}")
        console.print(f"  成功数: {summary['successful_requests']}")
        console.print(f"  成功率: {summary['success_rate']:.2%}")
        console.print(f"  総フォールバック数: {summary['total_fallbacks']}")
        console.print(f"  実行時間: {summary['duration_sec']:.1f}秒")
        console.print(f"  実際のRPS: {summary['rps']:.2f}")
        
        # レイテンシー統計
        latency = stats['latency']
        console.print(f"\n[bold]レイテンシー統計:[/bold]")
        console.print(f"  P50: {latency['p50_ms']:.1f}ms")
        console.print(f"  P95: {latency['p95_ms']:.1f}ms")
        console.print(f"  P99: {latency['p99_ms']:.1f}ms")
        console.print(f"  平均: {latency['avg_ms']:.1f}ms")
        
        # エラー統計
        if stats['errors']:
            console.print(f"\n[bold red]エラー統計:[/bold red]")
            for status, count in stats['errors'].items():
                console.print(f"  HTTP {status}: {count}回")
        
        # エンドポイント別統計
        console.print(f"\n[bold]エンドポイント別統計:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("エンドポイント")
        table.add_column("リクエスト数")
        table.add_column("成功率")
        table.add_column("平均レイテンシー")
        table.add_column("P95レイテンシー")
        
        for endpoint, ep_stats in stats['endpoints'].items():
            table.add_row(
                endpoint,
                str(ep_stats['requests']),
                f"{ep_stats['success_rate']:.2%}",
                f"{ep_stats['avg_latency_ms']:.1f}ms",
                f"{ep_stats['p95_latency_ms']:.1f}ms"
            )
        
        console.print(table)

    def save_to_csv(self, filepath: str):
        """結果をCSVファイルに保存"""
        import csv
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # ヘッダー
            writer.writerow([
                'timestamp', 'endpoint', 'success', 'status_code', 
                'latency_ms', 'fallback_count', 'attempt_count', 'error_message'
            ])
            
            # データ
            for req in self.requests:
                writer.writerow([
                    req.timestamp,
                    req.endpoint,
                    req.success,
                    req.status_code,
                    req.latency_ms,
                    req.fallback_count,
                    req.attempt_count,
                    req.error_message or ''
                ])
        
        console.print(f"[green]結果をCSVファイルに保存: {filepath}[/green]")

    def save_summary_json(self, filepath: str):
        """サマリー統計をJSONファイルに保存"""
        stats = self.get_summary_stats()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]サマリーをJSONファイルに保存: {filepath}[/green]")

    def get_prometheus_metrics(self) -> str:
        """Prometheusメトリクス形式で出力"""
        return generate_latest().decode('utf-8')