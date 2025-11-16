#!/usr/bin/env python3
"""
Test runner for JARVIS Trading System
Executes all unit and integration tests with coverage reporting.
"""

import sys
import unittest
import os
from pathlib import Path
import argparse
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def run_unit_tests(verbosity=2, pattern='test*.py'):
    """
    Run all unit tests.

    Args:
        verbosity: Test output verbosity level (0-2)
        pattern: Pattern to match test files

    Returns:
        TestResult object
    """
    print("\n" + "=" * 60)
    print("Running Unit Tests")
    print("=" * 60 + "\n")

    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.discover('tests/unit', pattern=pattern, top_level_dir=project_root)

    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    return result


def run_specific_test(test_module, verbosity=2):
    """
    Run a specific test module.

    Args:
        test_module: Module path (e.g., 'tests.unit.domain.test_trading_models')
        verbosity: Test output verbosity level

    Returns:
        TestResult object
    """
    print(f"\n Running specific test: {test_module}")
    print("-" * 40)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(test_module)

    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    return result


def run_integration_tests(verbosity=2):
    """
    Run all integration tests.

    Args:
        verbosity: Test output verbosity level

    Returns:
        TestResult object
    """
    print("\n" + "=" * 60)
    print("Running Integration Tests")
    print("=" * 60 + "\n")

    loader = unittest.TestLoader()
    suite = loader.discover('tests/integration', pattern='test*.py', top_level_dir=project_root)

    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    return result


def run_with_coverage():
    """
    Run tests with coverage reporting.
    Requires coverage package: pip install coverage
    """
    print("\n" + "=" * 60)
    print("Running Tests with Coverage")
    print("=" * 60 + "\n")

    try:
        import coverage

        # Initialize coverage
        cov = coverage.Coverage(source=['src'])
        cov.start()

        # Run all tests
        unit_result = run_unit_tests(verbosity=1)

        # Stop coverage
        cov.stop()
        cov.save()

        # Generate report
        print("\n" + "=" * 60)
        print("Coverage Report")
        print("=" * 60)
        cov.report()

        # Generate HTML report
        html_dir = 'htmlcov'
        cov.html_report(directory=html_dir)
        print(f"\nHTML coverage report generated in: {html_dir}/index.html")

        return unit_result

    except ImportError:
        print("Coverage package not installed. Run: pip install coverage")
        return None


def print_test_summary(results):
    """
    Print summary of test results.

    Args:
        results: List of TestResult objects
    """
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    total_tests = sum(r.testsRun for r in results)
    total_failures = sum(len(r.failures) for r in results)
    total_errors = sum(len(r.errors) for r in results)
    total_skipped = sum(len(r.skipped) for r in results)

    print(f"Total Tests Run: {total_tests}")
    print(f"Failures: {total_failures}")
    print(f"Errors: {total_errors}")
    print(f"Skipped: {total_skipped}")

    if total_failures == 0 and total_errors == 0:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ TESTS FAILED!")

        # Print failure details
        for i, result in enumerate(results):
            if result.failures:
                print(f"\nFailures in test set {i+1}:")
                for test, trace in result.failures:
                    print(f"  - {test}: {trace}")

            if result.errors:
                print(f"\nErrors in test set {i+1}:")
                for test, trace in result.errors:
                    print(f"  - {test}: {trace}")

    print("=" * 60)


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Run JARVIS Trading System tests")

    parser.add_argument(
        '--type',
        choices=['unit', 'integration', 'all'],
        default='all',
        help='Type of tests to run'
    )

    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Run with coverage reporting'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        type=int,
        choices=[0, 1, 2],
        default=2,
        help='Verbosity level (0=quiet, 1=normal, 2=verbose)'
    )

    parser.add_argument(
        '--test',
        help='Run specific test module (e.g., tests.unit.domain.test_trading_models)'
    )

    parser.add_argument(
        '--pattern',
        default='test*.py',
        help='Pattern for test file discovery'
    )

    args = parser.parse_args()

    print(f"\nJARVIS Trading System - Test Runner")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python version: {sys.version}")

    results = []

    # Run with coverage if requested
    if args.coverage:
        result = run_with_coverage()
        if result:
            results.append(result)
    else:
        # Run specific test if requested
        if args.test:
            result = run_specific_test(args.test, args.verbose)
            results.append(result)
        else:
            # Run tests based on type
            if args.type in ['unit', 'all']:
                result = run_unit_tests(args.verbose, args.pattern)
                results.append(result)

            if args.type in ['integration', 'all']:
                result = run_integration_tests(args.verbose)
                results.append(result)

    # Print summary
    if results:
        print_test_summary(results)

        # Exit with appropriate code
        total_failures = sum(len(r.failures) for r in results)
        total_errors = sum(len(r.errors) for r in results)

        if total_failures > 0 or total_errors > 0:
            sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()