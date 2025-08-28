"""
CSF 2.0 Grid API

Provides fast access to NIST Cybersecurity Framework 2.0 taxonomy data
including Functions, Categories, and Subcategories for assessment grid structures.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from domain.models import CSFFunction, CSFCategory, CSFSubcategory
from services.csf_taxonomy import get_csf_service
import logging


router = APIRouter(prefix="/api/v1/csf", tags=["csf"])
logger = logging.getLogger(__name__)


class CSFTaxonomyResponse(BaseModel):
    """Full CSF 2.0 taxonomy response"""
    version: str
    functions: List[CSFFunction]
    metadata: dict


class CSFErrorResponse(BaseModel):
    """Error response for CSF endpoints"""
    error: str
    details: Optional[str] = None


def get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request headers"""
    return request.headers.get("X-Correlation-ID", "csf-request")


@router.get("/functions", response_model=CSFTaxonomyResponse)
async def get_csf_functions(request: Request):
    """
    Get complete CSF 2.0 taxonomy with Functions → Categories → Subcategories.
    
    Returns the full hierarchical structure of NIST CSF 2.0 framework
    optimized for grid-based assessment interfaces.
    
    Response is cached for performance with p95 < 2s target.
    """
    correlation_id = get_correlation_id(request)
    
    try:
        logger.info(
            "CSF functions endpoint accessed",
            extra={"correlation_id": correlation_id}
        )
        
        # Get CSF service and load taxonomy
        csf_service = get_csf_service()
        functions = csf_service.get_functions()
        
        # Get version and metadata from raw taxonomy
        taxonomy_data = csf_service.load_csf_taxonomy()
        
        response = CSFTaxonomyResponse(
            version=taxonomy_data.get("version", "2.0"),
            functions=functions,
            metadata=taxonomy_data.get("metadata", {})
        )
        
        logger.info(
            "CSF taxonomy loaded successfully",
            extra={
                "correlation_id": correlation_id,
                "functions_count": len(functions),
                "categories_count": sum(len(f.categories) for f in functions),
                "subcategories_count": sum(
                    len(c.subcategories) for f in functions for c in f.categories
                )
            }
        )
        
        return response
        
    except FileNotFoundError as e:
        logger.error(
            "CSF taxonomy file not found",
            extra={
                "correlation_id": correlation_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail="CSF taxonomy data not available"
        )
        
    except ValueError as e:
        logger.error(
            "Invalid CSF taxonomy data",
            extra={
                "correlation_id": correlation_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Invalid CSF taxonomy format"
        )
        
    except Exception as e:
        logger.error(
            "Unexpected error loading CSF taxonomy",
            extra={
                "correlation_id": correlation_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to load CSF taxonomy"
        )


@router.get("/functions/{function_id}", response_model=CSFFunction)
async def get_csf_function_by_id(function_id: str, request: Request):
    """
    Get a specific CSF function by ID with its categories and subcategories.
    
    Args:
        function_id: CSF function identifier (e.g., "GV", "ID", "PR", "DE", "RS", "RC")
    
    Returns:
        Complete function with nested categories and subcategories
    """
    correlation_id = get_correlation_id(request)
    
    try:
        logger.info(
            "CSF function by ID endpoint accessed",
            extra={
                "correlation_id": correlation_id,
                "function_id": function_id
            }
        )
        
        csf_service = get_csf_service()
        function = csf_service.get_function_by_id(function_id)
        
        if function is None:
            logger.warning(
                "CSF function not found",
                extra={
                    "correlation_id": correlation_id,
                    "function_id": function_id
                }
            )
            raise HTTPException(
                status_code=404,
                detail=f"CSF function '{function_id}' not found"
            )
        
        logger.info(
            "CSF function retrieved successfully",
            extra={
                "correlation_id": correlation_id,
                "function_id": function_id,
                "categories_count": len(function.categories),
                "subcategories_count": sum(len(c.subcategories) for c in function.categories)
            }
        )
        
        return function
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error retrieving CSF function",
            extra={
                "correlation_id": correlation_id,
                "function_id": function_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve CSF function '{function_id}'"
        )


@router.get("/categories", response_model=List[CSFCategory])
async def get_csf_categories(
    function_id: Optional[str] = None, 
    request: Request = None
):
    """
    Get CSF categories, optionally filtered by function.
    
    Args:
        function_id: Optional function ID to filter categories
    
    Returns:
        List of categories with their subcategories
    """
    correlation_id = get_correlation_id(request)
    
    try:
        logger.info(
            "CSF categories endpoint accessed",
            extra={
                "correlation_id": correlation_id,
                "function_id": function_id
            }
        )
        
        csf_service = get_csf_service()
        categories = csf_service.get_categories(function_id)
        
        logger.info(
            "CSF categories retrieved successfully",
            extra={
                "correlation_id": correlation_id,
                "function_id": function_id,
                "categories_count": len(categories),
                "subcategories_count": sum(len(c.subcategories) for c in categories)
            }
        )
        
        return categories
        
    except Exception as e:
        logger.error(
            "Error retrieving CSF categories",
            extra={
                "correlation_id": correlation_id,
                "function_id": function_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve CSF categories"
        )


@router.get("/subcategories", response_model=List[CSFSubcategory])
async def get_csf_subcategories(
    function_id: Optional[str] = None,
    category_id: Optional[str] = None,
    request: Request = None
):
    """
    Get CSF subcategories, optionally filtered by function and/or category.
    
    Args:
        function_id: Optional function ID to filter subcategories
        category_id: Optional category ID to filter subcategories
    
    Returns:
        List of subcategories
    """
    correlation_id = get_correlation_id(request)
    
    try:
        logger.info(
            "CSF subcategories endpoint accessed",
            extra={
                "correlation_id": correlation_id,
                "function_id": function_id,
                "category_id": category_id
            }
        )
        
        csf_service = get_csf_service()
        subcategories = csf_service.get_subcategories(function_id, category_id)
        
        logger.info(
            "CSF subcategories retrieved successfully",
            extra={
                "correlation_id": correlation_id,
                "function_id": function_id,
                "category_id": category_id,
                "subcategories_count": len(subcategories)
            }
        )
        
        return subcategories
        
    except Exception as e:
        logger.error(
            "Error retrieving CSF subcategories",
            extra={
                "correlation_id": correlation_id,
                "function_id": function_id,
                "category_id": category_id,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve CSF subcategories"
        )