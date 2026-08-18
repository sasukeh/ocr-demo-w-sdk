"""
シナリオB (httpx + APIM) の簡単なテスト
"""
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent.parent / ".env.apim"
if env_path.exists():
    load_dotenv(env_path)
    print(f"環境変数を読み込みました: {env_path}")

# Add module path
sys.path.insert(0, str(Path(__file__).parent))

from client_via_apim import APIMClient
from rich.console import Console

console = Console()


async def test_scenario_b():
    """シナリオBの基本テスト"""
    console.print("\n" + "="*60, style="bold cyan")
    console.print("🧪 Scenario B (httpx + APIM) テスト開始", style="bold cyan")
    console.print("="*60 + "\n", style="bold cyan")
    
    try:
        # Check environment variables
        apim_gateway = os.getenv('APIM_GATEWAY_URL')
        apim_key = os.getenv('APIM_SUBSCRIPTION_KEY')
        
        if not apim_gateway or not apim_key:
            console.print("[red]✗ APIM_GATEWAY_URL または APIM_SUBSCRIPTION_KEY が設定されていません[/red]")
            console.print("[yellow]ヒント: .env.apim ファイルを確認してください[/yellow]")
            return
        
        # Create client
        console.print("[blue]1. APIMクライアントを作成中...[/blue]")
        console.print(f"[dim]   Gateway: {apim_gateway}[/dim]")
        
        client = APIMClient(apim_gateway, apim_key)
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
        console.print("\n[blue]3. OCR処理を実行中 (APIM経由)...[/blue]")
        result, metadata = await client.ocr_via_apim(image_data)
        
        # Display results
        console.print("\n" + "="*60, style="bold green")
        console.print("📊 テスト結果", style="bold green")
        console.print("="*60, style="bold green")
        
        if result:
            console.print("\n[green]✓ OCR処理成功![/green]")
            
            # Display metadata
            console.print(f"\n[cyan]クライアントタイプ:[/cyan] httpx + APIM")
            console.print(f"[cyan]レイテンシー:[/cyan] {metadata.get('latency_ms', 0)}ms")
            console.print(f"[cyan]ステータスコード:[/cyan] {metadata.get('status_code', 'Unknown')}")
            
            # APIM header information
            if 'backend' in metadata:
                console.print(f"[cyan]バックエンド:[/cyan] {metadata['backend']}")
            
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
            
        else:
            console.print("\n[red]✗ OCR処理失敗[/red]")
            console.print(f"\n[yellow]メタデータ:[/yellow]")
            console.print(f"  ステータスコード: {metadata.get('status_code', 'Unknown')}")
            console.print(f"  レイテンシー: {metadata.get('latency_ms', 0)}ms")
            
            if 'error' in metadata:
                console.print(f"\n[red]エラー詳細:[/red]")
                console.print(f"  {metadata['error']}")
        
        console.print("\n" + "="*60, style="bold cyan")
        console.print("🎉 テスト完了", style="bold cyan")
        console.print("="*60 + "\n", style="bold cyan")
        
    except Exception as e:
        console.print(f"\n[red]✗ テスト中にエラーが発生しました: {e}[/red]", style="bold")
        import traceback
        console.print(traceback.format_exc(), style="dim")


if __name__ == "__main__":
    asyncio.run(test_scenario_b())
