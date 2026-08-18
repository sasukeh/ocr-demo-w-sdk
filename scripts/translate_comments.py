#!/usr/bin/env python3
"""
Translate Japanese comments in Python files to English.
"""
import re
import os
from pathlib import Path

# Translation mappings for common Japanese comments
TRANSLATIONS = {
    # scenario_a_client/client.py
    "秒に変換": "convert to seconds",
    "URLからベースエンドポイントを抽出（/vision/... を除く）": "Extract base endpoint from URL (excluding /vision/...)",
    "SDKクライアントを作成": "Create SDK client",
    "画像解析を実行（同期的に）": "Execute image analysis (synchronously)",
    "SDKは内部で適切なタイムアウト処理を行う": "SDK handles timeout internally",
    "結果を辞書形式に変換": "Convert result to dictionary format",
    "Retry-Afterヘッダーを取得": "Get Retry-After header",
    "画像前処理（リサイズ・圧縮）": "Image preprocessing (resize and compression)",
    "SDKを使って画像解析を実行": "Execute image analysis using SDK",
    "フォールバック判定": "Determine if fallback is needed",
    "成功！": "Success!",
    "最後の試行でない場合は継続": "Continue if not the last attempt",
    "Retry-Afterがある場合はそれを尊重、なければ指数バックオフ + ジッター": "Respect Retry-After if present, otherwise use exponential backoff + jitter",
    "最大10秒に制限": "cap at 10 seconds max",
    "全ての試行が失敗": "All attempts failed",
    "環境変数からOCRクライアントを作成": "Create OCR client from environment variables",
    
    # Class and function docstrings
    "Azure Computer Vision OCR SDK クライアント。": "Azure Computer Vision OCR SDK client.",
    "複数エンドポイント間でのフォールバック機能を提供。": "Provides fallback functionality across multiple endpoints.",
    "指定されたエンドポイントに対してSDKクライアントを作成": "Create SDK client for the specified endpoint",
    "Endpointオブジェクト": "Endpoint object",
    "Azure Computer Vision SDK を使って画像解析（OCR）を実行": "Execute image analysis (OCR) using Azure Computer Vision SDK",
    "画像データ（バイト列）": "Image data (bytes)",
    "結果, ステータスコード, レイテンシー(ms), Retry-After秒数": "result, status code, latency (ms), Retry-After seconds",
    "フォールバック機能付きOCR実行": "Execute OCR with fallback functionality",
    "画像データ": "Image data",
    "結果, メタデータ": "result, metadata",
    
    # test_sdk.py
    ".envファイルを読み込み": "Load .env file",
    "モジュールパスを追加": "Add module path",
    "クライアント作成": "Create client",
    "テスト画像を探す": "Search for test images",
    "最初の画像でテスト": "Test with the first image",
    "画像読み込み": "Load image",
    "OCR実行": "Execute OCR",
    "結果表示": "Display results",
    "メタデータ表示": "Display metadata",
    "試行詳細": "Attempt details",
    "OCR結果サンプル表示": "Display OCR result sample",
    "画像処理情報": "Image processing information",
    "エラー詳細": "Error details",
    
    # client_via_apim.py
    "HTTP/2対応のクライアント設定": "HTTP/2 compatible client configuration",
    "レスポンスヘッダーを辞書として取得": "Get response headers as dictionary",
    "Retry-After ヘッダーを解析": "Parse Retry-After header",
    "日付形式の場合は無視（簡略化）": "Ignore date format (simplified)",
    "レスポンスボディの処理": "Process response body",
    "APIMのOCRエンドポイントURL構築 (v4.0 imageanalysis:analyze)": "Build APIM OCR endpoint URL (v4.0 imageanalysis:analyze)",
    "APIMから返されるメタデータを抽出": "Extract metadata returned from APIM",
    "メタデータ構築": "Build metadata",
    
    # test_httpx.py
    "環境変数確認": "Check environment variables",
    "APIMヘッダー情報": "APIM header information",
    
    # load_test_count.py
    "テスト画像の取得": "Get test images",
    "APIM クライアントのインポート": "Import APIM client",
    "設定読み込み（親ディレクトリの .env.apim を使用）": "Load configuration (using .env.apim from parent directory)",
    "結果格納": "Store results",
    "セマフォで並行数を制御": "Control concurrency with semaphore",
    "クライアントセッションを開始": "Start client session",
    "ランダムに画像を選択": "Select image randomly",
    "プログレスバー付きで実行": "Execute with progress bar",
    "全リクエストを並行実行": "Execute all requests concurrently",
    "統計計算": "Calculate statistics",
    "エラー集計": "Aggregate errors",
    "バックエンド使用状況": "Backend usage",
    "結果表示": "Display results",
    "結果をファイルに保存": "Save results to file",
    "メイン統計": "Main statistics",
    "エラーサマリー": "Error summary",
    "エラーメッセージを短縮": "Shorten error message",
    "負荷テスト実行": "Execute load test",
    
    # endpoints.py
    "URLからリージョンを推測": "Infer region from URL",
    "ヘルシーなエンドポイントからランダム選択（負荷分散）": "Randomly select from healthy endpoints (load balancing)",
    "全てペナルティ中の場合はラウンドロビン": "Use round-robin if all endpoints are penalized",
    
    # load_test.py
    "相対インポート": "Relative import",
    "対応画像形式": "Supported image formats",
    "タイムアウト付きでキューから取得": "Get from queue with timeout",
    "OCR実行（環境変数で同期/非同期を選択）": "Execute OCR (sync/async selected by environment variable)",
    "メトリクス記録": "Record metrics",
    "最後の試行の情報を取得": "Get last attempt information",
    "結果ログ": "Log result",
    "予期しないエラー": "Unexpected error",
    "プログレス更新": "Update progress",
    "キュータスク完了": "Queue task completed",
    "キューが空 = 全てのリクエスト処理完了": "Queue empty = all requests processed",
    "テスト画像読み込み": "Load test images",
    "総リクエスト数計算": "Calculate total request count",
    "画像キューとプログレス": "Image queue and progress",
    "リクエスト生成タスク": "Request generation task",
    "ラウンドロビンで画像選択": "Select image with round-robin",
    "画像データ読み込み": "Load image data",
    
    # Console messages
    "OCRクライアント初期化 (Azure SDK): タイムアウト": "OCR client initialized (Azure SDK): timeout",
    "最大リトライ": "max retries",
    "HTTP エラー": "HTTP error",
    "サービスエラー": "Service error",
    "タイムアウト": "Timeout",
    "秒": "seconds",
    "試行": "Attempt",
    "Azure SDK使用": "using Azure SDK",
    "Retry-Afterにより": "Due to Retry-After",
    "秒待機後にリトライ": "seconds, retrying",
    "指数バックオフで": "With exponential backoff",
}

