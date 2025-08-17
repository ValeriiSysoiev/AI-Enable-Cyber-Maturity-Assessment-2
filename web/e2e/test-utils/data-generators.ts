/**
 * Enterprise Test Data Generators
 * Generates realistic test data for enterprise features including AAD, GDPR, and multi-tenant scenarios
 */

export interface EnterpriseTestData {
  tenants: TenantData[];
  users: UserData[];
  engagements: EngagementData[];
  aadGroups: AADGroupData[];
  gdprRequests: GDPRRequestData[];
}

export interface TenantData {
  id: string;
  name: string;
  domain: string;
  settings: {
    aadEnabled: boolean;
    gdprEnabled: boolean;
    performanceMonitoring: boolean;
    retentionDays: number;
  };
}

export interface UserData {
  id: string;
  tenantId: string;
  email: string;
  role: 'Admin' | 'Lead' | 'Member' | 'TenantAdmin' | 'GlobalAdmin';
  aadObjectId?: string;
  groups: string[];
  permissions: string[];
  engagementRoles: Record<string, string>;
}

export interface EngagementData {
  id: string;
  tenantId: string;
  name: string;
  status: 'active' | 'completed' | 'archived';
  leadUserId: string;
  memberUserIds: string[];
  documents: DocumentData[];
  assessments: AssessmentData[];
}

export interface DocumentData {
  id: string;
  engagementId: string;
  name: string;
  type: string;
  sensitivity: 'public' | 'internal' | 'confidential' | 'restricted';
  uploadedBy: string;
  size: number;
}

export interface AssessmentData {
  id: string;
  engagementId: string;
  name: string;
  status: 'draft' | 'in_progress' | 'completed';
  responses: Record<string, any>;
  completedBy?: string;
}

export interface AADGroupData {
  id: string;
  displayName: string;
  description: string;
  memberIds: string[];
  roleMapping: string;
}

export interface GDPRRequestData {
  id: string;
  type: 'export' | 'purge';
  userId: string;
  requestedBy: string;
  reason: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  createdAt: Date;
  format?: 'json' | 'csv';
}

export class EnterpriseDataGenerator {
  private static instance: EnterpriseDataGenerator;
  private tenantCounter = 0;
  private userCounter = 0;
  private engagementCounter = 0;
  private groupCounter = 0;
  private requestCounter = 0;

  static getInstance(): EnterpriseDataGenerator {
    if (!EnterpriseDataGenerator.instance) {
      EnterpriseDataGenerator.instance = new EnterpriseDataGenerator();
    }
    return EnterpriseDataGenerator.instance;
  }

  /**
   * Generate a complete enterprise test dataset
   */
  generateEnterpriseDataset(options: {
    tenantCount: number;
    usersPerTenant: number;
    engagementsPerTenant: number;
    aadGroupCount: number;
  }): EnterpriseTestData {
    const { tenantCount, usersPerTenant, engagementsPerTenant, aadGroupCount } = options;

    const tenants = this.generateTenants(tenantCount);
    const aadGroups = this.generateAADGroups(aadGroupCount);
    const users = tenants.flatMap(tenant => 
      this.generateUsers(usersPerTenant, tenant.id, aadGroups)
    );
    const engagements = tenants.flatMap(tenant => 
      this.generateEngagements(engagementsPerTenant, tenant.id, users.filter(u => u.tenantId === tenant.id))
    );
    const gdprRequests = this.generateGDPRRequests(users, 20);

    return {
      tenants,
      users,
      engagements,
      aadGroups,
      gdprRequests
    };
  }

  /**
   * Generate tenant data
   */
  generateTenants(count: number): TenantData[] {
    const tenants: TenantData[] = [];
    const companies = ['Acme Corp', 'Global Tech', 'SecureBank', 'HealthCare Plus', 'EduTech'];
    const domains = ['acme.com', 'globaltech.org', 'securebank.net', 'healthplus.com', 'edutech.edu'];

    for (let i = 0; i < count; i++) {
      const companyIndex = i % companies.length;
      tenants.push({
        id: `tenant-${++this.tenantCounter}`,
        name: `${companies[companyIndex]} ${i > 4 ? Math.floor(i / 5) : ''}`.trim(),
        domain: domains[companyIndex],
        settings: {
          aadEnabled: Math.random() > 0.3, // 70% have AAD enabled
          gdprEnabled: Math.random() > 0.2, // 80% have GDPR enabled
          performanceMonitoring: Math.random() > 0.4, // 60% have performance monitoring
          retentionDays: [30, 90, 180, 365, 730][Math.floor(Math.random() * 5)]
        }
      });
    }

    return tenants;
  }

