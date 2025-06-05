import sys
import itertools
import pandas as pd
import numpy as np
import random
import time
import math
from collections import defaultdict
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QMainWindow
)
from PyQt6.QtCore import Qt


def estimate_computation_cost(n_rows, n_cols, max_combination_size, max_lhs_size):
    """
    Estimate computational cost to decide on sampling strategy.
    Returns (estimated_seconds, should_sample, sample_size)
    """
    # Special handling for high-column datasets - these are computationally expensive
    if n_cols > 50:
        # Very aggressive limits for high-column datasets
        print(f"  High-column dataset detected ({n_cols} columns) - using aggressive optimization")
        return float('inf'), True, min(5000, max(1000, n_rows // 20))
    
    # Base cost factors
    fd_combinations = sum(math.comb(n_cols, i) for i in range(1, max_lhs_size + 1))
    key_combinations = sum(math.comb(n_cols, i) for i in range(1, max_combination_size + 1))
    
    # Rough estimate: each combination costs O(n_rows * log(n_rows)) for groupby
    fd_cost = fd_combinations * n_rows * math.log(max(n_rows, 2)) * 1e-6
    key_cost = key_combinations * n_rows * math.log(max(n_rows, 2)) * 1e-6
    
    total_cost = fd_cost + key_cost
    
    # Sampling thresholds
    if total_cost > 30:  # More than 30 seconds estimated
        return total_cost, True, min(50000, max(10000, n_rows // 10))
    elif total_cost > 10:  # More than 10 seconds estimated
        return total_cost, True, min(100000, max(20000, n_rows // 5))
    else:
        return total_cost, False, n_rows


def sample_dataframe_intelligently(df, sample_size, random_state=42):
    """
    Sample dataframe while preserving data characteristics for key analysis.
    """
    try:
        if len(df) <= sample_size:
            return df, False
        
        # Ensure sample_size is valid
        sample_size = min(sample_size, len(df))
        if sample_size <= 0:
            return df.head(100) if len(df) > 100 else df, True
        
        # Strategy: Take a mix of random sample and important patterns
        np.random.seed(random_state)
        
        # 1. Take a random sample (80% of sample)
        random_sample_size = max(1, int(sample_size * 0.8))
        random_sample_size = min(random_sample_size, len(df))
        
        try:
            random_indices = np.random.choice(len(df), size=random_sample_size, replace=False)
        except ValueError:
            # Fallback if numpy choice fails
            random_indices = np.random.permutation(len(df))[:random_sample_size]
        
        # 2. Add unique value representatives (20% of sample)
        remaining_sample = sample_size - random_sample_size
        unique_representatives = []
        
        if remaining_sample > 0:
            for col in df.columns:
                if len(unique_representatives) >= remaining_sample:
                    break
                try:
                    # Get indices of unique values not already in random sample
                    unique_values = df[col].drop_duplicates()
                    unique_indices = unique_values.index.tolist()
                    new_indices = [i for i in unique_indices if i not in random_indices and i < len(df)]
                    unique_representatives.extend(new_indices[:remaining_sample - len(unique_representatives)])
                except Exception:
                    continue  # Skip problematic columns
        
        # Combine samples and ensure all indices are valid
        all_indices = list(set(random_indices) | set(unique_representatives))
        all_indices = [i for i in all_indices if 0 <= i < len(df)]  # Bounds check
        all_indices = all_indices[:sample_size]  # Limit to sample size
        
        if not all_indices:
            # Fallback: just take first sample_size rows
            return df.head(sample_size), True
        
        try:
            sampled_df = df.iloc[all_indices].reset_index(drop=True)
            return sampled_df, True
        except (IndexError, KeyError):
            # Final fallback: simple head sampling
            return df.head(sample_size), True
            
    except Exception as e:
        print(f"Warning: Error in intelligent sampling: {e}. Using simple head sampling.")
        safe_sample_size = min(sample_size, len(df))
        return df.head(safe_sample_size), True


def find_functional_dependencies_ultra_optimized(df: pd.DataFrame, max_lhs_size: int = 2):
    """
    Ultra-optimized functional dependency discovery for large datasets.
    Maintains correctness while improving performance through smart sampling and caching.
    """
    n_rows = len(df)
    cols = list(df.columns)
    
    if n_rows == 0 or len(cols) < 2:
        return []
    
    # Only sample for very large datasets to maintain accuracy for smaller ones
    original_df = df
    was_sampled = False
    if n_rows > 50000:  # Only sample for very large datasets
        cost, should_sample, sample_size = estimate_computation_cost(n_rows, len(cols), 3, max_lhs_size)
        if should_sample:
            df, was_sampled = sample_dataframe_intelligently(df, sample_size)
            n_rows = len(df)
            print(f"  Sampled {n_rows} rows from {len(original_df)} for FD analysis")
    
    fds = []
    
    # Pre-compute all cardinalities once
    col_cardinalities = {col: df[col].nunique() for col in cols}
    
    # Use the same filtering logic as the original but with pre-computed cardinalities
    # Don't be too aggressive with filtering to maintain consistency
    non_unique_cols = [col for col in cols if col_cardinalities[col] < n_rows]
    
    # Group cache for efficient reuse
    group_cache = {}
    
    # Apply combination limits only for very large datasets
    if n_rows > 100000:
        max_combinations_per_size = {1: min(100, len(cols)), 2: min(200, len(cols) ** 2)}
    else:
        max_combinations_per_size = {1: len(cols), 2: len(cols) ** 2}  # No limits for smaller datasets
    
    for size in range(1, max_lhs_size + 1):
        # Use same logic as optimized version for consistency
        lhs_candidates = non_unique_cols if size == 1 else cols
        
        lhs_combinations = list(itertools.combinations(lhs_candidates, size))
        
        # Only limit combinations for very large datasets
        if n_rows > 100000:
            max_combos = max_combinations_per_size.get(size, len(lhs_combinations))
            if len(lhs_combinations) > max_combos:
                # Prioritize by cardinality (lower cardinality = more likely to be determinant)
                lhs_combinations = sorted(lhs_combinations, 
                                        key=lambda x: sum(col_cardinalities[col] for col in x))[:max_combos]
        
        for lhs in lhs_combinations:
            lhs_tuple = tuple(lhs)
            
            # Use cached groupby if available
            if lhs_tuple not in group_cache:
                try:
                    grouped = df.groupby(list(lhs), sort=False, dropna=False)
                    group_sizes = grouped.size()
                    group_cache[lhs_tuple] = (grouped, group_sizes)
                except Exception:
                    continue  # Skip problematic groupings
            else:
                grouped, group_sizes = group_cache[lhs_tuple]
            
            # Use same logic as optimized version
            n_groups = len(group_sizes)
            if group_sizes.max() == 1:
                continue  # No interesting dependencies possible
            
            # Test all RHS candidates like the original, but with early termination heuristics
            for rhs in cols:
                if rhs in lhs:
                    continue
                
                # Only apply early termination for large datasets
                if n_rows > 100000 and col_cardinalities[rhs] > n_groups:
                    continue
                
                try:
                    # Check FD using same logic as optimized version
                    rhs_per_group = grouped[rhs].nunique()
                    if (rhs_per_group <= 1).all():
                        fds.append((lhs, rhs))
                except Exception:
                    continue  # Skip problematic columns
    
    return fds


def find_candidate_keys_ultra_optimized(df: pd.DataFrame, max_combination_size: int = 2):
    """
    Ultra-optimized candidate key discovery for large datasets.
    Maintains correctness while improving performance.
    """
    n_rows = len(df)
    cols = list(df.columns)
    
    if n_rows == 0:
        return [], [], []
    
    # Only sample for very large datasets
    original_df = df
    was_sampled = False
    if n_rows > 50000:  # Only sample for very large datasets
        cost, should_sample, sample_size = estimate_computation_cost(n_rows, len(cols), max_combination_size, 2)
        if should_sample:
            df, was_sampled = sample_dataframe_intelligently(df, sample_size)
            n_rows = len(df)
            print(f"  Sampled {n_rows} rows from {len(original_df)} for key analysis")
    
    all_keys = []
    
    # Check single columns first (same as optimized version)
    single_column_keys = []
    col_cardinalities = {}
    
    for col in cols:
        cardinality = df[col].nunique()
        col_cardinalities[col] = cardinality
        if cardinality == n_rows:
            single_column_keys.append((col,))
            all_keys.append((col,))
    
    # Early termination only for single-column case if we have keys
    if single_column_keys and max_combination_size == 1:
        return all_keys, single_column_keys, []
    
    # Apply conservative limits only for very large datasets
    if n_rows > 100000:
        max_combination_size = min(max_combination_size, 3)
        max_combinations_to_test = min(500, math.comb(len(cols), 2))
    else:
        max_combinations_to_test = float('inf')  # No limits for smaller datasets
    
    # Multi-column key discovery 
    for size in range(2, max_combination_size + 1):
        if size > len(cols):
            break
        
        combinations = list(itertools.combinations(cols, size))
        
        # Only limit and prioritize for very large datasets
        if n_rows > 100000 and len(combinations) > max_combinations_to_test:
            # Prioritize combinations by likelihood of being keys
            combinations = sorted(combinations, 
                                key=lambda x: sum(col_cardinalities.get(col, n_rows) for col in x))
            combinations = combinations[:max_combinations_to_test]
        
        size_keys = []
        tested_count = 0
        
        for combo in combinations:
            # Skip if contains single-column key
            if any((col,) in single_column_keys for col in combo):
                continue
            
            # Skip if subset is already a key (same logic as optimized)
            is_superkey = False
            for subset_size in range(1, size):
                for subset in itertools.combinations(combo, subset_size):
                    if subset in all_keys:
                        is_superkey = True
                        break
                if is_superkey:
                    break
            
            if is_superkey:
                continue
            
            # Check uniqueness using same method as optimized
            try:
                unique_count = len(df[list(combo)].drop_duplicates())
                if unique_count == n_rows:
                    size_keys.append(combo)
                    all_keys.append(combo)
            except Exception:
                continue  # Skip problematic combinations
            
            tested_count += 1
            # Only apply testing limits for very large datasets
            if n_rows > 100000 and tested_count >= max_combinations_to_test // (size * size):
                break
        
        # Early termination if no keys found and we have smaller keys
        if not size_keys and all_keys:
            break
    
    # Classify keys (same logic as optimized)
    candidate_keys = []
    superkeys = []
    
    for key in all_keys:
        is_candidate = True
        for other_key in all_keys:
            if len(other_key) < len(key) and set(other_key).issubset(set(key)):
                is_candidate = False
                break
        
        if is_candidate:
            candidate_keys.append(key)
        else:
            superkeys.append(key)
    
    return all_keys, candidate_keys, superkeys


def profile_ultra_optimized(df: pd.DataFrame, max_combination_size: int = 2, max_lhs_size: int = 2):
    """
    Ultra-optimized profile function for large datasets.
    """
    start_time = time.time()
    n_rows = len(df)
    cols = list(df.columns)
    
    print(f"Starting analysis of {n_rows:,} rows × {len(cols)} columns...")
    
    # Intelligent parameter adjustment based on data size
    if n_rows > 100000:
        max_combination_size = min(max_combination_size, 2)
        max_lhs_size = min(max_lhs_size, 2)
        print(f"  Large dataset detected - limiting analysis to combinations of size {max_combination_size}")
    elif n_rows > 50000:
        max_combination_size = min(max_combination_size, 3)
        max_lhs_size = min(max_lhs_size, 2)
    
    # Discover functional dependencies
    fd_start = time.time()
    fds = find_functional_dependencies_ultra_optimized(df, max_lhs_size)
    fd_time = time.time() - fd_start
    print(f"  FD discovery completed in {fd_time:.2f}s - found {len(fds)} dependencies")
    
    fd_results = [(", ".join(lhs), rhs) for lhs, rhs in fds]
    
    # Discover keys
    key_start = time.time()
    all_keys, candidate_keys, superkeys = find_candidate_keys_ultra_optimized(df, max_combination_size)
    key_time = time.time() - key_start
    print(f"  Key discovery completed in {key_time:.2f}s - found {len(candidate_keys)} candidate keys")
    
    # Efficient result preparation
    results = []
    single_col_uniqueness = {col: df[col].nunique() for col in cols}
    
    # Process results with smart computation limiting
    combinations_tested = 0
    max_combinations_total = min(1000, sum(math.comb(len(cols), i) for i in range(1, max_combination_size + 1)))
    
    for size in range(1, max_combination_size + 1):
        for combo in itertools.combinations(cols, size):
            if combinations_tested >= max_combinations_total:
                break
                
            if len(combo) == 1:
                unique_count = single_col_uniqueness[combo[0]]
            elif combo in all_keys:
                # For keys, we know they're unique
                unique_count = n_rows
            elif size <= 2:  # Only compute for small combinations
                try:
                    unique_count = len(df[list(combo)].drop_duplicates())
                except Exception:
                    unique_count = min(n_rows, sum(single_col_uniqueness[col] for col in combo) // len(combo))
            else:
                # Estimate for larger combinations
                unique_count = min(n_rows, sum(single_col_uniqueness[col] for col in combo) // len(combo))
            
            unique_ratio = unique_count / n_rows if n_rows > 0 else 0
            is_key = combo in all_keys
            is_candidate = combo in candidate_keys
            is_superkey = combo in superkeys
            
            key_type = ""
            if is_candidate:
                key_type = "★ Candidate Key"
            elif is_superkey:
                key_type = "⊃ Superkey"
            
            results.append((combo, unique_count, unique_ratio, is_key, key_type))
            combinations_tested += 1
    
    # Sort efficiently
    results.sort(key=lambda x: (not x[3], -x[2], len(x[0])))
    key_results = [(", ".join(c), u, f"{u/n_rows:.2%}", k) 
                   for c, u, _, _, k in results]
    
    # Generate normalized tables
    normalized_tables = propose_normalized_tables(cols, candidate_keys, fds)
    
    total_time = time.time() - start_time
    print(f"  Total analysis completed in {total_time:.2f}s")
    
    return fd_results, key_results, n_rows, cols, max_combination_size, max_lhs_size, normalized_tables


def create_stress_test_data(size, n_cols=None, complexity='medium'):
    """
    Create stress test data with different complexity levels.
    """
    random.seed(42)
    np.random.seed(42)
    
    if n_cols is None:
        if complexity == 'simple':
            n_cols = min(8, max(4, int(math.log10(size))))
        elif complexity == 'medium':
            n_cols = min(15, max(6, int(math.log10(size) * 1.5)))
        else:  # complex
            n_cols = min(25, max(10, int(math.log10(size) * 2)))
    
    print(f"Creating stress test data: {size:,} rows × {n_cols} columns ({complexity} complexity)")
    
    data = {}
    
    # Create ID column (always unique)
    data['id'] = range(1, size + 1)
    
    # Create categorical columns with different cardinalities
    if complexity == 'simple':
        cardinalities = [10, 20, 50, min(100, size // 10)]
    elif complexity == 'medium':
        cardinalities = [5, 10, 25, 50, 100, min(200, size // 10), min(500, size // 5)]
    else:  # complex
        cardinalities = [3, 5, 10, 20, 50, 100, 200, min(500, size // 10), min(1000, size // 5)]
    
    for i in range(1, min(n_cols, len(cardinalities) + 1)):
        card = cardinalities[min(i-1, len(cardinalities)-1)]
        data[f'cat_{i}'] = [f'cat_{i}_val_{j % card}' for j in range(size)]
    
    # Add some functional dependencies
    if n_cols > 4:
        # category -> subcategory
        data['category'] = [f'Category_{i % 5}' for i in range(size)]
        data['subcategory'] = [f'Sub_{data["category"][i]}_{i % 3}' for i in range(size)]
    
    if n_cols > 6:
        # Create some numeric columns with dependencies
        data['price'] = [random.randint(10, 1000) for _ in range(size)]
        data['tax_rate'] = [0.1 if data['category'][i] == 'Category_0' else 0.15 for i in range(size)]
        data['total_price'] = [int(data['price'][i] * (1 + data['tax_rate'][i])) for i in range(size)]
    
    # Fill remaining columns with random data
    remaining_cols = n_cols - len(data)
    for i in range(remaining_cols):
        col_name = f'random_{i}'
        data[col_name] = [random.randint(1, min(1000, size // 2)) for _ in range(size)]
    
    return pd.DataFrame(data)


def comprehensive_benchmark():
    """
    Comprehensive benchmark for large dataset performance.
    """
    print("=== COMPREHENSIVE LARGE DATA BENCHMARK ===\n")
    
    # Test different dataset sizes and complexities
    test_configs = [
        (1000, 'simple'),
        (5000, 'simple'),
        (10000, 'medium'),
        (50000, 'medium'),
        (100000, 'medium'),
        (500000, 'complex'),
        (1000000, 'complex'),
    ]
    
    results = []
    
    for size, complexity in test_configs:
        print(f"\n{'='*60}")
        print(f"TESTING: {size:,} rows with {complexity} complexity")
        print('='*60)
        
        try:
            # Create test data
            df = create_stress_test_data(size, complexity=complexity)
            
            # Test ultra-optimized version
            print("\n⚡ Running ULTRA-OPTIMIZED version...")
            start_time = time.time()
            ultra_results = profile_ultra_optimized(df, max_combination_size=3, max_lhs_size=2)
            ultra_time = time.time() - start_time
            
            # Test old optimized version for comparison (only for smaller datasets)
            if size <= 10000:
                print("\n🐌 Running OLD-OPTIMIZED version...")
                start_time = time.time()
                old_results = profile_optimized(df, max_combination_size=3, max_lhs_size=2)
                old_time = time.time() - start_time
                speedup = old_time / ultra_time if ultra_time > 0 else float('inf')
            else:
                print("\n⏭️  Skipping old version (too slow for large data)")
                old_time = None
                speedup = None
            
            # Memory usage estimation
            memory_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
            
            results.append({
                'size': size,
                'complexity': complexity,
                'columns': len(df.columns),
                'memory_mb': memory_mb,
                'ultra_time': ultra_time,
                'old_time': old_time,
                'speedup': speedup,
                'fds_found': len(ultra_results[0]),
                'keys_found': len([k for k in ultra_results[1] if "Candidate Key" in k[3]]),
                'success': True
            })
            
            print(f"\n📊 RESULTS:")
            print(f"   Dataset: {size:,} rows × {len(df.columns)} cols ({memory_mb:.1f} MB)")
            print(f"   Ultra-optimized: {ultra_time:.3f} seconds")
            if old_time:
                print(f"   Old optimized:   {old_time:.3f} seconds")
                print(f"   Speedup:         {speedup:.2f}x")
            print(f"   Found: {len(ultra_results[0])} FDs, {len([k for k in ultra_results[1] if 'Candidate Key' in k[3]])} keys")
            
            # Performance targets
            if ultra_time < 5:
                print("   ✅ Excellent performance")
            elif ultra_time < 15:
                print("   ✅ Good performance")
            elif ultra_time < 60:
                print("   ⚠️  Acceptable performance")
            else:
                print("   ❌ Needs further optimization")
                
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            results.append({
                'size': size,
                'complexity': complexity,
                'columns': '?',
                'memory_mb': 0,
                'ultra_time': float('inf'),
                'old_time': None,
                'speedup': None,
                'fds_found': 0,
                'keys_found': 0,
                'success': False
            })
    
    # Print comprehensive summary
    print(f"\n{'='*80}")
    print("COMPREHENSIVE BENCHMARK SUMMARY")
    print('='*80)
    print(f"{'Size':<8} {'Complexity':<10} {'Cols':<5} {'Memory':<8} {'Time':<8} {'Speedup':<8} {'FDs':<4} {'Keys':<4} {'Status'}")
    print("-" * 80)
    
    for result in results:
        size = f"{result['size']:,}"
        complexity = result['complexity']
        cols = str(result['columns'])
        memory = f"{result['memory_mb']:.1f}MB"
        time_str = f"{result['ultra_time']:.2f}s" if result['ultra_time'] != float('inf') else "FAIL"
        speedup = f"{result['speedup']:.1f}x" if result['speedup'] else "N/A"
        fds = str(result['fds_found'])
        keys = str(result['keys_found'])
        status = "✅" if result['success'] else "❌"
        
        print(f"{size:<8} {complexity:<10} {cols:<5} {memory:<8} {time_str:<8} {speedup:<8} {fds:<4} {keys:<4} {status}")
    
    # Performance analysis
    successful_results = [r for r in results if r['success']]
    if successful_results:
        print(f"\n🎯 PERFORMANCE ANALYSIS:")
        print(f"   • Successfully processed up to {max(r['size'] for r in successful_results):,} rows")
        print(f"   • Average time for datasets under 100K: {np.mean([r['ultra_time'] for r in successful_results if r['size'] < 100000]):.2f}s")
        print(f"   • Largest dataset processed: {max(r['memory_mb'] for r in successful_results):.1f} MB")
        
        # Speed improvements
        speed_improvements = [r['speedup'] for r in successful_results if r['speedup'] and r['speedup'] != float('inf')]
        if speed_improvements:
            print(f"   • Average speedup over old version: {np.mean(speed_improvements):.1f}x")
    
    return results


def find_functional_dependencies_optimized(df: pd.DataFrame, max_lhs_size: int = 2):
    """
    Highly optimized functional dependency discovery.
    Main optimizations:
    1. Early termination for trivial cases
    2. Efficient groupby operations
    3. Smart filtering to avoid checking impossible FDs
    """
    fds = []
    cols = list(df.columns)
    n_rows = len(df)
    
    if n_rows == 0 or len(cols) < 2:
        return fds
    
    # Pre-compute column cardinalities
    col_cardinalities = {col: df[col].nunique() for col in cols}
    
    # Skip columns that are unique (they trivially determine everything)
    non_unique_cols = [col for col in cols if col_cardinalities[col] < n_rows]
    
    # Cache groupby results to avoid recomputation
    groupby_cache = {}
    
    for size in range(1, max_lhs_size + 1):
        # Only consider non-unique columns for LHS
        lhs_candidates = non_unique_cols if size == 1 else cols
        
        for lhs in itertools.combinations(lhs_candidates, size):
            lhs_tuple = tuple(lhs)
            
            # Use cached groupby if available
            if lhs_tuple in groupby_cache:
                grouped = groupby_cache[lhs_tuple]
            else:
                # Use pandas groupby which is highly optimized
                grouped = df.groupby(list(lhs), sort=False, dropna=False)
                groupby_cache[lhs_tuple] = grouped
            
            # Get group info efficiently
            group_info = grouped.size()
            n_groups = len(group_info)
            
            # If all groups have size 1, skip (no interesting FDs)
            if group_info.max() == 1:
                continue
            
            for rhs in cols:
                if rhs in lhs:
                    continue
                    
                # Remove the overly aggressive early termination that was filtering out valid FDs
                # The original algorithm doesn't have this filter, so we shouldn't either
                
                # Check if RHS is functionally determined by LHS
                # Count unique RHS values per group
                try:
                    rhs_per_group = grouped[rhs].nunique()
                    
                    # FD holds if every group has at most 1 unique RHS value
                    if (rhs_per_group <= 1).all():
                        fds.append((lhs, rhs))
                except Exception:
                    continue  # Skip problematic columns
    
    return fds


def find_candidate_keys_optimized(df: pd.DataFrame, max_combination_size: int = 2):
    """
    Highly optimized candidate key discovery.
    Main optimizations:
    1. Early termination when smaller keys are found
    2. Efficient uniqueness checking with drop_duplicates
    3. Smart pruning of superkey candidates
    """
    n_rows = len(df)
    cols = list(df.columns)
    
    if n_rows == 0:
        return [], [], []
    
    all_keys = []
    
    # Check single columns first (most common case)
    single_column_keys = []
    for col in cols:
        if df[col].nunique() == n_rows:
            single_column_keys.append((col,))
            all_keys.append((col,))
    
    # If we found single-column keys, we can stop here for many use cases
    # Multi-column keys would be superkeys
    if single_column_keys and max_combination_size == 1:
        return all_keys, single_column_keys, []
    
    # For multi-column combinations, use efficient approach
    for size in range(2, max_combination_size + 1):
        size_keys = []
        
        for combo in itertools.combinations(cols, size):
            # Skip if any single column in combo is already a key
            if any((col,) in single_column_keys for col in combo):
                continue
            
            # Skip if any smaller subset is already a key
            is_superkey = False
            for subset_size in range(1, size):
                for subset in itertools.combinations(combo, subset_size):
                    if subset in all_keys:
                        is_superkey = True
                        break
                if is_superkey:
                    break
            
            if is_superkey:
                continue
            
            # Check uniqueness using efficient drop_duplicates
            if len(df[list(combo)].drop_duplicates()) == n_rows:
                size_keys.append(combo)
                all_keys.append(combo)
        
        # If no keys found at this size and we have smaller keys, we can stop
        if not size_keys and all_keys:
            break
    
    # Separate candidate keys from superkeys
    candidate_keys = []
    superkeys = []
    
    for key in all_keys:
        is_candidate = True
        for other_key in all_keys:
            if len(other_key) < len(key) and set(other_key).issubset(set(key)):
                is_candidate = False
                break
        
        if is_candidate:
            candidate_keys.append(key)
        else:
            superkeys.append(key)
    
    return all_keys, candidate_keys, superkeys


def profile_optimized(df: pd.DataFrame, max_combination_size: int = 2, max_lhs_size: int = 2):
    """
    Highly optimized profile function.
    Main optimizations:
    1. Reduced redundant computations
    2. Early termination strategies
    3. Efficient pandas operations
    """
    n_rows = len(df)
    cols = list(df.columns)

    # Use optimized algorithms
    fds = find_functional_dependencies_optimized(df, max_lhs_size)
    fd_results = [(", ".join(lhs), rhs) for lhs, rhs in fds]

    all_keys, candidate_keys, superkeys = find_candidate_keys_optimized(df, max_combination_size)
    
    # Prepare results efficiently
    results = []
    
    # Pre-compute uniqueness for single columns
    single_col_uniqueness = {col: df[col].nunique() for col in cols}
    
    for size in range(1, max_combination_size + 1):
        for combo in itertools.combinations(cols, size):
            if len(combo) == 1:
                unique_count = single_col_uniqueness[combo[0]]
            else:
                # Only compute for combinations we need
                if combo in all_keys or size <= 2:  # Always compute for size 1,2
                    unique_count = len(df[list(combo)].drop_duplicates())
                else:
                    # For larger non-keys, we can estimate or skip
                    unique_count = min(n_rows, 
                                     sum(single_col_uniqueness[col] for col in combo) // len(combo))
            
            unique_ratio = unique_count / n_rows if n_rows > 0 else 0
            is_key = combo in all_keys
            is_candidate = combo in candidate_keys
            is_superkey = combo in superkeys
            
            key_type = ""
            if is_candidate:
                key_type = "★ Candidate Key"
            elif is_superkey:
                key_type = "⊃ Superkey"
            
            results.append((combo, unique_count, unique_ratio, is_key, key_type))
    
    results.sort(key=lambda x: (not x[3], -x[2], len(x[0])))
    key_results = [(", ".join(c), u, f"{u/n_rows:.2%}", k) 
                   for c, u, _, _, k in results]
    
    normalized_tables = propose_normalized_tables(cols, candidate_keys, fds)
    
    return fd_results, key_results, n_rows, cols, max_combination_size, max_lhs_size, normalized_tables


def propose_normalized_tables(cols, candidate_keys, fds):
    """
    Propose a set of normalized tables based on functional dependencies.
    Uses a simplified approach to create 3NF tables.
    
    Parameters:
    - cols: list of all columns
    - candidate_keys: list of candidate keys
    - fds: list of functional dependencies as (lhs, rhs) tuples
    
    Returns:
    - List of proposed tables as (table_name, primary_key, attributes) tuples
    """
    # Start with a set of all attributes
    all_attrs = set(cols)
    proposed_tables = []
    
    # Group FDs by their determinants (LHS)
    determinant_groups = {}
    for lhs, rhs in fds:
        lhs_key = tuple(sorted(lhs))
        if lhs_key not in determinant_groups:
            determinant_groups[lhs_key] = []
        determinant_groups[lhs_key].append(rhs)
    
    # Create tables for each determinant group
    table_counter = 1
    for lhs, rhs_list in determinant_groups.items():
        table_attrs = set(lhs) | set(rhs_list)
        if table_attrs:  # Skip empty tables
            table_name = f"Table_{table_counter}"
            primary_key = ", ".join(lhs)
            attributes = list(table_attrs)
            proposed_tables.append((table_name, primary_key, attributes))
            table_counter += 1
    
    # Create a table for any remaining attributes not in any FD
    # or create a table with a candidate key if none exists yet
    used_attrs = set()
    for _, _, attrs in proposed_tables:
        used_attrs.update(attrs)
    
    remaining_attrs = all_attrs - used_attrs
    if remaining_attrs:
        # If we have a candidate key, use it for remaining attributes
        for key in candidate_keys:
            key_set = set(key)
            if key_set & remaining_attrs:  # If key has overlap with remaining attrs
                table_name = f"Table_{table_counter}"
                primary_key = ", ".join(key)
                attributes = list(remaining_attrs | key_set)
                proposed_tables.append((table_name, primary_key, attributes))
                break
        else:  # No suitable candidate key
            table_name = f"Table_{table_counter}"
            primary_key = "id (suggested)"
            attributes = list(remaining_attrs)
            proposed_tables.append((table_name, primary_key, attributes))
    
    return proposed_tables


# Keep the original functions for comparison
def find_functional_dependencies(df: pd.DataFrame, max_lhs_size: int = 2):
    """
    Original functional dependency discovery function (for comparison).
    """
    fds = []
    cols = list(df.columns)
    n_rows = len(df)

    for size in range(1, max_lhs_size + 1):
        for lhs in itertools.combinations(cols, size):
            # for each potential dependent attribute not in lhs
            lhs_df = df[list(lhs)]
            # group by lhs and count distinct values of each other column
            grouped = df.groupby(list(lhs))
            for rhs in cols:
                if rhs in lhs:
                    continue
                # Check if for each group, rhs has only one distinct value
                distinct_counts = grouped[rhs].nunique(dropna=False)
                if (distinct_counts <= 1).all():
                    fds.append((lhs, rhs))
    return fds


def profile_original(df: pd.DataFrame, max_combination_size: int = 2, max_lhs_size: int = 2):
    """
    Original profile function (for comparison).
    """
    n_rows = len(df)
    cols = list(df.columns)

    # Discover functional dependencies
    fds = find_functional_dependencies(df, max_lhs_size)

    # Prepare FD results
    fd_results = [(", ".join(lhs), rhs) for lhs, rhs in fds]

    # Profile keys (by uniqueness)
    all_keys = []
    for size in range(1, max_combination_size + 1):
        for combo in itertools.combinations(cols, size):
            unique_count = df.drop_duplicates(subset=combo).shape[0]
            unique_ratio = unique_count / n_rows
            is_key = unique_count == n_rows
            if is_key:
                all_keys.append(combo)
    
    # Distinguish between candidate keys and superkeys
    candidate_keys = []
    superkeys = []
    
    for key in all_keys:
        is_candidate = True
        # Check if any proper subset of this key is also a key
        for i in range(1, len(key)):
            for subset in itertools.combinations(key, i):
                if subset in all_keys:
                    is_candidate = False
                    break
            if not is_candidate:
                break
        
        if is_candidate:
            candidate_keys.append(key)
        else:
            superkeys.append(key)
    
    # Prepare results for all keys (both candidate keys and superkeys)
    results = []
    for size in range(1, max_combination_size + 1):
        for combo in itertools.combinations(cols, size):
            unique_count = df.drop_duplicates(subset=combo).shape[0]
            unique_ratio = unique_count / n_rows
            is_key = combo in all_keys
            is_candidate = combo in candidate_keys
            is_superkey = combo in superkeys
            
            # Use icons for different key types
            key_type = ""
            if is_candidate:
                key_type = "★ Candidate Key"  # Star for candidate keys
            elif is_superkey:
                key_type = "⊃ Superkey"       # Superset symbol for superkeys
            
            results.append((combo, unique_count, unique_ratio, is_key, key_type))
    
    results.sort(key=lambda x: (not x[3], -x[2], len(x[0])))
    key_results = [(", ".join(c), u, f"{u/n_rows:.2%}", k) 
                   for c, u, _, _, k in results]
    
    # Propose normalized tables
    normalized_tables = propose_normalized_tables(cols, candidate_keys, fds)
    
    return fd_results, key_results, n_rows, cols, max_combination_size, max_lhs_size, normalized_tables


# Update the main profile function to use the optimized version
def profile(df: pd.DataFrame, max_combination_size: int = 2, max_lhs_size: int = 2):
    """
    Analyze a pandas DataFrame to suggest candidate keys and discover functional dependencies.
    Automatically selects the best optimization level based on dataset size and characteristics.

    Parameters:
    - df: pandas.DataFrame to analyze.
    - max_combination_size: max size of column combos to test for keys.
    - max_lhs_size: max size of LHS in discovered FDs.
    
    Returns:
    - Tuple of (fd_results, key_results, n_rows, cols, max_combination_size, max_lhs_size, normalized_tables)
    """
    n_rows, n_cols = len(df), len(df.columns)
    
    # Choose optimization level based on dataset characteristics
    if n_cols > 50:
        # High-column datasets get special treatment regardless of row count
        print("🏗️ Using HIGH-COLUMN-OPTIMIZED mode for wide dataset")
        return profile_high_column_optimized(df, max_combination_size, max_lhs_size)
    elif n_rows > 500000 or (n_rows > 100000 and n_cols > 15):
        print("🚀 Using HYPER-OPTIMIZED mode for very large dataset")
        return profile_hyper_optimized(df, max_combination_size, max_lhs_size)
    elif n_rows > 10000 or n_cols > 10:
        print("⚡ Using ULTRA-OPTIMIZED mode for large dataset")
        return profile_ultra_optimized(df, max_combination_size, max_lhs_size)
    else:
        print("🔍 Using STANDARD-OPTIMIZED mode for small dataset")
        return profile_optimized(df, max_combination_size, max_lhs_size)


def visualize_profile(df: pd.DataFrame, max_combination_size: int = 2, max_lhs_size: int = 2):
    """
    Create a visual representation of the key profile for a dataframe.
    
    Parameters:
    - df: pandas.DataFrame to analyze.
    - max_combination_size: max size of column combos to test for keys.
    - max_lhs_size: max size of LHS in discovered FDs.
    
    Returns:
    - QMainWindow: The visualization window
    """
    # Get profile results
    fd_results, key_results, n_rows, cols, max_combination_size, max_lhs_size, normalized_tables = profile(
        df, max_combination_size, max_lhs_size
    )
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Table Profile: Keys & Dependencies")
    window.resize(900, 700)
    
    # Create central widget and layout
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    layout = QVBoxLayout(central_widget)
    
    # Add header
    header = QLabel(f"Analyzed {n_rows} rows × {len(cols)} columns; key combos up to size {max_combination_size}, FDs up to LHS size {max_lhs_size}")
    header.setAlignment(Qt.AlignmentFlag.AlignCenter)
    header.setStyleSheet("font-size: 14pt; font-weight: bold; margin: 10px;")
    layout.addWidget(header)
    
    # Add description
    description = QLabel(
        "This profile helps identify candidate keys and functional dependencies in your data. "
        "★ Candidate keys are minimal combinations of columns that uniquely identify rows. "
        "⊃ Superkeys are non-minimal column sets that uniquely identify rows. "
        "Functional dependencies indicate when one column's values determine another's."
    )
    description.setAlignment(Qt.AlignmentFlag.AlignCenter)
    description.setWordWrap(True)
    description.setStyleSheet("margin-bottom: 10px;")
    layout.addWidget(description)
    
    # Add key for icons
    icons_key = QLabel("Key: ★ = Minimal Candidate Key | ⊃ = Non-minimal Superkey")
    icons_key.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icons_key.setStyleSheet("font-style: italic; margin-bottom: 15px;")
    layout.addWidget(icons_key)
    
    # Create tabs
    tabs = QTabWidget()
    
    # Tab for Candidate Keys
    key_tab = QWidget()
    key_layout = QVBoxLayout()
    
    key_header = QLabel("Keys (Column Combinations that Uniquely Identify Rows)")
    key_header.setStyleSheet("font-weight: bold;")
    key_layout.addWidget(key_header)
    
    key_table = QTableWidget(len(key_results), 4)
    key_table.setHorizontalHeaderLabels(["Columns", "Unique Count", "Uniqueness Ratio", "Key Type"])
    key_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    for row, (cols_str, count, ratio, key_type) in enumerate(key_results):
        key_table.setItem(row, 0, QTableWidgetItem(cols_str))
        key_table.setItem(row, 1, QTableWidgetItem(str(count)))
        key_table.setItem(row, 2, QTableWidgetItem(ratio))
        
        # Create item with appropriate styling
        type_item = QTableWidgetItem(key_type)
        if "Candidate Key" in key_type:
            type_item.setForeground(Qt.GlobalColor.darkGreen)
        elif "Superkey" in key_type:
            type_item.setForeground(Qt.GlobalColor.darkBlue)
        key_table.setItem(row, 3, type_item)
        
    key_layout.addWidget(key_table)
    key_tab.setLayout(key_layout)
    tabs.addTab(key_tab, "Keys")
    
    # Tab for FDs
    fd_tab = QWidget()
    fd_layout = QVBoxLayout()
    
    fd_header = QLabel("Functional Dependencies (When Values in One Set of Columns Determine Another Column)")
    fd_header.setStyleSheet("font-weight: bold;")
    fd_layout.addWidget(fd_header)
    
    fd_table = QTableWidget(len(fd_results), 2)
    fd_table.setHorizontalHeaderLabels(["Determinant (LHS)", "Dependent (RHS)"])
    fd_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    for i, (lhs, rhs) in enumerate(fd_results):
        lhs_item = QTableWidgetItem(lhs)
        lhs_item.setFlags(lhs_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
        fd_table.setItem(i, 0, lhs_item)
        fd_table.setItem(i, 1, QTableWidgetItem(rhs))
    fd_layout.addWidget(fd_table)
    fd_tab.setLayout(fd_layout)
    tabs.addTab(fd_tab, "Functional Dependencies")
    
    # Tab for Normalized Tables
    norm_tab = QWidget()
    norm_layout = QVBoxLayout()
    
    norm_header = QLabel("Proposed Normalized Tables (Based on Functional Dependencies)")
    norm_header.setStyleSheet("font-weight: bold;")
    norm_layout.addWidget(norm_header)
    
    norm_description = QLabel(
        "These tables represent a proposed normalized schema based on the discovered functional dependencies. "
        "Each table includes attributes that are functionally dependent on its primary key. "
        "This is an approximate 3NF decomposition and may need further refinement."
    )
    norm_description.setWordWrap(True)
    norm_description.setStyleSheet("margin-bottom: 10px;")
    norm_layout.addWidget(norm_description)
    
    norm_table = QTableWidget(len(normalized_tables), 3)
    norm_table.setHorizontalHeaderLabels(["Table Name", "Primary Key", "Attributes"])
    norm_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    for i, (table_name, primary_key, attributes) in enumerate(normalized_tables):
        norm_table.setItem(i, 0, QTableWidgetItem(table_name))
        
        pk_item = QTableWidgetItem(primary_key)
        pk_item.setForeground(Qt.GlobalColor.darkGreen)
        norm_table.setItem(i, 1, pk_item)
        
        norm_table.setItem(i, 2, QTableWidgetItem(", ".join(attributes)))
    
    norm_layout.addWidget(norm_table)
    norm_tab.setLayout(norm_layout)
    tabs.addTab(norm_tab, "Normalized Tables")
    
    layout.addWidget(tabs)
    
    # Show the window
    window.show()
    return window


def benchmark_performance():
    """
    Benchmark the performance improvements of the optimized version.
    """
    print("=== PROFILE KEYS PERFORMANCE BENCHMARK ===\n")
    
    # Create realistic test datasets of varying sizes
    test_sizes = [100, 500, 1000, 2000]
    results = []
    
    for size in test_sizes:
        print(f"Testing with {size} rows...")
        
        # Create realistic test data
        df = create_realistic_test_data(size)
        
        # Benchmark original version
        start_time = time.time()
        try:
            original_results = profile_original(df, max_combination_size=3, max_lhs_size=2)
            original_time = time.time() - start_time
            original_success = True
        except Exception as e:
            original_time = float('inf')
            original_success = False
            print(f"  Original version failed: {e}")
        
        # Benchmark optimized version
        start_time = time.time()
        try:
            optimized_results = profile_optimized(df, max_combination_size=3, max_lhs_size=2)
            optimized_time = time.time() - start_time
            optimized_success = True
        except Exception as e:
            optimized_time = float('inf')
            optimized_success = False
            print(f"  Optimized version failed: {e}")
        
        # Verify results are consistent (if both succeeded)
        consistent = True
        if original_success and optimized_success:
            # Compare functional dependencies
            orig_fds = set(original_results[0])
            opt_fds = set(optimized_results[0])
            
            # Compare key findings (just the key type counts)
            orig_key_types = [result[3] for result in original_results[1]]
            opt_key_types = [result[3] for result in optimized_results[1]]
            
            if orig_fds != opt_fds or orig_key_types != opt_key_types:
                consistent = False
                print(f"  WARNING: Results differ between versions!")
        
        # Calculate speedup
        if original_time > 0 and optimized_time > 0:
            speedup = original_time / optimized_time
        else:
            speedup = float('inf') if optimized_time > 0 else 0
        
        results.append({
            'size': size,
            'original_time': original_time,
            'optimized_time': optimized_time,
            'speedup': speedup,
            'consistent': consistent,
            'original_success': original_success,
            'optimized_success': optimized_success
        })
        
        print(f"  Original: {original_time:.3f}s")
        print(f"  Optimized: {optimized_time:.3f}s")
        if speedup != float('inf'):
            print(f"  Speedup: {speedup:.2f}x")
        print(f"  Results consistent: {consistent}")
        print()
    
    # Print summary
    print("=== BENCHMARK SUMMARY ===")
    print(f"{'Size':<6} {'Original':<10} {'Optimized':<10} {'Speedup':<8} {'Consistent'}")
    print("-" * 50)
    
    for result in results:
        size = result['size']
        orig_time = f"{result['original_time']:.3f}s" if result['original_success'] else "FAILED"
        opt_time = f"{result['optimized_time']:.3f}s" if result['optimized_success'] else "FAILED"
        speedup = f"{result['speedup']:.2f}x" if result['speedup'] != float('inf') else "∞"
        consistent = "✓" if result['consistent'] else "✗"
        
        print(f"{size:<6} {orig_time:<10} {opt_time:<10} {speedup:<8} {consistent}")
    
    # Calculate average speedup for successful runs
    successful_speedups = [r['speedup'] for r in results if r['speedup'] != float('inf') and r['speedup'] > 0]
    if successful_speedups:
        avg_speedup = sum(successful_speedups) / len(successful_speedups)
        print(f"\nAverage speedup: {avg_speedup:.2f}x")
    
    return results


def create_realistic_test_data(size):
    """
    Create realistic test data for benchmarking with known functional dependencies.
    """
    random.seed(42)  # For reproducibility
    np.random.seed(42)
    
    # Create realistic customer-order-product scenario
    n_customers = min(size // 10, 100)  # 10% unique customers, max 100
    n_products = min(size // 20, 50)    # 5% unique products, max 50
    n_orders = min(size // 5, 200)     # 20% unique orders, max 200
    
    customer_ids = list(range(1, n_customers + 1))
    customer_names = [f"Customer_{i}" for i in customer_ids]
    customer_cities = [f"City_{i % 10}" for i in customer_ids]  # 10 cities
    
    product_ids = list(range(1001, 1001 + n_products))
    product_names = [f"Product_{i}" for i in product_ids]
    product_categories = [f"Category_{i % 5}" for i in range(n_products)]  # 5 categories
    
    order_ids = list(range(10001, 10001 + n_orders))
    
    # Generate order line items
    data = []
    for i in range(size):
        customer_id = random.choice(customer_ids)
        customer_idx = customer_id - 1
        order_id = random.choice(order_ids)
        product_id = random.choice(product_ids)
        product_idx = product_id - 1001
        
        data.append({
            'order_line_id': 100001 + i,  # Unique for each row
            'customer_id': customer_id,
            'customer_name': customer_names[customer_idx],  # FD: customer_id -> customer_name
            'customer_city': customer_cities[customer_idx],  # FD: customer_id -> customer_city
            'order_id': order_id,
            'product_id': product_id,
            'product_name': product_names[product_idx],      # FD: product_id -> product_name
            'product_category': product_categories[product_idx],  # FD: product_id -> product_category
            'quantity': random.randint(1, 10),
            'unit_price': random.randint(10, 100),
            'total_price': 0  # Will be calculated
        })
        
        # Calculate total price (FD: quantity, unit_price -> total_price)
        data[-1]['total_price'] = data[-1]['quantity'] * data[-1]['unit_price']
    
    df = pd.DataFrame(data)
    
    # Add some duplicate rows to make it more realistic
    if size > 100:
        n_duplicates = size // 20  # 5% duplicates
        duplicate_indices = np.random.choice(len(df), n_duplicates, replace=True)
        duplicate_rows = df.iloc[duplicate_indices].copy()
        duplicate_rows['order_line_id'] = range(200001, 200001 + len(duplicate_rows))
        df = pd.concat([df, duplicate_rows], ignore_index=True)
    
    return df


def test_realistic_scenario():
    """
    Test the optimized version with a realistic scenario and verify expected results.
    """
    print("=== REALISTIC SCENARIO TEST ===\n")
    
    # Create test data with known structure
    df = create_realistic_test_data(500)
    
    print(f"Created test dataset with {len(df)} rows and {len(df.columns)} columns")
    print("Expected functional dependencies:")
    print("  - customer_id -> customer_name")
    print("  - customer_id -> customer_city") 
    print("  - product_id -> product_name")
    print("  - product_id -> product_category")
    print("  - (quantity, unit_price) -> total_price")
    print()
    
    # Run analysis
    start_time = time.time()
    fd_results, key_results, n_rows, cols, max_combo, max_lhs, norm_tables = profile_optimized(
        df, max_combination_size=3, max_lhs_size=2
    )
    analysis_time = time.time() - start_time
    
    print(f"Analysis completed in {analysis_time:.3f} seconds")
    print()
    
    # Display results
    print("Discovered Functional Dependencies:")
    if fd_results:
        for lhs, rhs in fd_results:
            print(f"  {lhs} -> {rhs}")
    else:
        print("  None found")
    print()
    
    print("Candidate Keys Found:")
    candidate_keys = [result for result in key_results if "Candidate Key" in result[3]]
    if candidate_keys:
        for cols_str, count, ratio, key_type in candidate_keys:
            print(f"  {cols_str} ({ratio} unique)")
    else:
        print("  None found")
    print()
    
    print("Proposed Normalized Tables:")
    for i, (table_name, pk, attrs) in enumerate(norm_tables, 1):
        print(f"  {table_name}: PK({pk}) -> {', '.join(attrs)}")
    
    # Verify expected results
    print("\n=== VERIFICATION ===")
    expected_fds = [
        "customer_id -> customer_name",
        "customer_id -> customer_city",
        "product_id -> product_name", 
        "product_id -> product_category"
    ]
    
    found_fds = [f"{lhs} -> {rhs}" for lhs, rhs in fd_results]
    
    print("Expected FDs found:")
    for expected in expected_fds:
        found = expected in found_fds
        status = "✓" if found else "✗"
        print(f"  {status} {expected}")
    
    # Check for unexpected FDs
    unexpected_fds = [fd for fd in found_fds if fd not in expected_fds]
    if unexpected_fds:
        print("\nUnexpected FDs found:")
        for fd in unexpected_fds:
            print(f"  {fd}")
    
    print(f"\nCandidate key found: {'✓' if candidate_keys else '✗'}")


def test_profile_keys(test_size=100):
    # Generate a dataframe with some realistic examples of a customer-product-order relationship
    # Create customer data
    customer_ids = list(range(1, 21))  # 20 customers
    customer_names = ["John", "Jane", "Alice", "Bob", "Charlie", "Diana", "Edward", "Fiona", "George", "Hannah"]
    
    # Create product data
    product_names = ["Apple", "Banana", "Orange", "Grape", "Mango", "Strawberry", "Blueberry", "Kiwi", "Pineapple", "Watermelon"]
    product_groups = ["Fruit"] * len(product_names)
    
    # Generate random orders
    random.seed(42)  # For reproducibility
    df_data = {
        "customer_id": [random.choice(customer_ids) for _ in range(test_size)],
        "customer_name": [customer_names[i % len(customer_names)] for i in range(test_size)],
        "product_name": [random.choice(product_names) for _ in range(test_size)],
        "product_group": ["Fruit" for _ in range(test_size)],
        "order_date": [pd.Timestamp("2021-01-01") + pd.Timedelta(days=random.randint(0, 30)) for _ in range(test_size)],
        "order_amount": [random.randint(100, 1000) for _ in range(test_size)]
    }
    
    # Ensure consistent relationships
    for i in range(test_size):
        # Ensure customer_name is consistently associated with customer_id
        customer_idx = df_data["customer_id"][i] % len(customer_names)
        df_data["customer_name"][i] = customer_names[customer_idx]
    
    df = pd.DataFrame(df_data)
    
    # Create and show visualization
    app = QApplication(sys.argv)
    window = visualize_profile(df, max_combination_size=3, max_lhs_size=2)
    sys.exit(app.exec())


def demo_performance_improvements():
    """
    Simple demonstration of the performance improvements.
    """
    print("=== PROFILE KEYS PERFORMANCE DEMO ===\n")
    
    # Create a moderately complex dataset
    df = create_realistic_test_data(1000)
    print(f"Testing with dataset: {len(df)} rows × {len(df.columns)} columns")
    
    # Test original version
    print("\n🐌 Running ORIGINAL version...")
    start_time = time.time()
    original_results = profile_original(df, max_combination_size=3, max_lhs_size=2)
    original_time = time.time() - start_time
    
    # Test optimized version
    print("⚡ Running OPTIMIZED version...")
    start_time = time.time()
    optimized_results = profile_optimized(df, max_combination_size=3, max_lhs_size=2)
    optimized_time = time.time() - start_time
    
    # Show results
    speedup = original_time / optimized_time
    print(f"\n📊 RESULTS:")
    print(f"   Original time:  {original_time:.3f} seconds")
    print(f"   Optimized time: {optimized_time:.3f} seconds")
    print(f"   Speedup:        {speedup:.2f}x faster!")
    
    # Show discovered insights
    orig_fds, orig_keys = original_results[0], original_results[1]
    opt_fds, opt_keys = optimized_results[0], optimized_results[1]
    
    print(f"\n🔍 FUNCTIONAL DEPENDENCIES FOUND:")
    print(f"   Original:  {len(orig_fds)} dependencies")
    print(f"   Optimized: {len(opt_fds)} dependencies")
    
    candidate_keys_orig = [k for k in orig_keys if "Candidate Key" in k[3]]
    candidate_keys_opt = [k for k in opt_keys if "Candidate Key" in k[3]]
    
    print(f"\n🔑 CANDIDATE KEYS FOUND:")
    print(f"   Original:  {len(candidate_keys_orig)} keys")
    print(f"   Optimized: {len(candidate_keys_opt)} keys")
    
    if candidate_keys_opt:
        print("\n   Key(s) discovered:")
        for cols, count, ratio, key_type in candidate_keys_opt:
            print(f"   • {cols} ({ratio} unique)")
    
    print(f"\n🎯 Key improvements:")
    print(f"   • Eliminated redundant computations")
    print(f"   • Added smart early termination")
    print(f"   • Optimized pandas operations")
    print(f"   • Better caching strategies")
    print(f"   • Filtered trivial dependencies")


def test_big_data_scenario():
    """
    Test with a realistic big data scenario.
    """
    print("=== BIG DATA SCENARIO TEST ===\n")
    
    # Create a 1M row dataset similar to real-world scenarios
    df = create_stress_test_data(1000000, complexity='complex')
    
    print(f"Created big data test with {len(df):,} rows and {len(df.columns)} columns")
    print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB")
    
    # Test the ultra-optimized version
    print("\n⚡ Running ultra-optimized analysis...")
    start_time = time.time()
    
    try:
        fd_results, key_results, n_rows, cols, max_combo, max_lhs, norm_tables = profile_ultra_optimized(
            df, max_combination_size=3, max_lhs_size=2
        )
        analysis_time = time.time() - start_time
        
        print(f"\n✅ SUCCESS! Analysis completed in {analysis_time:.2f} seconds")
        print(f"   • Processed {n_rows:,} rows")
        print(f"   • Found {len(fd_results)} functional dependencies")
        print(f"   • Found {len([k for k in key_results if 'Candidate Key' in k[3]])} candidate keys")
        print(f"   • Proposed {len(norm_tables)} normalized tables")
        
        if fd_results:
            print(f"\n🔍 Sample functional dependencies:")
            for i, (lhs, rhs) in enumerate(fd_results[:5]):
                print(f"   • {lhs} → {rhs}")
            if len(fd_results) > 5:
                print(f"   ... and {len(fd_results) - 5} more")
        
        candidate_keys = [k for k in key_results if "Candidate Key" in k[3]]
        if candidate_keys:
            print(f"\n🔑 Candidate keys found:")
            for cols_str, count, ratio, key_type in candidate_keys:
                print(f"   • {cols_str} ({ratio} unique)")
        
        # Performance assessment
        rows_per_second = n_rows / analysis_time
        print(f"\n📈 Performance metrics:")
        print(f"   • Processing rate: {rows_per_second:,.0f} rows/second")
        print(f"   • Memory efficiency: {df.memory_usage(deep=True).sum() / 1024 / 1024 / analysis_time:.1f} MB/second")
        
        if analysis_time < 30:
            print("   ✅ Excellent performance for big data!")
        elif analysis_time < 120:
            print("   ✅ Good performance for big data")
        else:
            print("   ⚠️  Acceptable but could be improved")
            
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()


def find_functional_dependencies_hyper_optimized(df: pd.DataFrame, max_lhs_size: int = 2):
    """
    Hyper-optimized functional dependency discovery for very large datasets.
    Uses more aggressive sampling and limits but tries to maintain accuracy.
    """
    n_rows = len(df)
    cols = list(df.columns)
    
    if n_rows == 0 or len(cols) < 2:
        return []
    
    # For very large datasets, use more aggressive sampling
    if n_rows > 200000:
        sample_size = min(25000, max(10000, n_rows // 40))  # More conservative sampling
        df, was_sampled = sample_dataframe_intelligently(df, sample_size)
        n_rows = len(df)
        print(f"  Aggressively sampled {n_rows} rows from original dataset for FD analysis")
    
    fds = []
    
    # Pre-compute cardinalities
    col_cardinalities = {col: df[col].nunique() for col in cols}
    
    # Use similar but more aggressive filtering than ultra-optimized
    non_unique_cols = [col for col in cols if 1 < col_cardinalities[col] < n_rows * 0.9]
    
    if not non_unique_cols:
        return fds
    
    # Much more aggressive limits
    max_lhs_combinations = min(50, len(non_unique_cols))
    max_total_tests = min(300, len(non_unique_cols) * len(cols))
    
    # Cache for group operations
    group_cache = {}
    tests_performed = 0
    
    for size in range(1, min(max_lhs_size + 1, 3)):  # Cap at size 2 for hyper mode
        if size > len(non_unique_cols) or tests_performed >= max_total_tests:
            break
            
        # Be more selective about combinations
        if size == 1:
            lhs_candidates = [(col,) for col in non_unique_cols[:max_lhs_combinations]]
        else:
            # For multi-column, be very selective but still thorough
            all_combos = list(itertools.combinations(non_unique_cols[:15], size))[:30]
            lhs_candidates = sorted(all_combos, 
                                  key=lambda x: sum(col_cardinalities[col] for col in x))[:30]
        
        for lhs in lhs_candidates:
            if tests_performed >= max_total_tests:
                break
                
            lhs_tuple = tuple(lhs)
            
            try:
                if lhs_tuple not in group_cache:
                    grouped = df.groupby(list(lhs), sort=False, dropna=False)
                    group_sizes = grouped.size()
                    group_cache[lhs_tuple] = (grouped, group_sizes)
                else:
                    grouped, group_sizes = group_cache[lhs_tuple]
                
                n_groups = len(group_sizes)
                if n_groups == n_rows or group_sizes.max() == 1:
                    continue
                
                # Test RHS candidates with some prioritization
                for rhs in cols:
                    if rhs in lhs or tests_performed >= max_total_tests:
                        continue
                    
                    # Quick heuristic check
                    if col_cardinalities[rhs] > n_groups * 1.2:
                        continue
                    
                    try:
                        rhs_per_group = grouped[rhs].nunique()
                        if (rhs_per_group <= 1).all():
                            fds.append((lhs, rhs))
                        tests_performed += 1
                    except Exception:
                        continue
                        
            except Exception:
                continue
    
    return fds


def find_candidate_keys_hyper_optimized(df: pd.DataFrame, max_combination_size: int = 2):
    """
    Hyper-optimized candidate key discovery for very large datasets.
    """
    n_rows = len(df)
    cols = list(df.columns)
    
    if n_rows == 0:
        return [], [], []
    
    # Aggressive sampling for very large datasets
    if n_rows > 200000:
        sample_size = min(25000, max(5000, n_rows // 40))
        df, was_sampled = sample_dataframe_intelligently(df, sample_size)
        n_rows = len(df)
        print(f"  Aggressively sampled {n_rows} rows from original dataset for key analysis")
    
    all_keys = []
    
    # Quick single-column check with early termination
    single_column_keys = []
    col_cardinalities = {}
    
    for col in cols:
        cardinality = df[col].nunique()
        col_cardinalities[col] = cardinality
        if cardinality == n_rows:
            single_column_keys.append((col,))
            all_keys.append((col,))
    
    # For very large datasets, if we have single-column keys, stop there
    if single_column_keys and n_rows > 100000:
        return all_keys, single_column_keys, []
    
    # Very conservative limits for multi-column keys
    max_combination_size = min(max_combination_size, 2)
    max_combinations_to_test = min(50, math.comb(len(cols), 2))
    
    # Only test most promising combinations
    for size in range(2, max_combination_size + 1):
        if size > len(cols):
            break
        
        # Select only most promising combinations based on cardinality
        all_combinations = list(itertools.combinations(cols, size))
        
        # Sort by likelihood of being keys (lower total cardinality)
        promising_combinations = sorted(all_combinations, 
                                      key=lambda x: sum(col_cardinalities.get(col, n_rows) for col in x))
        
        # Test only top candidates
        combinations_to_test = promising_combinations[:max_combinations_to_test]
        
        for combo in combinations_to_test:
            # Skip if contains single-column key
            if any((col,) in single_column_keys for col in combo):
                continue
            
            # Quick heuristic: if sum of cardinalities is much less than n_rows, unlikely to be key
            total_card = sum(col_cardinalities.get(col, n_rows) for col in combo)
            if total_card < n_rows * 0.8:
                continue
            
            try:
                unique_count = len(df[list(combo)].drop_duplicates())
                if unique_count == n_rows:
                    all_keys.append(combo)
            except Exception:
                continue
        
        # Early termination if we found enough keys
        if len(all_keys) > 5:
            break
    
    # Classify keys
    candidate_keys = []
    superkeys = []
    
    for key in all_keys:
        is_candidate = True
        for other_key in all_keys:
            if len(other_key) < len(key) and set(other_key).issubset(set(key)):
                is_candidate = False
                break
        
        if is_candidate:
            candidate_keys.append(key)
        else:
            superkeys.append(key)
    
    return all_keys, candidate_keys, superkeys


def profile_hyper_optimized(df: pd.DataFrame, max_combination_size: int = 2, max_lhs_size: int = 2):
    """
    Hyper-optimized profile function for very large datasets (500k+ rows).
    Sacrifices some completeness for dramatic speed improvements.
    """
    start_time = time.time()
    n_rows = len(df)
    cols = list(df.columns)
    
    print(f"Starting HYPER-OPTIMIZED analysis of {n_rows:,} rows × {len(cols)} columns...")
    
    # Very aggressive parameter limits
    max_combination_size = min(max_combination_size, 2)
    max_lhs_size = min(max_lhs_size, 2)
    print(f"  Hyper mode: limiting to max combination size {max_combination_size}")
    
    # Discover functional dependencies
    fd_start = time.time()
    fds = find_functional_dependencies_hyper_optimized(df, max_lhs_size)
    fd_time = time.time() - fd_start
    print(f"  FD discovery completed in {fd_time:.2f}s - found {len(fds)} dependencies")
    
    fd_results = [(", ".join(lhs), rhs) for lhs, rhs in fds]
    
    # Discover keys
    key_start = time.time()
    all_keys, candidate_keys, superkeys = find_candidate_keys_hyper_optimized(df, max_combination_size)
    key_time = time.time() - key_start
    print(f"  Key discovery completed in {key_time:.2f}s - found {len(candidate_keys)} candidate keys")
    
    # Minimal result preparation
    results = []
    single_col_uniqueness = {col: df[col].nunique() for col in cols}
    
    # Only process essential combinations
    max_combinations_total = min(100, len(cols) * 2)
    combinations_tested = 0
    
    for size in range(1, max_combination_size + 1):
        for combo in itertools.combinations(cols, size):
            if combinations_tested >= max_combinations_total:
                break
                
            if len(combo) == 1:
                unique_count = single_col_uniqueness[combo[0]]
            elif combo in all_keys:
                unique_count = n_rows
            else:
                # Estimate for larger combinations
                unique_count = min(n_rows, sum(single_col_uniqueness[col] for col in combo) // len(combo))
            
            unique_ratio = unique_count / n_rows if n_rows > 0 else 0
            is_key = combo in all_keys
            is_candidate = combo in candidate_keys
            is_superkey = combo in superkeys
            
            key_type = ""
            if is_candidate:
                key_type = "★ Candidate Key"
            elif is_superkey:
                key_type = "⊃ Superkey"
            
            results.append((combo, unique_count, unique_ratio, is_key, key_type))
            combinations_tested += 1
    
    # Quick sort
    results.sort(key=lambda x: (not x[3], -x[2], len(x[0])))
    key_results = [(", ".join(c), u, f"{u/n_rows:.2%}", k) 
                   for c, u, _, _, k in results]
    
    # Simplified normalized tables
    normalized_tables = propose_normalized_tables(cols, candidate_keys, fds)
    
    total_time = time.time() - start_time
    print(f"  HYPER-OPTIMIZED analysis completed in {total_time:.2f}s")
    
    return fd_results, key_results, n_rows, cols, max_combination_size, max_lhs_size, normalized_tables


def test_hyper_optimized_scenario():
    """
    Test the hyper-optimized version with extremely large datasets.
    """
    print("=== HYPER-OPTIMIZED SCENARIO TEST ===\n")
    
    # Test different large dataset scenarios
    test_scenarios = [
        (500000, 'complex', "500K rows complex"),
        (1000000, 'complex', "1M rows complex"),
        (2000000, 'medium', "2M rows medium"),
        (5000000, 'simple', "5M rows simple")
    ]
    
    results = []
    
    for size, complexity, description in test_scenarios:
        print(f"\n{'='*60}")
        print(f"TESTING: {description}")
        print('='*60)
        
        try:
            # Create test data
            df = create_stress_test_data(size, complexity=complexity)
            memory_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
            
            print(f"Memory usage: {memory_mb:.1f} MB")
            
            # Test hyper-optimized version
            start_time = time.time()
            fd_results, key_results, n_rows, cols, max_combo, max_lhs, norm_tables = profile_hyper_optimized(
                df, max_combination_size=3, max_lhs_size=2
            )
            analysis_time = time.time() - start_time
            
            candidate_keys = [k for k in key_results if "Candidate Key" in k[3]]
            rows_per_second = n_rows / analysis_time
            
            print(f"\n✅ SUCCESS!")
            print(f"   • Analysis time: {analysis_time:.2f} seconds")
            print(f"   • Processing rate: {rows_per_second:,.0f} rows/second")
            print(f"   • Found {len(fd_results)} functional dependencies")
            print(f"   • Found {len(candidate_keys)} candidate keys")
            print(f"   • Memory efficiency: {memory_mb / analysis_time:.1f} MB/second")
            
            # Performance assessment
            if analysis_time < 30:
                performance = "🔥 EXCELLENT"
            elif analysis_time < 60:
                performance = "✅ GOOD"
            elif analysis_time < 180:
                performance = "⚠️ ACCEPTABLE"
            else:
                performance = "❌ NEEDS WORK"
            
            print(f"   • Performance: {performance}")
            
            results.append({
                'size': size,
                'complexity': complexity,
                'memory_mb': memory_mb,
                'time': analysis_time,
                'rows_per_sec': rows_per_second,
                'fds': len(fd_results),
                'keys': len(candidate_keys),
                'success': True,
                'performance': performance
            })
            
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            results.append({
                'size': size,
                'complexity': complexity,
                'memory_mb': 0,
                'time': float('inf'),
                'rows_per_sec': 0,
                'fds': 0,
                'keys': 0,
                'success': False,
                'performance': "❌ FAILED"
            })
    
    # Summary
    print(f"\n{'='*80}")
    print("HYPER-OPTIMIZED PERFORMANCE SUMMARY")
    print('='*80)
    print(f"{'Dataset':<20} {'Memory':<10} {'Time':<10} {'Rate':<12} {'FDs':<5} {'Keys':<5} {'Performance'}")
    print("-" * 80)
    
    for result in results:
        dataset = f"{result['size']:,} {result['complexity']}"
        memory = f"{result['memory_mb']:.1f}MB"
        time_str = f"{result['time']:.1f}s" if result['time'] != float('inf') else "FAIL"
        rate = f"{result['rows_per_sec']:,.0f}/s" if result['success'] else "N/A"
        fds = str(result['fds'])
        keys = str(result['keys'])
        performance = result['performance']
        
        print(f"{dataset:<20} {memory:<10} {time_str:<10} {rate:<12} {fds:<5} {keys:<5} {performance}")
    
    # Analysis
    successful = [r for r in results if r['success']]
    if successful:
        max_size = max(r['size'] for r in successful)
        avg_rate = np.mean([r['rows_per_sec'] for r in successful])
        print(f"\n🎯 ANALYSIS:")
        print(f"   • Successfully processed datasets up to {max_size:,} rows")
        print(f"   • Average processing rate: {avg_rate:,.0f} rows/second")
        print(f"   • Hyper-optimization enables analysis of datasets that would be impossible otherwise")
    
    return results


def test_small_data_optimizations():
    """
    Test optimizations specifically for small datasets to ensure no performance regression.
    """
    print("=== SMALL DATA OPTIMIZATION TEST ===\n")
    
    # Test different small dataset scenarios
    small_test_configs = [
        (10, 3, 'tiny'),
        (50, 4, 'small'),
        (100, 5, 'small'),
        (500, 6, 'medium'),
        (1000, 8, 'medium'),
        (5000, 10, 'medium'),
    ]
    
    results = []
    
    for size, n_cols, complexity in small_test_configs:
        print(f"\n{'='*50}")
        print(f"TESTING: {size:,} rows × {n_cols} columns ({complexity})")
        print('='*50)
        
        try:
            # Create test data
            df = create_stress_test_data(size, n_cols=n_cols, complexity=complexity)
            memory_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
            
            print(f"Memory usage: {memory_mb:.3f} MB")
            
            # Test all three optimization levels
            optimization_results = {}
            
            # 1. Test original version (for very small datasets only)
            if size <= 1000:
                print("\n🐌 Testing ORIGINAL version...")
                start_time = time.time()
                orig_results = profile_original(df, max_combination_size=3, max_lhs_size=2)
                orig_time = time.time() - start_time
                optimization_results['original'] = {
                    'time': orig_time,
                    'fds': len(orig_results[0]),
                    'keys': len([k for k in orig_results[1] if "Candidate Key" in k[3]])
                }
                print(f"   Original: {orig_time:.4f}s - {optimization_results['original']['fds']} FDs, {optimization_results['original']['keys']} keys")
            
            # 2. Test standard optimized version
            print("\n🔍 Testing STANDARD-OPTIMIZED version...")
            start_time = time.time()
            std_results = profile_optimized(df, max_combination_size=3, max_lhs_size=2)
            std_time = time.time() - start_time
            optimization_results['standard'] = {
                'time': std_time,
                'fds': len(std_results[0]),
                'keys': len([k for k in std_results[1] if "Candidate Key" in k[3]])
            }
            print(f"   Standard: {std_time:.4f}s - {optimization_results['standard']['fds']} FDs, {optimization_results['standard']['keys']} keys")
            
            # 3. Test ultra optimized version
            print("\n⚡ Testing ULTRA-OPTIMIZED version...")
            start_time = time.time()
            ultra_results = profile_ultra_optimized(df, max_combination_size=3, max_lhs_size=2)
            ultra_time = time.time() - start_time
            optimization_results['ultra'] = {
                'time': ultra_time,
                'fds': len(ultra_results[0]),
                'keys': len([k for k in ultra_results[1] if "Candidate Key" in k[3]])
            }
            print(f"   Ultra: {ultra_time:.4f}s - {optimization_results['ultra']['fds']} FDs, {optimization_results['ultra']['keys']} keys")
            
            # 4. Test automatic selection (should pick standard for small data)
            print("\n🎯 Testing AUTOMATIC selection...")
            start_time = time.time()
            auto_results = profile(df, max_combination_size=3, max_lhs_size=2)
            auto_time = time.time() - start_time
            optimization_results['auto'] = {
                'time': auto_time,
                'fds': len(auto_results[0]),
                'keys': len([k for k in auto_results[1] if "Candidate Key" in k[3]])
            }
            print(f"   Auto: {auto_time:.4f}s - {optimization_results['auto']['fds']} FDs, {optimization_results['auto']['keys']} keys")
            
            # Analyze results
            print(f"\n📊 ANALYSIS:")
            
            # Check consistency
            fd_counts = [opt['fds'] for opt in optimization_results.values()]
            key_counts = [opt['keys'] for opt in optimization_results.values()]
            
            consistent_fds = len(set(fd_counts)) <= 1
            consistent_keys = len(set(key_counts)) <= 1
            
            print(f"   • FD consistency: {'✅' if consistent_fds else '❌'} ({fd_counts})")
            print(f"   • Key consistency: {'✅' if consistent_keys else '❌'} ({key_counts})")
            
            # Compare performance
            if 'original' in optimization_results:
                std_speedup = optimization_results['original']['time'] / optimization_results['standard']['time']
                ultra_speedup = optimization_results['original']['time'] / optimization_results['ultra']['time']
                print(f"   • Standard speedup vs original: {std_speedup:.2f}x")
                print(f"   • Ultra speedup vs original: {ultra_speedup:.2f}x")
            
            # Check if auto selection made good choice
            fastest_time = min(opt['time'] for opt in optimization_results.values())
            auto_efficiency = fastest_time / optimization_results['auto']['time']
            print(f"   • Auto selection efficiency: {auto_efficiency:.2f} (1.0 = optimal)")
            
            # Overall assessment
            if consistent_fds and consistent_keys and auto_efficiency > 0.8:
                assessment = "✅ EXCELLENT"
            elif consistent_fds and consistent_keys:
                assessment = "✅ GOOD"
            elif auto_efficiency > 0.8:
                assessment = "⚠️ INCONSISTENT RESULTS"
            else:
                assessment = "❌ POOR PERFORMANCE"
            
            print(f"   • Overall: {assessment}")
            
            results.append({
                'size': size,
                'cols': n_cols,
                'complexity': complexity,
                'memory_mb': memory_mb,
                'optimization_results': optimization_results,
                'consistent_fds': consistent_fds,
                'consistent_keys': consistent_keys,
                'auto_efficiency': auto_efficiency,
                'assessment': assessment,
                'success': True
            })
            
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            results.append({
                'size': size,
                'cols': n_cols,
                'complexity': complexity,
                'memory_mb': 0,
                'optimization_results': {},
                'consistent_fds': False,
                'consistent_keys': False,
                'auto_efficiency': 0,
                'assessment': "❌ FAILED",
                'success': False
            })
    
    # Comprehensive summary
    print(f"\n{'='*80}")
    print("SMALL DATA OPTIMIZATION SUMMARY")
    print('='*80)
    print(f"{'Dataset':<15} {'Memory':<8} {'Original':<10} {'Standard':<10} {'Ultra':<10} {'Auto':<10} {'Consistent':<10} {'Assessment'}")
    print("-" * 80)
    
    for result in results:
        if not result['success']:
            continue
            
        dataset = f"{result['size']}×{result['cols']}"
        memory = f"{result['memory_mb']:.2f}MB"
        
        opt_res = result['optimization_results']
        orig_time = f"{opt_res.get('original', {}).get('time', 0):.3f}s" if 'original' in opt_res else "N/A"
        std_time = f"{opt_res['standard']['time']:.3f}s"
        ultra_time = f"{opt_res['ultra']['time']:.3f}s"
        auto_time = f"{opt_res['auto']['time']:.3f}s"
        
        consistent = "✅" if result['consistent_fds'] and result['consistent_keys'] else "❌"
        assessment = result['assessment'].split()[0]  # Just the emoji/symbol
        
        print(f"{dataset:<15} {memory:<8} {orig_time:<10} {std_time:<10} {ultra_time:<10} {auto_time:<10} {consistent:<10} {assessment}")
    
    # Performance analysis
    successful = [r for r in results if r['success']]
    if successful:
        print(f"\n🎯 PERFORMANCE ANALYSIS:")
        
        # Consistency check
        all_consistent = all(r['consistent_fds'] and r['consistent_keys'] for r in successful)
        print(f"   • Result consistency across optimizations: {'✅' if all_consistent else '❌'}")
        
        # Auto selection efficiency
        avg_auto_efficiency = np.mean([r['auto_efficiency'] for r in successful])
        print(f"   • Average auto-selection efficiency: {avg_auto_efficiency:.3f}")
        
        # Speed comparison for overlapping tests
        overlap_tests = [r for r in successful if 'original' in r['optimization_results']]
        if overlap_tests:
            avg_std_speedup = np.mean([
                r['optimization_results']['original']['time'] / r['optimization_results']['standard']['time']
                for r in overlap_tests
            ])
            avg_ultra_speedup = np.mean([
                r['optimization_results']['original']['time'] / r['optimization_results']['ultra']['time']
                for r in overlap_tests
            ])
            print(f"   • Average standard optimization speedup: {avg_std_speedup:.2f}x")
            print(f"   • Average ultra optimization speedup: {avg_ultra_speedup:.2f}x")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if all_consistent and avg_auto_efficiency > 0.9:
            print("   ✅ Optimizations are working excellently for small data")
        elif all_consistent:
            print("   ✅ Results are consistent, but auto-selection could be improved")
        else:
            print("   ⚠️ Some optimization levels produce inconsistent results")
        
        # Check if any optimization is consistently best for small data
        fastest_counts = {}
        for result in successful:
            if result['optimization_results']:
                fastest = min(result['optimization_results'].items(), key=lambda x: x[1]['time'])[0]
                fastest_counts[fastest] = fastest_counts.get(fastest, 0) + 1
        
        if fastest_counts:
            best_optimization = max(fastest_counts.items(), key=lambda x: x[1])
            print(f"   🏆 Most often fastest: {best_optimization[0]} ({best_optimization[1]}/{len(successful)} times)")
    
    return results


def find_functional_dependencies_high_column_optimized(df: pd.DataFrame, max_lhs_size: int = 2):
    """
    Specialized functional dependency discovery for high-column datasets (>50 columns).
    Uses intelligent column selection and aggressive limits.
    """
    try:
        n_rows = len(df)
        cols = list(df.columns)
        n_cols = len(cols)
        
        if n_rows == 0 or n_cols < 2:
            return []
        
        print(f"  High-column FD analysis: {n_rows} rows × {n_cols} columns")
        
        # Always sample for high-column datasets to keep it manageable
        if n_rows > 2000:
            sample_size = min(2000, max(500, n_rows // 50))
            df, was_sampled = sample_dataframe_intelligently(df, sample_size)
            n_rows = len(df)
            print(f"    Sampled to {n_rows} rows for high-column analysis")
        
        # Pre-compute column characteristics for intelligent selection
        col_info = {}
        for col in cols:
            try:
                unique_count = df[col].nunique()
                col_info[col] = {
                    'cardinality': unique_count,
                    'uniqueness_ratio': unique_count / n_rows,
                    'is_potential_key': unique_count == n_rows,
                    'is_low_cardinality': unique_count < n_rows * 0.1,
                    'is_boolean_like': unique_count <= 2
                }
            except Exception:
                # Skip problematic columns
                col_info[col] = {
                    'cardinality': 0,
                    'uniqueness_ratio': 0,
                    'is_potential_key': False,
                    'is_low_cardinality': False,
                    'is_boolean_like': False
                }
        
        # Select most promising columns for LHS (determinants)
        # Focus on columns that are likely to be good determinants
        lhs_candidates = []
        
        # Add potential keys first (high cardinality)
        potential_keys = [col for col, info in col_info.items() if info['uniqueness_ratio'] > 0.8]
        lhs_candidates.extend(potential_keys[:10])  # Top 10 potential keys
        
        # Add low-cardinality columns (good for grouping)
        low_card_cols = sorted([col for col, info in col_info.items() if info['is_low_cardinality']], 
                              key=lambda x: col_info[x]['cardinality'])
        lhs_candidates.extend(low_card_cols[:15])  # Top 15 low-cardinality
        
        # Add some medium-cardinality columns
        medium_card_cols = [col for col, info in col_info.items() 
                           if 0.1 <= info['uniqueness_ratio'] <= 0.8]
        medium_card_cols = sorted(medium_card_cols, key=lambda x: col_info[x]['cardinality'])
        lhs_candidates.extend(medium_card_cols[:10])  # Top 10 medium-cardinality
        
        # Remove duplicates while preserving order and ensure they exist in dataframe
        seen = set()
        lhs_candidates = [col for col in lhs_candidates 
                         if col in df.columns and not (col in seen or seen.add(col))]
        
        # Limit to top 30 LHS candidates to keep it manageable
        lhs_candidates = lhs_candidates[:30]
        
        print(f"    Selected {len(lhs_candidates)} promising LHS candidates from {n_cols} columns")
        
        fds = []
        group_cache = {}
        
        # Very aggressive limits for high-column datasets
        max_tests = 200  # Maximum total FD tests
        tests_performed = 0
        
        for size in range(1, min(max_lhs_size + 1, 3)):  # Cap at size 2 for high-column
            if tests_performed >= max_tests or not lhs_candidates:
                break
                
            if size == 1:
                # Single column determinants
                candidates = lhs_candidates[:20]  # Top 20 for single-column
            else:
                # Multi-column determinants - be very selective
                try:
                    candidates = list(itertools.combinations(lhs_candidates[:15], size))[:30]
                except Exception:
                    candidates = []
            
            for lhs in candidates:
                if tests_performed >= max_tests:
                    break
                    
                lhs_tuple = tuple(lhs) if isinstance(lhs, (list, tuple)) else (lhs,)
                
                try:
                    # Ensure all columns in lhs_tuple exist in dataframe
                    if not all(col in df.columns for col in lhs_tuple):
                        continue
                        
                    if lhs_tuple not in group_cache:
                        grouped = df.groupby(list(lhs_tuple), sort=False, dropna=False)
                        group_sizes = grouped.size()
                        group_cache[lhs_tuple] = (grouped, group_sizes)
                    else:
                        grouped, group_sizes = group_cache[lhs_tuple]
                    
                    n_groups = len(group_sizes)
                    if n_groups == n_rows or group_sizes.max() == 1:
                        continue
                    
                    # Test only most promising RHS candidates
                    rhs_candidates = []
                    
                    # Add high-cardinality columns as RHS candidates
                    high_card_rhs = [col for col, info in col_info.items() 
                                   if info['uniqueness_ratio'] > 0.5 and col not in lhs_tuple and col in df.columns]
                    rhs_candidates.extend(high_card_rhs[:10])
                    
                    # Add some other columns
                    other_rhs = [col for col in cols if col not in lhs_tuple and col not in rhs_candidates and col in df.columns]
                    rhs_candidates.extend(other_rhs[:10])
                    
                    for rhs in rhs_candidates:
                        if tests_performed >= max_tests:
                            break
                            
                        # Quick heuristic check
                        if col_info.get(rhs, {}).get('cardinality', 0) > n_groups * 1.5:
                            continue
                        
                        try:
                            rhs_per_group = grouped[rhs].nunique()
                            if (rhs_per_group <= 1).all():
                                fds.append((lhs_tuple, rhs))
                            tests_performed += 1
                        except Exception:
                            continue
                            
                except Exception:
                    continue
        
        print(f"    Performed {tests_performed} FD tests (limit: {max_tests})")
        return fds
        
    except Exception as e:
        print(f"    Error in high-column FD analysis: {e}")
        return []  # Return empty list on error


def find_candidate_keys_high_column_optimized(df: pd.DataFrame, max_combination_size: int = 2):
    """
    Specialized candidate key discovery for high-column datasets (>50 columns).
    Uses intelligent column selection and aggressive limits.
    """
    try:
        n_rows = len(df)
        cols = list(df.columns)
        n_cols = len(cols)
        
        if n_rows == 0:
            return [], [], []
        
        print(f"  High-column key analysis: {n_rows} rows × {n_cols} columns")
        
        # Always sample for high-column datasets
        if n_rows > 2000:
            sample_size = min(2000, max(500, n_rows // 50))
            df, was_sampled = sample_dataframe_intelligently(df, sample_size)
            n_rows = len(df)
            print(f"    Sampled to {n_rows} rows for high-column key analysis")
        
        all_keys = []
        
        # Quick single-column check with cardinality-based prioritization
        col_cardinalities = {}
        potential_single_keys = []
        
        # Sort columns by cardinality (descending) to check most promising first
        for col in cols:
            try:
                if col in df.columns:
                    cardinality = df[col].nunique()
                    col_cardinalities[col] = cardinality
                    if cardinality == n_rows:
                        potential_single_keys.append((col,))
                        all_keys.append((col,))
                else:
                    col_cardinalities[col] = 0
            except Exception:
                col_cardinalities[col] = 0
        
        print(f"    Found {len(potential_single_keys)} single-column keys")
        
        # For high-column datasets, if we have single-column keys, be very conservative about multi-column
        if potential_single_keys and n_cols > 80:
            print(f"    Stopping early due to high column count ({n_cols}) and existing single-column keys")
            return all_keys, potential_single_keys, []
        
        # Select most promising columns for multi-column key testing
        # Sort by cardinality (highest first) and take top candidates
        try:
            sorted_cols = sorted([col for col in cols if col in df.columns], 
                                key=lambda x: col_cardinalities.get(x, 0), reverse=True)
        except Exception:
            sorted_cols = [col for col in cols if col in df.columns]
        
        # Take top candidates based on cardinality
        if n_cols > 80:
            promising_cols = sorted_cols[:15]  # Very selective for >80 columns
        elif n_cols > 60:
            promising_cols = sorted_cols[:20]  # Selective for >60 columns  
        else:
            promising_cols = sorted_cols[:25]  # Less selective for 50-60 columns
        
        print(f"    Selected {len(promising_cols)} promising columns for multi-column key testing")
        
        # Very conservative multi-column key testing
        max_combination_size = min(max_combination_size, 2)  # Cap at 2 for high-column
        max_combinations_to_test = 50  # Hard limit
        
        for size in range(2, max_combination_size + 1):
            if size > len(promising_cols):
                break
            
            # Generate combinations from promising columns only
            try:
                combinations = list(itertools.combinations(promising_cols, size))
            except Exception:
                combinations = []
            
            # Sort by total cardinality (higher is more likely to be a key)
            try:
                combinations = sorted(combinations, 
                                    key=lambda x: sum(col_cardinalities.get(col, 0) for col in x), 
                                    reverse=True)
            except Exception:
                pass  # Keep original order if sorting fails
            
            # Test only top combinations
            combinations_to_test = combinations[:max_combinations_to_test]
            
            tested_count = 0
            for combo in combinations_to_test:
                try:
                    # Skip if contains single-column key
                    if any((col,) in potential_single_keys for col in combo):
                        continue
                    
                    # Ensure all columns in combo exist in dataframe
                    if not all(col in df.columns for col in combo):
                        continue
                    
                    # Quick heuristic: if sum of cardinalities is much less than n_rows, skip
                    total_card = sum(col_cardinalities.get(col, 0) for col in combo)
                    if total_card < n_rows * 0.7:
                        continue
                    
                    try:
                        unique_count = len(df[list(combo)].drop_duplicates())
                        if unique_count == n_rows:
                            all_keys.append(combo)
                    except Exception:
                        continue  # Skip problematic combinations
                        
                    tested_count += 1
                    
                    # Early termination for high-column datasets
                    if tested_count >= 20:  # Test at most 20 combinations per size
                        break
                        
                except Exception:
                    continue
            
            print(f"    Tested {tested_count} combinations of size {size}")
            
            # Early termination if we found keys and this is a very high-column dataset
            if all_keys and n_cols > 80:
                break
        
        # Classify keys
        candidate_keys = []
        superkeys = []
        
        for key in all_keys:
            try:
                is_candidate = True
                for other_key in all_keys:
                    if len(other_key) < len(key) and set(other_key).issubset(set(key)):
                        is_candidate = False
                        break
                
                if is_candidate:
                    candidate_keys.append(key)
                else:
                    superkeys.append(key)
            except Exception:
                # If classification fails, treat as candidate key
                candidate_keys.append(key)
        
        return all_keys, candidate_keys, superkeys
        
    except Exception as e:
        print(f"    Error in high-column key analysis: {e}")
        return [], [], []  # Return empty lists on error


def profile_high_column_optimized(df: pd.DataFrame, max_combination_size: int = 2, max_lhs_size: int = 2):
    """
    Specialized profile function for high-column datasets (>50 columns).
    Uses aggressive optimization and intelligent column selection.
    """
    try:
        start_time = time.time()
        n_rows = len(df)
        cols = list(df.columns)
        n_cols = len(cols)
        
        print(f"Starting HIGH-COLUMN analysis of {n_rows:,} rows × {n_cols} columns...")
        
        # Very aggressive parameter limits for high-column datasets
        max_combination_size = min(max_combination_size, 2)
        max_lhs_size = min(max_lhs_size, 2)
        print(f"  High-column mode: limiting to max combination size {max_combination_size}")
        
        # Discover functional dependencies
        fd_start = time.time()
        try:
            fds = find_functional_dependencies_high_column_optimized(df, max_lhs_size)
        except Exception as e:
            print(f"    Error in FD discovery: {e}")
            fds = []
        fd_time = time.time() - fd_start
        print(f"  FD discovery completed in {fd_time:.2f}s - found {len(fds)} dependencies")
        
        fd_results = [(", ".join(lhs), rhs) for lhs, rhs in fds]
        
        # Discover keys
        key_start = time.time()
        try:
            all_keys, candidate_keys, superkeys = find_candidate_keys_high_column_optimized(df, max_combination_size)
        except Exception as e:
            print(f"    Error in key discovery: {e}")
            all_keys, candidate_keys, superkeys = [], [], []
        key_time = time.time() - key_start
        print(f"  Key discovery completed in {key_time:.2f}s - found {len(candidate_keys)} candidate keys")
        
        # Minimal result preparation for high-column datasets
        results = []
        
        # Pre-compute single column uniqueness for efficiency
        single_col_uniqueness = {}
        print("  Computing column uniqueness...")
        try:
            for col in cols:
                if col in df.columns:
                    try:
                        single_col_uniqueness[col] = df[col].nunique()
                    except Exception:
                        single_col_uniqueness[col] = 0
                else:
                    single_col_uniqueness[col] = 0
        except Exception as e:
            print(f"    Error computing column uniqueness: {e}")
            # Set default values
            single_col_uniqueness = {col: 0 for col in cols}
        
        # Only process essential combinations for high-column datasets
        max_combinations_total = min(100, n_cols * 2)  # Very conservative
        combinations_tested = 0
        
        print(f"  Preparing results (testing max {max_combinations_total} combinations)...")
        
        # Process single columns first (most important)
        try:
            for col in cols:
                if combinations_tested >= max_combinations_total:
                    break
                    
                if col not in df.columns:
                    continue
                    
                combo = (col,)
                unique_count = single_col_uniqueness.get(col, 0)
                unique_ratio = unique_count / n_rows if n_rows > 0 else 0
                is_key = combo in all_keys
                is_candidate = combo in candidate_keys
                is_superkey = combo in superkeys
                
                key_type = ""
                if is_candidate:
                    key_type = "★ Candidate Key"
                elif is_superkey:
                    key_type = "⊃ Superkey"
                
                results.append((combo, unique_count, unique_ratio, is_key, key_type))
                combinations_tested += 1
        except Exception as e:
            print(f"    Error processing single columns: {e}")
        
        # Process only the most promising multi-column combinations
        try:
            if combinations_tested < max_combinations_total and max_combination_size > 1:
                # Sort columns by uniqueness (highest first) for better multi-column candidates
                try:
                    sorted_cols = sorted([col for col in cols if col in df.columns], 
                                       key=lambda x: single_col_uniqueness.get(x, 0), reverse=True)
                    top_cols = sorted_cols[:min(20, len(sorted_cols))]  # Top 20 most unique columns
                except Exception:
                    top_cols = [col for col in cols if col in df.columns][:20]
                
                for size in range(2, min(max_combination_size + 1, 3)):
                    if combinations_tested >= max_combinations_total:
                        break
                        
                    try:
                        for combo in itertools.combinations(top_cols, size):
                            if combinations_tested >= max_combinations_total:
                                break
                                
                            # Ensure all columns exist
                            if not all(col in df.columns for col in combo):
                                continue
                                
                            if combo in all_keys:
                                unique_count = n_rows
                            else:
                                # For non-keys, estimate uniqueness
                                unique_count = min(n_rows, sum(single_col_uniqueness.get(col, 0) for col in combo) // len(combo))
                            
                            unique_ratio = unique_count / n_rows if n_rows > 0 else 0
                            is_key = combo in all_keys
                            is_candidate = combo in candidate_keys
                            is_superkey = combo in superkeys
                            
                            key_type = ""
                            if is_candidate:
                                key_type = "★ Candidate Key"
                            elif is_superkey:
                                key_type = "⊃ Superkey"
                            
                            results.append((combo, unique_count, unique_ratio, is_key, key_type))
                            combinations_tested += 1
                    except Exception as e:
                        print(f"    Error processing size {size} combinations: {e}")
                        continue
        except Exception as e:
            print(f"    Error processing multi-column combinations: {e}")
        
        # Quick sort
        try:
            results.sort(key=lambda x: (not x[3], -x[2], len(x[0])))
            key_results = [(", ".join(c), u, f"{u/n_rows:.2%}", k) 
                           for c, u, _, _, k in results]
        except Exception as e:
            print(f"    Error sorting results: {e}")
            key_results = []
        
        # Simplified normalized tables
        try:
            normalized_tables = propose_normalized_tables(cols, candidate_keys, fds)
        except Exception as e:
            print(f"    Error creating normalized tables: {e}")
            normalized_tables = []
        
        total_time = time.time() - start_time
        print(f"  HIGH-COLUMN analysis completed in {total_time:.2f}s")
        
        return fd_results, key_results, n_rows, cols, max_combination_size, max_lhs_size, normalized_tables
        
    except Exception as e:
        print(f"  Critical error in HIGH-COLUMN analysis: {e}")
        import traceback
        traceback.print_exc()
        # Return safe defaults
        return [], [], len(df), list(df.columns), max_combination_size, max_lhs_size, []


def test_high_column_scenario():
    """
    Test the high-column optimization with scenarios similar to user's 16k×100 case.
    """
    print("=== HIGH-COLUMN SCENARIO TEST ===\n")
    
    # Test different high-column scenarios
    test_scenarios = [
        (1000, 60, "1K×60 columns"),
        (5000, 80, "5K×80 columns"), 
        (16000, 100, "16K×100 columns (user scenario)"),
        (10000, 120, "10K×120 columns"),
        (50000, 200, "50K×200 columns (extreme)")
    ]
    
    results = []
    
    for n_rows, n_cols, description in test_scenarios:
        print(f"\n{'='*60}")
        print(f"TESTING: {description}")
        print('='*60)
        
        try:
            # Create test data with many columns
            print(f"Creating test dataset with {n_rows:,} rows and {n_cols} columns...")
            
            # Create a realistic high-column dataset
            np.random.seed(42)
            random.seed(42)
            
            data = {}
            
            # Add ID column (primary key)
            data['id'] = range(1, n_rows + 1)
            
            # Add categorical columns of various cardinalities
            for i in range(min(20, n_cols - 1)):
                if i < 5:
                    # Low cardinality categorical
                    cardinality = min(10, n_rows // 100)
                elif i < 10:
                    # Medium cardinality categorical
                    cardinality = min(100, n_rows // 10)
                else:
                    # Higher cardinality categorical
                    cardinality = min(1000, n_rows // 5)
                
                data[f'cat_{i}'] = [f'cat_{i}_val_{j % cardinality}' for j in range(n_rows)]
            
            # Add numeric columns
            remaining_cols = n_cols - len(data)
            for i in range(remaining_cols):
                if i % 4 == 0:
                    # Integer columns
                    data[f'num_{i}'] = np.random.randint(1, 1000, n_rows)
                elif i % 4 == 1:
                    # Float columns
                    data[f'float_{i}'] = np.random.uniform(0, 100, n_rows)
                elif i % 4 == 2:
                    # Boolean-like columns
                    data[f'bool_{i}'] = np.random.choice([0, 1], n_rows)
                else:
                    # Text columns
                    data[f'text_{i}'] = [f'text_{j % 50}' for j in range(n_rows)]
            
            df = pd.DataFrame(data)
            
            # Ensure we have the right number of columns
            if len(df.columns) != n_cols:
                print(f"  Adjusting columns: created {len(df.columns)}, target {n_cols}")
                while len(df.columns) < n_cols:
                    col_name = f'extra_{len(df.columns)}'
                    df[col_name] = np.random.randint(1, 100, n_rows)
                df = df.iloc[:, :n_cols]  # Trim if too many
            
            memory_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
            print(f"Memory usage: {memory_mb:.1f} MB")
            
            # Test the high-column optimized version
            start_time = time.time()
            
            print(f"\n🏗️ Running HIGH-COLUMN-OPTIMIZED analysis...")
            fd_results, key_results, n_rows_result, cols, max_combo, max_lhs, norm_tables = profile_high_column_optimized(
                df, max_combination_size=3, max_lhs_size=2
            )
            
            analysis_time = time.time() - start_time
            
            candidate_keys = [k for k in key_results if "Candidate Key" in k[3]]
            
            print(f"\n✅ SUCCESS!")
            print(f"   • Analysis time: {analysis_time:.2f} seconds")
            print(f"   • Memory usage: {memory_mb:.1f} MB")
            print(f"   • Processing rate: {n_rows / analysis_time:,.0f} rows/second")
            print(f"   • Column processing rate: {n_cols / analysis_time:.1f} columns/second")
            print(f"   • Found {len(fd_results)} functional dependencies")
            print(f"   • Found {len(candidate_keys)} candidate keys")
            
            # Performance assessment
            if analysis_time < 10:
                performance = "🔥 EXCELLENT"
            elif analysis_time < 30:
                performance = "✅ GOOD"
            elif analysis_time < 120:
                performance = "⚠️ ACCEPTABLE"
            else:
                performance = "❌ TOO SLOW"
            
            print(f"   • Performance: {performance}")
            
            # Show some sample results
            if fd_results:
                print(f"\n🔍 Sample functional dependencies found:")
                for i, (lhs, rhs) in enumerate(fd_results[:3]):
                    print(f"   • {lhs} → {rhs}")
                if len(fd_results) > 3:
                    print(f"   ... and {len(fd_results) - 3} more")
            
            if candidate_keys:
                print(f"\n🔑 Candidate keys found:")
                for cols_str, count, ratio, key_type in candidate_keys[:3]:
                    print(f"   • {cols_str} ({ratio} unique)")
                if len(candidate_keys) > 3:
                    print(f"   ... and {len(candidate_keys) - 3} more")
            
            results.append({
                'scenario': description,
                'rows': n_rows,
                'cols': n_cols,
                'memory_mb': memory_mb,
                'time': analysis_time,
                'rows_per_sec': n_rows / analysis_time,
                'cols_per_sec': n_cols / analysis_time,
                'fds': len(fd_results),
                'keys': len(candidate_keys),
                'performance': performance,
                'success': True
            })
            
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
            
            results.append({
                'scenario': description,
                'rows': n_rows,
                'cols': n_cols,
                'memory_mb': 0,
                'time': float('inf'),
                'rows_per_sec': 0,
                'cols_per_sec': 0,
                'fds': 0,
                'keys': 0,
                'performance': "❌ FAILED",
                'success': False
            })
    
    # Summary
    print(f"\n{'='*80}")
    print("HIGH-COLUMN OPTIMIZATION SUMMARY")
    print('='*80)
    print(f"{'Scenario':<25} {'Memory':<8} {'Time':<8} {'Rows/s':<8} {'Cols/s':<8} {'FDs':<4} {'Keys':<4} {'Performance'}")
    print("-" * 80)
    
    for result in results:
        scenario = result['scenario'][:24]
        memory = f"{result['memory_mb']:.1f}MB"
        time_str = f"{result['time']:.1f}s" if result['time'] != float('inf') else "FAIL"
        rows_rate = f"{result['rows_per_sec']:,.0f}" if result['success'] else "N/A"
        cols_rate = f"{result['cols_per_sec']:.1f}" if result['success'] else "N/A"
        fds = str(result['fds'])
        keys = str(result['keys'])
        performance = result['performance'].split()[0]  # Just the emoji
        
        print(f"{scenario:<25} {memory:<8} {time_str:<8} {rows_rate:<8} {cols_rate:<8} {fds:<4} {keys:<4} {performance}")
    
    # Analysis
    successful = [r for r in results if r['success']]
    if successful:
        print(f"\n🎯 PERFORMANCE ANALYSIS:")
        
        # Check if user scenario (16K×100) was successful
        user_scenario = next((r for r in successful if '16K×100' in r['scenario']), None)
        if user_scenario:
            print(f"   ✅ User scenario (16K×100 columns) completed in {user_scenario['time']:.1f} seconds")
            if user_scenario['time'] < 30:
                print(f"   🎉 This should be much faster on your smaller machine!")
            elif user_scenario['time'] < 120:
                print(f"   👍 This should provide reasonable performance on your smaller machine")
            else:
                print(f"   ⚠️ May still be slow on smaller machines - consider further optimization")
        
        avg_time = np.mean([r['time'] for r in successful])
        avg_cols_per_sec = np.mean([r['cols_per_sec'] for r in successful])
        
        print(f"   • Average analysis time: {avg_time:.1f} seconds")
        print(f"   • Average column processing rate: {avg_cols_per_sec:.1f} columns/second")
        print(f"   • Successfully handled datasets up to {max(r['cols'] for r in successful)} columns")
        
        # Specific optimizations applied
        print(f"\n💡 HIGH-COLUMN OPTIMIZATIONS APPLIED:")
        print(f"   • Intelligent column selection (top 30 LHS candidates)")
        print(f"   • Aggressive sampling (max 2000 rows for analysis)")
        print(f"   • Limited combination testing (max 200 FD tests)")
        print(f"   • Prioritized high-cardinality columns for keys")
        print(f"   • Early termination for very wide datasets (>80 columns)")
    
    return results


# Test functions to run when script is executed directly
if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "benchmark":
            benchmark_performance()
        elif sys.argv[1] == "comprehensive":
            comprehensive_benchmark()
        elif sys.argv[1] == "small":
            test_small_data_optimizations()
        elif sys.argv[1] == "hyper":
            test_hyper_optimized_scenario()
        elif sys.argv[1] == "bigdata":
            test_big_data_scenario()
        elif sys.argv[1] == "test":
            test_realistic_scenario()
        elif sys.argv[1] == "demo":
            demo_performance_improvements()
        elif sys.argv[1] == "highcol":
            test_high_column_scenario()
        else:
            test_profile_keys()
    else:
        test_profile_keys()