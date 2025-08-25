#!/usr/bin/env node

/**
 * UAT Explorer Setup Validation Script
 * 
 * This script validates that the UAT Explorer is properly configured
 * and all required components are in place.
 */

const fs = require('fs');
const path = require('path');

const PROJECT_ROOT = path.join(__dirname, '..');
const E2E_ROOT = path.join(PROJECT_ROOT, 'e2e');

function validateFile(filePath, description) {
  if (fs.existsSync(filePath)) {
    console.log(`✅ ${description}: ${path.relative(PROJECT_ROOT, filePath)}`);
    return true;
  } else {
    console.log(`❌ ${description}: ${path.relative(PROJECT_ROOT, filePath)} (MISSING)`);
    return false;
  }
}

function validateDirectory(dirPath, description) {
  if (fs.existsSync(dirPath) && fs.statSync(dirPath).isDirectory()) {
    console.log(`✅ ${description}: ${path.relative(PROJECT_ROOT, dirPath)}`);
    return true;
  } else {
    console.log(`❌ ${description}: ${path.relative(PROJECT_ROOT, dirPath)} (MISSING)`);
    return false;
  }
}

function validatePackageScript(scriptName, description) {
  const packagePath = path.join(PROJECT_ROOT, 'package.json');
  
  if (!fs.existsSync(packagePath)) {
    console.log(`❌ ${description}: package.json not found`);
    return false;
  }

  const packageContent = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
  
  if (packageContent.scripts && packageContent.scripts[scriptName]) {
    console.log(`✅ ${description}: npm run ${scriptName}`);
    return true;
  } else {
    console.log(`❌ ${description}: npm script "${scriptName}" not found`);
    return false;
  }
}

function validatePlaywrightProject(projectName) {
  const configPath = path.join(E2E_ROOT, 'playwright.config.ts');
  
  if (!fs.existsSync(configPath)) {
    console.log(`❌ Playwright Project "${projectName}": config file not found`);
    return false;
  }

  const configContent = fs.readFileSync(configPath, 'utf8');
  
  if (configContent.includes(`name: '${projectName}'`)) {
    console.log(`✅ Playwright Project "${projectName}": configured`);
    return true;
  } else {
    console.log(`❌ Playwright Project "${projectName}": not found in config`);
    return false;
  }
}

console.log('🔍 UAT Explorer Setup Validation\n');

let allValid = true;

// Core files validation
console.log('📁 Core Files:');
allValid &= validateFile(path.join(E2E_ROOT, 'tests', 'uat-explorer.spec.ts'), 'UAT Test Suite');
allValid &= validateFile(path.join(E2E_ROOT, 'reporters', 'uat-reporter.ts'), 'UAT Reporter');
allValid &= validateFile(path.join(E2E_ROOT, 'playwright.config.ts'), 'Playwright Config');
allValid &= validateFile(path.join(E2E_ROOT, 'UAT_EXPLORER.md'), 'Documentation');

// Directory structure validation
console.log('\n📂 Directory Structure:');
allValid &= validateDirectory(path.join(PROJECT_ROOT, 'artifacts', 'uat'), 'UAT Artifacts Directory');
allValid &= validateDirectory(path.join(E2E_ROOT, 'reporters'), 'Reporters Directory');

// Package scripts validation
console.log('\n📜 NPM Scripts:');
allValid &= validatePackageScript('test:e2e:uat', 'Basic UAT Script');
allValid &= validatePackageScript('test:e2e:uat:demo', 'Demo UAT Script');
allValid &= validatePackageScript('test:e2e:uat:production', 'Production UAT Script');

// Playwright project validation
console.log('\n⚙️ Playwright Configuration:');
allValid &= validatePlaywrightProject('uat-explorer');

// Environment validation
console.log('\n🌍 Environment:');
const nodeVersion = process.version;
console.log(`✅ Node.js Version: ${nodeVersion}`);

// Check for Playwright installation
try {
  require.resolve('@playwright/test');
  console.log('✅ Playwright: Installed');
} catch (error) {
  console.log('❌ Playwright: Not installed or not found');
  allValid = false;
}

// Check for TypeScript
try {
  require.resolve('typescript');
  console.log('✅ TypeScript: Available');
} catch (error) {
  console.log('⚠️ TypeScript: Not found (may be installed globally)');
}

// Final validation
console.log('\n' + '='.repeat(50));
if (allValid) {
  console.log('🎉 UAT Explorer setup is VALID! Ready to run tests.');
  console.log('\nQuick start:');
  console.log('  npm run test:e2e:uat:demo    # Demo mode');
  console.log('  npm run test:e2e:uat         # Normal mode');
  console.log('  npm run test:e2e:uat:production # Production mode');
  process.exit(0);
} else {
  console.log('❌ UAT Explorer setup has ISSUES! Please fix the missing components.');
  console.log('\nTroubleshooting:');
  console.log('1. Run: npm install');
  console.log('2. Run: npx playwright install');
  console.log('3. Check file permissions');
  console.log('4. Review the UAT_EXPLORER.md documentation');
  process.exit(1);
}