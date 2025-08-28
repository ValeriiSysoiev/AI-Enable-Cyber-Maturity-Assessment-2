/**
 * CSF 2.0 API Library
 * 
 * Fast, memoized access to NIST CSF 2.0 taxonomy data
 * with error handling and loading states for grid interfaces.
 */

import { apiFetch } from './api';
import type { 
  CSFTaxonomyResponse, 
  CSFFunction, 
  CSFCategory, 
  CSFSubcategory 
} from '../types/csf';

// Memoization cache
const csfCache = new Map<string, any>();
const CACHE_TTL = 300000; // 5 minutes in milliseconds

interface CacheItem<T> {
  data: T;
  timestamp: number;
}

/**
 * Get cached item if valid, otherwise return null
 */
function getCachedItem<T>(key: string): T | null {
  const item = csfCache.get(key) as CacheItem<T> | undefined;
  if (!item) return null;
  
  const isExpired = Date.now() - item.timestamp > CACHE_TTL;
  if (isExpired) {
    csfCache.delete(key);
    return null;
  }
  
  return item.data;
}

/**
 * Set cache item with timestamp
 */
function setCacheItem<T>(key: string, data: T): void {
  csfCache.set(key, {
    data,
    timestamp: Date.now()
  });
}

/**
 * Get complete CSF 2.0 taxonomy with memoization
 * 
 * Returns full hierarchical structure optimized for grid rendering.
 * Cached for 5 minutes to meet p95 < 2s performance target.
 */
export async function getFunctions(): Promise<CSFFunction[]> {
  const cacheKey = 'csf:functions';
  
  // Check cache first
  const cached = getCachedItem<CSFFunction[]>(cacheKey);
  if (cached) {
    return cached;
  }
  
  try {
    const response: CSFTaxonomyResponse = await apiFetch('/api/v1/csf/functions', {
      timeout: 10000 // 10s timeout for initial load
    });
    
    const functions = response.functions;
    
    // Cache the result
    setCacheItem(cacheKey, functions);
    
    return functions;
  } catch (error) {
    console.error('Error loading CSF functions:', error);
    throw new Error(
      error instanceof Error 
        ? error.message 
        : 'Failed to load CSF taxonomy'
    );
  }
}

/**
 * Get specific CSF function by ID
 */
export async function getFunctionById(functionId: string): Promise<CSFFunction | null> {
  const cacheKey = `csf:function:${functionId}`;
  
  // Check cache first
  const cached = getCachedItem<CSFFunction>(cacheKey);
  if (cached) {
    return cached;
  }
  
  try {
    const function_data: CSFFunction = await apiFetch(`/api/v1/csf/functions/${functionId}`, {
      timeout: 5000
    });
    
    // Cache the result
    setCacheItem(cacheKey, function_data);
    
    return function_data;
  } catch (error) {
    if (error instanceof Error && error.message.includes('404')) {
      return null;
    }
    console.error(`Error loading CSF function ${functionId}:`, error);
    throw new Error(
      error instanceof Error 
        ? error.message 
        : `Failed to load CSF function ${functionId}`
    );
  }
}

/**
 * Get categories, optionally filtered by function
 */
export async function getCategories(functionId?: string): Promise<CSFCategory[]> {
  const cacheKey = functionId ? `csf:categories:${functionId}` : 'csf:categories';
  
  // Check cache first
  const cached = getCachedItem<CSFCategory[]>(cacheKey);
  if (cached) {
    return cached;
  }
  
  try {
    const url = functionId 
      ? `/api/v1/csf/categories?function_id=${functionId}`
      : '/api/v1/csf/categories';
      
    const categories: CSFCategory[] = await apiFetch(url, {
      timeout: 5000
    });
    
    // Cache the result
    setCacheItem(cacheKey, categories);
    
    return categories;
  } catch (error) {
    console.error('Error loading CSF categories:', error);
    throw new Error(
      error instanceof Error 
        ? error.message 
        : 'Failed to load CSF categories'
    );
  }
}

/**
 * Get subcategories, optionally filtered by function and/or category
 */
export async function getSubcategories(
  functionId?: string, 
  categoryId?: string
): Promise<CSFSubcategory[]> {
  const cacheKey = `csf:subcategories:${functionId || 'all'}:${categoryId || 'all'}`;
  
  // Check cache first
  const cached = getCachedItem<CSFSubcategory[]>(cacheKey);
  if (cached) {
    return cached;
  }
  
  try {
    const params = new URLSearchParams();
    if (functionId) params.append('function_id', functionId);
    if (categoryId) params.append('category_id', categoryId);
    
    const url = `/api/v1/csf/subcategories${params.toString() ? '?' + params.toString() : ''}`;
    
    const subcategories: CSFSubcategory[] = await apiFetch(url, {
      timeout: 5000
    });
    
    // Cache the result
    setCacheItem(cacheKey, subcategories);
    
    return subcategories;
  } catch (error) {
    console.error('Error loading CSF subcategories:', error);
    throw new Error(
      error instanceof Error 
        ? error.message 
        : 'Failed to load CSF subcategories'
    );
  }
}

/**
 * Clear CSF cache (useful for testing or forced refresh)
 */
export function clearCSFCache(): void {
  const keys = Array.from(csfCache.keys());
  keys.forEach(key => {
    if (key.startsWith('csf:')) {
      csfCache.delete(key);
    }
  });
}

/**
 * Get cache statistics (for debugging)
 */
export function getCSFCacheStats() {
  const csfKeys = Array.from(csfCache.keys()).filter(key => key.startsWith('csf:'));
  return {
    totalItems: csfKeys.length,
    keys: csfKeys,
    cacheSize: csfCache.size
  };
}