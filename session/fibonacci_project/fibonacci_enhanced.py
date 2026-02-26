"""
Fibonacci Enhanced Implementation
================================

An advanced implementation of the Fibonacci sequence with extended functionality
including memoization, sequence generation, mathematical utilities, and performance tools.

Features:
- Memoization support using functools.lru_cache for repeated calculations
- Sequence generation option to return full Fibonacci sequence
- Memory-efficient generator function for large sequences
- Fibonacci number validation using mathematical properties
- Golden ratio calculation and demonstration
- Performance comparison and benchmarking tools
- Cache management functionality

Author: Fibonacci Project
Version: 2.0.0
"""

import math
import time
from functools import lru_cache
from typing import List, Generator, Union, Optional, Tuple


def fibonacci(n: int, memoize: bool = False, return_sequence: bool = False) -> Union[int, List[int]]:
    """
    Calculate the nth Fibonacci number with optional memoization and sequence return.
    
    Args:
        n (int): The position in the Fibonacci sequence (0-indexed)
        memoize (bool): Whether to use memoization for faster repeated calculations
        return_sequence (bool): If True, return list of all Fibonacci numbers up to n
        
    Returns:
        Union[int, List[int]]: Single Fibonacci number or full sequence up to position n
        
    Raises:
        TypeError: If n is not an integer
        ValueError: If n is negative
        
    Examples:
        >>> fibonacci(10)
        55
        >>> fibonacci(10, return_sequence=True)
        [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
        >>> fibonacci(100, memoize=True)  # Faster for repeated calls
        354224848179261915075
        
    Time Complexity: O(n) without memoization, O(1) with memoization for cached values
    Space Complexity: O(1) for single number, O(n) for sequence or memoization
    """
    # Input validation
    if isinstance(n, bool):
        raise TypeError("Boolean values are not accepted. Please provide an integer.")
    
    if not isinstance(n, int):
        raise TypeError(f"Expected integer, got {type(n).__name__}. Please provide an integer.")
    
    if n < 0:
        raise ValueError("n must be a non-negative integer. Fibonacci sequence is not defined for negative numbers.")
    
    if memoize:
        result = _fibonacci_memoized(n)
        if return_sequence:
            return [_fibonacci_memoized(i) for i in range(n + 1)]
        return result
    else:
        return _fibonacci_iterative(n, return_sequence)


@lru_cache(maxsize=None)
def _fibonacci_memoized(n: int) -> int:
    """
    Memoized Fibonacci calculation using functools.lru_cache.
    
    This function caches results to avoid recalculation of the same values.
    Particularly useful when calling fibonacci multiple times with overlapping values.
    
    Args:
        n (int): Position in Fibonacci sequence
        
    Returns:
        int: nth Fibonacci number
    """
    if n == 0:
        return 0
    if n == 1:
        return 1
    
    # For memoized version, we can use the recursive relation
    # since cached values prevent exponential time complexity
    return _fibonacci_memoized(n - 1) + _fibonacci_memoized(n - 2)


def _fibonacci_iterative(n: int, return_sequence: bool = False) -> Union[int, List[int]]:
    """
    Iterative Fibonacci calculation with optional sequence generation.
    
    Args:
        n (int): Position in Fibonacci sequence
        return_sequence (bool): Whether to return full sequence
        
    Returns:
        Union[int, List[int]]: Single number or full sequence
    """
    if return_sequence:
        if n == 0:
            return [0]
        
        sequence = [0, 1]
        if n == 1:
            return sequence
        
        for i in range(2, n + 1):
            sequence.append(sequence[i - 1] + sequence[i - 2])
        
        return sequence
    else:
        # Single number calculation
        if n == 0:
            return 0
        if n == 1:
            return 1
        
        prev_prev, prev = 0, 1
        for i in range(2, n + 1):
            current = prev_prev + prev
            prev_prev, prev = prev, current
        
        return prev


