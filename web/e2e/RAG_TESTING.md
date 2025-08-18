# RAG E2E Testing Documentation

## Overview

This document describes the comprehensive End-to-End testing suite for RAG (Retrieval-Augmented Generation) functionality in the AI-Enabled Cyber Maturity Assessment platform.

## Test Structure

### Core Test Files

1. **`rag.spec.ts`** - Basic RAG functionality tests
   - RAG toggle component behavior
   - Enhanced evidence search
   - Citations and sources UI
   - RAG analysis integration
   - Status and administration
   - Accessibility and UX
   - Cross-browser compatibility

2. **`rag-advanced.spec.ts`** - Advanced RAG features and edge cases
   - Backend integration testing (Azure Search vs Cosmos DB)
   - Performance and scaling validation
   - Error handling and recovery scenarios
   - Security and privacy compliance
   - Multi-backend support testing

3. **`rag-integration.spec.ts`** - End-to-end integration workflows
   - Complete RAG workflow testing (upload → analyze → search → export)
   - Collaborative workflow simulation
   - System resilience under load
   - Data quality and relevance validation
   - Admin configuration testing

### Test Utilities

#### `RAGTestUtils` Class
Specialized utility class for RAG testing operations:

```typescript
class RAGTestUtils {
  enableRAG(): Promise<void>
  performRAGSearch(query: string, expectedMinResults?: number): Promise<number>
  verifyRAGStatus(): Promise<{ operational: boolean; mode: string }>
  performRAGAnalysis(prompt: string): Promise<{ hasAnalysis: boolean; hasCitations: boolean }>
  testCitationInteraction(): Promise<{ canExpand: boolean; canCopy: boolean }>
  validateRAGPerformance(maxSearchTime?: number, maxAnalysisTime?: number): Promise<boolean>
}
```

#### Enhanced Test Infrastructure
- **TestLogger**: Comprehensive logging with file output and annotations
- **TestStepTracker**: Step-by-step execution tracking with timing
- **PerformanceMonitor**: Performance metrics collection and validation
- **ErrorRecovery**: Automatic error context capture and recovery

## Test Categories

### 1. Basic Functionality Tests (`rag.spec.ts`)

#### RAG Toggle Component
- ✅ Display with correct initial state
- ✅ Status information indicators
- ✅ Toggle state changes
- ✅ ARIA accessibility attributes

#### Enhanced Evidence Search
- ✅ Search interface display
- ✅ Different search modes
- ✅ Search suggestions
- ✅ Results export functionality

#### Citations and Sources UI
- ✅ Citation display when available
- ✅ Expandable citation details
- ✅ Citation link copying
- ✅ Source metadata display

#### RAG Analysis Integration
- ✅ Analysis with RAG enabled
- ✅ Confidence scores and grounding
- ✅ Export with citations

### 2. Advanced Features Tests (`rag-advanced.spec.ts`)

#### Backend Integration
- ✅ Backend switching (Azure Search ↔ Cosmos DB)
- ✅ Graceful backend unavailability handling
- ✅ Semantic ranking and hybrid search (Azure Search)
- ✅ Vector search capabilities (Cosmos DB)

#### Performance and Scaling
- ✅ Performance benchmark validation
- ✅ Concurrent operation handling
- ✅ High-volume query processing
- ✅ Result caching optimization

#### Error Handling and Recovery
- ✅ Malformed query handling
- ✅ Network timeout recovery
- ✅ State preservation during errors
- ✅ Graceful degradation

#### Security and Privacy
- ✅ Sensitive data exposure prevention
- ✅ Engagement data isolation
- ✅ Authentication state change handling
- ✅ Audit trail verification

### 3. Integration Tests (`rag-integration.spec.ts`)

#### Complete Workflow Testing
- ✅ Document upload → RAG ingestion
- ✅ RAG-enhanced analysis
- ✅ Evidence search and validation
- ✅ Advanced RAG features
- ✅ Export with RAG data

