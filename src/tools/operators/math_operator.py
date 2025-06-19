import re
import ast
import operator
import logging
from typing import Union, Dict, Any

from langchain.tools import tool

logger = logging.getLogger(__name__)

# Safe operators for mathematical expressions
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Safe functions for mathematical expressions
SAFE_FUNCTIONS = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "sum": sum,
}


def safe_eval(expression: str) -> Union[int, float]:
    """
    Safely evaluate a mathematical expression without using eval().

    This function uses AST parsing to evaluate mathematical expressions
    safely, preventing code injection attacks.

    Args:
        expression: Mathematical expression as string

    Returns:
        Numerical result of the expression

    Raises:
        ValueError: If expression is invalid or contains unsafe operations
        ZeroDivisionError: If division by zero occurs
    """
    try:
        # Parse the expression into an AST
        tree = ast.parse(expression, mode="eval")

        def _eval_node(node):
            if isinstance(node, ast.Expression):
                return _eval_node(node.body)
            elif isinstance(node, ast.Constant):  # Python 3.8+
                return node.value
            elif isinstance(node, ast.Num):  # Python < 3.8
                return node.n
            elif isinstance(node, ast.BinOp):
                left = _eval_node(node.left)
                right = _eval_node(node.right)
                op_func = SAFE_OPERATORS.get(type(node.op))
                if op_func is None:
                    raise ValueError(f"Unsupported operation: {type(node.op).__name__}")
                return op_func(left, right)
            elif isinstance(node, ast.UnaryOp):
                operand = _eval_node(node.operand)
                op_func = SAFE_OPERATORS.get(type(node.op))
                if op_func is None:
                    raise ValueError(
                        f"Unsupported unary operation: {type(node.op).__name__}"
                    )
                return op_func(operand)
            elif isinstance(node, ast.Call):
                func_name = node.func.id if isinstance(node.func, ast.Name) else None
                if func_name not in SAFE_FUNCTIONS:
                    raise ValueError(f"Unsupported function: {func_name}")
                args = [_eval_node(arg) for arg in node.args]
                return SAFE_FUNCTIONS[func_name](*args)
            elif isinstance(node, ast.List):
                return [_eval_node(item) for item in node.elts]
            else:
                raise ValueError(f"Unsupported AST node type: {type(node).__name__}")

        result = _eval_node(tree)

        # Ensure result is a number
        if not isinstance(result, (int, float)):
            raise ValueError(
                f"Expression must evaluate to a number, got {type(result).__name__}"
            )

        return result

    except ZeroDivisionError:
        raise ZeroDivisionError("Division by zero in mathematical expression")
    except Exception as e:
        raise ValueError(f"Invalid mathematical expression: {str(e)}")


def validate_math_expression(expression: str) -> str:
    """
    Validate and clean a mathematical expression.

    Args:
        expression: Raw mathematical expression

    Returns:
        Cleaned expression

    Raises:
        ValueError: If expression is invalid
    """
    if not expression or not isinstance(expression, str):
        raise ValueError("Expression must be a non-empty string")

    # Remove whitespace
    expression = expression.strip()

    if not expression:
        raise ValueError("Expression cannot be empty after cleaning")

    # Check for basic validity
    if not re.match(r"^[0-9+\-*/().\s,a-zA-Z]+$", expression):
        raise ValueError("Expression contains invalid characters")

    # Check for balanced parentheses
    if expression.count("(") != expression.count(")"):
        raise ValueError("Unbalanced parentheses in expression")

    return expression