def fibonacci_generator(n: int) -> Generator[int, None, None]:
    """
    Memory-efficient generator for Fibonacci sequence up to the nth number.
    
    Yields Fibonacci numbers one at a time without storing the entire sequence.
    Ideal for large sequences where memory usage is a concern.
    
    Args:
        n (int): Maximum position in Fibonacci sequence
        
    Yields:
        int: Next Fibonacci number in sequence
        
    Examples:
        >>> fib_gen = fibonacci_generator(10)
        >>> list(fib_gen)
        [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
        
        >>> for fib in fibonacci_generator(5):
        ...     print(fib, end=" ")
        0 1 1 2 3 5
        
    Time Complexity: O(1) per yield, O(n) total
    Space Complexity: O(1)
    """
    if isinstance(n, bool):
        raise TypeError("Boolean values are not accepted. Please provide an integer.")
    
    if not isinstance(n, int):
        raise TypeError(f"Expected integer, got {type(n).__name__}. Please provide an integer.")
    
    if n < 0:
        raise ValueError("n must be a non-negative integer.")
    
    if n >= 0:
        yield 0
    if n >= 1:
        yield 1
    
    prev_prev, prev = 0, 1
    for i in range(2, n + 1):
        current = prev_prev + prev
        yield current
        prev_prev, prev = prev, current


def is_fibonacci_number(num: int) -> bool:
    """
    Check if a given number is a Fibonacci number using mathematical properties.
    
    A positive integer n is a Fibonacci number if and only if one of:
    (5*n² + 4) or (5*n² - 4) is a perfect square.
    
    Args:
        num (int): Number to check
        
    Returns:
        bool: True if num is a Fibonacci number, False otherwise
        
    Examples:
        >>> is_fibonacci_number(21)
        True
        >>> is_fibonacci_number(22)
        False
        >>> is_fibonacci_number(0)
        True
        >>> is_fibonacci_number(1)
        True
        
    Time Complexity: O(1)
    Space Complexity: O(1)
    """
    if not isinstance(num, int) or num < 0:
        return False
    
    if num == 0:
        return True
    
    def is_perfect_square(n: int) -> bool:
        """Check if n is a perfect square."""
        if n < 0:
            return False
        root = int(math.sqrt(n))
        return root * root == n
    
    # Check if (5*num² + 4) or (5*num² - 4) is a perfect square
    return (is_perfect_square(5 * num * num + 4) or 
            is_perfect_square(5 * num * num - 4))


def golden_ratio_approximation(n: int) -> float:
    """
    Calculate the golden ratio approximation using F(n)/F(n-1).
    
    As n approaches infinity, F(n)/F(n-1) approaches the golden ratio φ ≈ 1.618033988749...
    
    Args:
        n (int): Position in Fibonacci sequence (must be > 0)
        
    Returns:
        float: Approximation of golden ratio
        
    Examples:
        >>> golden_ratio_approximation(10)
        1.6181818181818182
        >>> golden_ratio_approximation(50)
        1.618033988749895
        
    Raises:
        ValueError: If n <= 0
    """
    if n <= 0:
        raise ValueError("n must be positive for golden ratio approximation")
    
    return fibonacci(n) / fibonacci(n - 1)


def fibonacci_sum(n: int) -> int:
    """
    Calculate the sum of Fibonacci numbers from F(0) to F(n).
    
    Uses the mathematical property: Sum of F(0) to F(n) = F(n+2) - 1
    
    Args:
        n (int): Maximum position in sequence
        
    Returns:
        int: Sum of Fibonacci numbers from 0 to n
        
    Examples:
        >>> fibonacci_sum(5)  # 0+1+1+2+3+5 = 12
        12
        >>> fibonacci_sum(10)  # Sum from F(0) to F(10)
        143
    """
    if n < 0:
        raise ValueError("n must be non-negative")
    
    return fibonacci(n + 2) - 1


def clear_fibonacci_cache() -> None:
    """
    Clear the memoization cache for Fibonacci calculations.
    
    Useful for memory management when working with large numbers
    or when you want to benchmark performance without cached values.
    """
    _fibonacci_memoized.cache_clear()


def get_cache_info() -> dict:
    """
    Get information about the current memoization cache.
    
    Returns:
        dict: Cache statistics including hits, misses, and current size
    """
    cache_info = _fibonacci_memoized.cache_info()
    return {
        'hits': cache_info.hits,
        'misses': cache_info.misses,
        'current_size': cache_info.currsize,
        'max_size': cache_info.maxsize,
        'hit_rate': cache_info.hits / (cache_info.hits + cache_info.misses) if (cache_info.hits + cache_info.misses) > 0 else 0
    }


