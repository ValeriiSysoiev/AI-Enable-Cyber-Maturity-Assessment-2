#!/usr/bin/env python3
"""
RAG Configuration Validation Script

Validates RAG configuration settings and Azure service connectivity.
Provides recommendations for optimal configuration.
"""

import os
import sys
import json
import asyncio
import aiohttp
import argparse
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class ValidationLevel(Enum):
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"

@dataclass
class ValidationResult:
    level: ValidationLevel
    category: str
    message: str
    recommendation: Optional[str] = None

class RAGConfigValidator:
    """Validates RAG configuration and Azure service connectivity"""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, str]:
        """Load configuration from environment variables"""
        return {
            # Core RAG settings
            'RAG_MODE': os.getenv('RAG_MODE', 'none'),
            'RAG_FEATURE_FLAG': os.getenv('RAG_FEATURE_FLAG', 'false'),
            'RAG_SEARCH_BACKEND': os.getenv('RAG_SEARCH_BACKEND', 'cosmos_db'),
            
            # Search parameters
            'RAG_SEARCH_TOP_K': os.getenv('RAG_SEARCH_TOP_K', '5'),
            'RAG_SIMILARITY_THRESHOLD': os.getenv('RAG_SIMILARITY_THRESHOLD', '0.5'),
            'RAG_USE_HYBRID_SEARCH': os.getenv('RAG_USE_HYBRID_SEARCH', 'false'),
            'RAG_RERANK_ENABLED': os.getenv('RAG_RERANK_ENABLED', 'false'),
            
            # Embedding settings
            'RAG_CHUNK_SIZE': os.getenv('RAG_CHUNK_SIZE', '800'),
            'RAG_CHUNK_OVERLAP': os.getenv('RAG_CHUNK_OVERLAP', '0.2'),
            'RAG_RATE_LIMIT': os.getenv('RAG_RATE_LIMIT', '25'),
            'RAG_MAX_DOCUMENT_LENGTH': os.getenv('RAG_MAX_DOCUMENT_LENGTH', '25000'),
            
            # Azure OpenAI
            'AZURE_OPENAI_ENDPOINT': os.getenv('AZURE_OPENAI_ENDPOINT', ''),
            'AZURE_OPENAI_API_KEY': os.getenv('AZURE_OPENAI_API_KEY', ''),
            'AZURE_OPENAI_EMBEDDING_DEPLOYMENT': os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', ''),
            'AZURE_OPENAI_EMBEDDING_MODEL': os.getenv('AZURE_OPENAI_EMBEDDING_MODEL', ''),
            'AZURE_OPENAI_EMBEDDING_DIMENSIONS': os.getenv('AZURE_OPENAI_EMBEDDING_DIMENSIONS', '3072'),
            
            # Azure Search
            'AZURE_SEARCH_ENDPOINT': os.getenv('AZURE_SEARCH_ENDPOINT', ''),
            'AZURE_SEARCH_API_KEY': os.getenv('AZURE_SEARCH_API_KEY', ''),
            'AZURE_SEARCH_INDEX_NAME': os.getenv('AZURE_SEARCH_INDEX_NAME', 'eng-docs'),
            
            # Cosmos DB
            'COSMOS_ENDPOINT': os.getenv('COSMOS_ENDPOINT', ''),
            'COSMOS_DATABASE': os.getenv('COSMOS_DATABASE', 'cybermaturity'),
            'RAG_COSMOS_CONTAINER': os.getenv('RAG_COSMOS_CONTAINER', 'embeddings'),
            
            # Environment info
            'BUILD_ENV': os.getenv('BUILD_ENV', os.getenv('ENVIRONMENT', 'development'))
        }
    
    def add_result(self, level: ValidationLevel, category: str, message: str, recommendation: str = None):
        """Add a validation result"""
        self.results.append(ValidationResult(level, category, message, recommendation))
    
    def validate_core_settings(self):
        """Validate core RAG configuration settings"""
        rag_mode = self.config['RAG_MODE']
        feature_flag = self.config['RAG_FEATURE_FLAG'].lower()
        search_backend = self.config['RAG_SEARCH_BACKEND']
        
        # Check RAG mode
        if rag_mode not in ['azure_openai', 'none']:
            self.add_result(
                ValidationLevel.ERROR,
                "Core Config",
                f"Invalid RAG_MODE: {rag_mode}",
                "Set RAG_MODE to 'azure_openai' or 'none'"
            )
        
        # Check feature flag consistency
        if rag_mode == 'azure_openai' and feature_flag != 'true':
            self.add_result(
                ValidationLevel.WARNING,
                "Core Config", 
                "RAG_MODE is enabled but RAG_FEATURE_FLAG is not true",
                "Set RAG_FEATURE_FLAG=true when RAG_MODE=azure_openai"
            )
        
        if rag_mode == 'none' and feature_flag == 'true':
            self.add_result(
                ValidationLevel.WARNING,
                "Core Config",
                "RAG_FEATURE_FLAG is true but RAG_MODE is none", 
                "Set RAG_FEATURE_FLAG=false when RAG_MODE=none"
            )
        
        # Check search backend
        if search_backend not in ['azure_search', 'cosmos_db']:
            self.add_result(
                ValidationLevel.ERROR,
                "Core Config",
                f"Invalid RAG_SEARCH_BACKEND: {search_backend}",
                "Set RAG_SEARCH_BACKEND to 'azure_search' or 'cosmos_db'"
            )
        
        # Environment-specific recommendations
        env = self.config['BUILD_ENV'].lower()
        if env in ['production', 'prod'] and search_backend != 'azure_search':
            self.add_result(
                ValidationLevel.WARNING,
                "Core Config",
                "Production environment should use Azure Search backend",
                "Set RAG_SEARCH_BACKEND=azure_search for production"
            )
    
    def validate_search_parameters(self):
        """Validate search-related parameters"""
        try:
            top_k = int(self.config['RAG_SEARCH_TOP_K'])
            if top_k < 1 or top_k > 50:
                self.add_result(
                    ValidationLevel.WARNING,
                    "Search Config",
                    f"RAG_SEARCH_TOP_K ({top_k}) outside recommended range",
                    "Set RAG_SEARCH_TOP_K between 5-20 for optimal performance"
                )
        except ValueError:
            self.add_result(
                ValidationLevel.ERROR,
                "Search Config", 
                f"Invalid RAG_SEARCH_TOP_K: {self.config['RAG_SEARCH_TOP_K']}",
                "Set RAG_SEARCH_TOP_K to a positive integer"
            )
        
        try:
            threshold = float(self.config['RAG_SIMILARITY_THRESHOLD'])
            if threshold < 0.0 or threshold > 1.0:
                self.add_result(
                    ValidationLevel.ERROR,
                    "Search Config",
                    f"RAG_SIMILARITY_THRESHOLD ({threshold}) outside valid range",
                    "Set RAG_SIMILARITY_THRESHOLD between 0.0-1.0"
                )
            elif threshold < 0.3:
                self.add_result(
                    ValidationLevel.WARNING,
                    "Search Config",
                    f"RAG_SIMILARITY_THRESHOLD ({threshold}) very low",
                    "Consider threshold >= 0.5 for better result quality"
                )
        except ValueError:
            self.add_result(
                ValidationLevel.ERROR,
                "Search Config",
                f"Invalid RAG_SIMILARITY_THRESHOLD: {self.config['RAG_SIMILARITY_THRESHOLD']}",
                "Set RAG_SIMILARITY_THRESHOLD to a decimal between 0.0-1.0"
            )
    
    def validate_embedding_settings(self):
        """Validate embedding and chunking settings"""
        try:
            chunk_size = int(self.config['RAG_CHUNK_SIZE'])
            if chunk_size < 100 or chunk_size > 3000:
                self.add_result(
                    ValidationLevel.WARNING,
                    "Embedding Config",
                    f"RAG_CHUNK_SIZE ({chunk_size}) outside recommended range",
                    "Set RAG_CHUNK_SIZE between 800-1500 for optimal performance"
                )
        except ValueError:
            self.add_result(
                ValidationLevel.ERROR,
                "Embedding Config",
                f"Invalid RAG_CHUNK_SIZE: {self.config['RAG_CHUNK_SIZE']}",
                "Set RAG_CHUNK_SIZE to a positive integer"
            )
        
        try:
            overlap = float(self.config['RAG_CHUNK_OVERLAP'])
            if overlap < 0.0 or overlap > 0.5:
                self.add_result(
                    ValidationLevel.WARNING,
                    "Embedding Config", 
                    f"RAG_CHUNK_OVERLAP ({overlap}) outside recommended range",
                    "Set RAG_CHUNK_OVERLAP between 0.1-0.2 (10-20%)"
                )
        except ValueError:
            self.add_result(
                ValidationLevel.ERROR,
                "Embedding Config",
                f"Invalid RAG_CHUNK_OVERLAP: {self.config['RAG_CHUNK_OVERLAP']}",
                "Set RAG_CHUNK_OVERLAP to a decimal between 0.0-0.5"
            )
        
        try:
            rate_limit = int(self.config['RAG_RATE_LIMIT'])
            env = self.config['BUILD_ENV'].lower()
            if env in ['production', 'prod'] and rate_limit < 50:
                self.add_result(
                    ValidationLevel.WARNING,
                    "Embedding Config",
                    f"RAG_RATE_LIMIT ({rate_limit}) low for production",
                    "Consider RAG_RATE_LIMIT >= 100 for production workloads"
                )
        except ValueError:
            self.add_result(
                ValidationLevel.ERROR,
                "Embedding Config",
                f"Invalid RAG_RATE_LIMIT: {self.config['RAG_RATE_LIMIT']}",
                "Set RAG_RATE_LIMIT to a positive integer"
            )
    
    def validate_azure_openai_config(self):
        """Validate Azure OpenAI configuration"""
        if self.config['RAG_MODE'] != 'azure_openai':
            return
        
        endpoint = self.config['AZURE_OPENAI_ENDPOINT']
        api_key = self.config['AZURE_OPENAI_API_KEY']
        deployment = self.config['AZURE_OPENAI_EMBEDDING_DEPLOYMENT']
        model = self.config['AZURE_OPENAI_EMBEDDING_MODEL']
        
        if not endpoint:
            self.add_result(
                ValidationLevel.ERROR,
                "Azure OpenAI",
                "AZURE_OPENAI_ENDPOINT not configured",
                "Set AZURE_OPENAI_ENDPOINT to your Azure OpenAI service URL"
            )
        elif not endpoint.startswith('https://'):
            self.add_result(
                ValidationLevel.ERROR,
                "Azure OpenAI",
                "AZURE_OPENAI_ENDPOINT must use HTTPS",
                "Update AZURE_OPENAI_ENDPOINT to use https://"
            )
        
        if not api_key:
            self.add_result(
                ValidationLevel.WARNING,
                "Azure OpenAI",
                "AZURE_OPENAI_API_KEY not configured",
                "Set AZURE_OPENAI_API_KEY or configure managed identity"
            )
        
        if not deployment:
            self.add_result(
                ValidationLevel.ERROR,
                "Azure OpenAI",
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT not configured",
                "Set AZURE_OPENAI_EMBEDDING_DEPLOYMENT to your deployment name"
            )
        
        if not model:
            self.add_result(
                ValidationLevel.ERROR,
                "Azure OpenAI",
                "AZURE_OPENAI_EMBEDDING_MODEL not configured",
                "Set AZURE_OPENAI_EMBEDDING_MODEL (e.g., text-embedding-3-large)"
            )
        
        # Validate embedding dimensions
        try:
            dimensions = int(self.config['AZURE_OPENAI_EMBEDDING_DIMENSIONS'])
            known_dimensions = {
                'text-embedding-3-large': 3072,
                'text-embedding-3-small': 1536,
                'text-embedding-ada-002': 1536
            }
            
            if model in known_dimensions and dimensions != known_dimensions[model]:
                self.add_result(
                    ValidationLevel.WARNING,
                    "Azure OpenAI",
                    f"Embedding dimensions ({dimensions}) may not match model {model}",
                    f"Consider setting AZURE_OPENAI_EMBEDDING_DIMENSIONS={known_dimensions[model]} for {model}"
                )
        except ValueError:
            self.add_result(
                ValidationLevel.ERROR,
                "Azure OpenAI",
                f"Invalid AZURE_OPENAI_EMBEDDING_DIMENSIONS: {self.config['AZURE_OPENAI_EMBEDDING_DIMENSIONS']}",
                "Set AZURE_OPENAI_EMBEDDING_DIMENSIONS to a positive integer"
            )
    
    def validate_azure_search_config(self):
        """Validate Azure Search configuration"""
        if self.config['RAG_SEARCH_BACKEND'] != 'azure_search':
            return
        
        endpoint = self.config['AZURE_SEARCH_ENDPOINT']
        api_key = self.config['AZURE_SEARCH_API_KEY']
        index_name = self.config['AZURE_SEARCH_INDEX_NAME']
        
        if not endpoint:
            self.add_result(
                ValidationLevel.ERROR,
                "Azure Search",
                "AZURE_SEARCH_ENDPOINT not configured",
                "Set AZURE_SEARCH_ENDPOINT to your Azure Search service URL"
            )
        elif not endpoint.startswith('https://'):
            self.add_result(
                ValidationLevel.ERROR,
                "Azure Search",
                "AZURE_SEARCH_ENDPOINT must use HTTPS",
                "Update AZURE_SEARCH_ENDPOINT to use https://"
            )
        
        if not api_key:
            self.add_result(
                ValidationLevel.WARNING,
                "Azure Search",
                "AZURE_SEARCH_API_KEY not configured",
                "Set AZURE_SEARCH_API_KEY or configure managed identity"
            )
        
        if not index_name:
            self.add_result(
                ValidationLevel.ERROR,
                "Azure Search",
                "AZURE_SEARCH_INDEX_NAME not configured",
                "Set AZURE_SEARCH_INDEX_NAME to your search index name"
            )
    
    def validate_cosmos_config(self):
        """Validate Cosmos DB configuration"""
        if self.config['RAG_SEARCH_BACKEND'] != 'cosmos_db':
            return
        
        endpoint = self.config['COSMOS_ENDPOINT']
        database = self.config['COSMOS_DATABASE']
        container = self.config['RAG_COSMOS_CONTAINER']
        
        if not endpoint:
            self.add_result(
                ValidationLevel.ERROR,
                "Cosmos DB",
                "COSMOS_ENDPOINT not configured",
                "Set COSMOS_ENDPOINT to your Cosmos DB account URL"
            )
        elif not endpoint.startswith('https://'):
            self.add_result(
                ValidationLevel.ERROR,
                "Cosmos DB",
                "COSMOS_ENDPOINT must use HTTPS",
                "Update COSMOS_ENDPOINT to use https://"
            )
        
        if not database:
            self.add_result(
                ValidationLevel.WARNING,
                "Cosmos DB",
                "COSMOS_DATABASE not configured, using default",
                "Set COSMOS_DATABASE to your database name"
            )
        
        if not container:
            self.add_result(
                ValidationLevel.WARNING,
                "Cosmos DB",
                "RAG_COSMOS_CONTAINER not configured, using default",
                "Set RAG_COSMOS_CONTAINER to your container name"
            )
    
    async def test_azure_openai_connectivity(self):
        """Test Azure OpenAI service connectivity"""
        if self.config['RAG_MODE'] != 'azure_openai':
            return
        
        endpoint = self.config['AZURE_OPENAI_ENDPOINT']
        api_key = self.config['AZURE_OPENAI_API_KEY']
        
        if not endpoint or not api_key:
            return
        
        try:
            headers = {
                'api-key': api_key,
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                # Test basic connectivity
                async with session.get(f"{endpoint}/openai/deployments", headers=headers, timeout=10) as response:
                    if response.status == 200:
                        self.add_result(
                            ValidationLevel.INFO,
                            "Connectivity",
                            "Azure OpenAI endpoint accessible",
                            None
                        )
                        
                        # Check if embedding deployment exists
                        deployments = await response.json()
                        deployment_names = [d['id'] for d in deployments.get('data', [])]
                        
                        target_deployment = self.config['AZURE_OPENAI_EMBEDDING_DEPLOYMENT']
                        if target_deployment and target_deployment not in deployment_names:
                            self.add_result(
                                ValidationLevel.WARNING,
                                "Connectivity",
                                f"Embedding deployment '{target_deployment}' not found",
                                f"Available deployments: {', '.join(deployment_names)}"
                            )
                        elif target_deployment:
                            self.add_result(
                                ValidationLevel.INFO,
                                "Connectivity",
                                f"Embedding deployment '{target_deployment}' found",
                                None
                            )
                    else:
                        self.add_result(
                            ValidationLevel.ERROR,
                            "Connectivity",
                            f"Azure OpenAI endpoint returned status {response.status}",
                            "Check endpoint URL and API key"
                        )
        except asyncio.TimeoutError:
            self.add_result(
                ValidationLevel.WARNING,
                "Connectivity",
                "Azure OpenAI endpoint timeout",
                "Check network connectivity and endpoint URL"
            )
        except Exception as e:
            self.add_result(
                ValidationLevel.WARNING,
                "Connectivity",
                f"Azure OpenAI connectivity test failed: {str(e)}",
                "Check endpoint URL, API key, and network connectivity"
            )
    
    async def test_azure_search_connectivity(self):
        """Test Azure Search service connectivity"""
        if self.config['RAG_SEARCH_BACKEND'] != 'azure_search':
            return
        
        endpoint = self.config['AZURE_SEARCH_ENDPOINT']
        api_key = self.config['AZURE_SEARCH_API_KEY']
        index_name = self.config['AZURE_SEARCH_INDEX_NAME']
        
        if not endpoint or not api_key:
            return
        
        try:
            headers = {
                'api-key': api_key,
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                # Test service connectivity
                async with session.get(f"{endpoint}/indexes", headers=headers, timeout=10) as response:
                    if response.status == 200:
                        self.add_result(
                            ValidationLevel.INFO,
                            "Connectivity",
                            "Azure Search endpoint accessible",
                            None
                        )
                        
                        # Check if index exists
                        indexes = await response.json()
                        index_names = [idx['name'] for idx in indexes.get('value', [])]
                        
                        if index_name not in index_names:
                            self.add_result(
                                ValidationLevel.WARNING,
                                "Connectivity",
                                f"Search index '{index_name}' not found",
                                "Create the search index before using Azure Search backend"
                            )
                        else:
                            self.add_result(
                                ValidationLevel.INFO,
                                "Connectivity",
                                f"Search index '{index_name}' found",
                                None
                            )
                    else:
                        self.add_result(
                            ValidationLevel.ERROR,
                            "Connectivity",
                            f"Azure Search endpoint returned status {response.status}",
                            "Check endpoint URL and API key"
                        )
        except asyncio.TimeoutError:
            self.add_result(
                ValidationLevel.WARNING,
                "Connectivity",
                "Azure Search endpoint timeout",
                "Check network connectivity and endpoint URL"
            )
        except Exception as e:
            self.add_result(
                ValidationLevel.WARNING,
                "Connectivity",
                f"Azure Search connectivity test failed: {str(e)}",
                "Check endpoint URL, API key, and network connectivity"
            )
    
    async def validate_all(self, test_connectivity: bool = True):
        """Run all validation checks"""
        self.validate_core_settings()
        self.validate_search_parameters()
        self.validate_embedding_settings()
        self.validate_azure_openai_config()
        self.validate_azure_search_config()
        self.validate_cosmos_config()
        
        if test_connectivity:
            await self.test_azure_openai_connectivity()
            await self.test_azure_search_connectivity()
    
    def print_results(self, show_config: bool = False):
        """Print validation results"""
        if show_config:
            print("🔧 Current RAG Configuration")
            print("=" * 50)
            for key, value in self.config.items():
                if 'api_key' in key.lower() or 'key' in key.lower():
                    display_value = '*' * 8 if value else '<not set>'
                else:
                    display_value = value if value else '<not set>'
                print(f"{key:35}: {display_value}")
            print()
        
        print("🔍 Validation Results")
        print("=" * 50)
        
        if not self.results:
            print("✅ No validation issues found!")
            return
        
        # Group results by level
        errors = [r for r in self.results if r.level == ValidationLevel.ERROR]
        warnings = [r for r in self.results if r.level == ValidationLevel.WARNING]
        info = [r for r in self.results if r.level == ValidationLevel.INFO]
        
        # Print errors
        if errors:
            print(f"\n❌ ERRORS ({len(errors)}):")
            for result in errors:
                print(f"   [{result.category}] {result.message}")
                if result.recommendation:
                    print(f"   💡 {result.recommendation}")
                print()
        
        # Print warnings
        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for result in warnings:
                print(f"   [{result.category}] {result.message}")
                if result.recommendation:
                    print(f"   💡 {result.recommendation}")
                print()
        
        # Print info
        if info:
            print(f"\n✅ INFO ({len(info)}):")
            for result in info:
                print(f"   [{result.category}] {result.message}")
                print()
        
        # Summary
        print("📊 Summary")
        print("-" * 20)
        print(f"Errors: {len(errors)}")
        print(f"Warnings: {len(warnings)}")
        print(f"Info: {len(info)}")
        
        if errors:
            print(f"\n🚨 {len(errors)} error(s) must be fixed before RAG can function properly!")
        elif warnings:
            print(f"\n⚠️  {len(warnings)} warning(s) should be addressed for optimal performance.")
        else:
            print(f"\n🎉 Configuration looks good!")
    
    def export_results(self, filename: str):
        """Export validation results to JSON file"""
        export_data = {
            'timestamp': os.popen('date -Iseconds').read().strip(),
            'config': self.config,
            'results': [
                {
                    'level': result.level.value,
                    'category': result.category,
                    'message': result.message,
                    'recommendation': result.recommendation
                }
                for result in self.results
            ],
            'summary': {
                'total_checks': len(self.results),
                'errors': len([r for r in self.results if r.level == ValidationLevel.ERROR]),
                'warnings': len([r for r in self.results if r.level == ValidationLevel.WARNING]),
                'info': len([r for r in self.results if r.level == ValidationLevel.INFO])
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"📄 Results exported to {filename}")

async def main():
    parser = argparse.ArgumentParser(description='Validate RAG configuration')
    parser.add_argument('--show-config', action='store_true', help='Show current configuration')
    parser.add_argument('--no-connectivity', action='store_true', help='Skip connectivity tests')
    parser.add_argument('--export', help='Export results to JSON file')
    
    args = parser.parse_args()
    
    validator = RAGConfigValidator()
    
    print("🔧 RAG Configuration Validator")
    print("=" * 50)
    
    await validator.validate_all(test_connectivity=not args.no_connectivity)
    validator.print_results(show_config=args.show_config)
    
    if args.export:
        validator.export_results(args.export)
    
    # Exit with error code if there are errors
    errors = [r for r in validator.results if r.level == ValidationLevel.ERROR]
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    asyncio.run(main())