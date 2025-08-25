/**
 * Path Sanitization Utility
 * 
 * Sanitizes file paths to prevent information disclosure while maintaining
 * useful information for debugging and testing.
 */

interface SanitizeOptions {
  maxDepth?: number;
  preserveFilename?: boolean;
  redactSensitiveDirectories?: boolean;
}

const DEFAULT_OPTIONS: SanitizeOptions = {
  maxDepth: 2,
  preserveFilename: true,
  redactSensitiveDirectories: true
};

// Sensitive directory patterns that should be redacted
const SENSITIVE_DIRECTORIES = [
  /users/gi,
  /home/gi, 
  /documents/gi,
  /desktop/gi,
  /downloads/gi,
  /temp/gi,
  /tmp/gi,
  /private/gi,
  /\.ssh/gi,
  /\.aws/gi,
  /\.config/gi,
  /appdata/gi,
  /localappdata/gi
];

/**
 * Sanitize a file path to prevent information disclosure
 */
export function sanitizeFilePath(filePath: string, options: SanitizeOptions = {}): string {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  
  if (typeof filePath !== 'string' || !filePath) {
    return '[INVALID-PATH]';
  }

  try {
    // Normalize path separators
    const normalizedPath = filePath.replace(/\\/g, '/');
    const pathParts = normalizedPath.split('/').filter(part => part.length > 0);
    
    if (pathParts.length === 0) {
      return '[EMPTY-PATH]';
    }

    // Take only the last N parts based on maxDepth
    let relevantParts = opts.maxDepth ? pathParts.slice(-opts.maxDepth) : pathParts;
    
    if (opts.redactSensitiveDirectories) {
      relevantParts = relevantParts.map(part => {
        // Check if this part matches sensitive directory patterns
        for (const pattern of SENSITIVE_DIRECTORIES) {
          if (pattern.test(part)) {
            return 'REDACTED';
          }
        }
        return part;
      });
    }

    // Clean up special characters but preserve basic filename chars
    relevantParts = relevantParts.map(part => {
      return part.replace(/[^a-zA-Z0-9._-]/g, '_');
    });

    const sanitizedPath = relevantParts.join('/');
    return sanitizedPath || '[REDACTED-PATH]';
    
  } catch (error) {
    console.warn('Error sanitizing path:', error);
    return '[ERROR-SANITIZING-PATH]';
  }
}

/**
 * Sanitize multiple paths
 */
export function sanitizeFilePaths(paths: string[], options?: SanitizeOptions): string[] {
  return paths.map(path => sanitizeFilePath(path, options));
}

/**
 * Create a sanitized log entry that includes both original info and sanitized path
 */
export function createSanitizedLogEntry(message: string, filePath: string, additionalData?: Record<string, any>) {
  return {
    message,
    sanitizedPath: sanitizeFilePath(filePath),
    timestamp: new Date().toISOString(),
    ...additionalData
  };
}

/**
 * Sanitize log data by removing or redacting sensitive information
 */
export function sanitizeLogData(data: any): any {
  if (typeof data === 'string') {
    return sanitizeTextForLogs(data);
  }
  
  if (Array.isArray(data)) {
    return data.map(sanitizeLogData);
  }
  
  if (data && typeof data === 'object') {
    const sanitized: any = {};
    for (const [key, value] of Object.entries(data)) {
      // Sanitize path-like keys
      if (key.toLowerCase().includes('path') && typeof value === 'string') {
        sanitized[key] = sanitizeFilePath(value);
      } else {
        sanitized[key] = sanitizeLogData(value);
      }
    }
    return sanitized;
  }
  
  return data;
}

/**
 * Sanitize text content for logging to prevent sensitive data leakage
 */
function sanitizeTextForLogs(text: string): string {
  if (typeof text !== 'string') {
    return String(text);
  }

  // Redact potential file paths in text
  text = text.replace(/[C-Z]:\\\\[^\\s"'<>|?*]+/gi, '[REDACTED-WINDOWS-PATH]');
  text = text.replace(/\/[^\\s"'<>|?*]+\/[^\\s"'<>|?*]+/g, '[REDACTED-UNIX-PATH]');
  
  // Redact email addresses
  text = text.replace(/\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b/g, '[REDACTED-EMAIL]');
  
  // Redact IP addresses
  text = text.replace(/\\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\b/g, '[REDACTED-IP]');
  
  // Redact potential tokens and secrets
  text = text.replace(/(?:token|key|secret|password)[="'\\s]*[A-Za-z0-9+\\/]{20,}/gi, '[REDACTED-CREDENTIAL]');
  
  return text;
}