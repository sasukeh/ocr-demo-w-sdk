"""
Scenario B: API Management メトリクス管理
メトリクス収集、保存、比較分析機能
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
import statistics

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


@dataclass
class ComparisonResult:
    """シナリオ比較結果"""
    scenario_a_stats: Dict[str, Any]
    scenario_b_stats: Dict[str, Any]
    performance_diff: Dict[str, float]
    recommendations: List[str]


class APIMMetricsManager:
    """APIM メトリクス管理クラス"""
    
    def __init__(self, console: Console):
        self.console = console
    
    def load_metrics(self, filename: str) -> Optional[Dict[str, Any]]:
        """メトリクスファイルを読み込み"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.console.print(f"❌ ファイル {filename} が見つかりません", style="red")
            return None
        except json.JSONDecodeError as e:
            self.console.print(f"❌ JSON 解析エラー: {e}", style="red")
            return None
    
    def save_metrics(self, data: Dict[str, Any], filename: str) -> bool:
        """メトリクスをファイルに保存"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.console.print(f"❌ 保存エラー: {e}", style="red")
            return False
    
    def analyze_apim_performance(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """APIM パフォーマンス分析"""
        if not metrics or 'metrics' not in metrics:
            return {}
        
        request_metrics = metrics['metrics']
        successful_requests = [m for m in request_metrics if m.get('success', False)]
        
        if not successful_requests:
            return {'error': 'No successful requests found'}
        
        # レスポンス時間分析
        response_times = [m['total_duration'] for m in successful_requests]
        ocr_times = [m.get('ocr_duration', 0) for m in successful_requests]
        result_times = [m.get('result_duration', 0) for m in successful_requests]
        
        # バックエンド使用状況
        backend_usage = {}
        attempt_counts = []
        
        for m in successful_requests:
            backend = m.get('served_by_backend', 'unknown')
            backend_usage[backend] = backend_usage.get(backend, 0) + 1
            attempt_counts.append(m.get('total_attempts', 1))
        
        # フェイルオーバー効果分析
        total_requests = len(request_metrics)
        successful_count = len(successful_requests)
        failed_count = total_requests - successful_count
        
        # APIM 特有のメトリクス
        circuit_breaker_activations = sum(1 for m in request_metrics if m.get('total_attempts', 1) > 1)
        
        analysis = {
            'total_requests': total_requests,
            'successful_requests': successful_count,
            'failed_requests': failed_count,
            'success_rate': successful_count / total_requests if total_requests > 0 else 0,
            
            # レスポンス時間統計
            'avg_response_time': statistics.mean(response_times),
            'median_response_time': statistics.median(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'response_time_std': statistics.stdev(response_times) if len(response_times) > 1 else 0,
            
            # 処理段階別時間
            'avg_ocr_time': statistics.mean(ocr_times),
            'avg_result_time': statistics.mean(result_times),
            
            # バックエンド分散
            'backend_usage': backend_usage,
            'backend_distribution': {
                k: v / successful_count for k, v in backend_usage.items()
            } if successful_count > 0 else {},
            
            # フェイルオーバー効果
            'avg_attempts_per_request': statistics.mean(attempt_counts),
            'circuit_breaker_activations': circuit_breaker_activations,
            'circuit_breaker_rate': circuit_breaker_activations / total_requests if total_requests > 0 else 0,
            
            # 可用性指標
            'availability': successful_count / total_requests if total_requests > 0 else 0,
            'reliability_score': self._calculate_reliability_score(request_metrics)
        }
        
        return analysis
    
    def _calculate_reliability_score(self, metrics: List[Dict[str, Any]]) -> float:
        """信頼性スコア計算（0-1の範囲）"""
        if not metrics:
            return 0.0
        
        success_rate = sum(1 for m in metrics if m.get('success', False)) / len(metrics)
        
        # レスポンス時間の安定性（低い方が良い）
        response_times = [m.get('total_duration', 0) for m in metrics if m.get('success', False)]
        if response_times:
            time_stability = 1 - min(1.0, statistics.stdev(response_times) / statistics.mean(response_times))
        else:
            time_stability = 0.0
        
        # フェイルオーバーの効果性
        attempts = [m.get('total_attempts', 1) for m in metrics]
        failover_efficiency = 1 - min(1.0, (statistics.mean(attempts) - 1) / 2)
        
        # 総合スコア（重み付き平均）
        reliability_score = (
            success_rate * 0.5 +           # 成功率（50%）
            time_stability * 0.3 +         # 応答時間安定性（30%）
            failover_efficiency * 0.2      # フェイルオーバー効率（20%）
        )
        
        return reliability_score
    
    def compare_scenarios(self, scenario_a_file: str, scenario_b_file: str) -> Optional[ComparisonResult]:
        """シナリオ A と B を比較"""
        scenario_a_data = self.load_metrics(scenario_a_file)
        scenario_b_data = self.load_metrics(scenario_b_file)
        
        if not scenario_a_data or not scenario_b_data:
            return None
        
        # A: Client-side analysis
        if 'summary' in scenario_a_data:
            scenario_a_stats = scenario_a_data['summary']
        else:
            # Fallback to detailed analysis
            scenario_a_stats = self._analyze_scenario_a(scenario_a_data)
        
        # B: APIM analysis
        scenario_b_stats = self.analyze_apim_performance(scenario_b_data)
        
        # パフォーマンス差分計算
        performance_diff = {}
        
        common_metrics = [
            'success_rate', 'avg_response_time', 'availability'
        ]
        
        for metric in common_metrics:
            a_val = scenario_a_stats.get(metric, 0)
            b_val = scenario_b_stats.get(metric, 0)
            
            if a_val > 0:
                diff_percent = ((b_val - a_val) / a_val) * 100
                performance_diff[metric] = diff_percent
        
        # レコメンデーション生成
        recommendations = self._generate_recommendations(scenario_a_stats, scenario_b_stats, performance_diff)
        
        return ComparisonResult(
            scenario_a_stats=scenario_a_stats,
            scenario_b_stats=scenario_b_stats,
            performance_diff=performance_diff,
            recommendations=recommendations
        )
    
    def _analyze_scenario_a(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Scenario A データの分析"""
        if 'metrics' not in data:
            return {}
        
        metrics = data['metrics']
        successful_requests = [m for m in metrics if m.get('success', False)]
        total_requests = len(metrics)
        
        if not successful_requests:
            return {'error': 'No successful requests in Scenario A'}
        
        response_times = [m['total_duration'] for m in successful_requests]
        
        # エンドポイント使用状況
        endpoint_usage = {}
        for m in successful_requests:
            endpoint = m.get('endpoint_used', 'unknown')
            endpoint_usage[endpoint] = endpoint_usage.get(endpoint, 0) + 1
        
        return {
            'total_requests': total_requests,
            'successful_requests': len(successful_requests),
            'success_rate': len(successful_requests) / total_requests,
            'avg_response_time': statistics.mean(response_times),
            'median_response_time': statistics.median(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'endpoint_usage': endpoint_usage,
            'availability': len(successful_requests) / total_requests
        }
    
    def _generate_recommendations(
        self, 
        scenario_a: Dict[str, Any], 
        scenario_b: Dict[str, Any], 
        diff: Dict[str, float]
    ) -> List[str]:
        """比較結果に基づくレコメンデーション生成"""
        recommendations = []
        
        # 成功率比較
        success_rate_diff = diff.get('success_rate', 0)
        if success_rate_diff > 5:
            recommendations.append("✅ APIM のサーキットブレイカーにより可用性が向上しています")
        elif success_rate_diff < -5:
            recommendations.append("⚠️ クライアント側フェイルオーバーの方が高い成功率を実現しています")
        else:
            recommendations.append("📊 両シナリオの可用性は同等レベルです")
        
        # レスポンス時間比較
        response_time_diff = diff.get('avg_response_time', 0)
        if response_time_diff > 20:
            recommendations.append("🐌 APIM 経由でレイテンシーが増加しています。キャッシュ戦略を検討してください")
        elif response_time_diff < -10:
            recommendations.append("🚀 APIM の最適化によりレスポンス時間が改善されています")
        else:
            recommendations.append("⚡ レスポンス時間は両シナリオで同等です")
        
        # 運用面の考慮
        a_circuit_breaker = scenario_a.get('circuit_breaker_rate', 0)
        b_circuit_breaker = scenario_b.get('circuit_breaker_rate', 0)
        
        if b_circuit_breaker < a_circuit_breaker:
            recommendations.append("🔧 APIM の集中管理により運用効率が向上する可能性があります")
        
        # バックエンド分散
        if scenario_b.get('backend_distribution'):
            distributions = list(scenario_b['backend_distribution'].values())
            if max(distributions) - min(distributions) < 0.2:  # 20%以内の差
                recommendations.append("⚖️ APIM により良好な負荷分散が実現されています")
        
        # セキュリティと管理
        recommendations.append("🔒 APIM はセキュリティ、認証、ログ管理の集中化に有利です")
        recommendations.append("📈 APIM は API バージョン管理とトラフィック制御に適しています")
        
        return recommendations
    
    def display_comparison(self, comparison: ComparisonResult):
        """比較結果の表示"""
        self.console.print("\n" + "="*80, style="bold")
        self.console.print("📊 Scenario A vs Scenario B 比較分析", style="bold cyan")
        self.console.print("="*80, style="bold")
        
        # パフォーマンス比較テーブル
        perf_table = Table(show_header=True, header_style="bold magenta")
        perf_table.add_column("メトリクス", style="cyan")
        perf_table.add_column("Scenario A\n(Client-side)", style="green")
        perf_table.add_column("Scenario B\n(APIM)", style="blue")
        perf_table.add_column("差分", style="yellow")
        
        metrics_to_compare = [
            ('成功率', 'success_rate', '%'),
            ('平均レスポンス時間', 'avg_response_time', 's'),
            ('可用性', 'availability', '%'),
            ('最小レスポンス時間', 'min_response_time', 's'),
            ('最大レスポンス時間', 'max_response_time', 's'),
        ]
        
        for label, key, unit in metrics_to_compare:
            a_val = comparison.scenario_a_stats.get(key, 0)
            b_val = comparison.scenario_b_stats.get(key, 0)
            diff = comparison.performance_diff.get(key, 0)
            
            if unit == '%':
                a_str = f"{a_val:.1%}"
                b_str = f"{b_val:.1%}"
            else:
                a_str = f"{a_val:.3f}{unit}"
                b_str = f"{b_val:.3f}{unit}"
            
            if diff > 0:
                diff_str = f"+{diff:.1f}%"
                diff_color = "green"
            elif diff < 0:
                diff_str = f"{diff:.1f}%"
                diff_color = "red"
            else:
                diff_str = "0%"
                diff_color = "white"
            
            perf_table.add_row(
                label,
                a_str,
                b_str,
                Text(diff_str, style=diff_color)
            )
        
        self.console.print(perf_table)
        
        # レコメンデーション表示
        self.console.print("\n💡 レコメンデーション:", style="bold yellow")
        for i, rec in enumerate(comparison.recommendations, 1):
            self.console.print(f"  {i}. {rec}")
        
        # 詳細分析
        self.console.print("\n📋 詳細分析:", style="bold cyan")
        
        # Scenario A 詳細
        if comparison.scenario_a_stats.get('endpoint_usage'):
            self.console.print("\n🏠 Scenario A エンドポイント使用状況:")
            for endpoint, count in comparison.scenario_a_stats['endpoint_usage'].items():
                total_a = comparison.scenario_a_stats.get('successful_requests', 1)
                percentage = (count / total_a) * 100
                self.console.print(f"  {endpoint}: {count}回 ({percentage:.1f}%)")
        
        # Scenario B 詳細
        if comparison.scenario_b_stats.get('backend_usage'):
            self.console.print("\n🏠 Scenario B バックエンド使用状況:")
            for backend, count in comparison.scenario_b_stats['backend_usage'].items():
                total_b = comparison.scenario_b_stats.get('successful_requests', 1)
                percentage = (count / total_b) * 100
                self.console.print(f"  {backend}: {count}回 ({percentage:.1f}%)")
    
    def export_comparison_report(self, comparison: ComparisonResult, filename: str) -> bool:
        """比較レポートをJSONで出力"""
        report = {
            'comparison_timestamp': datetime.now().isoformat(),
            'scenario_a': comparison.scenario_a_stats,
            'scenario_b': comparison.scenario_b_stats,
            'performance_differences': comparison.performance_diff,
            'recommendations': comparison.recommendations,
            'summary': {
                'winner': self._determine_winner(comparison),
                'key_insights': self._extract_key_insights(comparison)
            }
        }
        
        return self.save_metrics(report, filename)
    
    def _determine_winner(self, comparison: ComparisonResult) -> str:
        """総合評価でどちらが優れているかを判定"""
        a_stats = comparison.scenario_a_stats
        b_stats = comparison.scenario_b_stats
        
        # 重要指標での比較
        a_score = (
            a_stats.get('success_rate', 0) * 0.4 +
            (1 / max(a_stats.get('avg_response_time', 1), 0.001)) * 0.3 +
            a_stats.get('availability', 0) * 0.3
        )
        
        b_score = (
            b_stats.get('success_rate', 0) * 0.4 +
            (1 / max(b_stats.get('avg_response_time', 1), 0.001)) * 0.3 +
            b_stats.get('availability', 0) * 0.3
        )
        
        if abs(a_score - b_score) < 0.05:  # 5%以内の差
            return "同等レベル - 用途に応じて選択"
        elif a_score > b_score:
            return "Scenario A (Client-side) 優位"
        else:
            return "Scenario B (APIM) 優位"
    
    def _extract_key_insights(self, comparison: ComparisonResult) -> List[str]:
        """主要な洞察を抽出"""
        insights = []
        
        diff = comparison.performance_diff
        
        if abs(diff.get('success_rate', 0)) > 5:
            insights.append("可用性に有意な差があります")
        
        if abs(diff.get('avg_response_time', 0)) > 15:
            insights.append("レスポンス時間に大きな差があります")
        
        # 信頼性スコア比較
        a_reliability = comparison.scenario_a_stats.get('reliability_score', 0)
        b_reliability = comparison.scenario_b_stats.get('reliability_score', 0)
        
        if abs(a_reliability - b_reliability) > 0.1:
            insights.append("信頼性スコアに差があります")
        
        return insights


def main():
    """メトリクス分析のメイン関数"""
    console = Console()
    manager = APIMMetricsManager(console)
    
    # 最新のメトリクスファイルを探す
    current_dir = Path(".")
    
    # Scenario A ファイル
    scenario_a_files = list(current_dir.glob("client_metrics_*.json"))
    # Scenario B ファイル  
    scenario_b_files = list(current_dir.glob("apim_metrics_*.json"))
    
    if not scenario_a_files:
        console.print("❌ Scenario A のメトリクスファイルが見つかりません", style="red")
        return
    
    if not scenario_b_files:
        console.print("❌ Scenario B のメトリクスファイルが見つかりません", style="red")
        return
    
    # 最新のファイルを使用
    scenario_a_file = max(scenario_a_files, key=lambda f: f.stat().st_mtime)
    scenario_b_file = max(scenario_b_files, key=lambda f: f.stat().st_mtime)
    
    console.print(f"📊 Scenario A: {scenario_a_file.name}", style="green")
    console.print(f"📊 Scenario B: {scenario_b_file.name}", style="blue")
    
    # 比較実行
    comparison = manager.compare_scenarios(str(scenario_a_file), str(scenario_b_file))
    
    if comparison:
        manager.display_comparison(comparison)
        
        # レポート出力
        report_file = f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        if manager.export_comparison_report(comparison, report_file):
            console.print(f"\n💾 比較レポートを {report_file} に保存しました", style="green")
    else:
        console.print("❌ 比較分析に失敗しました", style="red")


if __name__ == "__main__":
    main()