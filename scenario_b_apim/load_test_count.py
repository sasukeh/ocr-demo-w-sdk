#!/usr/bin/env python3
"""
Scenario B: APIM 経由 OCR 負荷テスト（リクエスト数指定版）

使用例:
python scenario_b_apim/load_test_count.py --total-requests 1000 --workers 20
"""

import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
import json

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, MofNCompleteColumn
from rich.table import Table
from rich.panel import Panel

console = Console()


@dataclass
class RequestResult:
    """個別リクエストの結果"""
    success: bool
    duration: float
    backend: str
    error: str = None


async def run_load_test_by_count(
    total_requests: int,
    max_workers: int = 20,
    test_images_dir: str = "test_images"
) -> Dict[str, Any]:
    """指定されたリクエスト数で負荷テストを実行"""
    
    console.print(Panel.fit(
        f"[bold cyan]Scenario B 負荷テスト開始[/bold cyan]\n"
        f"総リクエスト数: {total_requests}\n"
        f"最大並行数: {max_workers}\n"
        f"テスト画像: {test_images_dir}",
        border_style="cyan"
    ))
    
    # Get test images
    images_path = Path(test_images_dir)
    test_images = list(images_path.glob("*.jpg")) + list(images_path.glob("*.png"))
    
    if not test_images:
        console.print(f"[red]エラー: {test_images_dir} にテスト画像がありません[/red]")
        return None
    
    console.print(f"[green]テスト画像数: {len(test_images)}[/green]")
    
    # Import APIM client
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    try:
        from scenario_b_apim.apim_client import APIMOCRClient, APIMConfig
    except ImportError:
        console.print("[red]エラー: apim_client モジュールが見つかりません[/red]")
        return None
    
    # Load configuration (using .env.apim from parent directory)
    import os
    env_file = Path(__file__).parent.parent / ".env.apim"
    if env_file.exists():
        config = APIMConfig.from_env(str(env_file))
    else:
        config = APIMConfig.from_env()
    
    if not config.gateway_url or not config.subscription_key:
        console.print(f"[red]エラー: APIM設定が不完全です（{env_file} を確認）[/red]")
        console.print(f"  Gateway URL: {config.gateway_url}")
        console.print(f"  Subscription Key: {'設定済み' if config.subscription_key else '未設定'}")
        return None
    
    client = APIMOCRClient(config, console)
    
    # Store results
    results: List[RequestResult] = []
    start_time = time.time()
    
    # Control concurrency with semaphore
    semaphore = asyncio.Semaphore(max_workers)
    
    # Start client session
    async with client:
        
        async def process_request(request_id: int) -> RequestResult:
            """1つのリクエストを処理"""
            async with semaphore:
                # Select image randomly
                import random
                image_path = random.choice(test_images)
                
                req_start = time.time()
                try:
                    metrics = await client.process_image(
                        str(image_path),
                        f"load-test-{request_id}"
                    )
                    
                    return RequestResult(
                        success=metrics.success,
                        duration=time.time() - req_start,
                        backend=metrics.served_by_backend or "unknown",
                        error=metrics.error
                    )
                except Exception as e:
                    return RequestResult(
                        success=False,
                        duration=time.time() - req_start,
                        backend="error",
                        error=str(e)
                    )
        
        # Execute with progress bar
        with Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                "[cyan]リクエスト実行中...",
                total=total_requests
            )
            
            # Execute all requests concurrently
            tasks = [process_request(i) for i in range(total_requests)]
            
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                progress.update(task, advance=1)
    
    total_duration = time.time() - start_time
    
    # Calculate statistics
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    # Aggregate errors
    error_counts = {}
    for r in failed:
        error_msg = r.error or "Unknown error"
        error_counts[error_msg] = error_counts.get(error_msg, 0) + 1
    
    stats = {
        "total_requests": total_requests,
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / total_requests * 100,
        "total_duration": total_duration,
        "avg_latency": sum(r.duration for r in successful) / len(successful) if successful else 0,
        "min_latency": min(r.duration for r in successful) if successful else 0,
        "max_latency": max(r.duration for r in successful) if successful else 0,
        "requests_per_second": total_requests / total_duration,
        "error_summary": error_counts
    }
    
    # Backend usage
    backend_counts = {}
    for r in successful:
        backend_counts[r.backend] = backend_counts.get(r.backend, 0) + 1
    
    stats["backend_usage"] = backend_counts
    
    # Display results
    display_results(stats, backend_counts, error_counts)
    
    # Save results to file
    output_file = f"scenario_b_load_test_{int(time.time())}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    console.print(f"\n[green]結果を保存しました: {output_file}[/green]")
    
    return stats


def display_results(stats: Dict[str, Any], backend_counts: Dict[str, int], error_counts: Dict[str, int]):
    """結果を表形式で表示"""
    
    console.print("\n" + "="*60)
    console.print("[bold cyan]📊 Scenario B 負荷テスト結果[/bold cyan]")
    console.print("="*60)
    
    # Main statistics
    table = Table(title="総合統計", show_header=True, header_style="bold magenta")
    table.add_column("メトリクス", style="cyan")
    table.add_column("値", justify="right", style="green")
    
    table.add_row("総リクエスト数", f"{stats['total_requests']:,}")
    table.add_row("成功", f"{stats['successful']:,} ({stats['success_rate']:.1f}%)")
    table.add_row("失敗", f"{stats['failed']:,}")
    table.add_row("実行時間", f"{stats['total_duration']:.2f}秒")
    table.add_row("スループット", f"{stats['requests_per_second']:.2f} req/s")
    table.add_row("平均レイテンシー", f"{stats['avg_latency']*1000:.0f}ms")
    table.add_row("最小レイテンシー", f"{stats['min_latency']*1000:.0f}ms")
    table.add_row("最大レイテンシー", f"{stats['max_latency']*1000:.0f}ms")
    
    console.print(table)
    
    # Error summary
    if error_counts:
        console.print("\n[bold red]❌ エラーサマリー[/bold red]")
        error_table = Table(show_header=True, header_style="bold red")
        error_table.add_column("エラー", style="yellow")
        error_table.add_column("回数", justify="right", style="red")
        error_table.add_column("割合", justify="right", style="red")
        
        total_errors = sum(error_counts.values())
        for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total_errors * 100
            # Shorten error message
            short_error = error[:80] + "..." if len(error) > 80 else error
            error_table.add_row(short_error, f"{count:,}", f"{percentage:.1f}%")
        
        console.print(error_table)
    
    console.print(table)
    
    # Backend usage
    if backend_counts:
        console.print("\n[bold cyan]🏠 バックエンド使用状況:[/bold cyan]")
        for backend, count in sorted(backend_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = count / stats['successful'] * 100
            console.print(f"  • {backend}: {count:,}回 ({percentage:.1f}%)")


def main():
    """メインエントリーポイント"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Scenario B APIM 経由 OCR 負荷テスト（リクエスト数指定版）"
    )
    parser.add_argument(
        "--total-requests",
        type=int,
        default=1000,
        help="総リクエスト数（デフォルト: 1000）"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=20,
        help="最大並行ワーカー数（デフォルト: 20）"
    )
    parser.add_argument(
        "--test-images",
        default="test_images",
        help="テスト画像ディレクトリ（デフォルト: test_images）"
    )
    
    args = parser.parse_args()
    
    # Execute load test
    try:
        asyncio.run(run_load_test_by_count(
            total_requests=args.total_requests,
            max_workers=args.workers,
            test_images_dir=args.test_images
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]テストが中断されました[/yellow]")
    except Exception as e:
        console.print(f"\n[red]エラーが発生しました: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
