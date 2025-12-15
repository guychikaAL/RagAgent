"""
Date Difference Calculator - MCP-Style Tool

WHY THIS TOOL EXISTS:
=====================
LLMs are trained to predict text, not perform arithmetic.
While they can approximate simple calculations, they are fundamentally
poor at deterministic computation, especially involving:

1. Complex date arithmetic (leap years, month lengths, timezones)
2. Exact numerical precision
3. Edge cases (invalid dates, format variations)

WHAT THIS TOOL PROVIDES:
========================
- Exact, deterministic date difference calculation
- Proper error handling for invalid inputs
- ISO 8601 standard date parsing
- Zero ambiguity, zero approximation

HOW IT EXTENDS LLM CAPABILITIES:
=================================
The LLM can:
1. Understand the user's natural language question
2. Extract the relevant dates
3. Call this tool with structured inputs
4. Use the precise result in its response

The tool provides:
- Computation the LLM cannot reliably perform
- Guaranteed accuracy
- Proper error handling

This is the core principle of MCP (Model Context Protocol):
LLMs orchestrate, tools compute.
"""

from datetime import datetime
from typing import Dict, Union


def calculate_days_between(
    start_date: str,
    end_date: str
) -> Dict[str, Union[int, str, bool]]:
    """
    Calculate the exact number of days between two dates.
    
    This is an MCP-style tool that performs deterministic date arithmetic.
    The LLM should NEVER attempt to compute this itself.
    
    Args:
        start_date: ISO 8601 format date string (YYYY-MM-DD)
        end_date: ISO 8601 format date string (YYYY-MM-DD)
    
    Returns:
        Dictionary containing:
        - success (bool): Whether calculation succeeded
        - number_of_days (int): Days between dates (negative if end < start)
        - start_date (str): Parsed start date
        - end_date (str): Parsed end date
        - error (str, optional): Error message if failed
    
    Examples:
        >>> calculate_days_between("2024-01-01", "2024-01-10")
        {'success': True, 'number_of_days': 9, ...}
        
        >>> calculate_days_between("2024-01-10", "2024-01-01")
        {'success': True, 'number_of_days': -9, ...}
        
        >>> calculate_days_between("invalid", "2024-01-01")
        {'success': False, 'error': '...', ...}
    """
    
    # WHY WE DON'T LET THE LLM DO THIS:
    # ----------------------------------
    # An LLM might produce responses like:
    # - "approximately 9 days" (imprecise)
    # - "about a week" (not numerical)
    # - "8 or 9 days" (uncertain)
    # - Wrong calculation due to not accounting for leap years
    #
    # This tool guarantees exact, deterministic results.
    
    try:
        # Parse dates using ISO 8601 standard
        # This handles edge cases the LLM would struggle with:
        # - Leap years (2024-02-29 is valid, 2023-02-29 is not)
        # - Month boundaries (varying days per month)
        # - Valid date ranges
        
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        # Calculate exact difference
        # datetime handles all the complexity:
        # - Different month lengths (28, 29, 30, 31 days)
        # - Leap year rules (divisible by 4, except centuries, except every 400 years)
        # - Time boundary calculations
        
        difference = (end - start).days
        
        return {
            "success": True,
            "number_of_days": difference,
            "start_date": start_date,
            "end_date": end_date,
            "calculation_type": "exact",
            "message": f"Calculated exact difference: {abs(difference)} days"
        }
        
    except ValueError as e:
        # Handle invalid date formats
        # The LLM cannot reliably validate date formats
        # This tool catches issues like:
        # - Invalid format (2024/01/01 instead of 2024-01-01)
        # - Invalid dates (2024-02-30, 2024-13-01)
        # - Malformed strings
        
        return {
            "success": False,
            "error": f"Invalid date format: {str(e)}",
            "expected_format": "YYYY-MM-DD (ISO 8601)",
            "start_date": start_date,
            "end_date": end_date,
            "message": "Please provide dates in ISO 8601 format (YYYY-MM-DD)"
        }
    
    except Exception as e:
        # Handle unexpected errors
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "start_date": start_date,
            "end_date": end_date
        }


# MCP-STYLE TOOL REGISTRY
# -----------------------
# In a full MCP implementation, this tool would be registered
# in a tool registry that the LLM can query and invoke.
#
# The LLM would:
# 1. See a natural language question about dates
# 2. Recognize it needs precise date calculation
# 3. Look up available tools
# 4. Find calculate_days_between
# 5. Extract dates from user query
# 6. Call this tool with structured inputs
# 7. Receive deterministic output
# 8. Format the result in natural language

TOOL_METADATA = {
    "name": "calculate_days_between",
    "description": "Calculate exact number of days between two dates",
    "category": "date_arithmetic",
    "deterministic": True,
    "parameters": {
        "start_date": {
            "type": "string",
            "format": "date",
            "description": "Start date in ISO 8601 format (YYYY-MM-DD)",
            "required": True,
            "example": "2024-01-01"
        },
        "end_date": {
            "type": "string",
            "format": "date",
            "description": "End date in ISO 8601 format (YYYY-MM-DD)",
            "required": True,
            "example": "2024-12-31"
        }
    },
    "returns": {
        "type": "object",
        "properties": {
            "success": {"type": "boolean"},
            "number_of_days": {"type": "integer"},
            "error": {"type": "string", "optional": True}
        }
    }
}


if __name__ == "__main__":
    # Quick sanity tests
    print("Testing Date Calculator Tool")
    print("=" * 60)
    
    # Test 1: Normal case
    print("\n1. Normal case (Jan 1 to Jan 10, 2024):")
    result = calculate_days_between("2024-01-01", "2024-01-10")
    print(f"   Result: {result}")
    
    # Test 2: Reverse order (negative days)
    print("\n2. Reverse order (Jan 10 to Jan 1, 2024):")
    result = calculate_days_between("2024-01-10", "2024-01-01")
    print(f"   Result: {result}")
    
    # Test 3: Leap year case
    print("\n3. Leap year (Feb 28 to Mar 1, 2024):")
    result = calculate_days_between("2024-02-28", "2024-03-01")
    print(f"   Result: {result}")
    
    # Test 4: Same date
    print("\n4. Same date (Dec 25, 2024):")
    result = calculate_days_between("2024-12-25", "2024-12-25")
    print(f"   Result: {result}")
    
    # Test 5: Invalid format
    print("\n5. Invalid format (2024/01/01):")
    result = calculate_days_between("2024/01/01", "2024-01-10")
    print(f"   Result: {result}")
    
    # Test 6: Invalid date (Feb 30)
    print("\n6. Invalid date (Feb 30, 2024):")
    result = calculate_days_between("2024-02-30", "2024-03-01")
    print(f"   Result: {result}")
    
    print("\n" + "=" * 60)
    print("✅ Tool tests complete")
