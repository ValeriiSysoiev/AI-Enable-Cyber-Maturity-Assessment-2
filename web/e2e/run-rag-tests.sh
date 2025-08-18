#!/bin/bash

# RAG E2E Test Runner Script
# Comprehensive test execution for RAG functionality with different configurations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test configuration
DEFAULT_BASE_URL="http://localhost:3000"
DEFAULT_API_URL="http://localhost:8000"
TEST_RESULTS_DIR="test-results"
REPORT_DIR="playwright-report"

# Parse command line arguments
ENVIRONMENT=${1:-"local"}
TEST_SUITE=${2:-"all"}
BROWSER=${3:-"chromium"}
HEADLESS=${4:-"true"}

echo -e "${BLUE}🧪 RAG E2E Test Runner${NC}"
echo -e "${BLUE}========================${NC}"
echo "Environment: $ENVIRONMENT"
echo "Test Suite: $TEST_SUITE"
echo "Browser: $BROWSER"
echo "Headless: $HEADLESS"
echo ""

# Set environment variables based on environment
case $ENVIRONMENT in
  "local")
    export WEB_BASE_URL="${WEB_BASE_URL:-$DEFAULT_BASE_URL}"
    export API_BASE_URL="${API_BASE_URL:-$DEFAULT_API_URL}"
    export RAG_MODE="${RAG_MODE:-demo}"
    export RAG_FEATURE_FLAG="${RAG_FEATURE_FLAG:-true}"
    ;;
  "dev")
    export WEB_BASE_URL="${WEB_BASE_URL:-https://dev-web.example.com}"
    export API_BASE_URL="${API_BASE_URL:-https://dev-api.example.com}"
    export RAG_MODE="${RAG_MODE:-azure_openai}"
    export RAG_FEATURE_FLAG="${RAG_FEATURE_FLAG:-true}"
    ;;
  "staging")
    export WEB_BASE_URL="${WEB_BASE_URL:-https://staging-web.example.com}"
    export API_BASE_URL="${API_BASE_URL:-https://staging-api.example.com}"
    export RAG_MODE="${RAG_MODE:-azure_openai}"
    export RAG_FEATURE_FLAG="${RAG_FEATURE_FLAG:-true}"
    ;;
  *)
    echo -e "${RED}❌ Unknown environment: $ENVIRONMENT${NC}"
    echo "Supported environments: local, dev, staging"
    exit 1
    ;;
esac

# Create results directories
mkdir -p "$TEST_RESULTS_DIR"
mkdir -p "$REPORT_DIR"

# Function to run specific test suite
run_test_suite() {
  local suite_name=$1
  local test_pattern=$2
  local timeout=${3:-"90000"}
  
  echo -e "${YELLOW}🔍 Running $suite_name tests...${NC}"
  
  if [ "$HEADLESS" = "false" ]; then
    PLAYWRIGHT_ARGS="--headed"
  else
    PLAYWRIGHT_ARGS=""
  fi
  
  npx playwright test \
    --project="$BROWSER" \
    --timeout="$timeout" \
    --grep="$test_pattern" \
    --reporter=html,junit,list \
    --output-dir="$TEST_RESULTS_DIR" \
    $PLAYWRIGHT_ARGS
}

# Function to run RAG-specific test projects
run_rag_project() {
  local project_name=$1
  local description=$2
  
  echo -e "${YELLOW}🔍 Running $description...${NC}"
  
  if [ "$HEADLESS" = "false" ]; then
    PLAYWRIGHT_ARGS="--headed"
  else
    PLAYWRIGHT_ARGS=""
  fi
  
  npx playwright test \
    --project="$project_name" \
    --reporter=html,junit,list \
    --output-dir="$TEST_RESULTS_DIR" \
    $PLAYWRIGHT_ARGS
}

