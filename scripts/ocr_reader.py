#!/usr/bin/env python3
"""
OCR実行とテキスト内容表示ツール

実際の画像ファイルを指定してOCR処理を行い、結果をターミナルに表示

使用例:
python scripts/ocr_reader.py --image ./samples/receipt.jpg --endpoint japaneast
python scripts/ocr_reader.py --image ./samples/receipt.jpg --show-all
python scripts/ocr_reader.py --folder ./my_receipts --format json
"""

import asyncio
import json
import click
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from dotenv import load_dotenv

# プロジェクトのパッケージをインポート
import sys
sys.path.append(str(Path(__file__).parent.parent))

from scenario_a_client.client import OCRClient
from scenario_a_client.endpoints import EndpointPool

console = Console()

class OCRReader:
    def __init__(self, env_file: str = '.env'):
        """OCRリーダーを初期化"""
        load_dotenv(env_file)
        
        # 環境変数から設定を読み込み
        endpoints_str = os.getenv('OCR_ENDPOINTS', '')
        keys_str = os.getenv('OCR_KEYS', '')
        
        if not endpoints_str or not keys_str:
            raise ValueError("OCR_ENDPOINTSまたはOCR_KEYSが設定されていません")
        
        # エンドポイントプールとクライアントを初期化
        self.endpoint_pool = EndpointPool.from_env()
        
        # フォールバックポリシーをインポートして初期化
        from scenario_a_client.fallback_policy import FallbackPolicy
        
        # 環境変数から設定値を読み込み（デフォルト値付き）
        single_ms = int(os.getenv('FALLBACK_SINGLE_MS', '1800'))
        ewma_p95_ms = int(os.getenv('EWMA_P95_MS', '2000'))
        alpha = float(os.getenv('EWMA_ALPHA', '0.2'))
        
        policy = FallbackPolicy(
            pool=self.endpoint_pool,
            single_ms=single_ms,
            ewma_p95_ms=ewma_p95_ms,
            alpha=alpha
        )
        
        self.ocr_client = OCRClient(self.endpoint_pool, policy)
        
        console.print("[green]OCRリーダー初期化完了[/green]")
        console.print(f"利用可能エンドポイント: {len(self.endpoint_pool.endpoints)}個")
    
    async def read_image(self, image_path: Path, endpoint_name: str = None) -> dict:
        """画像ファイルからテキストを読み取り"""
        
        if not image_path.exists():
            raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")
        
        # 画像データを読み込み
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        console.print(f"[blue]OCR処理開始: {image_path.name} ({len(image_data):,} bytes)[/blue]")
        
        # 特定のエンドポイントが指定された場合
        if endpoint_name:
            endpoint = None
            for ep in self.endpoint_pool.endpoints:
                if endpoint_name.lower() in ep.url.lower():
                    endpoint = ep
                    break
            
            if not endpoint:
                console.print(f"[red]エンドポイント '{endpoint_name}' が見つかりません[/red]")
                console.print("利用可能なエンドポイント:")
                for ep in self.endpoint_pool.endpoints:
                    region = ep.url.split('//')[1].split('.')[0].replace('ocr-test-a-cv-', '')
                    console.print(f"  - {region}")
                return None
        
        # OCR処理を実行
        try:
            result, metadata = await self.ocr_client.ocr_with_fallback(image_data)
            
            if result:
                console.print("[green]✓ OCR処理完了[/green]")
                
                # 画像処理情報を表示
                if 'image_processing' in metadata:
                    self._display_processing_info(metadata['image_processing'])
                
                return result
            else:
                console.print("[red]✗ OCR処理失敗[/red]")
                
                # 失敗時でも画像処理情報を表示
                if 'image_processing' in metadata:
                    self._display_processing_info(metadata['image_processing'])
                
                return None
                
        except Exception as e:
            console.print(f"[red]エラー: {e}[/red]")
            return None
    
    def display_result(self, result: dict, format_type: str = "rich", show_confidence: bool = True):
        """OCR結果を表示"""
        
        if not result:
            console.print("[red]表示する結果がありません[/red]")
            return
        
        # Azure Image Analysis v4.0とv3.2の形式に対応
        analyze_result = result.get('readResult')  # v4.0
        if not analyze_result:
            analyze_result = result.get('analyzeResult')  # v3.2
            if not analyze_result:
                console.print("[yellow]表示する結果がありません[/yellow]")
                console.print(f"[dim]利用可能なキー: {list(result.keys())}[/dim]")
                return
        
        if format_type == "json":
            # JSON形式で表示
            json_text = json.dumps(result, indent=2, ensure_ascii=False)
            syntax = Syntax(json_text, "json", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, title="[bold blue]OCR結果 (JSON)[/bold blue]"))
            return
        
        elif format_type == "raw":
            # 生のテキストのみ表示
            all_text = []
            
            # v4.0形式 (readResult.blocks)
            if 'blocks' in analyze_result:
                for block in analyze_result.get('blocks', []):
                    for line in block.get('lines', []):
                        all_text.append(line.get('text', ''))
            # v3.2形式 (readResults)
            else:
                for page in analyze_result.get('readResults', []):
                    for line in page.get('lines', []):
                        all_text.append(line.get('text', ''))
            
            text_content = '\n'.join(all_text)
            console.print(Panel(text_content, title="[bold green]抽出テキスト[/bold green]"))
            return
        
        # Rich形式で詳細表示（デフォルト）
        console.print(f"\n[bold blue]═══ OCR処理結果 ═══[/bold blue]")
        
        # v4.0とv3.2で異なる構造に対応
        if 'blocks' in analyze_result:
            # v4.0形式
            console.print(f"モデルバージョン: {result.get('modelVersion', 'N/A')}")
            console.print(f"ブロック数: {len(analyze_result.get('blocks', []))}")
            blocks_or_pages = analyze_result.get('blocks', [])
            is_v4 = True
        else:
            # v3.2形式
            console.print(f"モデルバージョン: {analyze_result.get('version', 'N/A')}")
            console.print(f"ページ数: {len(analyze_result.get('readResults', []))}")
            blocks_or_pages = analyze_result.get('readResults', [])
            is_v4 = False
        
        # ブロック/ページごとの結果を表示
        for idx, item in enumerate(blocks_or_pages, 1):
            if is_v4:
                console.print(f"\n[yellow]--- ブロック {idx} ---[/yellow]")
                lines = item.get('lines', [])
                console.print(f"検出行数: {len(lines)}")
            else:
                console.print(f"\n[yellow]--- ページ {idx} ---[/yellow]")
                console.print(f"サイズ: {item.get('width', 0)} x {item.get('height', 0)} {item.get('unit', 'pixel')}")
                console.print(f"回転角度: {item.get('angle', 0)}°")
                lines = item.get('lines', [])
                console.print(f"検出行数: {len(lines)}")
            
            if lines:
                # テーブル形式で行を表示
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("行", style="dim", width=4)
                table.add_column("テキスト", min_width=40)
                
                if show_confidence:
                    table.add_column("信頼度", justify="right", width=8)
                
                for line_idx, line in enumerate(lines, 1):
                    # v4.0とv3.2で異なるフィールド名に対応
                    text = line.get('text', '')
                    
                    # 信頼度の計算（単語の信頼度の平均）
                    if show_confidence and 'words' in line:
                        confidences = []
                        for word in line['words']:
                            if 'confidence' in word:
                                confidences.append(word['confidence'])
                        
                        if confidences:
                            avg_confidence = sum(confidences) / len(confidences)
                            confidence_str = f"{avg_confidence:.1%}"
                            
                            # 信頼度に応じて色分け
                            if avg_confidence >= 0.9:
                                confidence_str = f"[green]{confidence_str}[/green]"
                            elif avg_confidence >= 0.7:
                                confidence_str = f"[yellow]{confidence_str}[/yellow]"
                            else:
                                confidence_str = f"[red]{confidence_str}[/red]"
                        else:
                            confidence_str = "[dim]N/A[/dim]"
                        
                        table.add_row(str(line_idx), text, confidence_str)
                    else:
                        table.add_row(str(line_idx), text)
                
                console.print(table)
            else:
                console.print("[dim]テキストが検出されませんでした[/dim]")
        
        # 全テキストをまとめて表示
        all_text = []
        for page in analyze_result.get('readResults', []):
            for line in page.get('lines', []):
                all_text.append(line.get('text', ''))
        
        if all_text:
            combined_text = '\n'.join(all_text)
            console.print(f"\n[bold green]--- 全テキスト ---[/bold green]")
            console.print(Panel(combined_text, expand=False))
    
    async def read_folder(self, folder_path: Path, format_type: str = "rich"):
        """フォルダ内の全画像を処理"""
        
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(folder_path.glob(f'*{ext}'))
            image_files.extend(folder_path.glob(f'*{ext.upper()}'))
        
        if not image_files:
            console.print(f"[red]フォルダ内に画像ファイルが見つかりません: {folder_path}[/red]")
            return
        
        console.print(f"[blue]フォルダ内の {len(image_files)} 個の画像を処理します[/blue]")
        
        results = []
        for image_file in sorted(image_files):
            console.print(f"\n[cyan]{'='*60}[/cyan]")
            console.print(f"[bold]ファイル: {image_file.name}[/bold]")
            
            result = await self.read_image(image_file)
            if result:
                results.append({
                    'file': image_file.name,
                    'result': result
                })
                self.display_result(result, format_type)
            else:
                console.print(f"[red]処理失敗: {image_file.name}[/red]")
        
        console.print(f"\n[green]処理完了: {len(results)}/{len(image_files)} 個の画像[/green]")
    
    def _display_processing_info(self, processing_info: dict):
        """画像処理情報を表示"""
        if not processing_info.get('resized') and not processing_info.get('compressed'):
            return  # 処理が不要だった場合は表示しない
        
        console.print("[cyan]📸 画像処理情報:[/cyan]")
        console.print(f"  元サイズ: {processing_info['original_size_mb']:.2f} MB")
        
        if processing_info.get('resized'):
            console.print(f"  [yellow]リサイズ実行[/yellow]")
        
        if processing_info.get('compressed'):
            console.print(f"  [yellow]圧縮実行[/yellow]")
        
        console.print(f"  最終サイズ: {processing_info['final_size_mb']:.2f} MB")
        
        if processing_info['compression_ratio'] > 1:
            console.print(f"  圧縮率: {processing_info['compression_ratio']:.1f}x")
        
        console.print()