  /**
   * Generate user data for a tenant
   */
  generateUsers(count: number, tenantId: string, aadGroups: AADGroupData[]): UserData[] {
    const users: UserData[] = [];
    const firstNames = ['John', 'Jane', 'Mike', 'Sarah', 'David', 'Lisa', 'Chris', 'Amy', 'Tom', 'Emma'];
    const lastNames = ['Smith', 'Johnson', 'Brown', 'Davis', 'Wilson', 'Moore', 'Taylor', 'Anderson', 'Thomas', 'Jackson'];
    const roles: UserData['role'][] = ['Admin', 'Lead', 'Member'];

    for (let i = 0; i < count; i++) {
      const firstName = firstNames[Math.floor(Math.random() * firstNames.length)];
      const lastName = lastNames[Math.floor(Math.random() * lastNames.length)];
      const role = roles[Math.floor(Math.random() * roles.length)];
      
      // Assign AAD groups based on role
      const userGroups = this.assignAADGroups(role, aadGroups);
      const permissions = this.generatePermissions(role);

      users.push({
        id: `user-${++this.userCounter}`,
        tenantId,
        email: `${firstName.toLowerCase()}.${lastName.toLowerCase()}@${tenantId}.com`,
        role,
        aadObjectId: `aad-${this.userCounter}-${tenantId}`,
        groups: userGroups.map(g => g.id),
        permissions,
        engagementRoles: {} // Will be populated when generating engagements
      });
    }

    return users;
  }

  /**
   * Generate AAD groups with role mappings
   */
  generateAADGroups(count: number): AADGroupData[] {
    const groups: AADGroupData[] = [];
    const groupTypes = [
      { name: 'Administrators', role: 'Admin', description: 'Full system administrators' },
      { name: 'Assessment Leads', role: 'Lead', description: 'Assessment team leads' },
      { name: 'Team Members', role: 'Member', description: 'Regular team members' },
      { name: 'GDPR Officers', role: 'Admin', description: 'GDPR compliance officers' },
      { name: 'Security Analysts', role: 'Lead', description: 'Security analysis team' }
    ];

    for (let i = 0; i < count; i++) {
      const groupType = groupTypes[i % groupTypes.length];
      groups.push({
        id: `group-${++this.groupCounter}`,
        displayName: `${groupType.name} ${Math.floor(i / groupTypes.length) || ''}`.trim(),
        description: groupType.description,
        memberIds: [], // Will be populated by user assignment
        roleMapping: groupType.role
      });
    }

    return groups;
  }

  /**
   * Generate engagements for a tenant
   */
  generateEngagements(count: number, tenantId: string, users: UserData[]): EngagementData[] {
    const engagements: EngagementData[] = [];
    const engagementTypes = ['Security Assessment', 'Compliance Review', 'Risk Analysis', 'Penetration Test', 'Audit'];
    const statuses: EngagementData['status'][] = ['active', 'completed', 'archived'];

    const leads = users.filter(u => u.role === 'Lead' || u.role === 'Admin');
    const members = users.filter(u => u.role === 'Member');

    for (let i = 0; i < count; i++) {
      const engagementType = engagementTypes[Math.floor(Math.random() * engagementTypes.length)];
      const lead = leads[Math.floor(Math.random() * leads.length)];
      const engagementMembers = this.selectRandomMembers(members, Math.floor(Math.random() * 5) + 1);

      const engagement: EngagementData = {
        id: `engagement-${++this.engagementCounter}`,
        tenantId,
        name: `${engagementType} ${this.engagementCounter}`,
        status: statuses[Math.floor(Math.random() * statuses.length)],
        leadUserId: lead.id,
        memberUserIds: engagementMembers.map(m => m.id),
        documents: this.generateDocuments(3 + Math.floor(Math.random() * 5)),
        assessments: this.generateAssessments(1 + Math.floor(Math.random() * 3))
      };

      // Update user engagement roles
      if (lead) {
        lead.engagementRoles[engagement.id] = 'Lead';
      }
      engagementMembers.forEach(member => {
        member.engagementRoles[engagement.id] = 'Member';
      });

      engagements.push(engagement);
    }

    return engagements;
  }

