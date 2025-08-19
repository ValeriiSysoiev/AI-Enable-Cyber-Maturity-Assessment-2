# RAG (Retrieval-Augmented Generation) Configuration Guide

This document provides comprehensive guidance for configuring and deploying the RAG system in the AI-Enabled Cyber Maturity Assessment application.

## Overview

The RAG system enhances analysis capabilities by searching through uploaded documents to provide evidence-grounded insights. It supports multiple backend configurations and provides graceful fallback mechanisms.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend UI   │    │   API Gateway   │    │  RAG Retriever  │
│                 │    │                 │    │                 │
│ • Search UI     │────│ • /rag-search   │────│ • Backend       │
│ • Citations     │    │ • /analyze      │    │   Selection     │
│ • Sources Panel │    │ • /recommend    │    │ • Vector Search │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                      │
                                              ┌───────┴───────┐
                                              │               │
                                    ┌─────────────┐ ┌─────────────┐
                                    │Azure Search │ │ Cosmos DB   │
                                    │             │ │             │
                                    │• Production │ │• Development│
                                    │• Semantic   │ │• Brute Force│
                                    │• Vector Idx │ │• Fallback   │
                                    └─────────────┘ └─────────────┘
```

## Configuration Options

### Core RAG Settings

```bash
# Enable/disable RAG functionality
RAG_MODE=azure_openai  # azure_openai|none
RAG_FEATURE_FLAG=true  # Feature flag for gradual rollout

# Search backend selection
RAG_SEARCH_BACKEND=azure_search  # azure_search|cosmos_db

# Search parameters
RAG_SEARCH_TOP_K=10              # Maximum results per search
RAG_SIMILARITY_THRESHOLD=0.7     # Minimum similarity score
RAG_USE_HYBRID_SEARCH=true       # Enable hybrid search (Azure Search)
RAG_RERANK_ENABLED=true          # Enable semantic reranking
```

### Azure OpenAI Configuration

```bash
# Azure OpenAI endpoint and authentication
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key  # Or use managed identity
AZURE_OPENAI_API_VERSION=2024-02-01

# Embedding model configuration
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-large
AZURE_OPENAI_EMBEDDING_DIMENSIONS=3072
AZURE_OPENAI_MAX_TOKENS=8000
```

### Azure Cognitive Search Configuration

```bash
# Azure Search service configuration
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-api-key  # Or use managed identity
AZURE_SEARCH_INDEX_NAME=eng-docs
AZURE_SEARCH_API_VERSION=2024-07-01
```

### Cosmos DB Configuration (Fallback)

```bash
# Cosmos DB configuration for vector storage
COSMOS_ENDPOINT=https://your-cosmos.documents.azure.com:443/
COSMOS_DATABASE=cybermaturity
RAG_COSMOS_CONTAINER=embeddings
```

### Embedding Processing Settings

```bash
# Text chunking configuration
RAG_CHUNK_SIZE=1500               # Tokens per chunk
RAG_CHUNK_OVERLAP=0.1             # 10% overlap between chunks
RAG_BATCH_SIZE=10                 # Documents per batch
RAG_RATE_LIMIT=100                # Requests per minute
RAG_MAX_DOCUMENT_LENGTH=100000    # Max document size
```

## Deployment Configurations

### Production Configuration

**Recommended for production environments:**

```bash
# Production RAG settings
RAG_MODE=azure_openai
RAG_SEARCH_BACKEND=azure_search
RAG_FEATURE_FLAG=true
RAG_RERANK_ENABLED=true
RAG_USE_HYBRID_SEARCH=true

# Azure Search for production
AZURE_SEARCH_ENDPOINT=https://prod-search.search.windows.net
AZURE_SEARCH_INDEX_NAME=production-docs

# Production-grade embedding settings
RAG_CHUNK_SIZE=1500
RAG_SEARCH_TOP_K=10
RAG_SIMILARITY_THRESHOLD=0.7
RAG_RATE_LIMIT=100
```

**Benefits:**
- High-performance vector search with Azure Cognitive Search
- Semantic ranking for better results
- Hybrid search combining keyword and vector search
- Scalable and enterprise-ready

### Development Configuration

**For development and testing:**

```bash
# Development RAG settings
RAG_MODE=azure_openai
RAG_SEARCH_BACKEND=cosmos_db
RAG_FEATURE_FLAG=true
RAG_RERANK_ENABLED=false
RAG_USE_HYBRID_SEARCH=false

