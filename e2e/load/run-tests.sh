#!/bin/bash

# Load Testing Execution Script
# Quick and easy way to run load tests with common configurations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SCENARIO="smoke"
ENVIRONMENT="local"
DURATION=""
MAX_VUS=""
OUTPUT_FILE=""
VERBOSE=false
DRY_RUN=false

# Function to print usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -s, --scenario SCENARIO    Test scenario: smoke, load, stress, spike, soak, breakpoint (default: smoke)"
    echo "  -e, --environment ENV      Target environment: local, dev, staging, prod (default: local)"
    echo "  -d, --duration DURATION    Override test duration (e.g., 30s, 5m, 1h)"
    echo "  -u, --max-vus VUS          Override maximum virtual users"
    echo "  -o, --output FILE          Save results to JSON file"
    echo "  -v, --verbose              Enable verbose output"
    echo "  -n, --dry-run              Show configuration without running test"
    echo "  -h, --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 -s smoke -e local"
    echo "  $0 -s load -e dev -d 5m -o results.json"
    echo "  $0 -s stress -e staging -u 200 -v"
    echo ""
    echo "Environment Variables:"
    echo "  DEV_API_URL      Development API URL"
    echo "  STAGING_API_URL  Staging API URL"
    echo "  PROD_API_URL     Production API URL"
    echo "  SLACK_WEBHOOK_URL Slack webhook for notifications"
}

# Function to print colored output
log() {
    local level=$1
    shift
    case $level in
        "INFO")  echo -e "${BLUE}[INFO]${NC} $*" ;;
        "WARN")  echo -e "${YELLOW}[WARN]${NC} $*" ;;
        "ERROR") echo -e "${RED}[ERROR]${NC} $*" ;;
        "SUCCESS") echo -e "${GREEN}[SUCCESS]${NC} $*" ;;
    esac
}

# Function to validate scenario
validate_scenario() {
    case $SCENARIO in
        smoke|load|stress|spike|soak|breakpoint)
            return 0
            ;;
        *)
            log "ERROR" "Invalid scenario: $SCENARIO"
            log "INFO" "Valid scenarios: smoke, load, stress, spike, soak, breakpoint"
            exit 1
            ;;
    esac
}

# Function to validate environment
validate_environment() {
    case $ENVIRONMENT in
        local|dev|staging|prod)
            return 0
            ;;
        *)
            log "ERROR" "Invalid environment: $ENVIRONMENT"
            log "INFO" "Valid environments: local, dev, staging, prod"
            exit 1
            ;;
    esac
}

# Function to check k6 installation
check_k6() {
    if ! command -v k6 &> /dev/null; then
        log "ERROR" "k6 is not installed. Please install k6 first."
        log "INFO" "Visit https://k6.io/docs/getting-started/installation/ for installation instructions"
        exit 1
    fi
    
    local k6_version=$(k6 version | head -n1)
    log "INFO" "Using $k6_version"
}

# Function to setup environment variables
setup_environment() {
    export TARGET_ENV=$ENVIRONMENT
    
    # Set duration override if specified
    if [ -n "$DURATION" ]; then
        export DURATION_OVERRIDE=$DURATION
        log "INFO" "Duration override: $DURATION"
    fi
    
    # Set max VUs if specified
    if [ -n "$MAX_VUS" ]; then
        export MAX_VUS=$MAX_VUS
        log "INFO" "Max VUs override: $MAX_VUS"
    fi
    
    # Set auth mode based on environment
    case $ENVIRONMENT in
        local|dev)
            export AUTH_MODE=demo
            ;;
        staging|prod)
            export AUTH_MODE=aad
            ;;
    esac
    
    log "INFO" "Environment: $ENVIRONMENT"
    log "INFO" "Auth mode: ${AUTH_MODE:-demo}"
}

# Function to validate environment connectivity
check_connectivity() {
    local base_url=""
    
    case $ENVIRONMENT in
        local)
            base_url="http://localhost:8000"
            ;;
        dev)
            base_url=${DEV_API_URL}
            ;;
        staging)
            base_url=${STAGING_API_URL}
            ;;
        prod)
            base_url=${PROD_API_URL}
            ;;
    esac
    
    if [ -z "$base_url" ]; then
        log "WARN" "No URL configured for environment: $ENVIRONMENT"
        return 0
    fi
    
    log "INFO" "Checking connectivity to: $base_url"
    
    if curl -s --max-time 10 "$base_url/health" > /dev/null; then
        log "SUCCESS" "Environment is accessible"
    else
        log "WARN" "Environment may not be accessible - test may fail"
    fi
}

