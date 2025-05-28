#!/usr/bin/env python
"""
Test script to verify content extraction logic.
This script tests the modifications to the canvas_content handling.
"""

import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, Any, Optional

# Import the extraction function directly
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from .test_orchestrator_cli import (
    OrchestratorClient,
    print_success,
    print_error,
    Colors,
)


def test_canvas_content_extraction():
    """Test that extraction works correctly with various content formats."""
    print(f"{Colors.HEADER}Testing canvas_content extraction...{Colors.ENDC}")

    # Setup client
    client = OrchestratorClient()

    # Create test cases
    test_cases = [
        {
            "name": "Pure Python code (old format)",
            "query": "Generate a Python function to calculate factorial",
            "response_data": {
                "canvas_content": {
                    "type": "code",
                    "format": "python",
                    "content": 'def factorial(n):\n    """Calculate factorial of n."""\n    if n == 0 or n == 1:\n        return 1\n    else:\n        return n * factorial(n-1)',
                },
                "target_format": "python",
            },
            "expected_ext": "py",
        },
        {
            "name": "Pure Python code (new format)",
            "query": "Generate a Python function to calculate fibonacci",
            "response_data": {
                "canvas_content": 'def fibonacci(n):\n    """Calculate the nth Fibonacci number."""\n    if n <= 0:\n        return 0\n    elif n == 1:\n        return 1\n    else:\n        return fibonacci(n-1) + fibonacci(n-2)',
                "target_format": "python",
            },
            "expected_ext": "py",
        },
        {
            "name": "JavaScript code with markdown code block",
            "query": "Generate a JavaScript function",
            "response_data": {
                "canvas_content": "```javascript\nfunction greet(name) {\n    return `Hello, ${name}!`;\n}\n```",
                "target_format": "javascript",
            },
            "expected_ext": "js",
        },
        {
            "name": "Markdown document",
            "query": "Write a tutorial about Python",
            "response_data": {
                "canvas_content": "# Python Tutorial\n\nPython is a high-level programming language.\n\n## Getting Started\n\n```python\nprint('Hello, World!')\n```",
                "target_format": "markdown",
            },
            "expected_ext": "md",
        },
        {
            "name": "Complex document with explanatory text",
            "query": "Write a document about machine learning",
            "response_data": {
                "canvas_content": "# Machine Learning\n\nMachine learning is a field of AI focused on building systems that learn from data.\n\n## Supervised Learning\n\nIn supervised learning, models are trained on labeled data.",
                "target_format": "markdown",
            },
            "expected_ext": "md",
        },
    ]

    # Test each case
    results = []
    for idx, test_case in enumerate(test_cases):
        print(f"\n{Colors.BOLD}{'=' * 50}{Colors.ENDC}")
        print(f"{Colors.BOLD}Test Case {idx + 1}: {test_case['name']}{Colors.ENDC}")
        print(f"Query: {test_case['query']}")
        print(
            f"Canvas Content Type: {type(test_case['response_data']['canvas_content'])}"
        )

        if isinstance(test_case["response_data"]["canvas_content"], dict):
            print(
                f"Canvas Content Preview: {json.dumps(test_case['response_data']['canvas_content'], indent=2)[:100]}..."
            )
        else:
            print(
                f"Canvas Content Preview: {test_case['response_data']['canvas_content'][:100]}..."
            )

        # Extract the content
        output_path = client._save_generated_content(
            test_case["query"], test_case["response_data"]
        )

        # Verify the output
        if output_path:
            output_file = Path(output_path)
            if output_file.exists():
                with open(output_file, "r") as f:
                    content = f.read()
                    ext = output_file.suffix
                    success = ext == f".{test_case['expected_ext']}"

                    print(f"Output file: {output_path}")
                    print(
                        f"File extension: {ext} (Expected: .{test_case['expected_ext']})"
                    )
                    print(f"Content preview: {content[:100]}...")

                    if success:
                        print_success(f"Test PASSED")
                    else:
                        print_error(f"Test FAILED")

                    results.append(
                        {
                            "case": test_case["name"],
                            "path": output_path,
                            "content_length": len(content),
                            "extension_match": success,
                        }
                    )
            else:
                print_error(f"ERROR: Output file {output_path} doesn't exist")
                results.append(
                    {
                        "case": test_case["name"],
                        "error": f"Output file {output_path} doesn't exist",
                    }
                )
        else:
            print_error("ERROR: No output path returned")
            results.append(
                {"case": test_case["name"], "error": "No output path returned"}
            )

    # Print summary
    print(f"\n{Colors.HEADER}{'=' * 50}")
    print(f"TEST SUMMARY")
    print(f"{'=' * 50}{Colors.ENDC}")

    success_count = 0
    for result in results:
        status = (
            "SUCCESS"
            if "error" not in result and result.get("extension_match", False)
            else "FAILED"
        )
        if status == "SUCCESS":
            success_count += 1
            print_success(f"{result['case']}: {status}")
        else:
            print_error(f"{result['case']}: {status}")

    print(
        f"\nTotal: {len(results)}, Passed: {success_count}, Failed: {len(results) - success_count}"
    )

    return success_count == len(results)


if __name__ == "__main__":
    success = test_canvas_content_extraction()
    sys.exit(0 if success else 1)
