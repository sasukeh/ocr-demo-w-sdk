"""
Scenario B: API Management を使った OCR 処理
APIM レベルでのサーキットブレイカーとロードバランシング
"""
import asyncio
import time
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
from collections import defaultdict
import json
import os

import httpx
from PIL import Image
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TaskID
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.tree import Tree


@dataclass
class APIMConfig:
    """API Management 設定"""
    gateway_url: str
    subscription_key: str
    ocr_endpoint: str
    ocr_result_endpoint: str
    timeout: int = 30
    
    @classmethod
    def from_env(cls, env_file: str = "../.env.apim") -> "APIMConfig":
        """環境設定ファイルから設定を読み込み"""
        config = {}
        env_path = Path(env_file)
        
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        
        # 環境変数からも読み込み（優先）
        config.update({
            key: os.getenv(key, config.get(key, ''))
            for key in [
                'APIM_GATEWAY_URL', 'APIM_SUBSCRIPTION_KEY', 
                'APIM_OCR_ENDPOINT', 'APIM_OCR_RESULT_ENDPOINT'
            ]
        })
        
        return cls(
            gateway_url=config.get('APIM_GATEWAY_URL', ''),
            subscription_key=config.get('APIM_SUBSCRIPTION_KEY', ''),
            ocr_endpoint=config.get('APIM_OCR_ENDPOINT', ''),
            ocr_result_endpoint=config.get('APIM_OCR_RESULT_ENDPOINT', '')
        )


