#!/usr/bin/env python3
"""
SQLShell Test Runner

This script provides a unified interface for running all tests in the SQLShell project.
It supports various modes and options for different testing scenarios.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit             # Run only unit tests
    python run_tests.py --integration      # Run only integration tests
    python run_tests.py --quick            # Run quick tests (skip slow/performance)
    python run_tests.py --coverage         # Run with coverage report
    python run_tests.py --verbose          # Run with verbose output
    python run_tests.py --specific FILE    # Run specific test file
    python run_tests.py --branch           # Run tests specific to current branch features
    python run_tests.py --status           # Show test status summary
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

# Project root
PROJECT_ROOT = Path(__file__).parent.absolute()
TESTS_DIR = PROJECT_ROOT / "tests"


def get_terminal_width():
    """Get terminal width for formatting."""
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 80


def print_header(title: str):
    """Print a formatted header."""
    width = get_terminal_width()
    print("\n" + "=" * width)
    print(f" {title} ".center(width, "="))
    print("=" * width + "\n")


def print_section(title: str):
    """Print a section divider."""
    width = get_terminal_width()
    print("\n" + "-" * width)
    print(f" {title} ".center(width, "-"))
    print("-" * width + "\n")


def check_pytest_installed():
    """Check if pytest is installed."""
    try:
        import pytest
        return True
    except ImportError:
        return False


def install_test_dependencies():
    """Install test dependencies."""
    print("Installing test dependencies...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", 
        "pytest>=7.0.0", 
        "pytest-cov>=4.0.0",
        "pytest-xdist>=3.0.0",
        "pytest-timeout>=2.0.0"
    ], check=True)


def run_pytest(args: list, capture_output: bool = False) -> subprocess.CompletedProcess:
    """Run pytest with the given arguments."""
    cmd = [sys.executable, "-m", "pytest"] + args
    print(f"Running: {' '.join(cmd)}\n")
    
    if capture_output:
        return subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
    else:
        return subprocess.run(cmd, cwd=PROJECT_ROOT)


def run_all_tests(verbose: bool = False, parallel: bool = False):
    """Run all tests."""
    print_header("Running All Tests")
    
    args = [str(TESTS_DIR)]
    if verbose:
        args.append("-v")
    if parallel:
        args.extend(["-n", "auto"])
    
    return run_pytest(args)


def run_unit_tests(verbose: bool = False):
    """Run only unit tests."""
    print_header("Running Unit Tests")
    
    args = [str(TESTS_DIR), "-m", "unit or not (integration or slow or gui)"]
    if verbose:
        args.append("-v")
    
    return run_pytest(args)


def run_integration_tests(verbose: bool = False):
    """Run integration tests."""
    print_header("Running Integration Tests")
    
    args = [str(TESTS_DIR), "-m", "integration"]
    if verbose:
        args.append("-v")
    
    return run_pytest(args)


def run_quick_tests(verbose: bool = False):
    """Run quick tests, skipping slow and performance tests."""
    print_header("Running Quick Tests")
    
    args = [str(TESTS_DIR), "-m", "not slow and not performance"]
    if verbose:
        args.append("-v")
    
    return run_pytest(args)


def run_with_coverage(verbose: bool = False):
    """Run tests with coverage reporting."""
    print_header("Running Tests with Coverage")
    
    args = [
        str(TESTS_DIR),
        "--cov=sqlshell",
        "--cov-report=term-missing",
        "--cov-report=html:coverage_html",
        "--cov-config=pyproject.toml"
    ]
    if verbose:
        args.append("-v")
    
    result = run_pytest(args)
    
    if result.returncode == 0:
        print(f"\n✓ Coverage report generated: {PROJECT_ROOT / 'coverage_html' / 'index.html'}")
    
    return result


def run_specific_tests(test_path: str, verbose: bool = False):
    """Run specific test file or directory."""
    print_header(f"Running Tests: {test_path}")
    
    args = [test_path]
    if verbose:
        args.append("-v")
    
    return run_pytest(args)


def run_branch_tests(verbose: bool = False):
    """
    Run tests specific to the current branch features (feature/December).
    
    This runs all the core functionality tests that should be verified
    before merging the branch.
    """
    print_header("Running Branch Feature Tests (feature/December)")
    
    # Define the key feature tests for this branch
    branch_tests = [
        # Database management tests
        "tests/test_database_manager.py",
        # Multi-delete functionality
        "tests/test_multi_delete.py",
        # Search functionality
        "tests/test_search_performance.py",
        # Query execution (F5/F9)
        "tests/f5_f9_functionality/",
        # Export functionality
        "tests/test_export.py",
        # Query executor
        "tests/test_query_executor.py",
    ]
    
    # Filter to only existing test files
    existing_tests = []
    for test in branch_tests:
        test_path = PROJECT_ROOT / test
        if test_path.exists():
            existing_tests.append(str(test_path))
        else:
            print(f"⚠ Test not found (skipping): {test}")
    
    if not existing_tests:
        print("No branch tests found!")
        return subprocess.CompletedProcess(args=[], returncode=1)
    
    args = existing_tests
    if verbose:
        args.append("-v")
    
    return run_pytest(args)


def show_test_status():
    """Show a summary of test status across the project."""
    print_header("SQLShell Test Status Summary")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Generated: {timestamp}\n")
    
    # Collect tests
    print_section("Test Discovery")
    result = run_pytest(["--collect-only", "-q", str(TESTS_DIR)], capture_output=True)
    
    if result.returncode != 0:
        print(f"Error collecting tests:\n{result.stderr}")
        return result
    
    # Parse collection output
    lines = result.stdout.strip().split('\n')
    test_count = 0
    for line in lines:
        if 'test' in line.lower() or '::' in line:
            test_count += 1
    
    print(f"Total tests discovered: {test_count}")
    
    # Run tests and get summary
    print_section("Test Execution Summary")
    result = run_pytest([str(TESTS_DIR), "--tb=no", "-q"], capture_output=True)
    
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    
    # Print overall status
    print_section("Overall Status")
    if result.returncode == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nRun 'python run_tests.py --verbose' for detailed output")
    
    return result


def list_test_files():
    """List all test files in the project."""
    print_header("Test Files in Project")
    
    test_files = []
    
    # Tests directory
    for pattern in ["test_*.py", "*_test.py"]:
        test_files.extend(TESTS_DIR.rglob(pattern))
    
    # Root level test files
    for pattern in ["test_*.py", "*_test.py"]:
        test_files.extend(PROJECT_ROOT.glob(pattern))
    
    test_files = sorted(set(test_files))
    
    print(f"Found {len(test_files)} test files:\n")
    
    current_dir = None
    for f in test_files:
        rel_path = f.relative_to(PROJECT_ROOT)
        parent = rel_path.parent
        
        if parent != current_dir:
            current_dir = parent
            print(f"\n📁 {parent}/")
        
        # Check if file has content
        content = f.read_text().strip()
        has_content = len(content) > 10 and "def test_" in content
        status = "✓" if has_content else "○ (empty)"
        
        print(f"   {status} {f.name}")
    
    return subprocess.CompletedProcess(args=[], returncode=0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="SQLShell Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_tests.py                    # Run all tests
    python run_tests.py --quick            # Quick test run (skip slow tests)
    python run_tests.py --coverage         # Run with coverage report
    python run_tests.py --branch           # Run branch-specific tests
    python run_tests.py --status           # Show project test status
    python run_tests.py -s tests/test_db/  # Run specific directory
        """
    )
    
    parser.add_argument("--all", "-a", action="store_true", 
                        help="Run all tests (default)")
    parser.add_argument("--unit", "-u", action="store_true",
                        help="Run only unit tests")
    parser.add_argument("--integration", "-i", action="store_true",
                        help="Run only integration tests")
    parser.add_argument("--quick", "-q", action="store_true",
                        help="Run quick tests (skip slow/performance)")
    parser.add_argument("--coverage", "-c", action="store_true",
                        help="Run with coverage report")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")
    parser.add_argument("--parallel", "-p", action="store_true",
                        help="Run tests in parallel")
    parser.add_argument("--specific", "-s", type=str, metavar="PATH",
                        help="Run specific test file or directory")
    parser.add_argument("--branch", "-b", action="store_true",
                        help="Run tests for current branch features")
    parser.add_argument("--status", action="store_true",
                        help="Show test status summary")
    parser.add_argument("--list", "-l", action="store_true",
                        help="List all test files")
    parser.add_argument("--install-deps", action="store_true",
                        help="Install test dependencies")
    
    args = parser.parse_args()
    
    # Print banner
    print_header("SQLShell Test Runner")
    print(f"Project: {PROJECT_ROOT}")
    print(f"Python: {sys.version.split()[0]}")
    
    # Check/install dependencies
    if args.install_deps or not check_pytest_installed():
        if not check_pytest_installed():
            print("\n⚠ pytest not found. Installing test dependencies...")
        install_test_dependencies()
        if args.install_deps:
            print("\n✓ Test dependencies installed successfully.")
            return 0
    
    # Dispatch to appropriate test runner
    result = None
    
    if args.list:
        result = list_test_files()
    elif args.status:
        result = show_test_status()
    elif args.specific:
        result = run_specific_tests(args.specific, args.verbose)
    elif args.branch:
        result = run_branch_tests(args.verbose)
    elif args.unit:
        result = run_unit_tests(args.verbose)
    elif args.integration:
        result = run_integration_tests(args.verbose)
    elif args.quick:
        result = run_quick_tests(args.verbose)
    elif args.coverage:
        result = run_with_coverage(args.verbose)
    else:
        result = run_all_tests(args.verbose, args.parallel)
    
    # Return appropriate exit code
    return result.returncode if result else 0


if __name__ == "__main__":
    sys.exit(main())

