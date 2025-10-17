#!/usr/bin/env python3
"""
OCRテスト用のサンプル画像をダウンロードするスクリプト

使用例:
python scripts/seed_test_images/download_samples.py --output ./samples --count 10
"""

import asyncio
import aiofiles
import httpx
import click
import os
from pathlib import Path
from rich.console import Console
from rich.progress import Progress

console = Console()

# サンプル画像URL（テキストを含む画像）
SAMPLE_IMAGES = [
    # Azure Computer Vision サンプル画像
    {
        'url': 'https://moderatorsampleimages.blob.core.windows.net/samples/sample_text.jpg',
        'name': 'azure_sample_text.jpg',
        'description': 'Azure サンプルテキスト'
    },
    {
        'url': 'https://raw.githubusercontent.com/Azure-Samples/cognitive-services-sample-data-files/master/ComputerVision/Images/printed_text.jpg',
        'name': 'printed_text.jpg',
        'description': '印刷テキスト'
    },
    {
        'url': 'https://raw.githubusercontent.com/Azure-Samples/cognitive-services-sample-data-files/master/ComputerVision/Images/handwritten_text.jpg', 
        'name': 'handwritten_text.jpg',
        'description': '手書きテキスト'
    },
    # Microsoft Learn サンプル
    {
        'url': 'https://learn.microsoft.com/azure/ai-services/computer-vision/media/quickstarts/presentation.png',
        'name': 'presentation.png',
        'description': 'プレゼンテーション画像'
    },
    # GitHub の OCR テストサンプル
    {
        'url': 'https://raw.githubusercontent.com/microsoft/VisionSample/master/VisionSample.iOS/Resources/sign.jpg',
        'name': 'sign_sample.jpg',
        'description': '標識サンプル'
    },
    # レシート風の画像サンプル
    {
        'url': 'https://raw.githubusercontent.com/Azure-Samples/cognitive-services-sample-data-files/master/ComputerVision/Images/receipt.jpg',
        'name': 'receipt_sample.jpg',
        'description': 'レシートサンプル'
    },
    # Wikipedia のテキスト画像
    {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/f6/Sudoku-by-L2G-20050714.svg/256px-Sudoku-by-L2G-20050714.svg.png',
        'name': 'sudoku_numbers.png',
        'description': '数字（数独）'
    },
    {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/50/Vd-Orig.png/256px-Vd-Orig.png',
        'name': 'document_text.png',
        'description': '文書テキスト'
    },
    # 多言語テキスト
    {
        'url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/c4/PM5544_with_non-PAL_signals.png/640px-PM5544_with_non-PAL_signals.png',
        'name': 'test_pattern.png',
        'description': 'テストパターン'
    }
]

# 合成テキスト画像生成用のサンプルテキスト
SAMPLE_TEXTS = [
    "Hello World! OCR Test 123",
    "Azure Computer Vision API",
    "Performance Testing Sample",
    "Latency Optimization Demo",
    "Circuit Breaker Pattern",
    "Failover Mechanism Test",
    "高負荷テスト用サンプル",
    "レイテンシー最適化デモ"
]


async def download_image(session: httpx.AsyncClient, url: str, output_path: Path) -> bool:
    """画像をダウンロード"""
    try:
        response = await session.get(url)
        response.raise_for_status()
        
        async with aiofiles.open(output_path, 'wb') as f:
            await f.write(response.content)
        
        return True
    except Exception as e:
        console.print(f"[red]ダウンロード失敗: {url} - {e}[/red]")
        return False