  /**
   * Generate documents for an engagement
   */
  generateDocuments(count: number): DocumentData[] {
    const documents: DocumentData[] = [];
    const documentTypes = ['Policy', 'Procedure', 'Evidence', 'Report', 'Certificate'];
    const sensitivities: DocumentData['sensitivity'][] = ['public', 'internal', 'confidential', 'restricted'];

    for (let i = 0; i < count; i++) {
      const docType = documentTypes[Math.floor(Math.random() * documentTypes.length)];
      documents.push({
        id: `doc-${Date.now()}-${i}`,
        engagementId: '', // Will be set by parent
        name: `${docType}_${i + 1}.pdf`,
        type: docType,
        sensitivity: sensitivities[Math.floor(Math.random() * sensitivities.length)],
        uploadedBy: `user-${Math.floor(Math.random() * 100)}`,
        size: Math.floor(Math.random() * 10000000) + 100000 // 100KB to 10MB
      });
    }

    return documents;
  }

  /**
   * Generate assessments for an engagement
   */
  generateAssessments(count: number): AssessmentData[] {
    const assessments: AssessmentData[] = [];
    const assessmentTypes = ['NIST CSF', 'ISO 27001', 'SOC 2', 'GDPR', 'HIPAA'];
    const statuses: AssessmentData['status'][] = ['draft', 'in_progress', 'completed'];

    for (let i = 0; i < count; i++) {
      const assessmentType = assessmentTypes[Math.floor(Math.random() * assessmentTypes.length)];
      const status = statuses[Math.floor(Math.random() * statuses.length)];

      assessments.push({
        id: `assessment-${Date.now()}-${i}`,
        engagementId: '', // Will be set by parent
        name: `${assessmentType} Assessment ${i + 1}`,
        status,
        responses: this.generateAssessmentResponses(status),
        completedBy: status === 'completed' ? `user-${Math.floor(Math.random() * 100)}` : undefined
      });
    }

    return assessments;
  }

  /**
   * Generate GDPR requests
   */
  generateGDPRRequests(users: UserData[], count: number): GDPRRequestData[] {
    const requests: GDPRRequestData[] = [];
    const types: GDPRRequestData['type'][] = ['export', 'purge'];
    const statuses: GDPRRequestData['status'][] = ['pending', 'running', 'completed', 'failed'];
    const reasons = [
      'User requested data export',
      'GDPR Article 15 request',
      'Account deletion request',
      'Data portability request',
      'Right to be forgotten'
    ];

    for (let i = 0; i < count; i++) {
      const user = users[Math.floor(Math.random() * users.length)];
      const type = types[Math.floor(Math.random() * types.length)];
      const requestor = users.find(u => u.role === 'Admin' || u.role === 'Lead') || user;

      requests.push({
        id: `gdpr-${++this.requestCounter}`,
        type,
        userId: user.id,
        requestedBy: requestor.id,
        reason: reasons[Math.floor(Math.random() * reasons.length)],
        status: statuses[Math.floor(Math.random() * statuses.length)],
        createdAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000), // Last 30 days
        format: type === 'export' ? (Math.random() > 0.5 ? 'json' : 'csv') : undefined
      });
    }

