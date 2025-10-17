#!/usr/bin/env python3
"""
日本国内3リージョンでの最適化負荷テスト

このスクリプトは日本国内の3つのリージョン（Japan East, Japan West, Korea Central）
での負荷テストを実行し、レイテンシー最適化の効果を測定します。
"""

import asyncio
import json
import time
import statistics
from pathlib import Path
from typing import Dict, List, Any
import os
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

# プロジェクトのルートディレクトリをパスに追加
import sys
sys.path.append(str(Path(__file__).parent.parent))

from scenario_a_client.client import OCRClient
from scenario_a_client.endpoints import EndpointPool
from scenario_a_client.fallback_policy import FallbackPolicy

console = Console()


class JapanRegionLoadTester:
    """日本リージョン特化の負荷テスタークラス"""
    
    def __init__(self, env_file: str = '.env.japan'):
        """
        日本リージョン負荷テスターを初期化
        
        Args:
            env_file: 環境設定ファイル
        """
        load_dotenv(env_file)
        
        self.concurrent_requests = int(os.getenv('CONCURRENT_REQUESTS', '20'))
        self.test_duration = int(os.getenv('TEST_DURATION_SEC', '120'))
        self.ramp_up_duration = int(os.getenv('RAMP_UP_SEC', '10'))
        
        # OCR クライアントを初期化
        self.pool = EndpointPool.from_env()
        
        # 日本最適化のフォールバックポリシー
        single_ms = int(os.getenv('FALLBACK_SINGLE_MS', '1200'))
        ewma_p95_ms = int(os.getenv('EWMA_P95_MS', '1500'))  
        alpha = float(os.getenv('EWMA_ALPHA', '0.3'))
        
        self.policy = FallbackPolicy(
            pool=self.pool,
            single_ms=single_ms,
            ewma_p95_ms=ewma_p95_ms,
            alpha=alpha
        )
        
        self.client = OCRClient(self.pool, self.policy)
        
        # 結果収集
        self.results = []
        self.region_stats = {}
        
        console.print(f"[green]日本リージョン負荷テスト初期化完了[/green]")
        console.print(f"対象リージョン: {[ep.region for ep in self.pool.endpoints]}")
        console.print(f"同時接続数: {self.concurrent_requests}, 継続時間: {self.test_duration}秒")
    
    async def load_test_image(self) -> bytes:
        """テスト用画像を読み込み"""
        # 複数の画像をランダムに使用
        image_files = [
            'samples/handwritten_text.jpg',
            'samples/printed_text.jpg', 
            'samples/document_text.png'
        ]
        
        for img_path in image_files:
            if Path(img_path).exists():
                with open(img_path, 'rb') as f:
                    return f.read()
        
        # フォールバック: テストパターン生成
        return self._generate_test_pattern()
    
    def _generate_test_pattern(self) -> bytes:
        """簡単なテスト画像パターンを生成"""
        # 実際の画像がない場合の代替手段
        console.print("[yellow]警告: テスト画像が見つかりません。テストパターンを生成中...[/yellow]")
        
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io
            
            # 簡単なテスト画像を生成
            img = Image.new('RGB', (800, 600), color='white')
            draw = ImageDraw.Draw(img)
            
            # テキストを描画
            text_lines = [
                "日本リージョンテスト",
                f"実行時刻: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                "Japan East / Japan West / Korea Central",
                "レイテンシー最適化テスト実行中...",
                "1234567890 ABCDEFG あいうえお"
            ]
            
            y_offset = 100
            for line in text_lines:
                draw.text((50, y_offset), line, fill='black')
                y_offset += 60
            
            # バイト配列に変換
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85)
            return output.getvalue()
            
        except ImportError:
            console.print("[red]PIL が利用できません。実際の画像ファイルを samples/ に配置してください[/red]")
            raise
    
    async def single_request_test(self, request_id: int, image_data: bytes) -> Dict[str, Any]:
        """単一リクエストのテスト実行"""
        start_time = time.time()
        
        try:
            result, metadata = await self.client.ocr_with_fallback(image_data, use_sync=True)
            
            end_time = time.time()
            total_latency = int((end_time - start_time) * 1000)
            
            return {
                'request_id': request_id,
                'success': result is not None,
                'total_latency_ms': total_latency,
                'attempts': metadata.get('attempts', []),
                'fallback_count': metadata.get('fallback_count', 0),
                'final_endpoint': metadata.get('final_endpoint'),
                'image_processing': metadata.get('image_processing', {}),
                'timestamp': time.time()
            }
            
        except Exception as e:
            end_time = time.time()
            total_latency = int((end_time - start_time) * 1000)
            
            return {
                'request_id': request_id,
                'success': False,
                'total_latency_ms': total_latency,
                'error': str(e),
                'timestamp': time.time()
            }
    
    async def run_load_test(self):
        """負荷テストのメイン実行"""
        console.print(f"\n[bold blue]🚀 日本リージョン負荷テスト開始[/bold blue]")
        
        # テスト画像を準備
        image_data = await self.load_test_image()
        console.print(f"[green]テスト画像準備完了: {len(image_data):,} bytes[/green]")
        
        start_time = time.time()
        request_counter = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task(
                "負荷テスト実行中...", 
                total=self.test_duration
            )
            
            # 同時実行タスクプール
            active_tasks = set()
            
            while time.time() - start_time < self.test_duration:
                current_time = time.time() - start_time
                progress.update(task, completed=current_time)
                
                # ランプアップ期間中は徐々に負荷を上げる
                if current_time < self.ramp_up_duration:
                    max_concurrent = max(1, int(self.concurrent_requests * current_time / self.ramp_up_duration))
                else:
                    max_concurrent = self.concurrent_requests
                
                # 必要に応じて新しいタスクを開始
                while len(active_tasks) < max_concurrent and time.time() - start_time < self.test_duration:
                    request_counter += 1
                    task_coro = self.single_request_test(request_counter, image_data)
                    active_tasks.add(asyncio.create_task(task_coro))
                
                # 完了したタスクを処理
                if active_tasks:
                    done_tasks, active_tasks = await asyncio.wait(
                        active_tasks, 
                        timeout=0.1, 
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    for task_done in done_tasks:
                        try:
                            result = await task_done
                            self.results.append(result)
                        except Exception as e:
                            console.print(f"[red]タスクエラー: {e}[/red]")
            
            # 残りのタスクを完了まで待機
            if active_tasks:
                console.print(f"[yellow]残り{len(active_tasks)}タスクの完了を待機中...[/yellow]")
                remaining_results = await asyncio.gather(*active_tasks, return_exceptions=True)
                
                for result in remaining_results:
                    if isinstance(result, Exception):
                        console.print(f"[red]最終タスクエラー: {result}[/red]")
                    else:
                        self.results.append(result)
        
        console.print(f"[green]✅ 負荷テスト完了: {len(self.results)} リクエスト処理[/green]")
    
    def analyze_results(self):
        """結果を分析して表示"""
        if not self.results:
            console.print("[red]分析する結果がありません[/red]")
            return
        
        # 基本統計
        successful_results = [r for r in self.results if r['success']]
        failed_results = [r for r in self.results if not r['success']]
        
        success_rate = len(successful_results) / len(self.results) * 100
        
        # レイテンシー統計
        latencies = [r['total_latency_ms'] for r in successful_results]
        if latencies:
            avg_latency = statistics.mean(latencies)
            p50_latency = statistics.median(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
            p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
        else:
            avg_latency = p50_latency = p95_latency = p99_latency = 0
        
        # リージョン別統計
        region_stats = {}
        for result in successful_results:
            if 'final_endpoint' in result and result['final_endpoint']:
                region = result['final_endpoint']
                if region not in region_stats:
                    region_stats[region] = {'count': 0, 'latencies': []}
                
                region_stats[region]['count'] += 1
                region_stats[region]['latencies'].append(result['total_latency_ms'])
        
        # フォールバック統計
        fallback_counts = [r.get('fallback_count', 0) for r in self.results]
        avg_fallbacks = statistics.mean(fallback_counts) if fallback_counts else 0
        
        # 結果表示
        self._display_summary_table(success_rate, avg_latency, p50_latency, p95_latency, p99_latency, avg_fallbacks)
        self._display_region_table(region_stats)
        self._display_failure_analysis(failed_results)
    
    def _display_summary_table(self, success_rate: float, avg_latency: float, p50: float, p95: float, p99: float, avg_fallbacks: float):
        """サマリーテーブルの表示"""
        table = Table(title="🇯🇵 日本リージョン負荷テスト結果サマリー")
        
        table.add_column("メトリクス", style="cyan", no_wrap=True)
        table.add_column("値", style="magenta")
        table.add_column("評価", style="green")
        
        # 成功率の評価
        success_evaluation = "🟢 優秀" if success_rate >= 95 else "🟡 普通" if success_rate >= 90 else "🔴 要改善"
        
        # P95レイテンシーの評価（日本国内基準）
        p95_evaluation = "🟢 優秀" if p95 <= 1000 else "🟡 普通" if p95 <= 2000 else "🔴 要改善"
        
        table.add_row("総リクエスト数", f"{len(self.results):,}", "")
        table.add_row("成功率", f"{success_rate:.2f}%", success_evaluation)
        table.add_row("平均レイテンシー", f"{avg_latency:.1f}ms", "")
        table.add_row("P50レイテンシー", f"{p50:.1f}ms", "")  
        table.add_row("P95レイテンシー", f"{p95:.1f}ms", p95_evaluation)
        table.add_row("P99レイテンシー", f"{p99:.1f}ms", "")
        table.add_row("平均フォールバック回数", f"{avg_fallbacks:.2f}", "")
        
        console.print(table)
    
    def _display_region_table(self, region_stats: Dict[str, Any]):
        """リージョン別統計テーブルの表示"""
        if not region_stats:
            console.print("[yellow]リージョン別データがありません[/yellow]")
            return
            
        table = Table(title="📊 リージョン別パフォーマンス")
        
        table.add_column("リージョン", style="cyan", no_wrap=True)
        table.add_column("リクエスト数", justify="right", style="magenta")
        table.add_column("利用率", justify="right", style="blue")
        table.add_column("平均レイテンシー", justify="right", style="green")
        table.add_column("P95レイテンシー", justify="right", style="yellow")
        
        total_requests = sum(stats['count'] for stats in region_stats.values())
        
        # 各リージョンの統計を計算
        for region, stats in sorted(region_stats.items()):
            count = stats['count']
            latencies = stats['latencies']
            usage_rate = (count / total_requests * 100) if total_requests > 0 else 0
            avg_lat = statistics.mean(latencies) if latencies else 0
            p95_lat = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else (max(latencies) if latencies else 0)
            
            # リージョン名を日本語に変換
            region_display = {
                'japaneast': '🗾 Japan East (東京)',
                'japanwest': '🏯 Japan West (大阪)', 
                'koreacentral': '🇰🇷 Korea Central (ソウル)'
            }.get(region, region)
            
            table.add_row(
                region_display,
                f"{count:,}",
                f"{usage_rate:.1f}%",
                f"{avg_lat:.1f}ms",
                f"{p95_lat:.1f}ms"
            )
        
        console.print(table)
    
    def _display_failure_analysis(self, failed_results: List[Dict[str, Any]]):
        """失敗分析の表示"""
        if not failed_results:
            console.print("[green]✅ 失敗したリクエストはありません[/green]")
            return
        
        console.print(f"\n[red]⚠️  失敗したリクエスト: {len(failed_results)}件[/red]")
        
        # エラータイプ別集計
        error_types = {}
        for result in failed_results:
            error_msg = result.get('error', 'Unknown error')
            error_types[error_msg] = error_types.get(error_msg, 0) + 1
        
        table = Table(title="失敗原因分析")
        table.add_column("エラータイプ", style="red")
        table.add_column("発生回数", justify="right", style="magenta")
        
        for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            table.add_row(error, f"{count}")
        
        console.print(table)
    
    def save_detailed_results(self, filename: str = None):
        """詳細結果をJSONファイルに保存"""
        if filename is None:
            filename = f"japan_load_test_results_{int(time.time())}.json"
        
        detailed_results = {
            'test_config': {
                'concurrent_requests': self.concurrent_requests,
                'test_duration_sec': self.test_duration,
                'ramp_up_duration_sec': self.ramp_up_duration,
                'target_regions': [ep.region for ep in self.pool.endpoints]
            },
            'results': self.results,
            'summary': self._calculate_summary_stats()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(detailed_results, f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]📄 詳細結果を保存: {filename}[/green]")
    
    def _calculate_summary_stats(self) -> Dict[str, Any]:
        """サマリー統計を計算"""
        if not self.results:
            return {}
        
        successful_results = [r for r in self.results if r['success']]
        latencies = [r['total_latency_ms'] for r in successful_results]
        
        return {
            'total_requests': len(self.results),
            'successful_requests': len(successful_results),
            'success_rate': len(successful_results) / len(self.results) * 100,
            'avg_latency_ms': statistics.mean(latencies) if latencies else 0,
            'p95_latency_ms': statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else 0,
            'total_fallbacks': sum(r.get('fallback_count', 0) for r in self.results)
        }


async def main():
    """メイン実行関数"""
    console.print(Panel.fit(
        "[bold blue]🇯🇵 日本リージョン OCR 負荷テスト[/bold blue]\n"
        "Japan East + Japan West + Korea Central での最適化テスト",
        border_style="blue"
    ))
    
    try:
        # 環境ファイルの確認
        env_file = '.env.japan'
        if not Path(env_file).exists():
            console.print(f"[red]環境ファイルが見つかりません: {env_file}[/red]")
            console.print("[yellow]デフォルトの .env ファイルを使用します[/yellow]")
            env_file = '.env'
        
        # テスター初期化と実行
        tester = JapanRegionLoadTester(env_file)
        
        await tester.run_load_test()
        tester.analyze_results()
        tester.save_detailed_results()
        
        console.print("\n[bold green]🎉 日本リージョン負荷テスト完了！[/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⏸️  テストが中断されました[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ テストエラー: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")


if __name__ == '__main__':
    asyncio.run(main())