"""
Scenario B: APIM 負荷テストツール
Scenario A と同様の負荷テストを APIM 経由で実行
"""
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from apim_client import APIMOCRClient, APIMConfig, APIMMetrics


@dataclass
class LoadTestConfig:
    """負荷テスト設定"""
    concurrent_requests: int = 10
    total_requests: int = 100
    request_interval: float = 0.1
    test_duration: Optional[int] = None  # 秒数（Noneの場合は total_requests で制御）
    ramp_up_time: int = 5  # 秒数
    

class APIMLoadTester:
    """APIM 負荷テストクラス"""
    
    def __init__(self, config: APIMConfig, console: Console):
        self.config = config
        self.console = console
        self.results: List[APIMMetrics] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        
    async def run_load_test(
        self, 
        test_config: LoadTestConfig, 
        test_images: List[Path]
    ) -> Dict[str, Any]:
        """負荷テスト実行"""
        self.console.print(f"🔄 APIM 負荷テスト開始", style="bold green")
        self.console.print(f"📊 設定: 同時接続数={test_config.concurrent_requests}, 総リクエスト数={test_config.total_requests}")
        
        self.start_time = time.time()
        
        async with APIMOCRClient(self.config, self.console) as client:
            # セマフォで同時接続数を制御
            semaphore = asyncio.Semaphore(test_config.concurrent_requests)
            
            # 進行状況表示
            with Progress() as progress:
                main_task = progress.add_task(
                    "[green]負荷テスト実行中...", 
                    total=test_config.total_requests
                )
                
                # タスクリスト作成
                tasks = []
                for i in range(test_config.total_requests):
                    # テスト画像をローテーション
                    image_path = test_images[i % len(test_images)]
                    request_id = f"load-test-{i+1:04d}"
                    
                    task = asyncio.create_task(
                        self._execute_single_request(
                            semaphore, 
                            client, 
                            image_path, 
                            request_id,
                            progress,
                            main_task
                        )
                    )
                    tasks.append(task)
                    
                    # リクエスト間隔
                    if test_config.request_interval > 0:
                        await asyncio.sleep(test_config.request_interval)
                
                # 全タスク完了を待機
                await asyncio.gather(*tasks, return_exceptions=True)
        
        self.end_time = time.time()
        self.results = client.metrics
        
        # 結果分析
        return self._analyze_results(test_config)
    
    async def _execute_single_request(
        self,
        semaphore: asyncio.Semaphore,
        client: APIMOCRClient,
        image_path: Path,
        request_id: str,
        progress: Progress,
        task_id: TaskID
    ):
        """単一リクエスト実行"""
        async with semaphore:
            try:
                await client.process_image(str(image_path), request_id)
            except Exception as e:
                # エラーは client 内で記録される
                pass
            finally:
                progress.advance(task_id)
    
    def _analyze_results(self, test_config: LoadTestConfig) -> Dict[str, Any]:
        """結果分析"""
        if not self.results:
            return {"error": "No results to analyze"}
        
        successful_requests = [r for r in self.results if r.success]
        failed_requests = [r for r in self.results if not r.success]
        
        total_duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        # レスポンス時間統計
        response_times = [r.total_duration for r in successful_requests]
        
        # Backend usage
        backend_usage = {}
        for result in successful_requests:
            backend = result.served_by_backend or "unknown"
            backend_usage[backend] = backend_usage.get(backend, 0) + 1
        
        # スループット計算
        requests_per_second = len(successful_requests) / total_duration if total_duration > 0 else 0
        
        # パーセンタイル計算
        if response_times:
            response_times.sort()
            p50 = response_times[int(len(response_times) * 0.5)]
            p95 = response_times[int(len(response_times) * 0.95)]
            p99 = response_times[int(len(response_times) * 0.99)]
        else:
            p50 = p95 = p99 = 0
        
        # エラー分析
        error_types = {}
        for result in failed_requests:
            error = result.error or "Unknown error"
            error_types[error] = error_types.get(error, 0) + 1
        
        # フェイルオーバー効果
        total_attempts = sum(r.total_attempts for r in self.results)
        avg_attempts = total_attempts / len(self.results) if self.results else 0
        
        return {
            # 基本統計
            "total_requests": len(self.results),
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "success_rate": len(successful_requests) / len(self.results) if self.results else 0,
            
            # パフォーマンス
            "total_duration": total_duration,
            "requests_per_second": requests_per_second,
            "avg_response_time": sum(response_times) / len(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            
            # パーセンタイル
            "p50_response_time": p50,
            "p95_response_time": p95,
            "p99_response_time": p99,
            
            # 信頼性
            "backend_usage": backend_usage,
            "avg_attempts_per_request": avg_attempts,
            "error_types": error_types,
            
            # 設定情報
            "test_config": {
                "concurrent_requests": test_config.concurrent_requests,
                "total_requests": test_config.total_requests,
                "request_interval": test_config.request_interval
            }
        }
    
    def display_results(self, analysis: Dict[str, Any]):
        """結果表示"""
        self.console.print("\n" + "="*60, style="bold")
        self.console.print("📊 APIM 負荷テスト結果", style="bold cyan")
        self.console.print("="*60, style="bold")
        
        # サマリーテーブル
        summary_table = Table(show_header=True, header_style="bold magenta")
        summary_table.add_column("メトリクス", style="cyan")
        summary_table.add_column("値", style="green")
        
        # 基本統計
        summary_table.add_row("総リクエスト数", str(analysis["total_requests"]))
        summary_table.add_row("成功", f"{analysis['successful_requests']} ({analysis['success_rate']:.1%})")
        summary_table.add_row("失敗", str(analysis["failed_requests"]))
        summary_table.add_row("実行時間", f"{analysis['total_duration']:.2f}秒")
        summary_table.add_row("スループット", f"{analysis['requests_per_second']:.2f} req/s")
        
        # レスポンス時間
        summary_table.add_row("平均レスポンス時間", f"{analysis['avg_response_time']:.3f}秒")
        summary_table.add_row("最小レスポンス時間", f"{analysis['min_response_time']:.3f}秒")
        summary_table.add_row("最大レスポンス時間", f"{analysis['max_response_time']:.3f}秒")
        summary_table.add_row("P50 (中央値)", f"{analysis['p50_response_time']:.3f}秒")
        summary_table.add_row("P95", f"{analysis['p95_response_time']:.3f}秒")
        summary_table.add_row("P99", f"{analysis['p99_response_time']:.3f}秒")
        
        # 信頼性
        summary_table.add_row("平均試行回数", f"{analysis['avg_attempts_per_request']:.2f}")
        
        self.console.print(summary_table)
        
        # バックエンド分散
        if analysis["backend_usage"]:
            self.console.print("\n🏠 バックエンド使用状況:", style="bold yellow")
            total_successful = analysis["successful_requests"]
            for backend, count in analysis["backend_usage"].items():
                percentage = (count / total_successful) * 100 if total_successful > 0 else 0
                self.console.print(f"  {backend}: {count}回 ({percentage:.1f}%)")
        
        # エラー分析
        if analysis["error_types"]:
            self.console.print("\n❌ エラー分析:", style="bold red")
            for error, count in analysis["error_types"].items():
                self.console.print(f"  {error}: {count}回")
    
    def save_results(self, analysis: Dict[str, Any], filename: str) -> bool:
        """結果保存"""
        try:
            data = {
                "scenario": "B",
                "type": "APIM_Load_Test",
                "timestamp": datetime.now().isoformat(),
                "analysis": analysis,
                "raw_metrics": [r.to_dict() for r in self.results]
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            self.console.print(f"❌ 結果保存エラー: {e}", style="red")
            return False


async def run_apim_load_test():
    """APIM 負荷テスト実行関数"""
    console = Console()
    
    # 設定読み込み
    try:
        config = APIMConfig.from_env()
        if not config.gateway_url or not config.subscription_key:
            console.print("❌ APIM設定が不完全です。.env.apim ファイルを確認してください。", style="red")
            return
    except Exception as e:
        console.print(f"❌ 設定読み込みエラー: {e}", style="red")
        return
    
    # テスト画像準備
    test_images = list(Path("test_images").glob("*.jpg")) + list(Path("test_images").glob("*.png"))
    if not test_images:
        console.print("❌ test_images フォルダにテスト画像がありません。", style="red")
        return
    
    console.print(f"🎯 テスト画像数: {len(test_images)}")
    
    # 負荷テスト設定
    test_config = LoadTestConfig(
        concurrent_requests=5,  # 同時リクエスト数
        total_requests=50,      # 総リクエスト数
        request_interval=0.2,   # リクエスト間隔（秒）
    )
    
    console.print(f"⚙️ テスト設定: 同時接続={test_config.concurrent_requests}, "
                  f"総リクエスト={test_config.total_requests}, "
                  f"間隔={test_config.request_interval}s")
    
    # Execute load test
    tester = APIMLoadTester(config, console)
    
    console.print("\n🚀 APIM 負荷テスト開始...", style="bold green")
    
    try:
        analysis = await tester.run_load_test(test_config, test_images)
        
        # Display results
        tester.display_results(analysis)
        
        # 結果保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"apim_load_test_{timestamp}.json"
        
        if tester.save_results(analysis, filename):
            console.print(f"\n💾 結果を {filename} に保存しました", style="green")
        
        console.print("\n🎉 APIM 負荷テスト完了！", style="bold green")
        
    except Exception as e:
        console.print(f"❌ 負荷テストでエラーが発生しました: {e}", style="red")
        return


def main():
    """メイン関数"""
    asyncio.run(run_apim_load_test())


if __name__ == "__main__":
    main()