# Main test execution based on suite selection
case $TEST_SUITE in
  "basic")
    echo -e "${GREEN}📋 Running Basic RAG Tests${NC}"
    run_rag_project "rag-basic" "Basic RAG functionality tests"
    ;;
    
  "advanced")
    echo -e "${GREEN}📋 Running Advanced RAG Tests${NC}"
    run_rag_project "rag-advanced" "Advanced RAG functionality and error handling tests"
    ;;
    
  "integration")
    echo -e "${GREEN}📋 Running RAG Integration Tests${NC}"
    run_rag_project "rag-integration" "End-to-end RAG integration tests"
    ;;
    
  "cross-browser")
    echo -e "${GREEN}📋 Running Cross-browser RAG Tests${NC}"
    run_rag_project "rag-basic" "Basic RAG tests (Chromium)"
    run_rag_project "rag-firefox" "Basic RAG tests (Firefox)"
    ;;
    
  "mobile")
    echo -e "${GREEN}📋 Running Mobile RAG Tests${NC}"
    run_rag_project "rag-mobile" "RAG tests on mobile viewport"
    ;;
    
  "performance")
    echo -e "${GREEN}📋 Running RAG Performance Tests${NC}"
    run_test_suite "RAG Performance" "RAG.*performance|performance.*RAG" "180000"
    ;;
    
  "security")
    echo -e "${GREEN}📋 Running RAG Security Tests${NC}"
    run_test_suite "RAG Security" "RAG.*security|security.*RAG|RAG.*Privacy" "120000"
    ;;
    
  "smoke")
    echo -e "${GREEN}📋 Running RAG Smoke Tests${NC}"
    run_test_suite "RAG Smoke" "should display RAG toggle|should perform search|should handle backend" "60000"
    ;;
    
  "all")
    echo -e "${GREEN}📋 Running Complete RAG Test Suite${NC}"
    
    echo -e "${BLUE}Phase 1: Basic RAG Tests${NC}"
    run_rag_project "rag-basic" "Basic RAG functionality tests"
    
    echo -e "${BLUE}Phase 2: Advanced RAG Tests${NC}"
    run_rag_project "rag-advanced" "Advanced RAG functionality tests"
    
    echo -e "${BLUE}Phase 3: Integration Tests${NC}"
    run_rag_project "rag-integration" "RAG integration tests"
    
    if [ "$BROWSER" = "chromium" ]; then
      echo -e "${BLUE}Phase 4: Cross-browser Tests${NC}"
      run_rag_project "rag-firefox" "Firefox compatibility tests"
      
      echo -e "${BLUE}Phase 5: Mobile Tests${NC}"
      run_rag_project "rag-mobile" "Mobile viewport tests"
    fi
    ;;
    
  *)
    echo -e "${RED}❌ Unknown test suite: $TEST_SUITE${NC}"
    echo "Supported test suites:"
    echo "  basic       - Basic RAG functionality"
    echo "  advanced    - Advanced RAG features and error handling"
    echo "  integration - End-to-end integration scenarios"
    echo "  cross-browser - Cross-browser compatibility"
    echo "  mobile      - Mobile viewport testing"
    echo "  performance - Performance and load testing"
    echo "  security    - Security and privacy testing"
    echo "  smoke       - Quick smoke tests"
    echo "  all         - Complete test suite"
    exit 1
    ;;
esac

# Test execution completed
echo ""
echo -e "${GREEN}✅ RAG Test Execution Completed${NC}"

# Check for test results and generate summary
if [ -f "$TEST_RESULTS_DIR/junit.xml" ]; then
  echo -e "${BLUE}📊 Test Results Summary:${NC}"
  
  # Extract basic statistics from JUnit XML (if available)
  if command -v xmllint >/dev/null 2>&1; then
    TOTAL_TESTS=$(xmllint --xpath "//testsuites/@tests" "$TEST_RESULTS_DIR/junit.xml" 2>/dev/null | cut -d'"' -f2 || echo "N/A")
    FAILED_TESTS=$(xmllint --xpath "//testsuites/@failures" "$TEST_RESULTS_DIR/junit.xml" 2>/dev/null | cut -d'"' -f2 || echo "0")
    ERROR_TESTS=$(xmllint --xpath "//testsuites/@errors" "$TEST_RESULTS_DIR/junit.xml" 2>/dev/null | cut -d'"' -f2 || echo "0")
    
    echo "Total Tests: $TOTAL_TESTS"
    echo "Failed Tests: $FAILED_TESTS"
    echo "Error Tests: $ERROR_TESTS"
    
    if [ "$FAILED_TESTS" = "0" ] && [ "$ERROR_TESTS" = "0" ]; then
      echo -e "${GREEN}🎉 All tests passed!${NC}"
    else
      echo -e "${YELLOW}⚠️  Some tests failed or had errors${NC}"
    fi
  fi
fi

# Report locations
echo ""
echo -e "${BLUE}📁 Test Artifacts:${NC}"
echo "Results: $TEST_RESULTS_DIR/"
echo "HTML Report: $REPORT_DIR/index.html"

if [ -f "$REPORT_DIR/index.html" ]; then
  echo ""
  echo -e "${BLUE}🔗 View detailed report:${NC}"
  echo "file://$(pwd)/$REPORT_DIR/index.html"
fi

# Environment-specific post-test actions
case $ENVIRONMENT in
  "local")
    echo ""
    echo -e "${BLUE}💡 Local Development Tips:${NC}"
    echo "- View tests with UI: npx playwright test --ui"
    echo "- Debug specific test: npx playwright test --debug --grep='test name'"
    echo "- Record new tests: npx playwright codegen $WEB_BASE_URL"
    ;;
  "dev"|"staging")
    echo ""
    echo -e "${BLUE}🔄 CI/CD Integration:${NC}"
    echo "- Test results available for CI integration"
    echo "- JUnit XML: $TEST_RESULTS_DIR/junit.xml"
    echo "- Screenshots and videos available for failed tests"
    ;;
esac

echo ""
echo -e "${GREEN}✨ RAG E2E Testing Complete!${NC}"