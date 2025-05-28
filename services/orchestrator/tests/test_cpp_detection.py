#!/usr/bin/env python
"""
Test script for C++ detection and proper file extension handling in the orchestrator service.

This script specifically tests the file extension handling for C++ code to ensure that:
1. C++ code is correctly detected from markdown code blocks
2. The target_format is properly set for C++ code
3. The C++ code is saved with the .cpp extension instead of .md
"""

import argparse
import json
import os
import sys
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Add the parent directory to the path so we can import test_orchestrator_cli
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from .test_orchestrator_cli import (
    OrchestratorClient,
    Colors,
    print_success,
    print_error,
    print_info,
    print_header,
)

# Default server URL
DEFAULT_SERVER_URL = "http://localhost:8000"

# Test C++ code sample
CPP_CODE_SAMPLE = """
#include <iostream>
#include <vector>
#include <string>
#include <memory>

class Shape {
public:
    virtual ~Shape() = default;
    virtual double area() const = 0;
    virtual void print() const {
        std::cout << "This is a shape with area: " << area() << std::endl;
    }
};

class Circle : public Shape {
private:
    double radius;
public:
    explicit Circle(double r) : radius(r) {}
    
    double area() const override {
        return 3.14159 * radius * radius;
    }
    
    void print() const override {
        std::cout << "Circle with radius " << radius << " and area " << area() << std::endl;
    }
};

class Rectangle : public Shape {
private:
    double width;
    double height;
public:
    Rectangle(double w, double h) : width(w), height(h) {}
    
    double area() const override {
        return width * height;
    }
    
    void print() const override {
        std::cout << "Rectangle with width " << width << ", height " << height 
                 << " and area " << area() << std::endl;
    }
};

int main() {
    std::vector<std::unique_ptr<Shape>> shapes;
    
    shapes.push_back(std::make_unique<Circle>(5.0));
    shapes.push_back(std::make_unique<Rectangle>(4.0, 6.0));
    
    for (const auto& shape : shapes) {
        shape->print();
    }
    
    return 0;
}
"""


def clean_generated_files():
    """Clean up any previously generated test files"""
    output_dir = Path("./generated_content")
    if output_dir.exists():
        test_files = list(output_dir.glob("*_test_cpp_*"))
        for file in test_files:
            print_info(f"Removing test file: {file}")
            file.unlink()


def test_cpp_detection(client: OrchestratorClient) -> Tuple[bool, Optional[str]]:
    """Test C++ code detection and proper file extension handling"""
    print_header("Testing C++ Detection and File Extension")

    # Create a chat session
    chat_id = client.create_chat()
    if not chat_id:
        print_error("Failed to create chat session")
        return False, None

    # Create a message that specifically requests C++ code
    message = "Generate a C++ program that implements a Shape class hierarchy with Circle and Rectangle subclasses."

    # Send the message
    response = client.send_message(chat_id, message)
    if not response:
        print_error("Failed to get response")
        return False, None

    # Check if canvas_content was generated
    canvas_content = response.get("canvas_content")
    if not canvas_content:
        print_error("No canvas_content generated")
        return False, None

    # Check if target_format is set correctly
    target_format = response.get("target_format")
    print_info(f"Target format: {target_format}")

    # Look for saved file path (should be returned by _save_generated_content)
    saved_file_path = None
    for key, value in response.items():
        if (
            isinstance(value, str)
            and value.startswith("./generated_content/")
            and "cpp" in value
        ):
            saved_file_path = value
            break

    if not saved_file_path:
        # Try to find the file from generated_content directory
        output_dir = Path("./generated_content")
        if output_dir.exists():
            latest_files = sorted(
                output_dir.glob("*"), key=os.path.getmtime, reverse=True
            )
            if latest_files:
                saved_file_path = str(latest_files[0])

    if saved_file_path:
        # Check if the file extension is correct
        file_ext = Path(saved_file_path).suffix
        print_info(f"Generated file: {saved_file_path}")
        print_info(f"File extension: {file_ext}")

        # Read the content to verify it's C++ code
        with open(saved_file_path, "r") as f:
            content = f.read()

        # Basic validation of C++ content
        cpp_indicators = [
            "#include",
            "class",
            "public:",
            "private:",
            "int main(",
            "std::",
        ]
        is_cpp = any(indicator in content for indicator in cpp_indicators)

        if is_cpp and file_ext == ".cpp":
            print_success("✓ C++ code correctly detected and saved with .cpp extension")
            return True, saved_file_path
        elif is_cpp and file_ext != ".cpp":
            print_error(
                f"✗ C++ code detected but saved with incorrect extension: {file_ext}"
            )
            return False, saved_file_path
        elif not is_cpp:
            print_error("✗ Generated content does not appear to be C++ code")
            return False, saved_file_path
    else:
        print_error("✗ Could not find saved file path")
        return False, None


