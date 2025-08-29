#!/usr/bin/env node

/**
 * Script to migrate console.log statements to production-safe logger
 * Identifies and converts console logging to use the logger utility
 */

const fs = require('fs');
const path = require('path');
const glob = require('glob');

// Directories to process
const DIRECTORIES_TO_PROCESS = [
  'app/**/*.{ts,tsx}',
  'lib/**/*.{ts,tsx}',
  'components/**/*.{ts,tsx}'
];

// Files to exclude from migration
const EXCLUDE_PATTERNS = [
  '**/node_modules/**',
  '**/.next/**',
  '**/dist/**',
  '**/build/**',
  '**/test/**',
  '**/*.test.{ts,tsx}',
  '**/*.spec.{ts,tsx}',
  '**/e2e/**',
  '**/scripts/**',
  '**/logger.ts' // Don't modify the logger itself
];

// Patterns that indicate sensitive data
const SENSITIVE_PATTERNS = [
  /password/i,
  /secret/i,
  /token/i,
  /key/i,
  /credential/i,
  /auth/i,
  /session/i,
  /cookie/i,
  /bearer/i,
  /api[-_]?key/i,
  /client[-_]?secret/i,
  /access[-_]?token/i
];

function isSensitiveLog(line) {
  return SENSITIVE_PATTERNS.some(pattern => pattern.test(line));
}

function getLogLevel(line) {
  // Determine appropriate log level based on content
  if (line.includes('console.error')) return 'error';
  if (line.includes('console.warn')) return 'warn';
  if (line.includes('console.info')) return 'info';
  if (line.includes('console.debug')) return 'debug';
  
  // For console.log, check content
  if (isSensitiveLog(line)) return 'debug'; // Sensitive data should be debug only
  if (/error|fail|exception/i.test(line)) return 'error';
  if (/warn|warning|caution/i.test(line)) return 'warn';
  if (/success|complete|done/i.test(line)) return 'info';
  
  return 'debug'; // Default to debug for console.log
}

function needsLoggerImport(content) {
  // Check if logger is already imported
  return !content.includes("from './logger'") && 
         !content.includes('from "./logger"') &&
         !content.includes("from '../logger'") &&
         !content.includes('from "../logger"') &&
         !content.includes("from '../../logger'") &&
         !content.includes('from "../../logger"');
}

function calculateRelativeImportPath(filePath) {
  // Calculate relative path from file to lib/logger.ts
  const fileDir = path.dirname(filePath);
  const loggerPath = path.join(process.cwd(), 'lib/logger.ts');
  const relativePath = path.relative(fileDir, loggerPath);
  
  // Remove .ts extension and ensure starts with ./
  let importPath = relativePath.replace(/\.ts$/, '');
  if (!importPath.startsWith('.')) {
    importPath = './' + importPath;
  }
  
  return importPath;
}

function migrateFile(filePath) {
  let content = fs.readFileSync(filePath, 'utf8');
  const originalContent = content;
  let modified = false;
  
  // Pattern to match console.log/debug/info/warn/error
  const consolePattern = /console\.(log|debug|info|warn|error)\s*\(/g;
  
  // Check if file has console statements
  if (!consolePattern.test(content)) {
    return { modified: false };
  }
  
  // Reset regex
  consolePattern.lastIndex = 0;
  
  // Add logger import if needed
  if (needsLoggerImport(content)) {
    const importPath = calculateRelativeImportPath(filePath);
    const importStatement = `import { createLogger } from '${importPath}';\n\nconst logger = createLogger('${path.basename(filePath, path.extname(filePath))}');\n`;
    
    // Find where to insert the import
    const firstImportMatch = content.match(/^import .* from .*;$/m);
    if (firstImportMatch) {
      // Add after last import
      const lastImportIndex = content.lastIndexOf('import ', content.indexOf('\n\n'));
      const insertPoint = content.indexOf('\n', lastImportIndex) + 1;
      content = content.slice(0, insertPoint) + '\n' + importStatement + content.slice(insertPoint);
    } else {
      // Add at the beginning of file
      content = importStatement + '\n' + content;
    }
    modified = true;
  }
  
  // Replace console statements
  const lines = content.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    if (consolePattern.test(line)) {
      const level = getLogLevel(line);
      let newLine = line;
      
      // Simple replacement for common patterns
      newLine = newLine.replace(/console\.log\s*\(/g, `logger.${level}(`);
      newLine = newLine.replace(/console\.debug\s*\(/g, 'logger.debug(');
      newLine = newLine.replace(/console\.info\s*\(/g, 'logger.info(');
      newLine = newLine.replace(/console\.warn\s*\(/g, 'logger.warn(');
      newLine = newLine.replace(/console\.error\s*\(/g, 'logger.error(');
      
      if (newLine !== line) {
        lines[i] = newLine;
        modified = true;
      }
    }
  }
  
  if (modified) {
    content = lines.join('\n');
    fs.writeFileSync(filePath, content, 'utf8');
    return { 
      modified: true, 
      sensitive: isSensitiveLog(originalContent)
    };
  }
  
  return { modified: false };
}

function main() {
  console.log('🔍 Scanning for console.log statements to migrate...\n');
  
  let totalFiles = 0;
  let modifiedFiles = 0;
  let sensitiveFiles = 0;
  
  for (const pattern of DIRECTORIES_TO_PROCESS) {
    const files = glob.sync(pattern, {
      ignore: EXCLUDE_PATTERNS,
      nodir: true
    });
    
    for (const file of files) {
      totalFiles++;
      const result = migrateFile(file);
      
      if (result.modified) {
        modifiedFiles++;
        if (result.sensitive) {
          sensitiveFiles++;
          console.log(`⚠️  ${file} - migrated (contains sensitive logging)`);
        } else {
          console.log(`✅ ${file} - migrated`);
        }
      }
    }
  }
  
  console.log('\n📊 Migration Summary:');
  console.log(`   Total files scanned: ${totalFiles}`);
  console.log(`   Files modified: ${modifiedFiles}`);
  console.log(`   Files with sensitive logging: ${sensitiveFiles}`);
  
  if (modifiedFiles > 0) {
    console.log('\n⚠️  Please review the changes before committing.');
    console.log('   Sensitive data logging has been moved to debug level.');
  }
}

// Check if glob is installed
try {
  require('glob');
} catch (e) {
  console.error('Please install glob first: npm install --save-dev glob');
  process.exit(1);
}

main();