# Cosmos DB for development
COSMOS_ENDPOINT=https://dev-cosmos.documents.azure.com:443/
RAG_COSMOS_CONTAINER=embeddings-dev

# Development-friendly settings
RAG_CHUNK_SIZE=800
RAG_SEARCH_TOP_K=5
RAG_SIMILARITY_THRESHOLD=0.6
RAG_RATE_LIMIT=50
```

**Benefits:**
- Simpler setup with Cosmos DB
- Lower resource requirements
- Easier debugging and testing
- Cost-effective for development

### Disabled Configuration

**To disable RAG functionality:**

```bash
# Disable RAG
RAG_MODE=none
RAG_FEATURE_FLAG=false

# All other RAG_* variables can be omitted
```

## Feature Flags

### Gradual Rollout Strategy

Use feature flags to control RAG availability:

1. **Development Phase**: `RAG_FEATURE_FLAG=true` for dev environments only
2. **Limited Beta**: Enable for specific engagements or user groups
3. **Full Rollout**: Enable for all users

### Environment-Specific Flags

```bash
# Production
RAG_FEATURE_FLAG=true
RAG_MODE=azure_openai

# Staging
RAG_FEATURE_FLAG=true
RAG_MODE=azure_openai

# Development
RAG_FEATURE_FLAG=true
RAG_MODE=azure_openai

# Demo
RAG_FEATURE_FLAG=false  # Simplified demo without RAG
RAG_MODE=none
```

## Security Considerations

### Authentication

1. **Managed Identity (Recommended)**:
   ```bash
   # No API keys needed - use Azure managed identity
   # Remove AZURE_OPENAI_API_KEY and AZURE_SEARCH_API_KEY
   ```

2. **API Keys (Alternative)**:
   ```bash
   AZURE_OPENAI_API_KEY=your-openai-key
   AZURE_SEARCH_API_KEY=your-search-key
   ```

### Access Control

- RAG endpoints respect existing engagement-based access controls
- Document search is automatically filtered by engagement membership
- Admin endpoints require proper authentication

### Data Privacy

- Embeddings are stored with engagement isolation
- Documents are processed in-memory only
- No data is sent to external services beyond configured Azure services

## Monitoring and Observability

### Health Checks

The system provides several monitoring endpoints:

1. **RAG Status**: `/api/admin/status` - Overall system status
2. **Performance Metrics**: `/api/performance/metrics` - Detailed performance data

### Key Metrics

Monitor these metrics for RAG performance:

- **Search Latency**: Time to retrieve results
- **Embedding Success Rate**: Document ingestion success
- **Search Result Quality**: Average relevance scores
- **Backend Availability**: Azure Search vs Cosmos DB usage

### Logging

RAG operations are logged with structured data:

```json
{
  "operation": "search",
  "backend": "azure_search",
  "engagement_id": "eng-123",
  "results_found": 5,
  "duration_seconds": 0.45,
  "correlation_id": "req-456"
}
```

## Troubleshooting

### Common Issues

1. **RAG Not Operational**
   - Check `RAG_MODE=azure_openai`
   - Verify Azure service connectivity
   - Check managed identity permissions

2. **Poor Search Results**
   - Lower `RAG_SIMILARITY_THRESHOLD`
   - Increase `RAG_SEARCH_TOP_K`
   - Check document ingestion status

3. **Slow Performance**
   - Monitor Azure Search SKU
   - Check embedding batch sizes
   - Review rate limiting settings

4. **High Costs**
   - Optimize chunk sizes
   - Implement caching
   - Review embedding model usage

### Debugging Commands

```bash
# Check RAG configuration
curl -H "X-User-Email: admin@example.com" \
     -H "X-Engagement-ID: test" \
     /api/admin/status

# Test document search
curl -X POST -H "Content-Type: application/json" \
     -H "X-User-Email: user@example.com" \
     -H "X-Engagement-ID: eng-123" \
     -d '{"query": "test search", "top_k": 5}' \
     /api/proxy/orchestrations/rag-search