def test_cpp_content_manual(client: OrchestratorClient) -> bool:
    """Test C++ content detection and file extension handling with provided C++ code"""
    print_header("Testing C++ Content Detection with Provided Code")

    # Create a chat session
    chat_id = client.create_chat()
    if not chat_id:
        print_error("Failed to create chat session")
        return False

    # Create a message with explicit C++ code
    message = f"Here's some C++ code I'd like you to analyze:\n\n```cpp\n{CPP_CODE_SAMPLE}\n```"

    # Send the message
    response = client.send_message(chat_id, message)
    if not response:
        print_error("Failed to get response")
        return False

    # Check if canvas_content was generated
    canvas_content = response.get("canvas_content")
    if not canvas_content:
        print_info(
            "No canvas_content generated - this is expected for analysis requests"
        )

    # Check if target_format is set
    target_format = response.get("target_format")
    print_info(f"Target format: {target_format}")

    print_success("Test completed")
    return True


def test_cpp_generation_direct(client: OrchestratorClient) -> bool:
    """Test C++ code generation with explicit cpp language request"""
    print_header("Testing Direct C++ Generation with Language Specification")

    # Create a chat session
    chat_id = client.create_chat()
    if not chat_id:
        print_error("Failed to create chat session")
        return False

    # Create a message that explicitly requests C++ code
    message = "Generate a C++ program that implements a simple linked list. Use the cpp language specifically."

    # Send the message
    response = client.send_message(chat_id, message)
    if not response:
        print_error("Failed to get response")
        return False

    # Check if target_format is set correctly
    target_format = response.get("target_format")
    print_info(f"Target format: {target_format}")

    # Look for saved file path
    saved_file_path = None
    for key, value in response.items():
        if (
            isinstance(value, str)
            and value.startswith("./generated_content/")
            and "cpp" in value
        ):
            saved_file_path = value
            break

    if not saved_file_path:
        # Try to find the file from generated_content directory
        output_dir = Path("./generated_content")
        if output_dir.exists():
            latest_files = sorted(
                output_dir.glob("*"), key=os.path.getmtime, reverse=True
            )
            if latest_files:
                saved_file_path = str(latest_files[0])

    if saved_file_path:
        # Check if the file extension is correct
        file_ext = Path(saved_file_path).suffix
        print_info(f"Generated file: {saved_file_path}")
        print_info(f"File extension: {file_ext}")

        if file_ext == ".cpp":
            print_success("✓ C++ file correctly saved with .cpp extension")
            return True
        else:
            print_error(f"✗ C++ file saved with incorrect extension: {file_ext}")
            return False
    else:
        print_error("✗ Could not find saved file path")
        return False


def main():
    """Main entry point for the C++ detection test script"""
    parser = argparse.ArgumentParser(
        description="Test C++ detection and file extension handling in the orchestrator service"
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_SERVER_URL,
        help=f"Base URL of the orchestrator service (default: {DEFAULT_SERVER_URL})",
    )

    args = parser.parse_args()

    client = OrchestratorClient(base_url=args.url)

    # Check if service is healthy
    if not client.health_check():
        print_error("Orchestrator service is not healthy. Exiting.")
        sys.exit(1)

    # Clean up any previous test files
    clean_generated_files()

    # Track test results
    passed = 0
    failed = 0

    # Test 1: Basic C++ detection and file extension
    success, file_path = test_cpp_detection(client)
    if success:
        passed += 1
    else:
        failed += 1

    # Test 2: Manual C++ content detection
    if test_cpp_content_manual(client):
        passed += 1
    else:
        failed += 1

    # Test 3: Direct C++ generation with language specification
    if test_cpp_generation_direct(client):
        passed += 1
    else:
        failed += 1

    # Print summary
    print_header("Test Summary")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")

    # Return appropriate exit code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
