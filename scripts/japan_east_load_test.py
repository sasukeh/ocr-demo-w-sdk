#!/usr/bin/env python3
"""
Japan East Computer Vision 負荷分散・フォールバックテストスクリプト
同一リージョン内での3エンドポイント間の最適化効果を測定
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any
import json
from dataclasses import dataclass
import statistics

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scenario_a_client.client import create_client
from scenario_a_client.endpoints import EndpointPool
from scenario_a_client.fallback_policy import FallbackPolicy
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, TaskID
from rich.live import Live
import click
from dotenv import load_dotenv

console = Console()

@dataclass
class TestResult:
    """テスト結果データクラス"""
    endpoint: str
    success: bool
    latency_ms: int
    status_code: int
    error: str = None
    image_size_bytes: int = 0
    processing_info: Dict = None

@dataclass 
class TestSummary:
    """テストサマリーデータクラス"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    success_rate: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    min_latency_ms: int
    max_latency_ms: int
    endpoint_distribution: Dict[str, int]
    fallback_count: int
    total_duration_sec: float
    requests_per_sec: float

class JapanEastLoadTester:
    """Japan East 負荷テスタークラス"""
    
    def __init__(self, env_file: str = '.env.japan-east'):
        # 環境変数読み込み
        if not load_dotenv(env_file):
            raise ValueError(f"環境変数ファイルが見つかりません: {env_file}")
        
        # 設定読み込み
        self.concurrency = int(os.getenv('LOAD_TEST_CONCURRENCY', '10'))
        self.duration = int(os.getenv('LOAD_TEST_DURATION', '300'))
        self.image_path = Path(os.getenv('LOAD_TEST_IMAGE_PATH', './samples/handwritten_text.jpg'))
        
        # エンドポイント設定確認
        endpoints_str = os.getenv('OCR_ENDPOINTS', '')
        keys_str = os.getenv('OCR_KEYS', '') 
        
        if not endpoints_str or not keys_str:
            raise ValueError("OCR_ENDPOINTS または OCR_KEYS が設定されていません")
        
        # OCRクライアント初期化は後で行う
        self.client = None
        self.image_data = None
        
        # 結果格納
        self.results: List[TestResult] = []
        self.start_time = None
        self.end_time = None
        
        console.print(f"[green]Japan East 負荷テスター初期化完了[/green]")
        console.print(f"並行性: {self.concurrency}, 持続時間: {self.duration}秒")
    
    async def initialize(self):
        """非同期初期化"""
        # OCRクライアント作成
        self.client = await create_client()
        
        # テスト画像読み込み
        if not self.image_path.exists():
            raise FileNotFoundError(f"テスト画像が見つかりません: {self.image_path}")
        
        with open(self.image_path, 'rb') as f:
            self.image_data = f.read()
        
        console.print(f"[green]テスト画像読み込み完了: {self.image_path.name} ({len(self.image_data):,} bytes)[/green]")
    
    async def single_request(self, request_id: int) -> TestResult:
        """単一リクエストの実行"""
        start_time = time.time()
        
        try:
            result, metadata = await self.client.ocr_with_fallback(self.image_data)
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if result:
                final_endpoint = metadata.get('final_endpoint', 'unknown')
                return TestResult(
                    endpoint=final_endpoint,
                    success=True,
                    latency_ms=latency_ms,
                    status_code=200,
                    image_size_bytes=len(self.image_data),
                    processing_info=metadata.get('image_processing')
                )
            else:
                return TestResult(
                    endpoint='failed',
                    success=False,
                    latency_ms=latency_ms,
                    status_code=500,
                    error="OCR処理失敗",
                    image_size_bytes=len(self.image_data)
                )
                
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return TestResult(
                endpoint='error',
                success=False,
                latency_ms=latency_ms,
                status_code=500,
                error=str(e),
                image_size_bytes=len(self.image_data)
            )
    
    async def worker(self, worker_id: int, progress: Progress, task_id: TaskID):
        """ワーカータスク"""
        request_count = 0
        
        while time.time() - self.start_time < self.duration:
            request_count += 1
            result = await self.single_request(f"{worker_id}-{request_count}")
            self.results.append(result)
            
            # プログレスを更新
            progress.advance(task_id)
            
            # 短い間隔でリクエスト調整
            await asyncio.sleep(0.1)
    
    async def run_load_test(self) -> TestSummary:
        """負荷テストの実行"""
        console.print(f"[yellow]負荷テスト開始: {self.concurrency}並行 × {self.duration}秒[/yellow]")
        
        # 進行状況表示の準備
        with Progress() as progress:
            task_id = progress.add_task("[cyan]リクエスト実行中...", total=None)
            
            # テスト開始時刻記録
            self.start_time = time.time()
            
            # 複数ワーカーを起動
            workers = [
                self.worker(i, progress, task_id) 
                for i in range(self.concurrency)
            ]
            
            # 全ワーカーが完了するまで待機
            await asyncio.gather(*workers)
            
            # テスト終了時刻記録
            self.end_time = time.time()
        
        # 結果分析
        return self.analyze_results()
    
    def analyze_results(self) -> TestSummary:
        """結果分析"""
        if not self.results:
            raise ValueError("テスト結果がありません")
        
        # 基本統計
        total_requests = len(self.results)
        successful_results = [r for r in self.results if r.success]
        successful_requests = len(successful_results)
        failed_requests = total_requests - successful_requests
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        
        # レイテンシー統計（成功したリクエストのみ）
        if successful_results:
            latencies = [r.latency_ms for r in successful_results]
            avg_latency = statistics.mean(latencies)
            p50_latency = statistics.median(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
            p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
        else:
            avg_latency = p50_latency = p95_latency = p99_latency = min_latency = max_latency = 0
        
        # エンドポイント分布
        endpoint_distribution = {}
        fallback_count = 0
        
        for result in self.results:
            endpoint = result.endpoint
            endpoint_distribution[endpoint] = endpoint_distribution.get(endpoint, 0) + 1
            
            # フォールバックが発生したかチェック（プライマリ以外を使用）
            if endpoint not in ['cv-ocr-demo-je-primary', 'primary'] and result.success:
                fallback_count += 1
        
        # パフォーマンス計算
        total_duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        requests_per_sec = total_requests / total_duration if total_duration > 0 else 0
        
        return TestSummary(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            success_rate=success_rate,
            avg_latency_ms=avg_latency,
            p50_latency_ms=p50_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            min_latency_ms=min_latency,
            max_latency_ms=max_latency,
            endpoint_distribution=endpoint_distribution,
            fallback_count=fallback_count,
            total_duration_sec=total_duration,
            requests_per_sec=requests_per_sec
        )
    
    def display_results(self, summary: TestSummary):
        """結果表示"""
        # メインサマリー
        console.print(f"\n[bold blue]🚀 Japan East 負荷テスト結果[/bold blue]")
        console.print("=" * 60)
        
        # 基本統計テーブル
        stats_table = Table(title="📊 基本統計", show_header=True, header_style="bold magenta")
        stats_table.add_column("項目", style="cyan")
        stats_table.add_column("値", justify="right")
        
        stats_table.add_row("総リクエスト数", f"{summary.total_requests:,}")
        stats_table.add_row("成功", f"[green]{summary.successful_requests:,}[/green]")
        stats_table.add_row("失敗", f"[red]{summary.failed_requests:,}[/red]")
        stats_table.add_row("成功率", f"[green]{summary.success_rate:.1%}[/green]")
        stats_table.add_row("テスト時間", f"{summary.total_duration_sec:.1f}秒")
        stats_table.add_row("スループット", f"{summary.requests_per_sec:.1f} req/sec")
        
        console.print(stats_table)
        
        # レイテンシー統計テーブル  
        latency_table = Table(title="⏱️ レイテンシー統計", show_header=True, header_style="bold magenta")
        latency_table.add_column("統計", style="cyan")
        latency_table.add_column("値 (ms)", justify="right")
        
        latency_table.add_row("平均", f"{summary.avg_latency_ms:.0f}")
        latency_table.add_row("中央値 (P50)", f"{summary.p50_latency_ms:.0f}")
        latency_table.add_row("P95", f"{summary.p95_latency_ms:.0f}")
        latency_table.add_row("P99", f"{summary.p99_latency_ms:.0f}")
        latency_table.add_row("最小", f"[green]{summary.min_latency_ms}[/green]")
        latency_table.add_row("最大", f"[red]{summary.max_latency_ms}[/red]")
        
        console.print(latency_table)
        
        # エンドポイント分布
        endpoint_table = Table(title="🌐 エンドポイント利用分布", show_header=True, header_style="bold magenta")
        endpoint_table.add_column("エンドポイント", style="cyan")
        endpoint_table.add_column("リクエスト数", justify="right")
        endpoint_table.add_column("割合", justify="right")
        
        for endpoint, count in summary.endpoint_distribution.items():
            percentage = (count / summary.total_requests) * 100
            color = "green" if "primary" in endpoint else "yellow" if count > 0 else "red"
            endpoint_table.add_row(
                endpoint,
                f"[{color}]{count:,}[/{color}]",
                f"[{color}]{percentage:.1f}%[/{color}]"
            )
        
        console.print(endpoint_table)
        
        # フォールバック分析
        fallback_panel = Panel(
            f"[yellow]フォールバック発生: {summary.fallback_count:,} 回[/yellow]\n"
            f"フォールバック率: [yellow]{(summary.fallback_count/summary.total_requests)*100:.1f}%[/yellow]\n"
            f"負荷分散効果: [{'green' if summary.fallback_count > 0 else 'red'}]{'有効' if summary.fallback_count > 0 else '無効'}[/{'green' if summary.fallback_count > 0 else 'red'}]",
            title="🔄 フォールバック分析",
            border_style="yellow"
        )
        console.print(fallback_panel)

@click.command()
@click.option('--env-file', default='.env.japan-east', help='環境変数ファイル')
@click.option('--concurrency', type=int, help='並行リクエスト数')
@click.option('--duration', type=int, help='テスト持続時間（秒）')
@click.option('--output', help='結果をJSONファイルに出力')
def main(env_file: str, concurrency: int, duration: int, output: str):
    """Japan East Computer Vision 負荷分散・フォールバックテスト"""
    
    try:
        # テスター初期化
        tester = JapanEastLoadTester(env_file)
        
        # CLIオプションで設定上書き
        if concurrency:
            tester.concurrency = concurrency
        if duration:
            tester.duration = duration
        
        async def run_test():
            await tester.initialize()
            summary = await tester.run_load_test()
            tester.display_results(summary)
            
            # JSON出力
            if output:
                result_data = {
                    'test_config': {
                        'concurrency': tester.concurrency,
                        'duration': tester.duration,
                        'image_path': str(tester.image_path),
                        'image_size_bytes': len(tester.image_data)
                    },
                    'summary': {
                        'total_requests': summary.total_requests,
                        'successful_requests': summary.successful_requests,
                        'failed_requests': summary.failed_requests,
                        'success_rate': summary.success_rate,
                        'avg_latency_ms': summary.avg_latency_ms,
                        'p50_latency_ms': summary.p50_latency_ms,
                        'p95_latency_ms': summary.p95_latency_ms,
                        'p99_latency_ms': summary.p99_latency_ms,
                        'min_latency_ms': summary.min_latency_ms,
                        'max_latency_ms': summary.max_latency_ms,
                        'endpoint_distribution': summary.endpoint_distribution,
                        'fallback_count': summary.fallback_count,
                        'total_duration_sec': summary.total_duration_sec,
                        'requests_per_sec': summary.requests_per_sec
                    },
                    'detailed_results': [
                        {
                            'endpoint': r.endpoint,
                            'success': r.success,
                            'latency_ms': r.latency_ms,
                            'status_code': r.status_code,
                            'error': r.error,
                            'image_size_bytes': r.image_size_bytes
                        }
                        for r in tester.results
                    ]
                }
                
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(result_data, f, indent=2, ensure_ascii=False)
                
                console.print(f"[green]結果をJSONファイルに出力: {output}[/green]")
        
        # 非同期テスト実行
        asyncio.run(run_test())
        
    except KeyboardInterrupt:
        console.print("\n[yellow]テストが中断されました[/yellow]")
    except Exception as e:
        console.print(f"[red]エラー: {e}[/red]")
        sys.exit(1)

if __name__ == '__main__':
    main()