# Check performance metrics
curl /api/performance/metrics?time_window_minutes=60
```

## Migration Guide

### From Cosmos DB to Azure Search

1. **Phase 1**: Deploy with both backends available
   ```bash
   RAG_SEARCH_BACKEND=cosmos_db  # Current
   ```

2. **Phase 2**: Create Azure Search index
   ```bash
   # Use admin endpoints to create index
   curl -X POST /api/admin/rag/index/create
   ```

3. **Phase 3**: Migrate data
   ```bash
   # Bulk reindex all documents
   curl -X POST -H "Content-Type: application/json" \
        -d '{"engagement_id": "*", "force": true}' \
        /api/admin/rag/reindex
   ```

4. **Phase 4**: Switch backend
   ```bash
   RAG_SEARCH_BACKEND=azure_search  # New
   ```

5. **Phase 5**: Verify and cleanup
   ```bash
   # Test search functionality
   # Monitor performance metrics
   # Clean up old Cosmos data if needed
   ```

## Performance Tuning

### Azure Search Optimization

1. **Index Configuration**:
   - Use appropriate SKU (Standard S1+ for production)
   - Configure semantic search
   - Optimize field configurations

2. **Query Optimization**:
   - Use hybrid search for best results
   - Enable semantic ranking
   - Fine-tune similarity thresholds

### Embedding Optimization

1. **Chunk Size Tuning**:
   - Smaller chunks (800-1200 tokens): Better precision
   - Larger chunks (1500-2000 tokens): Better context

2. **Batch Processing**:
   - Optimize batch sizes for Azure API limits
   - Implement retry logic with exponential backoff
   - Monitor rate limiting

## Cost Management

### Optimization Strategies

1. **Model Selection**:
   - `text-embedding-3-large`: Best quality, higher cost
   - `text-embedding-3-small`: Good quality, lower cost

2. **Search Optimization**:
   - Cache frequent queries
   - Implement result pagination
   - Optimize top_k values

3. **Storage Optimization**:
   - Regular cleanup of old embeddings
   - Compress metadata where possible
   - Use appropriate Cosmos DB throughput

### Cost Monitoring

Track costs across:
- Azure OpenAI API calls
- Azure Search queries
- Cosmos DB operations
- Storage usage

## API Reference

### RAG Search Endpoint

```http
POST /api/proxy/orchestrations/rag-search
Content-Type: application/json
X-User-Email: user@example.com
X-Engagement-ID: engagement-123

{
  "query": "What are the security controls?",
  "top_k": 10,
  "score_threshold": 0.7,
  "use_grounding": true
}
```

### Enhanced Analysis Endpoint

```http
POST /api/proxy/orchestrations/analyze
Content-Type: application/json
X-User-Email: user@example.com
X-Engagement-ID: engagement-123

{
  "assessment_id": "assessment-456",
  "content": "Analyze this content",
  "use_evidence": true
}
```

### Admin Endpoints

```http
# Get RAG status
GET /api/admin/rag/status

# Create search index
POST /api/admin/rag/index/create

# Bulk reindex documents
POST /api/admin/rag/reindex
{
  "engagement_id": "engagement-123",
  "force": true
}
```

## Best Practices

### Configuration Management

1. **Environment Variables**: Use environment-specific configurations
2. **Secrets Management**: Store API keys in Azure Key Vault
3. **Monitoring**: Implement comprehensive logging and metrics
4. **Testing**: Test RAG functionality in staging before production

### Operational Excellence

1. **Backup Strategy**: Regular backup of search indexes and embeddings
2. **Disaster Recovery**: Multi-region deployment for critical workloads
3. **Capacity Planning**: Monitor usage and scale proactively
4. **Security**: Regular security reviews and access audits

### Development Workflow

1. **Local Development**: Use Cosmos DB backend for easier setup
2. **Testing**: Comprehensive unit and integration tests
3. **Deployment**: Gradual rollout with feature flags
4. **Monitoring**: Real-time monitoring and alerting

This configuration guide provides the foundation for successfully deploying and managing the RAG system in your AI-Enabled Cyber Maturity Assessment application.