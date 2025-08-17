/**
 * Test data management utilities for k6 load testing
 * 
 * Generates and manages test data for various scenarios
 */

import { getCurrentEnvironment, testData } from '../k6.config.js';

/**
 * Generate unique engagement data
 */
export function generateEngagementData() {
  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
  const randomId = Math.random().toString(36).substring(2, 8);
  
  return {
    name: `${testData.engagements.defaultName} ${timestamp}`,
    description: testData.engagements.descriptions[
      Math.floor(Math.random() * testData.engagements.descriptions.length)
    ],
    id: `load-test-${randomId}-${timestamp}`,
    created_by: 'load-test-user@example.com',
    tags: ['load-test', 'automated', 'k6']
  };
}

/**
 * Generate assessment data
 */
export function generateAssessmentData(engagementId = null) {
  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
  const randomId = Math.random().toString(36).substring(2, 8);
  const preset = testData.presets[Math.floor(Math.random() * testData.presets.length)];
  
  return {
    name: `Load Test Assessment ${timestamp}`,
    preset_id: preset,
    engagement_id: engagementId,
    id: `assessment-${randomId}-${timestamp}`,
    created_by: 'load-test-user@example.com'
  };
}

/**
 * Generate answer data for assessments
 */
export function generateAnswerData(pillarId, questionId) {
  const levels = [1, 2, 3, 4, 5];
  const level = levels[Math.floor(Math.random() * levels.length)];
  
  const notes = [
    'Load test automated response',
    'Performance testing scenario answer',
    'Generated answer for load testing purposes',
    'Stress test response data',
    'Automated assessment completion'
  ];
  
  return {
    pillar_id: pillarId,
    question_id: questionId,
    level: level,
    notes: notes[Math.floor(Math.random() * notes.length)]
  };
}

/**
 * Generate document data for upload testing
 */
export function generateDocumentData() {
  const docType = testData.documentTypes[
    Math.floor(Math.random() * testData.documentTypes.length)
  ];
  
  const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
  const randomId = Math.random().toString(36).substring(2, 8);
  
  return {
    name: `${randomId}-${timestamp}-${docType.name}`,
    content: docType.content,
    size: docType.size,
    type: 'text/plain',
    description: 'Load test document for performance validation'
  };
}

/**
 * Generate RAG search queries
 */
export function generateRAGQueries() {
  return [
    'What are the security requirements for AI systems?',
    'How do we implement data governance frameworks?',
    'What are the best practices for cyber resilience?',
    'How should we handle security incident response?',
    'What are the requirements for third-party risk management?',
    'How do we ensure compliance with data protection regulations?',
    'What are the key controls for access management?',
    'How should we implement security monitoring?',
    'What are the requirements for security training?',
    'How do we manage cryptographic controls?'
  ];
}

/**
 * Generate admin operation data
 */
export function generateAdminOperationData() {
  return {
    operations: [
      'system-status-check',
      'user-role-validation',
      'cache-statistics',
      'performance-metrics',
      'security-audit'
    ],
    timeRanges: ['1h', '6h', '24h', '7d'],
    filters: ['error', 'warning', 'info', 'debug']
  };
}

/**
 * Generate GDPR operation data
 */
export function generateGDPROperationData(userEmail) {
  return {
    export: {
      user_email: userEmail,
      data_types: ['assessments', 'engagements', 'documents', 'audit_logs'],
      format: 'json'
    },
    purge: {
      user_email: userEmail,
      confirmation: `DELETE-${userEmail}-${Date.now()}`,
      reason: 'Load testing data cleanup'
    }
  };
}

/**
 * Test data cleanup utilities
 */
export class TestDataManager {
  constructor(authSession) {
    this.authSession = authSession;
    this.createdEngagements = [];
    this.createdAssessments = [];
    this.uploadedDocuments = [];
  }
  
  /**
   * Track created engagement
   */
  trackEngagement(engagementId) {
    this.createdEngagements.push(engagementId);
  }
  
  /**
   * Track created assessment
   */
  trackAssessment(assessmentId) {
    this.createdAssessments.push(assessmentId);
  }
  
  /**
   * Track uploaded document
   */
  trackDocument(documentId) {
    this.uploadedDocuments.push(documentId);
  }
  
  /**
   * Cleanup all created test data
   */
  async cleanup() {
    const errors = [];
    
    // Cleanup assessments
    for (const assessmentId of this.createdAssessments) {
      try {
        const response = this.authSession.apiRequest('DELETE', `/assessments/${assessmentId}`);
        if (response.status !== 200 && response.status !== 404) {
          errors.push(`Failed to delete assessment ${assessmentId}: ${response.status}`);
        }
      } catch (error) {
        errors.push(`Error deleting assessment ${assessmentId}: ${error.message}`);
      }
    }
    
    // Cleanup documents
    for (const documentId of this.uploadedDocuments) {
      try {
        const response = this.authSession.apiRequest('DELETE', `/documents/${documentId}`);
        if (response.status !== 200 && response.status !== 404) {
          errors.push(`Failed to delete document ${documentId}: ${response.status}`);
        }
      } catch (error) {
        errors.push(`Error deleting document ${documentId}: ${error.message}`);
      }
    }
    
    // Cleanup engagements
    for (const engagementId of this.createdEngagements) {
      try {
        const response = this.authSession.apiRequest('DELETE', `/engagements/${engagementId}`);
        if (response.status !== 200 && response.status !== 404) {
          errors.push(`Failed to delete engagement ${engagementId}: ${response.status}`);
        }
      } catch (error) {
        errors.push(`Error deleting engagement ${engagementId}: ${error.message}`);
      }
    }
    
    return {
      cleaned: {
        engagements: this.createdEngagements.length,
        assessments: this.createdAssessments.length,
        documents: this.uploadedDocuments.length
      },
      errors: errors
    };
  }
}