#### Collaborative Scenarios
- ✅ Multi-user workflow simulation
- ✅ Cross-functional team usage
- ✅ Shared analysis and citations

#### System Resilience
- ✅ Load testing with concurrent operations
- ✅ Rapid sequential operations
- ✅ Backend failover scenarios

#### Data Quality Validation
- ✅ Result relevance scoring
- ✅ Citation accuracy verification
- ✅ Content quality assessment

## Configuration and Setup

### Test Projects (Playwright Configuration)

```typescript
// Basic RAG tests
{
  name: 'rag-basic',
  testMatch: '**/rag.spec.ts',
  timeout: 90_000
}

// Advanced RAG tests
{
  name: 'rag-advanced', 
  testMatch: '**/rag-advanced.spec.ts',
  timeout: 180_000,
  retries: 1
}

// Integration tests
{
  name: 'rag-integration',
  testMatch: '**/rag-integration.spec.ts', 
  timeout: 240_000,
  retries: 1
}

// Cross-browser testing
{
  name: 'rag-firefox',
  use: { ...devices['Desktop Firefox'] },
  testMatch: '**/rag.spec.ts'
}

// Mobile testing
{
  name: 'rag-mobile',
  use: { ...devices['Pixel 5'] },
  testMatch: '**/rag.spec.ts'
}
```

### Environment Configuration

#### Local Development
```bash
export WEB_BASE_URL="http://localhost:3000"
export API_BASE_URL="http://localhost:8000"
export RAG_MODE="demo"
export RAG_FEATURE_FLAG="true"
```

#### Development Environment
```bash
export WEB_BASE_URL="https://dev-web.example.com"
export API_BASE_URL="https://dev-api.example.com"
export RAG_MODE="azure_openai"
export RAG_SEARCH_BACKEND="azure_search"
```

#### Staging Environment
```bash
export WEB_BASE_URL="https://staging-web.example.com"
export API_BASE_URL="https://staging-api.example.com"
export RAG_MODE="azure_openai"
export RAG_SEARCH_BACKEND="azure_search"
export RAG_USE_HYBRID_SEARCH="true"
```

## Running Tests

### Using the Test Runner Script

```bash
# Run all RAG tests
./run-rag-tests.sh local all chromium

# Run basic tests only
./run-rag-tests.sh local basic chromium

# Run advanced tests with visible browser
./run-rag-tests.sh local advanced chromium false

# Run integration tests in staging
./run-rag-tests.sh staging integration firefox

# Run cross-browser tests
./run-rag-tests.sh local cross-browser

# Run mobile tests
./run-rag-tests.sh local mobile

# Run performance tests
./run-rag-tests.sh local performance

# Run security tests
./run-rag-tests.sh local security

# Run smoke tests
./run-rag-tests.sh local smoke
```

### Direct Playwright Commands

```bash
# Run specific RAG test project
npx playwright test --project=rag-basic

# Run with UI mode for debugging
npx playwright test --ui --grep="RAG"

# Run specific test with debug mode
npx playwright test --debug --grep="should perform RAG analysis"

# Run all RAG tests with HTML reporter
npx playwright test --project=rag-basic --project=rag-advanced --project=rag-integration --reporter=html
```

## Test Data and Fixtures

### Sample Test Queries
- "cybersecurity framework implementation"
- "ISO 27001 information security management"
- "NIST cybersecurity framework"
- "GDPR data protection compliance"
- "incident response procedures"
- "vulnerability management process"

### Test Scenarios
1. **Document Analysis**: Analyze security posture based on uploaded documents
2. **Compliance Assessment**: Evaluate compliance gaps with specific frameworks
3. **Risk Evaluation**: Assess organizational risks with evidence grounding
4. **Policy Review**: Review and analyze security policies

## Performance Benchmarks

### Response Time Targets
- **Search Operations**: < 5 seconds
- **Analysis Operations**: < 12 seconds
- **Citation Loading**: < 2 seconds
- **Export Generation**: < 15 seconds

