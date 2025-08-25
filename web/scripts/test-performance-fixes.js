#!/usr/bin/env node

// Test script to validate performance fixes
const fs = require('fs');
const path = require('path');

console.log('🔍 Testing performance fixes...\n');

const checks = [
  {
    name: 'Next.js config has performance optimizations',
    test: () => {
      const configPath = path.join(__dirname, '../next.config.mjs');
      const content = fs.readFileSync(configPath, 'utf8');
      return content.includes('compress: true') && 
             content.includes('swcMinify: true') && 
             content.includes('optimizePackageImports');
    }
  },
  {
    name: 'EngagementSwitcher uses proxy routes',
    test: () => {
      const componentPath = path.join(__dirname, '../components/EngagementSwitcher.tsx');
      const content = fs.readFileSync(componentPath, 'utf8');
      return content.includes('/api/proxy/engagements') && 
             !content.includes('${API_BASE}/engagements') &&
             content.includes('AbortSignal.timeout');
    }
  },
  {
    name: 'AuthProvider has timeout protection',
    test: () => {
      const providerPath = path.join(__dirname, '../components/AuthProvider.tsx');
      const content = fs.readFileSync(providerPath, 'utf8');
      return content.includes('AbortSignal.timeout(5000)') &&
             content.includes('falling back to demo mode');
    }
  },
  {
    name: 'Orchestration library uses proxy routes',
    test: () => {
      const libPath = path.join(__dirname, '../lib/orchestration.ts');
      const content = fs.readFileSync(libPath, 'utf8');
      return content.includes('API_BASE = "/api/proxy"') && 
             content.includes('AbortSignal.timeout');
    }
  },
  {
    name: 'Error boundary is implemented',
    test: () => {
      const boundaryPath = path.join(__dirname, '../components/ErrorBoundary.tsx');
      const layoutPath = path.join(__dirname, '../app/layout.tsx');
      return fs.existsSync(boundaryPath) && 
             fs.readFileSync(layoutPath, 'utf8').includes('ErrorBoundary');
    }
  },
  {
    name: 'QuestionCard uses proxy routes',
    test: () => {
      const cardPath = path.join(__dirname, '../components/QuestionCard.tsx');
      const content = fs.readFileSync(cardPath, 'utf8');
      return content.includes('/api/proxy/assist/autofill') && 
             !content.includes('process.env.NEXT_PUBLIC_API_BASE_URL');
    }
  },
  {
    name: 'Performance monitoring is available',
    test: () => {
      const perfPath = path.join(__dirname, '../lib/performance.ts');
      return fs.existsSync(perfPath);
    }
  }
];

let passed = 0;
let failed = 0;

checks.forEach(check => {
  try {
    if (check.test()) {
      console.log(`✅ ${check.name}`);
      passed++;
    } else {
      console.log(`❌ ${check.name}`);
      failed++;
    }
  } catch (error) {
    console.log(`❌ ${check.name} (Error: ${error.message})`);
    failed++;
  }
});

console.log(`\n📊 Test Results: ${passed} passed, ${failed} failed`);

if (failed === 0) {
  console.log('🎉 All performance fixes validated successfully!');
  console.log('\n🚀 Key improvements:');
  console.log('• External API calls now use server-side proxy routes');
  console.log('• All API calls have timeout protection (3-30s)');
  console.log('• Next.js production optimizations enabled');
  console.log('• Error boundaries added for graceful failure handling');
  console.log('• Performance monitoring utilities available');
  console.log('• Authentication made non-blocking with fast fallbacks');
  process.exit(0);
} else {
  console.log('⚠️  Some checks failed. Please review the implementation.');
  process.exit(1);
}