@tool
def calculate(expression: str) -> str:
    """
    Perform mathematical calculations on expressions.

    This tool can evaluate mathematical expressions safely, including:
    - Basic arithmetic operations (+, -, *, /, //, %, **)
    - Parentheses for grouping
    - Common mathematical functions (abs, min, max, round, sum)
    - Integer and floating-point numbers

    Examples:
    - "2 + 3 * 4" -> 14
    - "(10 - 5) * 2" -> 10
    - "abs(-42)" -> 42
    - "round(3.14159, 2)" -> 3.14
    - "sum([1, 2, 3, 4, 5])" -> 15

    Args:
        expression: Mathematical expression as a string

    Returns:
        String containing the calculated result and explanation

    Security Note:
        This tool uses AST parsing instead of eval() to prevent code injection.
        Only mathematical operations and safe functions are allowed.
    """
    logger.info(f"Calculating expression: {expression}")

    try:
        # Validate input
        if not expression:
            return "Error: No expression provided. Please provide a mathematical expression to calculate."

        # Handle case where LangChain passes JSON string instead of raw expression
        import json

        actual_expression = expression
        if expression.startswith('{"expression":') or expression.startswith(
            "{'expression'"
        ):
            try:
                # Try to parse as JSON and extract the expression
                data = json.loads(expression.replace("'", '"'))
                if isinstance(data, dict) and "expression" in data:
                    actual_expression = data["expression"]
                    logger.debug(f"Extracted expression from JSON: {actual_expression}")
            except (json.JSONDecodeError, KeyError):
                # If JSON parsing fails, use the original string
                actual_expression = expression

        # Clean and validate the expression
        clean_expression = validate_math_expression(actual_expression)
        logger.debug(f"Cleaned expression: {clean_expression}")

        # Perform safe calculation
        result = safe_eval(clean_expression)

        # Format result based on type
        if isinstance(result, float):
            # Check if it's effectively an integer
            if result.is_integer():
                formatted_result = str(int(result))
            else:
                # Round to reasonable precision
                formatted_result = f"{result:.10g}"
        else:
            formatted_result = str(result)

        response = f"The calculation result is {formatted_result}, as {clean_expression} = {formatted_result}."

        logger.info(f"Calculation successful: {clean_expression} = {formatted_result}")
        return response

    except ZeroDivisionError as e:
        error_msg = (
            "Error: Division by zero is not allowed in mathematical expressions."
        )
        logger.warning(f"Division by zero in expression: {expression}")
        return error_msg
    except ValueError as e:
        error_msg = f"Error: {str(e)}"
        logger.warning(f"ValueError in expression: {expression} - {str(e)}")
        return error_msg
    except Exception as e:
        error_msg = f"Error: An unexpected error occurred while calculating the expression. {str(e)}"
        logger.error(f"Unexpected error in expression: {expression} - {str(e)}")
        return error_msg


@tool
def math_help() -> str:
    """
    Get help and information about mathematical operations and functions available.

    This tool provides guidance on:
    - Supported mathematical operations
    - Available functions
    - Syntax and examples
    - Common use cases

    Returns:
        String containing comprehensive help information about mathematical capabilities
    """
    help_text = """Mathematical Calculator Help

SUPPORTED OPERATIONS:
• Basic arithmetic: +, -, *, /, //, %, **
• Parentheses for grouping: ( )
• Comparison operations work in expressions

AVAILABLE FUNCTIONS:
• abs(x) - Absolute value
• min(a, b, ...) - Minimum value
• max(a, b, ...) - Maximum value  
• round(x, digits) - Round to specified decimal places
• sum([a, b, c]) - Sum of a list of numbers

EXAMPLES:
• Simple: "2 + 3 * 4" → 14
• Parentheses: "(10 - 5) * 2" → 10
• Functions: "abs(-42)" → 42
• Decimals: "round(3.14159, 2)" → 3.14
• Lists: "sum([1, 2, 3, 4, 5])" → 15
• Complex: "2 ** 3 + abs(-5)" → 13

SECURITY FEATURES:
• Safe evaluation using AST parsing
• No code execution or eval() risks
• Only mathematical operations allowed
• Input validation and error handling

LIMITATIONS:
• No variable assignments
• No loops or conditionals
• Integer and float operations only
• Limited to supported functions above

Ask me to calculate any mathematical expression following these guidelines!"""

    return help_text
