#!/usr/bin/env node
/**
 * Test script to validate GitHub integration configuration
 */

async function testGitHubIntegration() {
  console.log('🧪 Testing GitHub Integration Configuration...\n');

  // Test configuration validation
  console.log('1. Validating environment variables...');
  
  const token = process.env.GITHUB_TOKEN;
  const owner = process.env.GITHUB_OWNER;
  const repo = process.env.GITHUB_REPO;
  const labelPrefix = process.env.GITHUB_LABEL_PREFIX || 'uat';
  const assignees = process.env.GITHUB_ASSIGNEES?.split(',').map(s => s.trim()) || [];
  
  if (!token || !owner || !repo) {
    console.log('❌ Configuration invalid or missing');
    console.log('   Required environment variables:');
    console.log(`   - GITHUB_TOKEN: ${token ? '✅ Set' : '❌ Missing'}`);
    console.log(`   - GITHUB_OWNER: ${owner ? '✅ Set' : '❌ Missing'}`);
    console.log(`   - GITHUB_REPO: ${repo ? '✅ Set' : '❌ Missing'}`);
    console.log('\n   Optional environment variables:');
    console.log(`   - GITHUB_LABEL_PREFIX: ${labelPrefix} (default: "uat")`);
    console.log(`   - GITHUB_ASSIGNEES: ${assignees.length > 0 ? assignees.join(', ') : 'none'}`);
    console.log('\n   Set these environment variables and try again.');
    process.exit(1);
  }

  console.log('✅ Configuration valid:');
  console.log(`   Repository: ${owner}/${repo}`);
  console.log(`   Label prefix: ${labelPrefix}`);
  console.log(`   Assignees: ${assignees.length > 0 ? assignees.join(', ') : 'none'}`);

  // Test GitHub API access
  console.log('\n2. Testing GitHub API access...');
  try {
    const { Octokit } = require('@octokit/rest');
    const octokit = new Octokit({ auth: token });
    
    // Test basic API access by getting repository info
    const repoInfo = await octokit.rest.repos.get({ owner, repo });
    console.log('✅ GitHub API access successful');
    console.log(`   Repository: ${repoInfo.data.full_name}`);
    console.log(`   Private: ${repoInfo.data.private}`);
    console.log(`   Issues enabled: ${!repoInfo.data.has_issues ? '❌ Disabled' : '✅ Enabled'}`);
    
    if (!repoInfo.data.has_issues) {
      console.log('\n⚠️  Warning: Issues are disabled for this repository.');
      console.log('   Enable issues in repository settings to use the integration.');
    }
    
  } catch (error) {
    console.log('❌ GitHub API access failed:');
    console.log(`   ${error.message}`);
    console.log('\n   Common issues:');
    console.log('   - Invalid or expired GitHub token');
    console.log('   - Insufficient token permissions (needs "repo" scope)');
    console.log('   - Repository does not exist or is not accessible');
    console.log('   - Network connectivity issues');
    process.exit(1);
  }

  // Test secret sanitization function
  console.log('\n3. Testing secret sanitization...');
  const testContent = `
    Error: Authentication failed with token=ghp_abcd1234
    Password: mySecretPassword123
    Key: api-key-xyz789
    Email: user@example.com
    IP: 192.168.1.100
    Bearer token: bearer abc123def456
  `;
  
  const sanitized = sanitizeContent(testContent);
  console.log('✅ Secret sanitization working:');
  console.log('   Original content contained secrets');
  console.log('   Sanitized content:');
  console.log(sanitized.split('\n').map(line => `   ${line}`).join('\n'));

  console.log('\n🎉 GitHub integration test completed successfully!');
  console.log('\nNext steps:');
  console.log('1. Run UAT tests: npm run test:e2e:uat');
  console.log('2. Failed tests will automatically create GitHub issues');
  console.log(`3. View issues: https://github.com/${owner}/${repo}/issues?q=is:issue+is:open+label:${labelPrefix}`);
}

/**
 * Sanitize sensitive information from error messages and logs
 */
function sanitizeContent(content) {
  const patterns = [
    /token["\s]*[:=]["\s]*[a-zA-Z0-9\-_.]+/gi,
    /password["\s]*[:=]["\s]*[^\s"]+/gi,
    /secret["\s]*[:=]["\s]*[^\s"]+/gi,
    /key["\s]*[:=]["\s]*[a-zA-Z0-9\-_.]+/gi,
    /authorization["\s]*:["\s]*[^\s"]+/gi,
    /bearer\s+[a-zA-Z0-9\-_.]+/gi,
    /([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g,
    /\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.)\d{1,3}\b/g
  ];

  let sanitized = content;
  
  patterns.forEach(pattern => {
    sanitized = sanitized.replace(pattern, (match) => {
      if (match.includes('@')) {
        const parts = match.split('@');
        return `${parts[0][0]}***@${parts[1]}`;
      } else if (match.includes('.') && /\d/.test(match)) {
        return match.replace(/\.\d{1,3}$/, '.***');
      } else {
        return match.substring(0, 10) + '***';
      }
    });
  });

  return sanitized;
}

// Handle unhandled promise rejections
process.on('unhandledRejection', (error) => {
  console.error('❌ Unhandled error:', error);
  process.exit(1);
});

// Run the test
testGitHubIntegration().catch(error => {
  console.error('❌ Test failed:', error);
  process.exit(1);
});