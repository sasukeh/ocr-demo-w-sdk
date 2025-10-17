import io
import os
from typing import Tuple, Optional
from PIL import Image, ImageOps
from rich.console import Console

console = Console()


class ImageProcessor:
    """画像処理ユーティリティクラス"""
    
    # Azure Computer Vision APIの制限
    MAX_FILE_SIZE_MB = 4  # 4MBまで
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    
    # 推奨解像度設定
    MAX_DIMENSION = 4096  # 最大辺長
    MIN_DIMENSION = 50    # 最小辺長
    
    # 品質設定
    JPEG_QUALITY = 85     # JPEG圧縮品質
    
    @classmethod
    def process_image(cls, image_data: bytes, filename: str = "image") -> Tuple[bytes, dict]:
        """
        画像データを処理してAPIに適した形式に変換
        
        Args:
            image_data: 元の画像データ
            filename: ファイル名（ログ用）
            
        Returns:
            Tuple[処理後の画像データ, 処理情報]
        """
        original_size = len(image_data)
        processing_info = {
            'original_size_mb': original_size / (1024 * 1024),
            'original_size_bytes': original_size,
            'resized': False,
            'compressed': False,
            'format_changed': False,
            'final_size_mb': 0,
            'final_size_bytes': 0,
            'compression_ratio': 1.0
        }
        
        console.print(f"[blue]画像処理開始: {filename} ({original_size:,} bytes, {original_size/(1024*1024):.2f} MB)[/blue]")
        
        # サイズチェック - 小さい場合はそのまま返す
        if original_size <= cls.MAX_FILE_SIZE_BYTES:
            console.print(f"[green]✓ サイズOK: 処理不要[/green]")
            processing_info['final_size_mb'] = processing_info['original_size_mb']
            processing_info['final_size_bytes'] = original_size
            return image_data, processing_info
        
        try:
            # PILで画像を読み込み
            with Image.open(io.BytesIO(image_data)) as img:
                console.print(f"[yellow]画像情報: {img.size[0]}x{img.size[1]}, {img.format}, {img.mode}[/yellow]")
                
                # 画像を処理
                processed_img = cls._resize_image(img)
                
                # 圧縮して保存
                processed_data = cls._compress_image(processed_img, original_format=img.format)
                
                final_size = len(processed_data)
                processing_info.update({
                    'resized': True,
                    'compressed': True,
                    'final_size_mb': final_size / (1024 * 1024),
                    'final_size_bytes': final_size,
                    'compression_ratio': original_size / final_size if final_size > 0 else 1.0
                })
                
                console.print(f"[green]✓ 画像処理完了: {final_size:,} bytes ({final_size/(1024*1024):.2f} MB)[/green]")
                console.print(f"[dim]  圧縮率: {processing_info['compression_ratio']:.1f}x[/dim]")
                
                return processed_data, processing_info
                
        except Exception as e:
            console.print(f"[red]✗ 画像処理エラー: {e}[/red]")
            # エラーの場合は元データを返す
            processing_info['final_size_mb'] = processing_info['original_size_mb']
            processing_info['final_size_bytes'] = original_size
            return image_data, processing_info
    
    @classmethod
    def _resize_image(cls, img: Image.Image) -> Image.Image:
        """画像のリサイズ処理"""
        width, height = img.size
        max_dim = max(width, height)
        
        if max_dim <= cls.MAX_DIMENSION:
            return img
        
        # アスペクト比を保持してリサイズ
        ratio = cls.MAX_DIMENSION / max_dim
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        
        console.print(f"[yellow]リサイズ: {width}x{height} → {new_width}x{new_height}[/yellow]")
        
        # 高品質リサンプリング
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return resized
    
    @classmethod
    def _compress_image(cls, img: Image.Image, original_format: Optional[str] = None) -> bytes:
        """画像の圧縮処理"""
        output = io.BytesIO()
        
        # RGBAをRGBに変換（JPEGサポートのため）
        if img.mode in ('RGBA', 'LA', 'P'):
            # 透明背景を白に変換
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        
        # フォーマット決定
        format_to_use = 'JPEG'
        if original_format == 'PNG' and cls._should_keep_png(img):
            format_to_use = 'PNG'
        
        # 圧縮保存
        if format_to_use == 'JPEG':
            img.save(output, format='JPEG', quality=cls.JPEG_QUALITY, optimize=True)
        else:
            img.save(output, format='PNG', optimize=True)
        
        return output.getvalue()
    
    @classmethod
    def _should_keep_png(cls, img: Image.Image) -> bool:
        """PNGフォーマットを保持すべきかを判定"""
        # 小さい画像や図表っぽい場合はPNGを保持
        width, height = img.size
        if width <= 800 and height <= 600:
            return True
        
        # その他の場合はJPEGに変換
        return False
    
    @classmethod
    def validate_image_size(cls, image_data: bytes, filename: str = "image") -> bool:
        """画像サイズが適切かを検証"""
        size_mb = len(image_data) / (1024 * 1024)
        
        if len(image_data) > cls.MAX_FILE_SIZE_BYTES:
            console.print(f"[red]✗ {filename}: サイズ超過 ({size_mb:.2f} MB > {cls.MAX_FILE_SIZE_MB} MB)[/red]")
            return False
        
        console.print(f"[green]✓ {filename}: サイズOK ({size_mb:.2f} MB)[/green]")
        return True
    
    @classmethod
    def get_image_info(cls, image_data: bytes) -> dict:
        """画像の基本情報を取得"""
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                return {
                    'size': img.size,
                    'format': img.format,
                    'mode': img.mode,
                    'file_size_bytes': len(image_data),
                    'file_size_mb': len(image_data) / (1024 * 1024)
                }
        except Exception as e:
            return {
                'error': str(e),
                'file_size_bytes': len(image_data),
                'file_size_mb': len(image_data) / (1024 * 1024)
            }