def generate_text_image(text: str, output_path: Path) -> bool:
    """テキスト画像を生成（PIL使用）"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        
        # 画像サイズとフォント設定
        width, height = 800, 600
        background_color = (255, 255, 255)  # 白背景
        text_color = (0, 0, 0)  # 黒文字
        
        # 画像作成
        image = Image.new('RGB', (width, height), background_color)
        draw = ImageDraw.Draw(image)
        
        # フォント設定（システム標準フォントを使用）
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        # テキストを複数行に分割
        lines = textwrap.wrap(text, width=25)
        
        # テキストを描画
        y_offset = 50
        line_height = 60
        
        for line in lines:
            # テキストのバウンディングボックスを取得
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            
            # 中央に配置
            x = (width - text_width) // 2
            draw.text((x, y_offset), line, fill=text_color, font=font)
            y_offset += line_height
        
        # 追加のランダムテキスト（バリエーション増加）
        import random
        random_texts = [
            f"Random Text {random.randint(1000, 9999)}",
            f"Test Image #{random.randint(1, 100)}",
            f"Timestamp: {random.randint(1600000000, 1700000000)}"
        ]
        
        y_offset = height - 150
        for random_text in random_texts:
            bbox = draw.textbbox((0, 0), random_text, font=font)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            draw.text((x, y_offset), random_text, fill=(128, 128, 128), font=font)
            y_offset += 40
        
        # 画像保存
        image.save(output_path)
        return True
        
    except ImportError:
        console.print("[yellow]PIL (Pillow) がインストールされていません。テキスト画像生成をスキップします。[/yellow]")
        return False
    except Exception as e:
        console.print(f"[red]テキスト画像生成失敗: {e}[/red]")
        return False


async def download_samples(output_dir: str, count: int = 10):
    """サンプル画像をダウンロード"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    console.print(f"[green]サンプル画像ダウンロード開始: {output_path}[/green]")
    
    downloaded_count = 0
    
    async with httpx.AsyncClient(timeout=30.0) as session:
        with Progress() as progress:
            # 外部画像のダウンロード
            if SAMPLE_IMAGES:
                download_task = progress.add_task("外部画像ダウンロード中...", total=len(SAMPLE_IMAGES))
                
                for img_info in SAMPLE_IMAGES:
                    if downloaded_count >= count:
                        break
                        
                    output_file = output_path / img_info['name']
                    
                    if output_file.exists():
                        console.print(f"[yellow]スキップ（既存）: {img_info['name']}[/yellow]")
                    else:
                        console.print(f"[blue]ダウンロード: {img_info['description']} -> {img_info['name']}[/blue]")
                        
                        success = await download_image(session, img_info['url'], output_file)
                        if success:
                            downloaded_count += 1
                            console.print(f"[green]完了: {img_info['name']}[/green]")
                        else:
                            console.print(f"[red]失敗: {img_info['name']}[/red]")
                    
                    progress.update(download_task, advance=1)
    
    # テキスト画像の生成
    if downloaded_count < count:
        remaining = count - downloaded_count
        console.print(f"[blue]テキスト画像を{remaining}枚生成します...[/blue]")
        
        with Progress() as progress:
            gen_task = progress.add_task("テキスト画像生成中...", total=remaining)
            
            for i in range(remaining):
                text_index = i % len(SAMPLE_TEXTS)
                text = SAMPLE_TEXTS[text_index]
                
                # ファイル名にバリエーション
                output_file = output_path / f'generated_text_{i+1:03d}.png'
                
                if output_file.exists():
                    console.print(f"[yellow]スキップ（既存）: {output_file.name}[/yellow]")
                else:
                    console.print(f"[blue]生成: {text} -> {output_file.name}[/blue]")
                    
                    success = generate_text_image(text, output_file)
                    if success:
                        downloaded_count += 1
                        console.print(f"[green]完了: {output_file.name}[/green]")
                    else:
                        console.print(f"[red]失敗: {output_file.name}[/red]")
                
                progress.update(gen_task, advance=1)
    
    console.print(f"\n[bold green]完了: {downloaded_count}枚のサンプル画像を準備しました[/bold green]")
    console.print(f"出力ディレクトリ: {output_path.absolute()}")
    
    # ディレクトリ内容を表示
    files = list(output_path.glob('*'))
    image_files = [f for f in files if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']]
    
    console.print(f"\n画像ファイル数: {len(image_files)}")
    for img_file in sorted(image_files)[:10]:  # 最初の10個を表示
        file_size = img_file.stat().st_size
        console.print(f"  {img_file.name} ({file_size:,} bytes)")
    
    if len(image_files) > 10:
        console.print(f"  ... その他 {len(image_files) - 10} ファイル")


@click.command()
@click.option('--output', default='./samples', help='出力ディレクトリ')
@click.option('--count', default=10, help='ダウンロードする画像数')
def main(output: str, count: int):
    """サンプル画像ダウンロードのメインエントリーポイント"""
    
    try:
        asyncio.run(download_samples(output, count))
    except KeyboardInterrupt:
        console.print("\n[yellow]ダウンロードが中断されました[/yellow]")
    except Exception as e:
        console.print(f"[red]エラー: {e}[/red]")
        exit(1)


if __name__ == '__main__':
    main()