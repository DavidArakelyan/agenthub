# AgentHub Tests

This directory contains test scripts for the AgentHub project. These tests help ensure that critical functionality works correctly across different environments and system configurations.

## Available Tests

### `test_pip_detection.sh`

Tests the detection of Python and pip commands in the system environment. This script verifies that the system can correctly identify and use either `python`/`python3` and `pip`/`pip3` commands.

**Purpose**: Ensures that the setup scripts can work correctly regardless of how Python and pip are installed on the user's system.

**Usage**:
```bash
./test_pip_detection.sh
```

### `test_pip_freeze.sh`

Tests the generation of requirements-lock.txt files using `pip freeze`. This script creates a temporary virtual environment, installs sample dependencies, and generates a lock file.

**Purpose**: Demonstrates and validates the approach used in the setup scripts to generate lock files without needing pip-tools.

**Usage**:
```bash
./test_pip_freeze.sh
```

## Running All Tests

To run all tests, execute:

```bash
./run_all_tests.sh
```

The script will:
1. Find all test files with names starting with `test_`
2. Execute each test and track pass/fail status
3. Display a summary of results with color-coded output
4. Exit with a non-zero status code if any test fails

## Adding New Tests

When adding new test scripts:

1. Name the file with a `test_` prefix (e.g., `test_new_feature.sh`)
2. Make the script executable: `chmod +x test_new_feature.sh`
3. Include a clear comment header explaining the purpose of the test
4. Ensure the script exits with code 0 on success and non-zero on failure
5. Update this README.md with information about the new test

## Test Development Guidelines

- Keep tests focused on a single feature or functionality
- Make tests deterministic (same input produces same output)
- Include clear output messages for debugging
- Clean up any temporary files or resources created during testing
- Add proper error handling and timeouts for external dependencies

## Continuous Integration

These tests are designed to be run in continuous integration environments. The `run_all_tests.sh` script's exit code can be used to determine if the test suite passed or failed.