### Concurrency Targets
- **Concurrent Searches**: 5+ simultaneous operations
- **Sequential Operations**: 70%+ success rate under load
- **Backend Failover**: < 10 seconds recovery time

## Accessibility Testing

### ARIA Compliance
- ✅ RAG toggle with proper `role="switch"`
- ✅ Search inputs with `aria-label` attributes
- ✅ Results with semantic markup
- ✅ Citation interactions with keyboard support

### Keyboard Navigation
- ✅ Tab navigation through RAG components
- ✅ Space/Enter key activation
- ✅ Focus management during operations
- ✅ Screen reader compatibility

## Cross-Browser Support

### Desktop Browsers
- ✅ Chrome/Chromium
- ✅ Firefox
- ✅ Safari (via webkit project)
- ✅ Edge (Chromium-based)

### Mobile Browsers
- ✅ Mobile Chrome (Android)
- ✅ Mobile Safari (iOS)
- ✅ Responsive design validation

## Debugging and Troubleshooting

### Common Issues

1. **RAG Toggle Not Found**
   - Check if RAG is enabled in environment
   - Verify feature flags are set correctly
   - Ensure proper authentication

2. **Search Timeouts**
   - Increase test timeouts for slow environments
   - Check backend connectivity
   - Verify network configuration

3. **Citation Display Issues**
   - Ensure test data includes documents with embeddings
   - Check RAG backend configuration
   - Verify analysis includes evidence grounding

### Debug Mode

```bash
# Run with debug mode and slow motion
DEBUG_MODE=true npx playwright test --debug --grep="RAG"

# Capture full traces
npx playwright test --trace=on --grep="RAG"

# Run with custom viewport for mobile debugging
npx playwright test --config=playwright-mobile.config.ts
```

### Log Analysis

Test logs include:
- **Step Execution**: Detailed step timing and results
- **Performance Metrics**: Response times and operation counts
- **Error Context**: Screenshots, HTML, and console logs on failure
- **RAG Status**: Backend configuration and operational status

## CI/CD Integration

### GitHub Actions Integration

```yaml
- name: Run RAG E2E Tests
  run: |
    cd web/e2e
    ./run-rag-tests.sh staging all chromium
  env:
    RAG_MODE: azure_openai
    RAG_FEATURE_FLAG: true
```

### Test Result Artifacts
- **JUnit XML**: `test-results/junit.xml`
- **HTML Report**: `playwright-report/index.html`
- **Screenshots**: `test-results/*.png`
- **Videos**: `test-results/*.webm`
- **Traces**: `test-results/*.zip`

## Maintenance and Updates

### Regular Maintenance Tasks
1. Update test selectors when UI changes
2. Adjust performance thresholds based on infrastructure
3. Add new test scenarios for new RAG features
4. Review and update environment configurations

### Test Health Monitoring
- Monitor test execution times
- Track flaky test patterns
- Validate test coverage for new features
- Review and update test data

## Contributing

### Adding New RAG Tests

1. **Choose appropriate test file**:
   - Basic functionality → `rag.spec.ts`
   - Advanced features → `rag-advanced.spec.ts`
   - End-to-end workflows → `rag-integration.spec.ts`

2. **Use RAG test utilities**:
   ```typescript
   const ragUtils = new RAGTestUtils(page, logger);
   await ragUtils.performRAGSearch('test query');
   ```

3. **Follow test patterns**:
   - Use `stepTracker.executeStep()` for major operations
   - Include appropriate error handling
   - Add performance validation where relevant
   - Test both success and failure scenarios

4. **Update documentation**:
   - Add new test descriptions to this file
   - Update the test runner script if needed
   - Include any new environment requirements

### Code Review Checklist

- [ ] Tests follow existing patterns and utilities
- [ ] Appropriate timeouts and retries configured
- [ ] Error scenarios are tested
- [ ] Performance implications considered
- [ ] Accessibility requirements met
- [ ] Cross-browser compatibility verified
- [ ] Documentation updated