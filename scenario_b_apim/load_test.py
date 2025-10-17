#!/usr/bin/env python3
"""
シナリオB: APIM経由でのOCR負荷テスト

使用例:
python -m scenario_b_apim.load_test --images ./samples --rps 5 --duration 120
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

# 相対インポート
from .client_via_apim import create_apim_client
from .metrics import APIMMetricsCollector
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
    
    # 対応画像形式
    extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
    images = []
    
    for ext in extensions:
        images.extend(images_path.glob(f'*{ext}'))
        images.extend(images_path.glob(f'*{ext.upper()}'))
    
    if not images:
        console.print(f"[red]画像ファイルが見つかりません: {images_dir}[/red]")
        console.print(f"対応形式: {', '.join(extensions)}")
    
    return sorted(images)


async def worker(worker_id: int, client, image_queue: asyncio.Queue, metrics: APIMMetricsCollector, 
                total_requests: int, progress: Progress, task_id: TaskID):
    """ワーカータスク: 画像キューからAPIM経由OCRリクエストを処理"""
    
    while True:
        try:
            # タイムアウト付きでキューから取得
            image_data, image_name = await asyncio.wait_for(image_queue.get(), timeout=1.0)
            
            try:
                # APIM経由でOCR実行
                result, metadata = await client.ocr_via_apim(image_data)
                
                # メトリクス記録
                success = metadata.get('success', False)
                selected_endpoint = metadata.get('selected_endpoint', 'unknown')
                status_code = metadata.get('status_code')
                client_latency_ms = metadata.get('client_latency_ms', 0)
                apim_latency_ms = metadata.get('apim_latency_ms')
                circuit_state = metadata.get('circuit_state')
                retry_after = metadata.get('retry_after')
                error_info = metadata.get('error_info')
                
                metrics.record_request(
                    apim_gateway=metadata.get('apim_gateway', 'unknown'),
                    selected_endpoint=selected_endpoint,
                    success=success,
                    status_code=status_code,
                    client_latency_ms=client_latency_ms,
                    apim_latency_ms=apim_latency_ms,
                    circuit_state=circuit_state,
                    retry_after=retry_after,
                    error_message=error_info
                )
                
                # 結果ログ
                if success:
                    circuit_info = f" [{circuit_state}]" if circuit_state else ""
                    console.print(f"[green]Worker-{worker_id}: {image_name} -> {selected_endpoint}{circuit_info} ({client_latency_ms}ms)[/green]")
                else:
                    error_msg = error_info or f'HTTP {status_code}'
                    console.print(f"[red]Worker-{worker_id}: {image_name} -> FAILED ({error_msg})[/red]")
                
            except Exception as e:
                # 予期しないエラー
                metrics.record_request(
                    apim_gateway='unknown',
                    selected_endpoint='unknown',
                    success=False,
                    status_code=500,
                    client_latency_ms=0,
                    apim_latency_ms=None,
                    circuit_state=None,
                    error_message=str(e)
                )
                console.print(f"[red]Worker-{worker_id}: {image_name} -> EXCEPTION ({e})[/red]")
            
            # プログレス更新
            progress.update(task_id, advance=1)
            
            # キュータスク完了
            image_queue.task_done()
            
        except asyncio.TimeoutError:
            # キューが空 = 全てのリクエスト処理完了
            break
        except Exception as e:
            console.print(f"[red]Worker-{worker_id} エラー: {e}[/red]")
            break


async def run_load_test(images_dir: str, target_rps: float, duration_sec: int, 
                       concurrent_workers: int = 10):
    """負荷テストを実行"""
    
    console.print(f"[bold blue]シナリオB: APIM経由OCR負荷テスト開始[/bold blue]")
    console.print(f"画像ディレクトリ: {images_dir}")
    console.print(f"目標RPS: {target_rps}")
    console.print(f"実行時間: {duration_sec}秒")
    console.print(f"並行ワーカー数: {concurrent_workers}")
    
    # テスト画像読み込み
    image_files = await get_test_images(images_dir)
    if not image_files:
        console.print("[red]テスト用画像が見つかりません[/red]")
        return
    
    console.print(f"[green]テスト画像数: {len(image_files)}[/green]")
    
    # APIMクライアント作成
    client = await create_apim_client()
    metrics = APIMMetricsCollector()
    
    # 総リクエスト数計算
    total_requests = int(target_rps * duration_sec)
    console.print(f"総リクエスト数: {total_requests}")
    
    # 画像キューとプログレス
    image_queue = asyncio.Queue()
    
    with Progress() as progress:
        task_id = progress.add_task("APIM OCR処理中...", total=total_requests)
        
        # リクエスト生成タスク
        async def request_generator():
            interval = 1.0 / target_rps
            
            for i in range(total_requests):
                # ラウンドロビンで画像選択
                image_file = image_files[i % len(image_files)]
                
                try:
                    # 画像データ読み込み
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
    
    csv_path = f'out/scenario_b_results_{timestamp}.csv'
    json_path = f'out/scenario_b_summary_{timestamp}.json'
    
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
    """シナリオB負荷テストのメインエントリーポイント"""
    
    # 環境変数読み込み
    if os.path.exists(env_file):
        load_dotenv(env_file)
        console.print(f"[green]環境変数読み込み: {env_file}[/green]")
    else:
        console.print(f"[yellow]環境変数ファイルが見つかりません: {env_file}[/yellow]")
    
    # 必須環境変数チェック
    required_vars = ['APIM_GATEWAY', 'APIM_SUBSCRIPTION_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        console.print(f"[red]必須環境変数が設定されていません: {', '.join(missing_vars)}[/red]")
        sys.exit(1)
    
    try:
        # 負荷テスト実行
        results = asyncio.run(run_load_test(images, rps, duration, workers))
        
        # 簡易判定結果
        if results:
            success_rate = results['summary']['success_rate']
            client_p95_latency = results['client_latency']['p95_ms']
            
            console.print(f"\n[bold]結果判定:[/bold]")
            
            if success_rate >= 0.95:
                console.print(f"[green]✓ 成功率: {success_rate:.2%} (良好)[/green]")
            else:
                console.print(f"[red]✗ 成功率: {success_rate:.2%} (改善必要)[/red]")
            
            if client_p95_latency <= 2000:
                console.print(f"[green]✓ P95レイテンシー: {client_p95_latency:.1f}ms (良好)[/green]")
            else:
                console.print(f"[red]✗ P95レイテンシー: {client_p95_latency:.1f}ms (改善必要)[/red]")
                
            # サーキットブレーカー効果
            if 'circuit_breaker' in results and results['circuit_breaker']:
                circuit_events = sum(results['circuit_breaker'].values())
                console.print(f"[blue]ℹ サーキットブレーカー動作: {circuit_events}回[/blue]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]テストが中断されました[/yellow]")
    except Exception as e:
        console.print(f"[red]テスト実行エラー: {e}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    main()