/**
 * Realistic user behavior patterns
 */
export const userBehaviorPatterns = {
  // Quick user - fast interactions, minimal thinking time
  quickUser: {
    thinkTime: { min: 1, max: 3 }, // seconds
    sessionDuration: { min: 5, max: 15 }, // minutes
    actionsPerSession: { min: 10, max: 25 },
    errorRate: 0.02 // 2% chance of making errors
  },
  
  // Normal user - typical business user behavior
  normalUser: {
    thinkTime: { min: 3, max: 10 }, // seconds
    sessionDuration: { min: 15, max: 45 }, // minutes
    actionsPerSession: { min: 15, max: 40 },
    errorRate: 0.05 // 5% chance of making errors
  },
  
  // Careful user - deliberate, thorough interactions
  carefulUser: {
    thinkTime: { min: 5, max: 20 }, // seconds
    sessionDuration: { min: 30, max: 90 }, // minutes
    actionsPerSession: { min: 20, max: 60 },
    errorRate: 0.01 // 1% chance of making errors
  },
  
  // Power user - experienced, efficient interactions
  powerUser: {
    thinkTime: { min: 1, max: 5 }, // seconds
    sessionDuration: { min: 10, max: 30 }, // minutes
    actionsPerSession: { min: 25, max: 50 },
    errorRate: 0.03 // 3% chance of making errors (exploring features)
  }
};

/**
 * Get random user behavior pattern
 */
export function getRandomUserPattern() {
  const patterns = Object.keys(userBehaviorPatterns);
  const pattern = patterns[Math.floor(Math.random() * patterns.length)];
  return userBehaviorPatterns[pattern];
}

/**
 * Calculate think time based on user pattern
 */
export function getThinkTime(pattern) {
  const { min, max } = pattern.thinkTime;
  return Math.random() * (max - min) + min;
}

/**
 * Generate realistic file content for document uploads
 */
export function generateRealisticDocumentContent(type = 'policy', size = 1024) {
  const templates = {
    policy: `
      INFORMATION SECURITY POLICY
      
      Document ID: POL-${Math.random().toString(36).substring(2, 8).toUpperCase()}
      Version: 1.0
      Date: ${new Date().toISOString().split('T')[0]}
      
      1. PURPOSE AND SCOPE
      This policy establishes the requirements for information security management
      within the organization to protect information assets and ensure business continuity.
      
      2. POLICY STATEMENTS
      - All information assets must be classified and protected according to their sensitivity
      - Access to information systems must be granted on a need-to-know basis
      - Security incidents must be reported and managed according to established procedures
      
      3. RESPONSIBILITIES
      - Information Security Officer: Overall policy compliance
      - System Administrators: Technical implementation
      - All Users: Adherence to security requirements
      
      4. COMPLIANCE
      Failure to comply with this policy may result in disciplinary action.
    `,
    
    procedure: `
      SECURITY INCIDENT RESPONSE PROCEDURE
      
      Procedure ID: PROC-${Math.random().toString(36).substring(2, 8).toUpperCase()}
      Version: 2.1
      Date: ${new Date().toISOString().split('T')[0]}
      
      1. INCIDENT IDENTIFICATION
      Step 1: Recognize potential security incident
      Step 2: Classify incident severity (Low/Medium/High/Critical)
      Step 3: Document initial findings
      
      2. INCIDENT RESPONSE
      Step 1: Contain the incident to prevent further damage
      Step 2: Assess the scope and impact
      Step 3: Implement recovery procedures
      Step 4: Monitor for recurrence
      
      3. REPORTING
      All incidents must be reported to the Security Operations Center within 1 hour
      of discovery for High and Critical incidents, within 4 hours for Medium and Low.
      
      4. POST-INCIDENT ACTIVITIES
      - Conduct lessons learned session
      - Update procedures if necessary
      - Implement additional controls as needed
    `,
    
    assessment: `
      CYBER SECURITY MATURITY ASSESSMENT
      
      Assessment ID: ASMT-${Math.random().toString(36).substring(2, 8).toUpperCase()}
      Date: ${new Date().toISOString().split('T')[0]}
      Assessor: Load Test User
      
      EXECUTIVE SUMMARY
      This assessment evaluates the organization's cybersecurity maturity across
      multiple domains including governance, risk management, and technical controls.
      
      KEY FINDINGS
      - Governance framework is well-established
      - Risk management processes need improvement
      - Technical controls are adequately implemented
      - Staff awareness training requires enhancement
      
      RECOMMENDATIONS
      1. Enhance risk assessment procedures
      2. Implement automated security monitoring
      3. Conduct regular security awareness training
      4. Review and update incident response procedures
      
      MATURITY SCORES
      - Governance: 4/5
      - Risk Management: 3/5
      - Technical Controls: 4/5
      - Awareness & Training: 2/5
    `
  };
  
  let content = templates[type] || templates.policy;
  
  // Pad content to reach desired size
  while (content.length < size) {
    content += `\n\nAdditional content for load testing purposes. ` +
              `This section is repeated to reach the desired file size. ` +
              `Generated at ${new Date().toISOString()}.`;
  }
  
  return content.substring(0, size);
}

export default {
  generateEngagementData,
  generateAssessmentData,
  generateAnswerData,
  generateDocumentData,
  generateRAGQueries,
  generateAdminOperationData,
  generateGDPROperationData,
  TestDataManager,
  userBehaviorPatterns,
  getRandomUserPattern,
  getThinkTime,
  generateRealisticDocumentContent
};