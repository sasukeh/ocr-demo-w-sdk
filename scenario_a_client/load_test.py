#!/usr/bin/env python3
"""
シナリオA: クライアント側フォールバック機能の負荷テスト

使用例:
python -m scenario_a_client.load_test --images ./samples --rps 5 --duration 120
"""

import asyncio
import os
import sys
import time
import click
import random
from pathlib import Path
from typing import List
import aiofiles
from dotenv import load_dotenv

# Relative import
from client import create_client
from metrics import MetricsCollector
from rich.console import Console
from rich.progress import Progress, TaskID

console = Console()


async def load_image(image_path: Path) -> bytes:
    """画像ファイルを非同期で読み込み"""
    async with aiofiles.open(image_path, 'rb') as f:
        return await f.read()


async def get_test_images(images_dir: str) -> List[Path]:
    """テスト用画像ファイル一覧を取得"""
    images_path = Path(images_dir)
    
    if not images_path.exists():
        console.print(f"[red]画像ディレクトリが見つかりません: {images_dir}[/red]")
        return []
    
    # Supported image formats
    extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    images = []
    
    for ext in extensions:
        images.extend(images_path.glob(f'*{ext}'))
        images.extend(images_path.glob(f'*{ext.upper()}'))
    
    if not images:
        console.print(f"[red]画像ファイルが見つかりません: {images_dir}[/red]")
        console.print(f"対応形式: {', '.join(extensions)}")
    
    return sorted(images)


async def worker(worker_id: int, client, image_queue: asyncio.Queue, metrics: MetricsCollector, 
                total_requests: int, progress: Progress, task_id: TaskID):
    """ワーカータスク: 画像キューからOCRリクエストを処理"""
    
    while True:
        try:
            # Get from queue with timeout
            image_data, image_name = await asyncio.wait_for(image_queue.get(), timeout=1.0)
            
            request_start = time.time()
            
            try:
                # Execute OCR (sync/async selected by environment variable)
                use_sync = os.getenv('USE_SYNC_API', 'false').lower() == 'true'
                result, metadata = await client.ocr_with_fallback(image_data, use_sync=use_sync)
                
                # Record metrics
                final_endpoint = metadata.get('final_endpoint', 'unknown')
                success = result is not None
                
                # Get last attempt information
                last_attempt = metadata['attempts'][-1] if metadata['attempts'] else {}
                status_code = last_attempt.get('status')
                latency_ms = last_attempt.get('latency_ms', 0)
                
                metrics.record_request(
                    endpoint=final_endpoint,
                    success=success,
                    status_code=status_code,
                    latency_ms=latency_ms,
                    fallback_count=metadata.get('fallback_count', 0),
                    attempt_count=metadata.get('total_attempts', 1)
                )
                
                # Log result
                if success:
                    console.print(f"[green]Worker-{worker_id}: {image_name} -> {final_endpoint} ({latency_ms}ms)[/green]")
                else:
                    error_msg = last_attempt.get('error', 'Unknown error')
                    console.print(f"[red]Worker-{worker_id}: {image_name} -> FAILED ({error_msg})[/red]")
                
            except Exception as e:
                # Unexpected error
                metrics.record_request(
                    endpoint='unknown',
                    success=False,
                    status_code=500,
                    latency_ms=0,
                    fallback_count=0,
                    attempt_count=1,
                    error_message=str(e)
                )
                console.print(f"[red]Worker-{worker_id}: {image_name} -> EXCEPTION ({e})[/red]")
            
            # Update progress
            progress.update(task_id, advance=1)
            
            # Queue task completed
            image_queue.task_done()
            
        except asyncio.TimeoutError:
            # Queue empty = all requests processed
            break
        except Exception as e:
            console.print(f"[red]Worker-{worker_id} エラー: {e}[/red]")
            break