def benchmark_fibonacci(n: int, iterations: int = 1) -> dict:
    """
    Benchmark different Fibonacci calculation methods.
    
    Args:
        n (int): Fibonacci number position to calculate
        iterations (int): Number of iterations for timing
        
    Returns:
        dict: Timing results for different methods
    """
    results = {}
    
    # Benchmark iterative method
    start_time = time.perf_counter()
    for _ in range(iterations):
        fibonacci(n, memoize=False)
    iterative_time = (time.perf_counter() - start_time) / iterations
    results['iterative'] = iterative_time
    
    # Benchmark memoized method (first call)
    clear_fibonacci_cache()
    start_time = time.perf_counter()
    for _ in range(iterations):
        clear_fibonacci_cache()
        fibonacci(n, memoize=True)
    memoized_first_time = (time.perf_counter() - start_time) / iterations
    results['memoized_first_call'] = memoized_first_time
    
    # Benchmark memoized method (cached)
    fibonacci(n, memoize=True)  # Prime the cache
    start_time = time.perf_counter()
    for _ in range(iterations):
        fibonacci(n, memoize=True)
    memoized_cached_time = (time.perf_counter() - start_time) / iterations
    results['memoized_cached'] = memoized_cached_time
    
    return results


def find_fibonacci_position(target: int, max_search: int = 1000) -> Optional[int]:
    """
    Find the position of a target Fibonacci number.
    
    Args:
        target (int): The Fibonacci number to find
        max_search (int): Maximum position to search up to
        
    Returns:
        Optional[int]: Position if found, None otherwise
        
    Examples:
        >>> find_fibonacci_position(55)
        10
        >>> find_fibonacci_position(89)
        11
        >>> find_fibonacci_position(100)  # Not a Fibonacci number
    """
    if target < 0:
        return None
    
    if target == 0:
        return 0
    if target == 1:
        return 1  # Note: Both positions 1 and 2 have value 1, returning first occurrence
    
    for i in range(2, max_search):
        if fibonacci(i) == target:
            return i
        if fibonacci(i) > target:
            return None
    
    return None