# Function to prepare output directory
prepare_output() {
    if [ -n "$OUTPUT_FILE" ]; then
        local dir=$(dirname "$OUTPUT_FILE")
        mkdir -p "$dir"
        
        # Add timestamp if not present
        if [[ "$OUTPUT_FILE" != *"$(date +%Y%m%d)"* ]]; then
            local timestamp=$(date +%Y%m%d-%H%M%S)
            local base=$(basename "$OUTPUT_FILE" .json)
            local ext="${OUTPUT_FILE##*.}"
            OUTPUT_FILE="${dir}/${base}-${timestamp}.${ext}"
        fi
        
        log "INFO" "Results will be saved to: $OUTPUT_FILE"
    else
        # Create default output file
        mkdir -p reports
        OUTPUT_FILE="reports/${SCENARIO}-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S).json"
        log "INFO" "Results will be saved to: $OUTPUT_FILE"
    fi
}

# Function to build k6 command
build_k6_command() {
    local cmd="k6 run"
    
    # Add output option
    if [ -n "$OUTPUT_FILE" ]; then
        cmd="$cmd --out json=$OUTPUT_FILE"
    fi
    
    # Add verbose option
    if [ "$VERBOSE" = true ]; then
        cmd="$cmd --verbose"
    fi
    
    # Add summary options
    cmd="$cmd --summary-trend-stats=avg,min,med,max,p(90),p(95),p(99)"
    cmd="$cmd --summary-time-unit=ms"
    
    # Add scenario file
    cmd="$cmd scenarios/${SCENARIO}.js"
    
    echo "$cmd"
}

# Function to run the test
run_test() {
    local cmd=$(build_k6_command)
    
    log "INFO" "Starting $SCENARIO test on $ENVIRONMENT environment"
    log "INFO" "Command: $cmd"
    
    if [ "$DRY_RUN" = true ]; then
        log "INFO" "Dry run mode - not executing test"
        return 0
    fi
    
    local start_time=$(date +%s)
    
    # Run the test
    if eval "$cmd"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        log "SUCCESS" "Test completed successfully in ${duration}s"
        
        if [ -n "$OUTPUT_FILE" ] && [ -f "$OUTPUT_FILE" ]; then
            local file_size=$(du -h "$OUTPUT_FILE" | cut -f1)
            log "INFO" "Results saved to $OUTPUT_FILE ($file_size)"
            
            # Basic result analysis
            if command -v jq &> /dev/null; then
                analyze_results
            else
                log "INFO" "Install jq for automatic result analysis"
            fi
        fi
    else
        local exit_code=$?
        log "ERROR" "Test failed with exit code: $exit_code"
        return $exit_code
    fi
}

# Function to analyze results
analyze_results() {
    if [ ! -f "$OUTPUT_FILE" ]; then
        return 0
    fi
    
    log "INFO" "Analyzing results..."
    
    # Extract basic metrics
    local total_requests=$(jq -r '[.[] | select(.type=="Point" and .metric=="http_reqs")] | length' "$OUTPUT_FILE" 2>/dev/null || echo "0")
    local failed_requests=$(jq -r '[.[] | select(.type=="Point" and .metric=="http_req_failed" and .data.value==1)] | length' "$OUTPUT_FILE" 2>/dev/null || echo "0")
    
    if [ "$total_requests" -gt 0 ]; then
        local success_rate=$(echo "scale=2; (($total_requests - $failed_requests) * 100) / $total_requests" | bc -l 2>/dev/null || echo "N/A")
        log "INFO" "Total requests: $total_requests"
        log "INFO" "Failed requests: $failed_requests"
        log "INFO" "Success rate: ${success_rate}%"
        
        # Check if success rate is acceptable
        if [ "$failed_requests" -gt 0 ] && command -v bc &> /dev/null; then
            local error_rate=$(echo "scale=4; $failed_requests / $total_requests" | bc -l)
            local error_threshold="0.05"
            
            if (( $(echo "$error_rate > $error_threshold" | bc -l) )); then
                log "WARN" "Error rate (${error_rate}) exceeds threshold (${error_threshold})"
            fi
        fi
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--scenario)
            SCENARIO="$2"
            shift 2
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -d|--duration)
            DURATION="$2"
            shift 2
            ;;
        -u|--max-vus)
            MAX_VUS="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    log "INFO" "AI Cyber Maturity Assessment - Load Testing"
    log "INFO" "============================================"
    
    # Validate inputs
    validate_scenario
    validate_environment
    
    # Check prerequisites
    check_k6
    
    # Setup environment
    setup_environment
    
    # Check connectivity
    check_connectivity
    
    # Prepare output
    prepare_output
    
    # Run the test
    run_test
    
    log "SUCCESS" "Load testing completed"
}

# Run main function
main "$@"