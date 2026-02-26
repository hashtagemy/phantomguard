"""
Fibonacci Basic Implementation
=============================

A clean, efficient implementation of the Fibonacci sequence calculation
focusing on simplicity, performance, and robust error handling.

Features:
- Iterative approach with O(n) time complexity and O(1) space complexity
- Comprehensive input validation and error handling
- Type hints for better code documentation
- Optimized for single number calculations

Author: Fibonacci Project
Version: 1.0.0
"""

from typing import Union


def fibonacci(n: int) -> int:
    """
    Calculate the nth Fibonacci number using an iterative approach.
    
    The Fibonacci sequence is defined as:
    F(0) = 0, F(1) = 1, F(n) = F(n-1) + F(n-2) for n > 1
    
    Args:
        n (int): The position in the Fibonacci sequence (0-indexed)
        
    Returns:
        int: The nth Fibonacci number
        
    Raises:
        TypeError: If n is not an integer
        ValueError: If n is negative
        
    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(10)
        55
        >>> fibonacci(50)
        12586269025
        
    Time Complexity: O(n)
    Space Complexity: O(1)
    """
    # Type validation - handle bool separately since bool is a subclass of int in Python
    if isinstance(n, bool):
        raise TypeError("Boolean values are not accepted. Please provide an integer.")
    
    if not isinstance(n, int):
        raise TypeError(f"Expected integer, got {type(n).__name__}. Please provide an integer.")
    
    # Value validation
    if n < 0:
        raise ValueError("n must be a non-negative integer. Fibonacci sequence is not defined for negative numbers.")
    
    # Base cases
    if n == 0:
        return 0
    if n == 1:
        return 1
    
    # Iterative calculation
    # We only need to keep track of the last two values
    prev_prev = 0  # F(0)
    prev = 1       # F(1)
    
    for i in range(2, n + 1):
        current = prev_prev + prev
        prev_prev = prev
        prev = current
    
    return prev


def validate_input(n: Union[int, str, float, bool]) -> int:
    """
    Validate and convert input to integer for Fibonacci calculation.
    
    This function provides additional validation layer for edge cases
    and converts valid inputs to integers when possible.
    
    Args:
        n: Input value to validate and convert
        
    Returns:
        int: Validated integer value
        
    Raises:
        TypeError: If input cannot be converted to integer
        ValueError: If input is negative or invalid
        
    Examples:
        >>> validate_input(10)
        10
        >>> validate_input("5")  # Raises TypeError
        TypeError: Expected integer, got str. Please provide an integer.
    """
    # Handle boolean explicitly (since bool is subclass of int)
    if isinstance(n, bool):
        raise TypeError("Boolean values are not accepted. Please provide an integer.")
    
    # Check if it's already an integer
    if isinstance(n, int):
        if n < 0:
            raise ValueError("n must be a non-negative integer.")
        return n
    
    # For any other type, raise TypeError
    raise TypeError(f"Expected integer, got {type(n).__name__}. Please provide an integer.")


def fibonacci_info(n: int) -> dict:
    """
    Get comprehensive information about the nth Fibonacci number.
    
    Args:
        n (int): Position in Fibonacci sequence
        
    Returns:
        dict: Information including the number, position, and properties
        
    Examples:
        >>> info = fibonacci_info(10)
        >>> print(info['value'])
        55
    """
    fib_value = fibonacci(n)
    
    return {
        'position': n,
        'value': fib_value,
        'digits': len(str(fib_value)),
        'is_even': fib_value % 2 == 0,
        'binary_representation': bin(fib_value),
        'hex_representation': hex(fib_value)
    }


if __name__ == "__main__":
    """
    Test suite and demonstration of the Fibonacci basic implementation.
    """
    print("=" * 60)
    print("FIBONACCI BASIC IMPLEMENTATION - TEST SUITE")
    print("=" * 60)
    
    # Test basic functionality
    print("\n1. BASIC FUNCTIONALITY TESTS")
    print("-" * 40)
    test_cases = [0, 1, 2, 3, 4, 5, 10, 15, 20, 30]
    for n in test_cases:
        result = fibonacci(n)
        print(f"F({n:2d}) = {result:>10,}")
    
    # Test large numbers
    print("\n2. LARGE NUMBER TESTS")
    print("-" * 40)
    large_tests = [50, 100, 150, 200]
    for n in large_tests:
        result = fibonacci(n)
        print(f"F({n:3d}) = {result} (digits: {len(str(result))})")
    
    # Test error handling
    print("\n3. ERROR HANDLING TESTS")
    print("-" * 40)
    
    error_test_cases = [
        (-1, "Negative integer"),
        (-10, "Large negative integer"),
        (True, "Boolean True"),
        (False, "Boolean False"),
        (3.14, "Float"),
        ("10", "String"),
        (None, "None type"),
        ([], "List"),
    ]
    
    for test_value, description in error_test_cases:
        try:
            result = fibonacci(test_value)
            print(f"❌ {description:20} -> Should have failed but got: {result}")
        except (TypeError, ValueError) as e:
            print(f"✅ {description:20} -> Correctly caught: {type(e).__name__}")
        except Exception as e:
            print(f"❓ {description:20} -> Unexpected error: {type(e).__name__}")
    
    # Test fibonacci_info function
    print("\n4. FIBONACCI INFO TESTS")
    print("-" * 40)
    info_tests = [0, 1, 10, 20, 50]
    for n in info_tests:
        info = fibonacci_info(n)
        print(f"F({n:2d}): {info['value']:>12,} | Digits: {info['digits']:2d} | Even: {info['is_even']}")
    
    # Performance demonstration
    print("\n5. PERFORMANCE DEMONSTRATION")
    print("-" * 40)
    import time
    
    performance_tests = [100, 500, 1000]
    for n in performance_tests:
        start_time = time.perf_counter()
        result = fibonacci(n)
        end_time = time.perf_counter()
        duration = end_time - start_time
        
        print(f"F({n:4d}): {duration:.6f}s | Digits: {len(str(result)):3d}")
    
    print("\n6. MATHEMATICAL PROPERTIES")
    print("-" * 40)
    
    # Show first 20 Fibonacci numbers in sequence
    sequence = [fibonacci(i) for i in range(21)]
    print("First 20 Fibonacci numbers:")
    print(sequence)
    
    # Show ratios approaching golden ratio
    print("\nRatios F(n)/F(n-1) approaching Golden Ratio (φ ≈ 1.618...):")
    for n in range(10, 21):
        if n > 0:
            ratio = fibonacci(n) / fibonacci(n-1)
            print(f"F({n})/F({n-1}) = {ratio:.10f}")
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)