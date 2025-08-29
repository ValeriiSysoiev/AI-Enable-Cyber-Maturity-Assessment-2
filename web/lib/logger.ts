/**
 * Production-safe logging utility
 * Only logs in development or when explicitly enabled
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LoggerConfig {
  enabled: boolean;
  level: LogLevel;
  sanitize: boolean;
}

/**
 * Get logger configuration based on environment
 */
function getLoggerConfig(): LoggerConfig {
  const isDevelopment = process.env.NODE_ENV === 'development';
  const isDebugEnabled = process.env.DEBUG === 'true' || process.env.DEBUG === '1';
  const logLevel = (process.env.LOG_LEVEL || 'info').toLowerCase() as LogLevel;
  
  return {
    enabled: isDevelopment || isDebugEnabled,
    level: logLevel,
    sanitize: !isDevelopment, // Always sanitize in production
  };
}

/**
 * Sanitize sensitive data from log output
 */
function sanitizeData(data: any): any {
  if (typeof data !== 'object' || data === null) {
    return data;
  }
  
  const sensitiveKeys = [
    'password',
    'secret',
    'token',
    'authorization',
    'cookie',
    'session',
    'credential',
    'private',
    'api_key',
    'apikey',
    'client_secret',
    'clientsecret',
    'access_token',
    'accesstoken',
    'refresh_token',
    'refreshtoken',
    'private_key',
    'privatekey',
    'secret_key',
    'secretkey',
  ];
  
  const sanitized = Array.isArray(data) ? [...data] : { ...data };
  
  for (const key in sanitized) {
    const lowerKey = key.toLowerCase();
    
    // Check if key contains sensitive terms
    if (sensitiveKeys.some(term => lowerKey.includes(term))) {
      sanitized[key] = '[REDACTED]';
    } else if (typeof sanitized[key] === 'object') {
      // Recursively sanitize nested objects
      sanitized[key] = sanitizeData(sanitized[key]);
    }
  }
  
  return sanitized;
}

/**
 * Check if current log level allows the message
 */
function shouldLog(messageLevel: LogLevel, configLevel: LogLevel): boolean {
  const levels: LogLevel[] = ['debug', 'info', 'warn', 'error'];
  const messagePriority = levels.indexOf(messageLevel);
  const configPriority = levels.indexOf(configLevel);
  
  return messagePriority >= configPriority;
}

/**
 * Format log message with timestamp and level
 */
function formatMessage(level: LogLevel, message: string, data?: any): string {
  const timestamp = new Date().toISOString();
  const prefix = `[${timestamp}] [${level.toUpperCase()}]`;
  
  if (data !== undefined) {
    const jsonData = JSON.stringify(data, null, 2);
    return `${prefix} ${message}\n${jsonData}`;
  }
  
  return `${prefix} ${message}`;
}

/**
 * Production-safe logger class
 */
class Logger {
  private config: LoggerConfig;
  private context?: string;
  
  constructor(context?: string) {
    this.config = getLoggerConfig();
    this.context = context;
  }
  
  private log(level: LogLevel, message: string, data?: any): void {
    if (!this.config.enabled || !shouldLog(level, this.config.level)) {
      return;
    }
    
    // Add context to message if available
    const contextMessage = this.context ? `[${this.context}] ${message}` : message;
    
    // Sanitize data in production
    const logData = this.config.sanitize && data ? sanitizeData(data) : data;
    
    // Format and output based on level
    const formatted = formatMessage(level, contextMessage, logData);
    
    switch (level) {
      case 'debug':
        console.debug(formatted);
        break;
      case 'info':
        console.info(formatted);
        break;
      case 'warn':
        console.warn(formatted);
        break;
      case 'error':
        console.error(formatted);
        break;
    }
  }
  
  debug(message: string, data?: any): void {
    this.log('debug', message, data);
  }
  
  info(message: string, data?: any): void {
    this.log('info', message, data);
  }
  
  warn(message: string, data?: any): void {
    this.log('warn', message, data);
  }
  
  error(message: string, data?: any): void {
    this.log('error', message, data);
  }
  
  /**
   * Create a child logger with additional context
   */
  child(context: string): Logger {
    const childContext = this.context 
      ? `${this.context}:${context}`
      : context;
    return new Logger(childContext);
  }
}

/**
 * Create a logger instance
 */
export function createLogger(context?: string): Logger {
  return new Logger(context);
}

/**
 * Default logger instance
 */
export const logger = createLogger();

/**
 * Check if logging is enabled (for conditional expensive operations)
 */
export function isLoggingEnabled(): boolean {
  const config = getLoggerConfig();
  return config.enabled;
}

/**
 * Check if debug logging is enabled
 */
export function isDebugEnabled(): boolean {
  const config = getLoggerConfig();
  return config.enabled && config.level === 'debug';
}