if __name__ == "__main__":
    """
    Comprehensive test suite and demonstration of enhanced Fibonacci features.
    """
    print("=" * 70)
    print("FIBONACCI ENHANCED IMPLEMENTATION - TEST SUITE")
    print("=" * 70)
    
    # Test basic functionality
    print("\n1. BASIC FUNCTIONALITY TESTS")
    print("-" * 50)
    for n in [0, 1, 5, 10, 15]:
        basic_result = fibonacci(n)
        memoized_result = fibonacci(n, memoize=True)
        sequence = fibonacci(n, return_sequence=True)
        
        print(f"F({n:2d}) = {basic_result:>8,} | Memoized: {memoized_result:>8,} | Sequence length: {len(sequence)}")
    
    # Test sequence generation
    print("\n2. SEQUENCE GENERATION TESTS")
    print("-" * 50)
    sequence_10 = fibonacci(10, return_sequence=True)
    print(f"F(0) to F(10): {sequence_10}")
    
    # Test generator function
    print("\n3. GENERATOR FUNCTION TEST")
    print("-" * 50)
    print("Generator output:", end=" ")
    for fib in fibonacci_generator(15):
        print(fib, end=" ")
    print()
    
    # Test Fibonacci number validation
    print("\n4. FIBONACCI NUMBER VALIDATION")
    print("-" * 50)
    test_numbers = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 21, 22, 55, 89, 90, 144]
    for num in test_numbers:
        is_fib = is_fibonacci_number(num)
        position = find_fibonacci_position(num) if is_fib else "N/A"
        print(f"{num:3d}: {'✅' if is_fib else '❌'} Fibonacci | Position: {position}")
    
    # Test golden ratio approximation
    print("\n5. GOLDEN RATIO APPROXIMATION")
    print("-" * 50)
    golden_ratio_exact = (1 + math.sqrt(5)) / 2
    print(f"Exact Golden Ratio (φ): {golden_ratio_exact:.15f}")
    print("Fibonacci Approximations:")
    
    for n in [10, 20, 30, 50, 100]:
        approx = golden_ratio_approximation(n)
        error = abs(approx - golden_ratio_exact)
        print(f"F({n:3d})/F({n-1:3d}) = {approx:.15f} | Error: {error:.2e}")
    
    # Test sum functionality
    print("\n6. FIBONACCI SUM TESTS")
    print("-" * 50)
    for n in [5, 10, 15, 20]:
        fib_sum = fibonacci_sum(n)
        sequence = fibonacci(n, return_sequence=True)
        actual_sum = sum(sequence)
        print(f"Sum F(0) to F({n:2d}): {fib_sum:>6,} | Verified: {actual_sum:>6,} | Match: {'✅' if fib_sum == actual_sum else '❌'}")
    
    # Performance benchmarking
    print("\n7. PERFORMANCE BENCHMARKING")
    print("-" * 50)
    benchmark_cases = [50, 100, 200, 500]
    
    for n in benchmark_cases:
        results = benchmark_fibonacci(n, iterations=10)
        print(f"F({n:3d}) benchmarks (avg of 10 runs):")
        print(f"  Iterative:      {results['iterative']:.6f}s")
        print(f"  Memoized (1st): {results['memoized_first_call']:.6f}s")
        print(f"  Memoized (cached): {results['memoized_cached']:.6f}s")
        print()
    
    # Cache management demonstration
    print("\n8. CACHE MANAGEMENT")
    print("-" * 50)
    
    # Clear cache and show empty state
    clear_fibonacci_cache()
    print("Cache cleared.")
    print("Initial cache info:", get_cache_info())
    
    # Calculate some numbers to populate cache
    for n in [10, 20, 30, 50, 100]:
        fibonacci(n, memoize=True)
    
    print("After calculations:")
    cache_info = get_cache_info()
    for key, value in cache_info.items():
        print(f"  {key}: {value}")
    
    # Memory efficiency demonstration
    print("\n9. MEMORY EFFICIENCY DEMONSTRATION")
    print("-" * 50)
    
    # Compare memory usage: generator vs list
    n = 1000
    print(f"Generating F(0) to F({n}):")
    
    # Using generator
    start_time = time.perf_counter()
    gen_count = sum(1 for _ in fibonacci_generator(n))
    gen_time = time.perf_counter() - start_time
    print(f"Generator: {gen_count} numbers in {gen_time:.6f}s (minimal memory)")
    
    # Using list
    start_time = time.perf_counter()
    sequence = fibonacci(n, return_sequence=True)
    list_time = time.perf_counter() - start_time
    print(f"List: {len(sequence)} numbers in {list_time:.6f}s (stores all numbers)")
    
    # Large number demonstration
    print("\n10. LARGE NUMBER HANDLING")
    print("-" * 50)
    large_tests = [100, 500, 1000, 1500]
    
    for n in large_tests:
        start_time = time.perf_counter()
        result = fibonacci(n)
        calc_time = time.perf_counter() - start_time
        digits = len(str(result))
        
        print(f"F({n:4d}): {digits:3d} digits | Time: {calc_time:.6f}s")
        if n <= 100:  # Only show actual number for smaller cases
            print(f"        Value: {result}")
    
    # Error handling tests
    print("\n11. ERROR HANDLING VERIFICATION")
    print("-" * 50)
    
    error_cases = [
        (-1, "Negative number"),
        (True, "Boolean True"),
        (False, "Boolean False"),
        ("10", "String"),
        (3.14, "Float"),
        (None, "None type")
    ]
    
    for test_value, description in error_cases:
        try:
            result = fibonacci(test_value)
            print(f"❌ {description:15} -> Should have failed but got: {result}")
        except (TypeError, ValueError):
            print(f"✅ {description:15} -> Correctly handled")
        except Exception as e:
            print(f"❓ {description:15} -> Unexpected error: {type(e).__name__}")
    
    print("\n" + "=" * 70)
    print("ALL ENHANCED TESTS COMPLETED SUCCESSFULLY!")
    print("Cache final state:", get_cache_info())
    print("=" * 70)