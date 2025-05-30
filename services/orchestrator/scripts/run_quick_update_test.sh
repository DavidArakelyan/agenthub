#!/bin/bash
# Test the update workflow functionality

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PARENT_DIR="$(dirname "$DIR")"

# Create sample content for testing
echo "Creating sample content for testing..."
TEST_DIR="$PARENT_DIR/generated_content"
mkdir -p "$TEST_DIR"

# Create a sample Python file if it doesn't exist
if [ ! -f "$TEST_DIR/factorial_function.py" ]; then
    cat > "$TEST_DIR/factorial_function.py" << 'EOF'
def factorial(n):
    """Calculate the factorial of a number."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)

# Example usage
if __name__ == "__main__":
    print(factorial(5))  # 120
EOF
    echo "Created sample Python file."
fi

# Create a sample Markdown file if it doesn't exist
if [ ! -f "$TEST_DIR/ai_benefits_doc.md" ]; then
    cat > "$TEST_DIR/ai_benefits_doc.md" << 'EOF'
# Benefits of AI

Artificial Intelligence offers numerous benefits across various domains:

## Economic Benefits
- Increased productivity
- Automation of routine tasks
- New industry creation

## Scientific Benefits
- Accelerated research
- Pattern discovery in complex data
- Enhanced problem solving

## Social Benefits
- Improved healthcare diagnosis
- Personalized education
- Accessibility enhancements
EOF
    echo "Created sample Markdown file."
fi

# Create metadata files
if [ ! -f "$TEST_DIR/factorial_function.json" ]; then
    cat > "$TEST_DIR/factorial_function.json" << 'EOF'
{
  "content": "def factorial(n):\n    \"\"\"Calculate the factorial of a number.\"\"\"\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n\n# Example usage\nif __name__ == \"__main__\":\n    print(factorial(5))  # 120",
  "metadata": {
    "generator_type": "code",
    "code_language": "py",
    "created_at": "2025-05-30T00:00:00.000Z"
  }
}
EOF
    echo "Created sample Python metadata file."
fi

if [ ! -f "$TEST_DIR/ai_benefits_doc.json" ]; then
    cat > "$TEST_DIR/ai_benefits_doc.json" << 'EOF'
{
  "content": "# Benefits of AI\n\nArtificial Intelligence offers numerous benefits across various domains:\n\n## Economic Benefits\n- Increased productivity\n- Automation of routine tasks\n- New industry creation\n\n## Scientific Benefits\n- Accelerated research\n- Pattern discovery in complex data\n- Enhanced problem solving\n\n## Social Benefits\n- Improved healthcare diagnosis\n- Personalized education\n- Accessibility enhancements",
  "metadata": {
    "generator_type": "document",
    "document_format": "md",
    "created_at": "2025-05-30T00:00:00.000Z"
  }
}
EOF
    echo "Created sample Markdown metadata file."
fi

# Run the update workflow tests
echo "Running update workflow tests..."
python -m pytest "$PARENT_DIR/tests/test_content_retriever.py" "$PARENT_DIR/tests/test_update_workflow.py" "$PARENT_DIR/tests/test_document_update_workflow.py" -v

# Store the exit code
EXIT_CODE=$?

# Print a summary
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All update workflow tests passed!"
else
    echo "❌ Some tests failed. Check the output above for details."
fi

exit $EXIT_CODE
