#!/bin/bash
# Run all test scripts in the tests directory

# Set error handling
set -e

# Define color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Counter for tests
TOTAL=0
PASSED=0
FAILED=0

# Function to run a test
run_test() {
  TEST_FILE="$1"
  TEST_NAME=$(basename "$TEST_FILE")
  
  echo -e "${BLUE}Running test: ${TEST_NAME}${NC}"
  
  # Run the test
  if bash "$TEST_FILE"; then
    echo -e "${GREEN}Test passed: ${TEST_NAME}${NC}"
    PASSED=$((PASSED + 1))
  else
    echo -e "${RED}Test failed: ${TEST_NAME}${NC}"
    FAILED=$((FAILED + 1))
  fi
  
  TOTAL=$((TOTAL + 1))
  echo ""
}

# Find and run all test scripts
echo -e "${BLUE}Running all tests in ${SCRIPT_DIR}${NC}"
echo ""

for TEST_FILE in "$SCRIPT_DIR"/test_*.sh; do
  if [ -f "$TEST_FILE" ] && [ -x "$TEST_FILE" ]; then
    run_test "$TEST_FILE"
  fi
done

# Print summary
echo -e "${BLUE}Test Summary:${NC}"
echo -e "Total tests: ${TOTAL}"
echo -e "${GREEN}Passed: ${PASSED}${NC}"
if [ $FAILED -gt 0 ]; then
  echo -e "${RED}Failed: ${FAILED}${NC}"
else
  echo -e "Failed: ${FAILED}"
fi

# Exit with error if any test failed
if [ $FAILED -gt 0 ]; then
  exit 1
fi

exit 0