@click.command()
@click.option('--image', type=click.Path(exists=True, path_type=Path), help='処理する画像ファイル')
@click.option('--folder', type=click.Path(exists=True, path_type=Path), help='処理する画像フォルダ')
@click.option('--endpoint', help='使用するエンドポイント (japaneast, eastus, westeurope)')
@click.option('--format', 'format_type', 
              type=click.Choice(['rich', 'json', 'raw'], case_sensitive=False),
              default='rich', help='出力形式')
@click.option('--show-confidence/--no-confidence', default=True, help='信頼度を表示')
@click.option('--env-file', default='.env', help='環境変数ファイル')
def main(image: Path, folder: Path, endpoint: str, format_type: str, show_confidence: bool, env_file: str):
    """OCR読み取りとテキスト表示のメインエントリーポイント"""
    
    if not image and not folder:
        console.print("[red]--image または --folder のいずれかを指定してください[/red]")
        return
    
    if image and folder:
        console.print("[red]--image と --folder を同時に指定することはできません[/red]")
        return
    
    try:
        # OCRリーダーを初期化
        reader = OCRReader(env_file)
        
        async def run_ocr():
            if image:
                # 単一画像の処理
                result = await reader.read_image(image, endpoint)
                if result:
                    reader.display_result(result, format_type, show_confidence)
            
            elif folder:
                # フォルダ内画像の一括処理
                await reader.read_folder(folder, format_type)
        
        # 非同期処理を実行
        asyncio.run(run_ocr())
        
    except KeyboardInterrupt:
        console.print("\n[yellow]処理が中断されました[/yellow]")
    except Exception as e:
        console.print(f"[red]エラー: {e}[/red]")
        exit(1)


if __name__ == '__main__':
    main()