    return requests;
  }

  /**
   * Assign AAD groups based on user role
   */
  private assignAADGroups(role: UserData['role'], aadGroups: AADGroupData[]): AADGroupData[] {
    const roleGroupMap: Record<string, string[]> = {
      'Admin': ['Administrators', 'GDPR Officers'],
      'Lead': ['Assessment Leads', 'Security Analysts'],
      'Member': ['Team Members'],
      'TenantAdmin': ['Administrators'],
      'GlobalAdmin': ['Administrators', 'GDPR Officers']
    };

    const targetGroups = roleGroupMap[role] || ['Team Members'];
    return aadGroups.filter(group => 
      targetGroups.some(target => group.displayName.includes(target))
    );
  }

  /**
   * Generate permissions based on role
   */
  private generatePermissions(role: UserData['role']): string[] {
    const permissionMap: Record<string, string[]> = {
      'Admin': [
        'admin:users', 'admin:settings', 'admin:presets', 'admin:jobs',
        'read:all', 'write:all', 'delete:all',
        'gdpr:export', 'gdpr:purge', 'performance:monitor'
      ],
      'Lead': [
        'read:engagements', 'write:engagements', 'delete:engagements',
        'read:assessments', 'write:assessments',
        'read:documents', 'write:documents',
        'gdpr:export'
      ],
      'Member': [
        'read:engagements', 'read:assessments', 'read:documents'
      ],
      'TenantAdmin': [
        'admin:tenant', 'read:all', 'write:all', 'gdpr:export'
      ],
      'GlobalAdmin': [
        'admin:global', 'admin:tenant', 'admin:users', 'admin:settings',
        'read:all', 'write:all', 'delete:all',
        'gdpr:export', 'gdpr:purge', 'performance:monitor'
      ]
    };

    return permissionMap[role] || permissionMap['Member'];
  }

  /**
   * Select random members from a list
   */
  private selectRandomMembers(members: UserData[], count: number): UserData[] {
    const shuffled = [...members].sort(() => 0.5 - Math.random());
    return shuffled.slice(0, Math.min(count, members.length));
  }

  /**
   * Generate assessment responses based on status
   */
  private generateAssessmentResponses(status: AssessmentData['status']): Record<string, any> {
    const baseResponses = {
      'control-1': status === 'draft' ? null : 'Implemented',
      'control-2': status === 'draft' ? null : 'Partially Implemented',
      'control-3': status === 'completed' ? 'Not Implemented' : null
    };

    if (status === 'completed') {
      return {
        ...baseResponses,
        'control-4': 'Implemented',
        'control-5': 'Not Applicable',
        'overall-score': Math.floor(Math.random() * 100) + 1
      };
    }

    return baseResponses;
  }

  /**
   * Generate test scenarios for specific features
   */
  generateTestScenarios(): {
    aadAuth: any[];
    gdprExport: any[];
    gdprPurge: any[];
    roleAccess: any[];
    tenantIsolation: any[];
  } {
    return {
      aadAuth: [
        {
          name: 'Admin with multiple groups',
          claims: {
            groups: ['group-1', 'group-2'],
            tid: 'tenant-1',
            oid: 'admin-user-1',
            preferred_username: 'admin@tenant1.com'
          },
          expectedRole: 'Admin'
        },
        {
          name: 'Lead with single group',
          claims: {
            groups: ['group-3'],
            tid: 'tenant-1',
            oid: 'lead-user-1',
            preferred_username: 'lead@tenant1.com'
          },
          expectedRole: 'Lead'
        },
        {
          name: 'Member with no admin groups',
          claims: {
            groups: ['group-4'],
            tid: 'tenant-1',
            oid: 'member-user-1',
            preferred_username: 'member@tenant1.com'
          },
          expectedRole: 'Member'
        }
      ],
      gdprExport: [
        {
          userId: 'user-1',
          reason: 'GDPR Article 15 request',
          format: 'json',
          expectedStatus: 'completed'
        },
        {
          userId: 'user-2',
          reason: 'Data portability request',
          format: 'csv',
          expectedStatus: 'completed'
        }
      ],
      gdprPurge: [
        {
          userId: 'user-to-purge-1',
          reason: 'User requested account deletion',
          confirmations: ['irreversible', 'DELETE']
        }
      ],
      roleAccess: [
        {
          role: 'Admin',
          endpoints: [
            { url: '/admin/ops', expectedStatus: 200 },
            { url: '/admin/gdpr', expectedStatus: 200 },
            { url: '/admin/performance', expectedStatus: 200 }
          ]
        },
        {
          role: 'Lead',
          endpoints: [
            { url: '/admin/ops', expectedStatus: 403 },
            { url: '/engagements', expectedStatus: 200 },
            { url: '/admin/presets', expectedStatus: 200 }
          ]
        },
        {
          role: 'Member',
          endpoints: [
            { url: '/admin/ops', expectedStatus: 403 },
            { url: '/admin/gdpr', expectedStatus: 403 },
            { url: '/engagements', expectedStatus: 200 }
          ]
        }
      ],
      tenantIsolation: [
        {
          userTenantId: 'tenant-1',
          crossTenantResource: 'engagement-from-tenant-2',
          endpoint: '/api/engagements/{resourceId}',
          expectedBlocked: true
        },
        {
          userTenantId: 'tenant-2',
          crossTenantResource: 'user-from-tenant-1',
          endpoint: '/api/users/{resourceId}',
          expectedBlocked: true
        }
      ]
    };
  }
}