async def run_load_test(images_dir: str, target_rps: float, duration_sec: int, 
                       concurrent_workers: int = 10):
    """負荷テストを実行"""
    
    console.print(f"[bold green]シナリオA: クライアント側フォールバック負荷テスト開始[/bold green]")
    console.print(f"画像ディレクトリ: {images_dir}")
    console.print(f"目標RPS: {target_rps}")
    console.print(f"実行時間: {duration_sec}秒")
    console.print(f"並行ワーカー数: {concurrent_workers}")
    
    # Load test images
    image_files = await get_test_images(images_dir)
    if not image_files:
        console.print("[red]テスト用画像が見つかりません[/red]")
        return
    
    console.print(f"[green]テスト画像数: {len(image_files)}[/green]")
    
    # Create client
    client = await create_client()
    metrics = MetricsCollector()
    
    # Calculate total request count
    total_requests = int(target_rps * duration_sec)
    console.print(f"総リクエスト数: {total_requests}")
    
    # Image queue and progress
    image_queue = asyncio.Queue()
    
    with Progress() as progress:
        task_id = progress.add_task("OCR処理中...", total=total_requests)
        
        # Request generation task
        async def request_generator():
            interval = 1.0 / target_rps
            
            for i in range(total_requests):
                # Select image with round-robin
                image_file = image_files[i % len(image_files)]
                
                try:
                    # Load image data
                    image_data = await load_image(image_file)
                    await image_queue.put((image_data, image_file.name))
                    
                    # RPS制御のための待機
                    if i < total_requests - 1:  # 最後のリクエストでは待機しない
                        await asyncio.sleep(interval)
                        
                except Exception as e:
                    console.print(f"[red]画像読み込みエラー: {image_file} - {e}[/red]")
        
        # ワーカータスク群を作成
        workers = [
            worker(i, client, image_queue, metrics, total_requests, progress, task_id)
            for i in range(concurrent_workers)
        ]
        
        # 全タスクを並行実行
        await asyncio.gather(
            request_generator(),
            *workers,
            return_exceptions=True
        )
    
    console.print("[green]負荷テスト完了![/green]")
    
    # 結果出力
    console.print("\n" + "="*60)
    metrics.print_summary()
    
    # 結果保存
    os.makedirs('out', exist_ok=True)
    timestamp = int(time.time())
    
    csv_path = f'out/scenario_a_results_{timestamp}.csv'
    json_path = f'out/scenario_a_summary_{timestamp}.json'
    
    metrics.save_to_csv(csv_path)
    metrics.save_summary_json(json_path)
    
    return metrics.get_summary_stats()


@click.command()
@click.option('--images', required=True, help='テスト画像ディレクトリパス')
@click.option('--rps', default=5.0, help='目標RPS（リクエスト毎秒）')
@click.option('--duration', default=120, help='実行時間（秒）')
@click.option('--workers', default=10, help='並行ワーカー数')
@click.option('--env-file', default='.env', help='環境変数ファイル')
def main(images: str, rps: float, duration: int, workers: int, env_file: str):
    """シナリオA負荷テストのメインエントリーポイント"""
    
    # 環境変数読み込み
    if os.path.exists(env_file):
        load_dotenv(env_file)
        console.print(f"[green]環境変数読み込み: {env_file}[/green]")
    else:
        console.print(f"[yellow]環境変数ファイルが見つかりません: {env_file}[/yellow]")
    
    # 必須環境変数チェック
    required_vars = ['OCR_ENDPOINTS', 'OCR_KEYS']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        console.print(f"[red]必須環境変数が設定されていません: {', '.join(missing_vars)}[/red]")
        sys.exit(1)
    
    try:
        # Execute load test
        results = asyncio.run(run_load_test(images, rps, duration, workers))
        
        # 簡易判定結果
        if results:
            success_rate = results['summary']['success_rate']
            p95_latency = results['latency']['p95_ms']
            
            console.print(f"\n[bold]結果判定:[/bold]")
            
            if success_rate >= 0.95:
                console.print(f"[green]✓ 成功率: {success_rate:.2%} (良好)[/green]")
            else:
                console.print(f"[red]✗ 成功率: {success_rate:.2%} (改善必要)[/red]")
            
            if p95_latency <= 2000:
                console.print(f"[green]✓ P95レイテンシー: {p95_latency:.1f}ms (良好)[/green]")
            else:
                console.print(f"[red]✗ P95レイテンシー: {p95_latency:.1f}ms (改善必要)[/red]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]テストが中断されました[/yellow]")
    except Exception as e:
        console.print(f"[red]テスト実行エラー: {e}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main()