#!/usr/bin/env python3
"""
Complete 2025 Analysis Pipeline.

Orchestrates the full workflow:
1. Download 2025 data from Binance
2. Run comprehensive backtests with FinRL models
3. Generate performance analysis and reports
4. Identify learning opportunities

Usage:
    python scripts/run_2025_analysis.py
    python scripts/run_2025_analysis.py --skip-download
    python scripts/run_2025_analysis.py --skip-backtest
    python scripts/run_2025_analysis.py --symbols BTC,ETH --timeframes 1d

Output:
    - data/2025/*.csv - Downloaded market data
    - data/backtests/2025/results.json - Backtest results
    - data/backtests/2025/BACKTEST_REPORT.txt - Human-readable report
    - data/backtests/2025/analysis.json - Performance analysis
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """2025 market analysis pipeline."""

    def __init__(self, project_root: Path = None):
        """Initialize pipeline."""
        self.project_root = project_root or Path(__file__).parent.parent
        self.data_dir = self.project_root / 'data' / '2025'
        self.backtest_dir = self.project_root / 'data' / 'backtests' / '2025'
        self.models_dir = self.project_root.parent / 'finrl' / 'trained_models'

    def download_data(self, symbols: str = None, timeframes: str = None, dry_run: bool = False) -> bool:
        """Download 2025 market data."""
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 1: DOWNLOAD 2025 MARKET DATA")
        logger.info("=" * 80)

        cmd = [
            sys.executable,
            'scripts/download_2025_data.py'
        ]

        if symbols:
            cmd.extend(['--symbols', symbols])
        if timeframes:
            cmd.extend(['--timeframes', timeframes])
        if dry_run:
            cmd.append('--dry-run')

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=False
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error downloading data: {e}")
            return False

    def run_backtest(self, min_confidence: float = 0.0) -> bool:
        """Run backtests with FinRL models."""
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 2: RUN BACKTESTS WITH FINRL MODELS")
        logger.info("=" * 80)

        cmd = [
            sys.executable,
            'scripts/backtest_2025.py',
            '--all-models',
            '--data-dir', str(self.data_dir),
            '--models-dir', str(self.models_dir),
            '--output-dir', str(self.backtest_dir),
            '--min-confidence', str(min_confidence)
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=False
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return False

    def analyze_results(self) -> bool:
        """Analyze backtest results and generate insights."""
        logger.info("\n" + "=" * 80)
        logger.info("STAGE 3: ANALYZE BACKTEST RESULTS")
        logger.info("=" * 80)

        results_file = self.backtest_dir / 'results.json'
        if not results_file.exists():
            logger.error(f"Results file not found: {results_file}")
            return False

        try:
            with open(results_file, 'r') as f:
                results = json.load(f)

            analysis = self._generate_analysis(results)

            # Save analysis
            analysis_file = self.backtest_dir / 'analysis.json'
            with open(analysis_file, 'w') as f:
                json.dump(analysis, f, indent=2)

            logger.info(f"Analysis saved to {analysis_file.name}")
            self._print_analysis(analysis)

            return True

        except Exception as e:
            logger.error(f"Error analyzing results: {e}")
            return False

    def _generate_analysis(self, results: dict) -> dict:
        """Generate performance analysis from results."""
        analysis = {
            'generated_at': datetime.now().isoformat(),
            'total_combinations': len(results),
            'period': '2025-01-01 to 2025-11-14',
            'symbols': {},
            'timeframes': {},
            'top_performers': [],
            'bottom_performers': [],
            'timeframe_ranking': {},
            'insights': []
        }

        if not results:
            return analysis

        # Parse results
        parsed = []
        for key, data in results.items():
            try:
                parsed.append({
                    'key': key,
                    'symbol': data.get('symbol', 'UNKNOWN'),
                    'timeframe': data.get('timeframe', 'UNKNOWN'),
                    'return_pct': data.get('total_return_pct', 0),
                    'sharpe': data.get('sharpe_ratio', 0),
                    'max_dd': data.get('max_drawdown_pct', 0),
                    'win_rate': data.get('win_rate_pct', 0),
                    'trades': data.get('total_trades', 0)
                })
            except Exception as e:
                logger.warning(f"Error parsing result {key}: {e}")

        if not parsed:
            return analysis

        # Group by symbol
        for item in parsed:
            symbol = item['symbol']
            if symbol not in analysis['symbols']:
                analysis['symbols'][symbol] = {
                    'combinations': 0,
                    'avg_return': 0,
                    'best_return': 0,
                    'worst_return': 0
                }
            analysis['symbols'][symbol]['combinations'] += 1

        # Group by timeframe
        for item in parsed:
            tf = item['timeframe']
            if tf not in analysis['timeframes']:
                analysis['timeframes'][tf] = {
                    'combinations': 0,
                    'avg_return': 0,
                    'best_return': 0,
                    'worst_return': 0
                }
            analysis['timeframes'][tf]['combinations'] += 1

        # Calculate aggregates
        for item in parsed:
            symbol = item['symbol']
            analysis['symbols'][symbol]['avg_return'] += item['return_pct']
            if item['return_pct'] > analysis['symbols'][symbol]['best_return']:
                analysis['symbols'][symbol]['best_return'] = item['return_pct']
            if item['return_pct'] < analysis['symbols'][symbol]['worst_return']:
                analysis['symbols'][symbol]['worst_return'] = item['return_pct']

        for symbol in analysis['symbols']:
            count = analysis['symbols'][symbol]['combinations']
            analysis['symbols'][symbol]['avg_return'] /= count

        for item in parsed:
            tf = item['timeframe']
            analysis['timeframes'][tf]['avg_return'] += item['return_pct']
            if item['return_pct'] > analysis['timeframes'][tf]['best_return']:
                analysis['timeframes'][tf]['best_return'] = item['return_pct']
            if item['return_pct'] < analysis['timeframes'][tf]['worst_return']:
                analysis['timeframes'][tf]['worst_return'] = item['return_pct']

        for tf in analysis['timeframes']:
            count = analysis['timeframes'][tf]['combinations']
            analysis['timeframes'][tf]['avg_return'] /= count

        # Top/bottom performers
        sorted_parsed = sorted(parsed, key=lambda x: x['return_pct'], reverse=True)

        analysis['top_performers'] = [
            {
                'combination': item['key'],
                'symbol': item['symbol'],
                'timeframe': item['timeframe'],
                'return': item['return_pct'],
                'sharpe': item['sharpe'],
                'max_dd': item['max_dd'],
                'win_rate': item['win_rate']
            }
            for item in sorted_parsed[:10]
        ]

        analysis['bottom_performers'] = [
            {
                'combination': item['key'],
                'symbol': item['symbol'],
                'timeframe': item['timeframe'],
                'return': item['return_pct'],
                'sharpe': item['sharpe'],
                'max_dd': item['max_dd'],
                'win_rate': item['win_rate']
            }
            for item in sorted_parsed[-10:]
        ]

        # Rank timeframes by performance
        analysis['timeframe_ranking'] = sorted(
            [
                {
                    'timeframe': tf,
                    'avg_return': data['avg_return'],
                    'best_return': data['best_return'],
                    'combinations': data['combinations']
                }
                for tf, data in analysis['timeframes'].items()
            ],
            key=lambda x: x['avg_return'],
            reverse=True
        )

        # Generate insights
        if sorted_parsed:
            profitable = [item for item in sorted_parsed if item['return_pct'] > 0]
            total_trades = sum(item['trades'] for item in parsed)
            avg_win_rate = sum(item['win_rate'] for item in parsed) / len(parsed)

            analysis['insights'] = [
                f"Analyzed {len(parsed)} symbol/timeframe combinations",
                f"Profitable combinations: {len(profitable)}/{len(parsed)} ({len(profitable)/len(parsed)*100:.1f}%)",
                f"Average return: {sum(item['return_pct'] for item in parsed)/len(parsed):.1f}%",
                f"Total trades executed: {int(total_trades):,}",
                f"Average win rate: {avg_win_rate:.1f}%",
                f"Best performer: {analysis['top_performers'][0]['combination']} "
                f"(+{analysis['top_performers'][0]['return']:.1f}%)" if analysis['top_performers'] else None,
                f"Worst performer: {analysis['bottom_performers'][-1]['combination']} "
                f"({analysis['bottom_performers'][-1]['return']:.1f}%)" if analysis['bottom_performers'] else None
            ]
            analysis['insights'] = [i for i in analysis['insights'] if i]

        return analysis

    def _print_analysis(self, analysis: dict):
        """Print analysis summary."""
        logger.info("\n" + "=" * 80)
        logger.info("ANALYSIS SUMMARY")
        logger.info("=" * 80)

        logger.info(f"Tested combinations: {analysis['total_combinations']}")
        logger.info(f"Period: {analysis['period']}")

        if analysis['symbols']:
            logger.info("\nBy Symbol:")
            for symbol in sorted(analysis['symbols'].keys()):
                data = analysis['symbols'][symbol]
                logger.info(
                    f"  {symbol:12s} - "
                    f"Combos: {data['combinations']:2d}, "
                    f"Avg Return: {data['avg_return']:+6.1f}%, "
                    f"Range: {data['worst_return']:+6.1f}% to {data['best_return']:+6.1f}%"
                )

        if analysis['timeframe_ranking']:
            logger.info("\nTimeframe Performance (ranked):")
            for i, item in enumerate(analysis['timeframe_ranking'], 1):
                logger.info(
                    f"  {i}. {item['timeframe']:5s} - "
                    f"Avg Return: {item['avg_return']:+6.1f}%, "
                    f"Best: {item['best_return']:+6.1f}%, "
                    f"Combos: {item['combinations']}"
                )

        if analysis['top_performers']:
            logger.info("\nTop 5 Performers:")
            for i, item in enumerate(analysis['top_performers'][:5], 1):
                logger.info(
                    f"  {i}. {item['symbol']:12s} {item['timeframe']:5s} - "
                    f"Return: {item['return']:+6.1f}%, "
                    f"Sharpe: {item['sharpe']:6.2f}"
                )

        if analysis['insights']:
            logger.info("\nKey Insights:")
            for insight in analysis['insights']:
                logger.info(f"  • {insight}")

    def run_pipeline(
        self,
        skip_download: bool = False,
        skip_backtest: bool = False,
        symbols: str = None,
        timeframes: str = None
    ) -> bool:
        """Run complete pipeline."""
        logger.info("\n" + "=" * 80)
        logger.info("2025 MARKET ANALYSIS PIPELINE")
        logger.info("=" * 80)
        logger.info(f"Project: {self.project_root}")
        logger.info(f"Data Dir: {self.data_dir}")
        logger.info(f"Backtest Dir: {self.backtest_dir}")
        logger.info(f"Models Dir: {self.models_dir}")

        try:
            # Stage 1: Download
            if not skip_download:
                success = self.download_data(symbols, timeframes)
                if not success:
                    logger.warning("Download failed or incomplete")
                    # Continue anyway - may have partial data
            else:
                logger.info("Skipping download (--skip-download)")

            # Stage 2: Backtest
            if not skip_backtest:
                success = self.run_backtest()
                if not success:
                    logger.error("Backtest failed")
                    return False
            else:
                logger.info("Skipping backtest (--skip-backtest)")

            # Stage 3: Analyze
            success = self.analyze_results()
            if not success:
                logger.error("Analysis failed")
                return False

            logger.info("\n" + "=" * 80)
            logger.info("PIPELINE COMPLETE")
            logger.info("=" * 80)

            return True

        except KeyboardInterrupt:
            logger.warning("\nPipeline interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Run 2025 market analysis pipeline')
    parser.add_argument('--skip-download', action='store_true', help='Skip data download')
    parser.add_argument('--skip-backtest', action='store_true', help='Skip backtesting')
    parser.add_argument('--symbols', type=str, help='Symbols to analyze (comma-separated)')
    parser.add_argument('--timeframes', type=str, help='Timeframes to analyze (comma-separated)')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (show what would happen)')

    args = parser.parse_args()

    pipeline = AnalysisPipeline()

    success = pipeline.run_pipeline(
        skip_download=args.skip_download,
        skip_backtest=args.skip_backtest,
        symbols=args.symbols,
        timeframes=args.timeframes
    )

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