def translate_comment(comment):
    """Translate a Japanese comment to English."""
    # Remove leading # and whitespace
    original = comment.strip()
    if not original.startswith('#'):
        return comment
    
    # Extract comment text
    comment_text = original[1:].strip()
    
    # Check if translation exists
    if comment_text in TRANSLATIONS:
        return f"# {TRANSLATIONS[comment_text]}"
    
    # Return original if no translation found
    return comment

def translate_file(file_path):
    """Translate Japanese comments in a Python file."""
    print(f"Processing: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        modified = False
        new_lines = []
        
        for line in lines:
            # Check if line contains a Japanese comment
            if '#' in line and re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', line):
                # Split line into code and comment
                parts = line.split('#', 1)
                if len(parts) == 2:
                    code_part = parts[0]
                    comment_part = '#' + parts[1]
                    
                    # Translate comment
                    translated = translate_comment(comment_part)
                    
                    if translated != comment_part:
                        new_line = code_part + translated + '\n' if not translated.endswith('\n') else code_part + translated
                        new_lines.append(new_line)
                        modified = True
                        continue
            
            new_lines.append(line)
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"  ✓ Translated comments in {file_path}")
            return True
        else:
            print(f"  - No translations needed for {file_path}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error processing {file_path}: {e}")
        return False

def main():
    """Main function to translate comments in Python files."""
    root_dir = Path(__file__).parent.parent
    
    # Target directories
    target_dirs = [
        root_dir / 'scenario_a_client',
        root_dir / 'scenario_b_apim'
    ]
    
    total_files = 0
    translated_files = 0
    
    for target_dir in target_dirs:
        if not target_dir.exists():
            print(f"Directory not found: {target_dir}")
            continue
        
        print(f"\nProcessing directory: {target_dir}")
        
        for py_file in target_dir.glob('*.py'):
            if py_file.name.startswith('__'):
                continue
            
            total_files += 1
            if translate_file(py_file):
                translated_files += 1
    
    print(f"\n{'='*60}")
    print(f"Translation complete!")
    print(f"Total files processed: {total_files}")
    print(f"Files with translations: {translated_files}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
