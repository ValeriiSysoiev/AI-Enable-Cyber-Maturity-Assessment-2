"""CSF 2.0 Taxonomy Service

Fast, cached access to NIST Cybersecurity Framework 2.0 taxonomy data.
Provides structured access to Functions, Categories, and Subcategories.
"""

import json
import os
from functools import lru_cache
from typing import List, Optional, Dict
from pathlib import Path

from app.domain.models import CSFFunction, CSFCategory, CSFSubcategory
from app.util.logging import get_logger

logger = get_logger(__name__)

class CSFTaxonomyService:
    """Service for loading and accessing CSF 2.0 taxonomy data"""
    
    def __init__(self):
        self._taxonomy_cache: Optional[Dict] = None
        self._functions_cache: Optional[List[CSFFunction]] = None
        
    def _get_data_path(self) -> Path:
        """Get path to CSF 2.0 data file"""
        current_dir = Path(__file__).parent.parent
        return current_dir / "data" / "csf2.json"
    
    @lru_cache(maxsize=1)
    def load_csf_taxonomy(self) -> Dict:
        """Load CSF taxonomy from JSON file with caching"""
        data_path = self._get_data_path()
        
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                taxonomy_data = json.load(f)
            
            logger.info(f"Loaded CSF 2.0 taxonomy from {data_path}")
            return taxonomy_data
            
        except FileNotFoundError:
            logger.error(f"CSF 2.0 taxonomy file not found: {data_path}")
            raise FileNotFoundError(f"CSF taxonomy file not found: {data_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in CSF taxonomy file: {e}")
            raise ValueError(f"Invalid JSON in CSF taxonomy file: {e}")
    
    def get_functions(self) -> List[CSFFunction]:
        """Get all CSF functions with nested categories and subcategories"""
        if self._functions_cache is not None:
            return self._functions_cache
            
        taxonomy = self.load_csf_taxonomy()
        functions = []
        
        for func_data in taxonomy.get('functions', []):
            categories = []
            
            for cat_data in func_data.get('categories', []):
                subcategories = [
                    CSFSubcategory(
                        id=sub['id'],
                        function_id=func_data['id'],
                        category_id=cat_data['id'],
                        title=sub['title'],
                        description=sub['description']
                    )
                    for sub in cat_data.get('subcategories', [])
                ]
                
                category = CSFCategory(
                    id=cat_data['id'],
                    function_id=func_data['id'],
                    title=cat_data['title'],
                    description=cat_data['description'],
                    subcategories=subcategories
                )
                categories.append(category)
            
            function = CSFFunction(
                id=func_data['id'],
                title=func_data['title'],
                description=func_data['description'],
                categories=categories
            )
            functions.append(function)
        
        self._functions_cache = functions
        logger.info(f"Cached {len(functions)} CSF functions with full taxonomy")
        return functions
    
    def get_categories(self, function_id: Optional[str] = None) -> List[CSFCategory]:
        """Get all categories, optionally filtered by function"""
        functions = self.get_functions()
        categories = []
        
        for function in functions:
            if function_id is None or function.id == function_id:
                categories.extend(function.categories)
        
        return categories
    
    def get_subcategories(self, function_id: Optional[str] = None, 
                         category_id: Optional[str] = None) -> List[CSFSubcategory]:
        """Get all subcategories, optionally filtered by function and/or category"""
        categories = self.get_categories(function_id)
        subcategories = []
        
        for category in categories:
            if category_id is None or category.id == category_id:
                subcategories.extend(category.subcategories)
        
        return subcategories
    
    def get_function_by_id(self, function_id: str) -> Optional[CSFFunction]:
        """Get a specific function by ID"""
        functions = self.get_functions()
        return next((f for f in functions if f.id == function_id), None)
    
    def get_category_by_id(self, category_id: str) -> Optional[CSFCategory]:
        """Get a specific category by ID"""
        categories = self.get_categories()
        return next((c for c in categories if c.id == category_id), None)
    
    def get_subcategory_by_id(self, subcategory_id: str) -> Optional[CSFSubcategory]:
        """Get a specific subcategory by ID"""
        subcategories = self.get_subcategories()
        return next((s for s in subcategories if s.id == subcategory_id), None)


# Singleton instance for global access
_csf_service: Optional[CSFTaxonomyService] = None

def get_csf_service() -> CSFTaxonomyService:
    """Get singleton CSF taxonomy service instance"""
    global _csf_service
    if _csf_service is None:
        _csf_service = CSFTaxonomyService()
    return _csf_service