@dataclass
class APIMMetrics:
    """APIM リクエストメトリクス"""
    request_id: str
    start_time: float
    end_time: Optional[float] = None
    total_duration: float = 0.0
    ocr_duration: float = 0.0
    result_duration: float = 0.0
    backend_used: Optional[str] = None
    total_attempts: int = 0
    success: bool = False
    error: Optional[str] = None
    response_code: Optional[int] = None
    
    # APIM 特有のメトリクス
    served_by_backend: Optional[str] = None
    request_attempts: int = 0
    final_backend: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class APIMOCRClient:
    """API Management 経由の OCR クライアント"""
    
    def __init__(self, config: APIMConfig, console: Console):
        self.config = config
        self.console = console
        self.metrics: List[APIMMetrics] = []
        self.session: Optional[httpx.AsyncClient] = None
        
    async def __aenter__(self):
        """非同期コンテキストマネージャー開始"""
        self.session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout),
            http2=True,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャー終了"""
        if self.session:
            await self.session.aclose()
    
    def _prepare_image(self, image_path: str, max_size: int = 4 * 1024 * 1024) -> bytes:
        """画像を準備（リサイズ・圧縮）"""
        with Image.open(image_path) as img:
            # PNG を JPEG に変換
            if img.mode in ('RGBA', 'P', 'LA'):
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode in ('RGBA', 'LA'):
                    rgb_img.paste(img, mask=img.split()[-1])
                img = rgb_img
            
            # ファイルサイズチェック用
            import io
            temp_buffer = io.BytesIO()
            quality = 95
            
            while True:
                temp_buffer.seek(0)
                temp_buffer.truncate()
                img.save(temp_buffer, format='JPEG', quality=quality, optimize=True)
                
                if temp_buffer.tell() <= max_size or quality <= 10:
                    break
                quality -= 5
            
            return temp_buffer.getvalue()
    
    async def _make_apim_request(
        self, 
        method: str, 
        url: str, 
        **kwargs
    ) -> Tuple[httpx.Response, Dict[str, str]]:
        """APIM経由でリクエストを実行し、メタデータを取得"""
        headers = kwargs.get('headers', {})
        headers.update({
            'Ocp-Apim-Subscription-Key': self.config.subscription_key,
            'User-Agent': 'OCR-Demo-Scenario-B/1.0'
        })
        kwargs['headers'] = headers
        
        response = await self.session.request(method, url, **kwargs)
        
        # APIM メタデータヘッダーを抽出
        apim_metadata = {
            'served_by_backend': response.headers.get('X-Served-By-Backend'),
            'request_attempts': response.headers.get('X-Request-Attempts'),
            'final_backend': response.headers.get('X-APIM-Final-Backend'),
            'total_attempts': response.headers.get('X-APIM-Total-Attempts'),
            'result_served_by_backend': response.headers.get('X-Result-Served-By-Backend'),
            'result_request_attempts': response.headers.get('X-Result-Request-Attempts')
        }
        
        return response, apim_metadata
    
    async def process_image(
        self, 
        image_path: str, 
        request_id: str,
        language: str = "ja",
        max_retries: int = 3
    ) -> APIMMetrics:
        """画像を処理してテキストを抽出（リトライ機能付き）"""
        metrics = APIMMetrics(
            request_id=request_id,
            start_time=time.time()
        )
        
        retry_count = 0
        last_error = None
        
        while retry_count <= max_retries:
            try:
                # 画像準備
                image_data = self._prepare_image(image_path)
                
                # OCR リクエスト開始
                ocr_start = time.time()
                
                # Image Analysis v4 用のバイナリ送信
                response, apim_metadata = await self._make_apim_request(
                    'POST',
                    self.config.ocr_endpoint,
                    headers={'Content-Type': 'application/octet-stream'},
                    content=image_data
                )
                
                ocr_end = time.time()
                metrics.ocr_duration = ocr_end - ocr_start
                
                # 429エラー（レート制限）の場合はリトライ
                if response.status_code == 429:
                    retry_count += 1
                    if retry_count <= max_retries:
                        # エクスポネンシャルバックオフ
                        wait_time = min(2 ** retry_count, 10)
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"OCR request failed after {max_retries} retries: {response.status_code} - {response.text}")
                
                # Image Analysis v4 は同期 API で 200 を返す
                if response.status_code != 200:
                    raise Exception(f"OCR request failed: {response.status_code} - {response.text}")
                
                # メタデータ更新
                metrics.served_by_backend = apim_metadata.get('served_by_backend')
                metrics.request_attempts = int(apim_metadata.get('request_attempts') or 1) + retry_count
                metrics.final_backend = apim_metadata.get('final_backend')
                metrics.total_attempts = int(apim_metadata.get('total_attempts') or 1) + retry_count
                
                # Image Analysis v4 はすぐに結果を返すため、ポーリング不要
                result_data = response.json()
                
                # v4 の結果構造を確認してテキストを抽出
                if result_data.get('readResult'):
                    metrics.success = True
                    metrics.response_code = 200
                    break
                else:
                    raise Exception("No readResult in v4 response")
                    
            except Exception as e:
                last_error = e
                retry_count += 1
                if retry_count <= max_retries:
                    # エクスポネンシャルバックオフ
                    wait_time = min(2 ** retry_count, 10)
                    await asyncio.sleep(wait_time)
                else:
                    metrics.error = str(last_error)
                    metrics.success = False
                    metrics.response_code = getattr(last_error, 'status_code', 500)
                    break
        
        # 最終処理
        metrics.end_time = time.time()
        metrics.total_duration = metrics.end_time - metrics.start_time
        self.metrics.append(metrics)
        
        return metrics
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """統計サマリーを取得"""
        if not self.metrics:
            return {}
        
        successful_requests = [m for m in self.metrics if m.success]
        failed_requests = [m for m in self.metrics if not m.success]
        
        # バックエンド使用状況
        backend_usage = defaultdict(int)
        for metrics in successful_requests:
            if metrics.served_by_backend:
                backend_usage[metrics.served_by_backend] += 1
        
        # レスポンス時間統計
        response_times = [m.total_duration for m in successful_requests]
        
        stats = {
            'total_requests': len(self.metrics),
            'successful_requests': len(successful_requests),
            'failed_requests': len(failed_requests),
            'success_rate': len(successful_requests) / len(self.metrics) if self.metrics else 0,
            'backend_usage': dict(backend_usage),
            'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
            'min_response_time': min(response_times) if response_times else 0,
            'max_response_time': max(response_times) if response_times else 0,
            'total_attempts': sum(m.total_attempts for m in self.metrics),
            'avg_attempts_per_request': sum(m.total_attempts for m in self.metrics) / len(self.metrics) if self.metrics else 0
        }
        
        return stats


class APIMDisplay:
    """APIM メトリクス表示"""
    
    def __init__(self, console: Console):
        self.console = console
        self.start_time = time.time()
    
    def create_status_panel(self, client: APIMOCRClient) -> Panel:
        """ステータスパネル作成"""
        stats = client.get_summary_stats()
        
        if not stats:
            return Panel("📊 まだリクエストがありません", title="Scenario B: APIM Stats")
        
        # メトリクステーブル
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("項目", style="cyan")
        table.add_column("値", style="green")
        
        table.add_row("総リクエスト数", str(stats['total_requests']))
        table.add_row("成功", f"{stats['successful_requests']} ({stats['success_rate']:.1%})")
        table.add_row("失敗", str(stats['failed_requests']))
        table.add_row("平均レスポンス時間", f"{stats['avg_response_time']:.2f}s")
        table.add_row("最小レスポンス時間", f"{stats['min_response_time']:.2f}s")
        table.add_row("最大レスポンス時間", f"{stats['max_response_time']:.2f}s")
        table.add_row("平均試行回数", f"{stats['avg_attempts_per_request']:.1f}")
        
        # バックエンド使用状況
        backend_info = Text()
        for backend, count in stats['backend_usage'].items():
            percentage = (count / stats['successful_requests']) * 100 if stats['successful_requests'] > 0 else 0
            backend_info.append(f"{backend}: {count} ({percentage:.1f}%)\n")
        
        table.add_row("バックエンド使用状況", backend_info.rstrip())
        
        elapsed = time.time() - self.start_time
        
        return Panel(
            table,
            title=f"📊 Scenario B: APIM Circuit Breaker (実行時間: {elapsed:.1f}s)",
            border_style="blue"
        )
    
    def create_recent_requests_table(self, client: APIMOCRClient, limit: int = 10) -> Table:
        """最近のリクエスト一覧"""
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("時刻", width=8)
        table.add_column("ID", width=10)
        table.add_column("ステータス", width=8)
        table.add_column("時間", width=8)
        table.add_column("バックエンド", width=12)
        table.add_column("試行回数", width=8)
        
        recent_metrics = client.metrics[-limit:] if client.metrics else []
        
        for metrics in recent_metrics:
            timestamp = datetime.fromtimestamp(metrics.start_time).strftime("%H:%M:%S")
            status = "✅ 成功" if metrics.success else "❌ 失敗"
            duration = f"{metrics.total_duration:.2f}s"
            backend = metrics.served_by_backend or "不明"
            attempts = str(metrics.total_attempts)
            
            # ステータスに応じて色を変更
            status_style = "green" if metrics.success else "red"
            
            table.add_row(
                timestamp,
                metrics.request_id[:8],
                Text(status, style=status_style),
                duration,
                backend,
                attempts
            )
        
        return table


async def run_apim_demo():
    """APIM デモの実行"""
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
    
    # テスト画像の確認
    test_images = list(Path("test_images").glob("*.jpg")) + list(Path("test_images").glob("*.png"))
    if not test_images:
        console.print("❌ test_images フォルダにテスト画像がありません。", style="red")
        return
    
    console.print(f"🚀 Scenario B: APIM Circuit Breaker Demo 開始", style="bold green")
    console.print(f"📍 Gateway URL: {config.gateway_url}")
    console.print(f"📋 テスト画像数: {len(test_images)}")
    
    display = APIMDisplay(console)
    
    async with APIMOCRClient(config, console) as client:
        # ライブ表示開始
        layout = Layout()
        layout.split_column(
            Layout(name="status", ratio=2),
            Layout(name="requests", ratio=3)
        )
        
        with Live(layout, refresh_per_second=2, console=console) as live:
            # 並行処理でテスト実行
            tasks = []
            for i, image_path in enumerate(test_images):
                request_id = f"apim-req-{i+1:03d}"
                task = asyncio.create_task(
                    client.process_image(str(image_path), request_id)
                )
                tasks.append(task)
                
                # 表示更新
                layout["status"].update(display.create_status_panel(client))
                layout["requests"].update(
                    Panel(
                        display.create_recent_requests_table(client),
                        title="🔄 最近のリクエスト"
                    )
                )
                
                # 少し待機してから次のリクエスト
                await asyncio.sleep(0.1)
            
            # 全てのタスクの完了を待機
            completed_tasks = 0
            while completed_tasks < len(tasks):
                completed_tasks = sum(1 for task in tasks if task.done())
                
                # 表示更新
                layout["status"].update(display.create_status_panel(client))
                layout["requests"].update(
                    Panel(
                        display.create_recent_requests_table(client),
                        title="🔄 最近のリクエスト"
                    )
                )
                
                await asyncio.sleep(0.5)
        
        # 最終結果表示
        await asyncio.sleep(1)
        stats = client.get_summary_stats()
        
        console.print("\n" + "="*60, style="bold")
        console.print("📊 Scenario B 最終結果 (APIM Circuit Breaker)", style="bold cyan")
        console.print("="*60, style="bold")
        
        # サマリーテーブル
        summary_table = Table(show_header=True, header_style="bold magenta")
        summary_table.add_column("メトリクス", style="cyan")
        summary_table.add_column("値", style="green")
        
        summary_table.add_row("📊 総リクエスト数", str(stats['total_requests']))
        summary_table.add_row("✅ 成功リクエスト", f"{stats['successful_requests']} ({stats['success_rate']:.1%})")
        summary_table.add_row("❌ 失敗リクエスト", str(stats['failed_requests']))
        summary_table.add_row("⏱️  平均レスポンス時間", f"{stats['avg_response_time']:.3f}秒")
        summary_table.add_row("🔄 平均試行回数", f"{stats['avg_attempts_per_request']:.2f}")
        
        console.print(summary_table)
        
        # バックエンド分散状況
        if stats['backend_usage']:
            console.print("\n🏠 バックエンド使用状況:", style="bold yellow")
            for backend, count in stats['backend_usage'].items():
                percentage = (count / stats['successful_requests']) * 100
                console.print(f"  {backend}: {count}回 ({percentage:.1f}%)")
        
        # メトリクス保存
        metrics_file = f"apim_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(metrics_file, 'w', encoding='utf-8') as f:
            json.dump({
                'scenario': 'B',
                'type': 'APIM_Circuit_Breaker',
                'summary': stats,
                'metrics': [m.to_dict() for m in client.metrics]
            }, f, ensure_ascii=False, indent=2)
        
        console.print(f"\n💾 詳細メトリクスを {metrics_file} に保存しました", style="green")
        console.print("🎉 Scenario B デモ完了！", style="bold green")


def main():
    """メイン関数"""
    asyncio.run(run_apim_demo())


if __name__ == "__main__":
    main()