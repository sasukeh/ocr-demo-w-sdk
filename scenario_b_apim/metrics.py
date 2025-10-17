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
class APIMRequestMetric:
    """APIM経由リクエストのメトリクス"""
    timestamp: float
    apim_gateway: str
    selected_endpoint: str
    success: bool
    status_code: Optional[int]
    client_latency_ms: int
    apim_latency_ms: Optional[int]
    circuit_state: Optional[str]
    retry_after: Optional[int] = None
    error_message: Optional[str] = None


class APIMMetricsCollector:
    """APIM経由リクエストのメトリクス収集・集計クラス"""
    
    def __init__(self):
        self.requests: List[APIMRequestMetric] = []
        self.start_time = time.time()
        
        # Prometheus メトリクス
        self.request_counter = Counter('apim_ocr_requests_total', 'Total APIM OCR requests', ['endpoint', 'status'])
        self.latency_histogram = Histogram('apim_ocr_request_duration_seconds', 'APIM request duration', ['endpoint'])
        self.circuit_counter = Counter('apim_ocr_circuit_events_total', 'Circuit breaker events', ['endpoint', 'state'])
        self.endpoint_health = Gauge('apim_ocr_endpoint_health', 'APIM endpoint health', ['endpoint'])

    def record_request(self, apim_gateway: str, selected_endpoint: str, success: bool, 
                      status_code: Optional[int], client_latency_ms: int, 
                      apim_latency_ms: Optional[int], circuit_state: Optional[str],
                      retry_after: Optional[int] = None, error_message: Optional[str] = None):
        """APIM リクエスト結果を記録"""
        metric = APIMRequestMetric(
            timestamp=time.time(),
            apim_gateway=apim_gateway,
            selected_endpoint=selected_endpoint,
            success=success,
            status_code=status_code,
            client_latency_ms=client_latency_ms,
            apim_latency_ms=apim_latency_ms,
            circuit_state=circuit_state,
            retry_after=retry_after,
            error_message=error_message
        )
        
        self.requests.append(metric)
        
        # Prometheusメトリクス更新
        status_label = str(status_code) if status_code else 'unknown'
        self.request_counter.labels(endpoint=selected_endpoint, status=status_label).inc()
        self.latency_histogram.labels(endpoint=selected_endpoint).observe(client_latency_ms / 1000.0)
        
        if circuit_state:
            self.circuit_counter.labels(endpoint=selected_endpoint, state=circuit_state).inc()

    def get_summary_stats(self) -> Dict:
        """サマリー統計を計算"""
        if not self.requests:
            return {}
        
        # 基本統計
        total_requests = len(self.requests)
        successful_requests = len([r for r in self.requests if r.success])
        success_rate = successful_requests / total_requests
        
        # レイテンシー統計（クライアント側）
        client_latencies = [r.client_latency_ms for r in self.requests]
        client_p50 = statistics.median(client_latencies)
        client_p95 = statistics.quantiles(client_latencies, n=20)[18] if len(client_latencies) >= 20 else max(client_latencies)
        client_avg = statistics.mean(client_latencies)
        
        # APIM側レイテンシー統計
        apim_latencies = [r.apim_latency_ms for r in self.requests if r.apim_latency_ms is not None]
        apim_stats = {}
        if apim_latencies:
            apim_stats = {
                'p50_ms': statistics.median(apim_latencies),
                'p95_ms': statistics.quantiles(apim_latencies, n=20)[18] if len(apim_latencies) >= 20 else max(apim_latencies),
                'avg_ms': statistics.mean(apim_latencies)
            }
        
        # エラー統計
        error_counts = defaultdict(int)
        for r in self.requests:
            if not r.success and r.status_code:
                error_counts[r.status_code] += 1
        
        # エンドポイント別統計
        endpoint_stats = defaultdict(lambda: {'requests': 0, 'successes': 0, 'latencies': [], 'circuit_events': []})
        for r in self.requests:
            stats = endpoint_stats[r.selected_endpoint]
            stats['requests'] += 1
            if r.success:
                stats['successes'] += 1
            stats['latencies'].append(r.client_latency_ms)
            if r.circuit_state:
                stats['circuit_events'].append(r.circuit_state)
        
        # サーキットブレーカー統計
        circuit_events = defaultdict(int)
        for r in self.requests:
            if r.circuit_state:
                circuit_events[r.circuit_state] += 1
        
        # 実行時間
        duration_sec = time.time() - self.start_time
        rps = total_requests / duration_sec if duration_sec > 0 else 0
        
        return {
            'summary': {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'success_rate': success_rate,
                'duration_sec': duration_sec,
                'rps': rps
            },
            'client_latency': {
                'p50_ms': client_p50,
                'p95_ms': client_p95,
                'avg_ms': client_avg
            },
            'apim_latency': apim_stats,
            'errors': dict(error_counts),
            'circuit_breaker': dict(circuit_events),
            'endpoints': {
                ep: {
                    'requests': stats['requests'],
                    'success_rate': stats['successes'] / stats['requests'],
                    'avg_latency_ms': statistics.mean(stats['latencies']) if stats['latencies'] else 0,
                    'p95_latency_ms': statistics.quantiles(stats['latencies'], n=20)[18] 
                                    if len(stats['latencies']) >= 20 else (max(stats['latencies']) if stats['latencies'] else 0),
                    'circuit_events': len(stats['circuit_events'])
                } for ep, stats in endpoint_stats.items()
            }
        }

    def print_summary(self):
        """サマリー統計をコンソールに表示"""
        stats = self.get_summary_stats()
        
        if not stats:
            console.print("[yellow]メトリクスデータがありません[/yellow]")
            return
        
        console.print("\n[bold blue]═══ APIM OCR 負荷テスト結果 ═══[/bold blue]")
        
        # 全体統計
        summary = stats['summary']
        console.print(f"\n[bold]全体統計:[/bold]")
        console.print(f"  総リクエスト数: {summary['total_requests']}")
        console.print(f"  成功数: {summary['successful_requests']}")
        console.print(f"  成功率: {summary['success_rate']:.2%}")
        console.print(f"  実行時間: {summary['duration_sec']:.1f}秒")
        console.print(f"  実際のRPS: {summary['rps']:.2f}")
        
        # クライアント側レイテンシー統計
        client_latency = stats['client_latency']
        console.print(f"\n[bold]クライアント側レイテンシー:[/bold]")
        console.print(f"  P50: {client_latency['p50_ms']:.1f}ms")
        console.print(f"  P95: {client_latency['p95_ms']:.1f}ms")
        console.print(f"  平均: {client_latency['avg_ms']:.1f}ms")
        
        # APIM側レイテンシー統計
        if stats['apim_latency']:
            apim_latency = stats['apim_latency']
            console.print(f"\n[bold]APIM側レイテンシー:[/bold]")
            console.print(f"  P50: {apim_latency['p50_ms']:.1f}ms")
            console.print(f"  P95: {apim_latency['p95_ms']:.1f}ms")
            console.print(f"  平均: {apim_latency['avg_ms']:.1f}ms")
        
        # サーキットブレーカー統計
        if stats['circuit_breaker']:
            console.print(f"\n[bold magenta]サーキットブレーカー統計:[/bold magenta]")
            for state, count in stats['circuit_breaker'].items():
                console.print(f"  {state}: {count}回")
        
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
        table.add_column("サーキット開放数")
        
        for endpoint, ep_stats in stats['endpoints'].items():
            table.add_row(
                endpoint,
                str(ep_stats['requests']),
                f"{ep_stats['success_rate']:.2%}",
                f"{ep_stats['avg_latency_ms']:.1f}ms",
                f"{ep_stats['p95_latency_ms']:.1f}ms",
                str(ep_stats['circuit_events'])
            )
        
        console.print(table)

    def save_to_csv(self, filepath: str):
        """結果をCSVファイルに保存"""
        import csv
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # ヘッダー
            writer.writerow([
                'timestamp', 'apim_gateway', 'selected_endpoint', 'success', 'status_code', 
                'client_latency_ms', 'apim_latency_ms', 'circuit_state', 'retry_after', 'error_message'
            ])
            
            # データ
            for req in self.requests:
                writer.writerow([
                    req.timestamp,
                    req.apim_gateway,
                    req.selected_endpoint,
                    req.success,
                    req.status_code,
                    req.client_latency_ms,
                    req.apim_latency_ms,
                    req.circuit_state,
                    req.retry_after,
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