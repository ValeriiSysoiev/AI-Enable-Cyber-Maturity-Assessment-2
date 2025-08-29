/**
 * XSS Sanitization utilities
 * 
 * This module provides secure sanitization functions to prevent XSS attacks
 * while maintaining necessary formatting for the application.
 */

import DOMPurify from 'dompurify';

// Configure DOMPurify for strict sanitization
const DEFAULT_CONFIG: DOMPurify.Config = {
  ALLOWED_TAGS: ['mark', 'strong', 'em', 'b', 'i', 'u', 'span', 'br'],
  ALLOWED_ATTR: ['class'],
  ALLOWED_CLASSES: {
    'mark': ['bg-yellow-200', 'bg-yellow-300', 'highlight'],
    'span': ['highlight', 'match']
  },
  KEEP_CONTENT: true,
  SANITIZE_DOM: true,
  SANITIZE_NAMED_PROPS: true,
  WHOLE_DOCUMENT: false,
  RETURN_DOM: false,
  RETURN_DOM_FRAGMENT: false,
  FORCE_BODY: false,
  IN_PLACE: false
};

// More restrictive config for user-generated content
const USER_CONTENT_CONFIG: DOMPurify.Config = {
  ALLOWED_TAGS: [],  // No HTML tags allowed
  ALLOWED_ATTR: [],
  KEEP_CONTENT: true,  // Keep text content only
  SANITIZE_DOM: true,
  SANITIZE_NAMED_PROPS: true
};

/**
 * Sanitize HTML content while preserving safe formatting
 * Used for content that may contain highlighting markup
 * 
 * @param dirty - The untrusted HTML string
 * @returns Sanitized HTML string safe for rendering
 */
export function sanitizeHTML(dirty: string): string {
  if (typeof window === 'undefined') {
    // Server-side: strip all HTML for safety
    return dirty.replace(/<[^>]*>/g, '');
  }
  
  return DOMPurify.sanitize(dirty, DEFAULT_CONFIG);
}

/**
 * Sanitize user-generated content completely
 * Strips all HTML, keeping only text content
 * 
 * @param dirty - The untrusted user input
 * @returns Plain text with all HTML removed
 */
export function sanitizeUserContent(dirty: string): string {
  if (typeof window === 'undefined') {
    // Server-side: strip all HTML for safety
    return dirty.replace(/<[^>]*>/g, '');
  }
  
  return DOMPurify.sanitize(dirty, USER_CONTENT_CONFIG);
}

/**
 * Escape HTML special characters
 * Use this when you need to display HTML code as text
 * 
 * @param text - The text to escape
 * @returns Escaped text safe for display
 */
export function escapeHTML(text: string): string {
  const div = typeof document !== 'undefined' ? document.createElement('div') : null;
  if (div) {
    div.textContent = text;
    return div.innerHTML;
  }
  
  // Fallback for server-side
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Highlight search terms in text with proper sanitization
 * 
 * @param text - The text to highlight
 * @param query - The search query
 * @param highlightClass - CSS class for highlighting (default: bg-yellow-200)
 * @returns Sanitized HTML with highlighted terms
 */
export function highlightTextSafely(
  text: string, 
  query: string, 
  highlightClass: string = 'bg-yellow-200'
): string {
  if (!query.trim()) {
    return escapeHTML(text);
  }
  
  // First escape the text to prevent XSS
  let safeText = escapeHTML(text);
  
  // Split query into terms and escape each
  const terms = query.toLowerCase().split(/\s+/)
    .filter(term => term.length > 2)  // Only highlight terms > 2 chars
    .map(term => escapeHTML(term));
  
  // Apply highlighting to escaped text
  terms.forEach(term => {
    const regex = new RegExp(`(${term})`, 'gi');
    safeText = safeText.replace(regex, `<mark class="${highlightClass}">$1</mark>`);
  });
  
  // Finally sanitize to ensure only safe tags remain
  return sanitizeHTML(safeText);
}

/**
 * Validate and sanitize URLs to prevent javascript: and data: XSS
 * 
 * @param url - The URL to validate
 * @returns Sanitized URL or empty string if invalid
 */
export function sanitizeURL(url: string): string {
  if (!url) return '';
  
  // Remove any whitespace and convert to lowercase for checking
  const cleanUrl = url.trim().toLowerCase();
  
  // Block dangerous protocols
  const dangerousProtocols = [
    'javascript:',
    'data:',
    'vbscript:',
    'file:',
    'about:',
    'blob:'
  ];
  
  if (dangerousProtocols.some(protocol => cleanUrl.startsWith(protocol))) {
    console.warn('Blocked potentially dangerous URL:', url);
    return '';
  }
  
  // Only allow http, https, and relative URLs
  if (!cleanUrl.startsWith('http://') && 
      !cleanUrl.startsWith('https://') && 
      !cleanUrl.startsWith('/') &&
      !cleanUrl.startsWith('#')) {
    // Assume relative URL, prepend /
    return '/' + encodeURI(url);
  }
  
  return encodeURI(url);
}

/**
 * Create a safe data attribute value
 * Prevents XSS through data attributes
 * 
 * @param value - The value to sanitize
 * @returns Safe value for data attributes
 */
export function sanitizeDataAttribute(value: any): string {
  if (value === null || value === undefined) {
    return '';
  }
  
  // Convert to string and escape
  const stringValue = String(value);
  return escapeHTML(stringValue);
}

/**
 * Sanitize JSON for safe embedding in HTML
 * 
 * @param obj - The object to sanitize
 * @returns Safe JSON string
 */
export function sanitizeJSON(obj: any): string {
  try {
    // JSON.stringify already escapes dangerous characters
    const json = JSON.stringify(obj);
    // Additional escape for HTML context
    return escapeHTML(json);
  } catch (error) {
    console.error('Failed to sanitize JSON:', error);
    return '{}';
  }
}

/**
 * Check if content needs sanitization
 * Quick check to avoid unnecessary processing
 * 
 * @param content - The content to check
 * @returns True if content contains potential HTML
 */
export function needsSanitization(content: string): boolean {
  return /<[^>]*>/.test(content) || /[<>&"']/.test(content);
}

// Export configured DOMPurify instance for advanced use cases
export const purify = typeof window !== 'undefined' ? DOMPurify : null;