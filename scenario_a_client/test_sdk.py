"""
シナリオA (Azure SDK) の簡単なテスト
"""
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"環境変数を読み込みました: {env_path}")

# Add module path
sys.path.insert(0, str(Path(__file__).parent))

from client import create_client
from rich.console import Console

console = Console()


async def test_scenario_a():
    """シナリオAの基本テスト"""
    console.print("\n" + "="*60, style="bold cyan")
    console.print("🧪 Scenario A (Azure SDK) テスト開始", style="bold cyan")
    console.print("="*60 + "\n", style="bold cyan")
    
    try:
        # Create client
        console.print("[blue]1. OCRクライアントを作成中...[/blue]")
        client = await create_client()
        console.print("[green]✓ クライアント作成成功[/green]")
        
        # Search for test images
        test_images_dir = Path(__file__).parent.parent / "test_images"
        
        if not test_images_dir.exists():
            console.print(f"[red]✗ test_images ディレクトリが見つかりません: {test_images_dir}[/red]")
            return
        
        test_images = list(test_images_dir.glob("*.jpg")) + list(test_images_dir.glob("*.png"))
        
        if not test_images:
            console.print("[red]✗ テスト画像が見つかりません[/red]")
            return
        
        # Test with the first image
        test_image = test_images[0]
        console.print(f"\n[blue]2. テスト画像: {test_image.name}[/blue]")
        
        # Load image
        with open(test_image, 'rb') as f:
            image_data = f.read()
        
        console.print(f"[dim]   サイズ: {len(image_data):,} bytes ({len(image_data)/(1024*1024):.2f} MB)[/dim]")
        
        # Execute OCR
        console.print("\n[blue]3. OCR処理を実行中...[/blue]")
        result, metadata = await client.ocr_with_fallback(image_data)
        
        # Display results
        console.print("\n" + "="*60, style="bold green")
        console.print("📊 テスト結果", style="bold green")
        console.print("="*60, style="bold green")
        
        if result:
            console.print("\n[green]✓ OCR処理成功![/green]")
            
            # Display metadata
            console.print(f"\n[cyan]クライアントタイプ:[/cyan] {metadata.get('client_type', 'Unknown')}")
            console.print(f"[cyan]最終エンドポイント:[/cyan] {metadata.get('final_endpoint', 'Unknown')}")
            console.print(f"[cyan]試行回数:[/cyan] {metadata.get('total_attempts', 0)}")
            console.print(f"[cyan]フォールバック回数:[/cyan] {metadata.get('fallback_count', 0)}")
            
            # Attempt details
            console.print("\n[yellow]試行詳細:[/yellow]")
            for attempt in metadata.get('attempts', []):
                status_color = "green" if attempt['success'] else "red"
                console.print(
                    f"  {attempt['attempt']}. [{status_color}]{attempt['endpoint']}[/{status_color}]: "
                    f"status={attempt['status']}, "
                    f"latency={attempt['latency_ms']}ms, "
                    f"method={attempt.get('method', 'Unknown')}"
                )
            
            # Display OCR result sample
            if 'readResult' in result and 'blocks' in result['readResult']:
                blocks = result['readResult']['blocks']
                if blocks and len(blocks) > 0 and 'lines' in blocks[0]:
                    lines = blocks[0]['lines']
                    console.print(f"\n[yellow]抽出されたテキスト (最初の3行):[/yellow]")
                    for i, line in enumerate(lines[:3]):
                        console.print(f"  {i+1}. {line['text']}")
                    
                    total_lines = sum(len(block.get('lines', [])) for block in blocks)
                    console.print(f"\n[dim]総行数: {total_lines}[/dim]")
            
            # Image processing information
            if 'image_processing' in metadata:
                proc_info = metadata['image_processing']
                console.print(f"\n[yellow]画像処理:[/yellow]")
                console.print(f"  元サイズ: {proc_info.get('original_size_mb', 0):.2f} MB")
                console.print(f"  最終サイズ: {proc_info.get('final_size_mb', 0):.2f} MB")
                if proc_info.get('resized') or proc_info.get('compressed'):
                    console.print(f"  圧縮率: {proc_info.get('compression_ratio', 1.0):.1f}x")
            
        else:
            console.print("\n[red]✗ OCR処理失敗[/red]")
            console.print(f"\n[yellow]メタデータ:[/yellow]")
            console.print(f"  試行回数: {metadata.get('total_attempts', 0)}")
            console.print(f"  フォールバック回数: {metadata.get('fallback_count', 0)}")
            
            # Error details
            for attempt in metadata.get('attempts', []):
                if not attempt['success']:
                    console.print(f"\n[red]エラー詳細:[/red]")
                    console.print(f"  エンドポイント: {attempt['endpoint']}")
                    console.print(f"  ステータス: {attempt['status']}")
                    if 'error' in attempt:
                        console.print(f"  エラー: {attempt['error']}")
        
        console.print("\n" + "="*60, style="bold cyan")
        console.print("🎉 テスト完了", style="bold cyan")
        console.print("="*60 + "\n", style="bold cyan")
        
    except Exception as e:
        console.print(f"\n[red]✗ テスト中にエラーが発生しました: {e}[/red]", style="bold")
        import traceback
        console.print(traceback.format_exc(), style="dim")


if __name__ == "__main__":
    asyncio.run(test_scenario_a())
