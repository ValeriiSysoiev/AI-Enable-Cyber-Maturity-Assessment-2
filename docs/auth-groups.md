# Azure AD Group-based Authentication and Multi-Tenancy

This document describes the implementation and configuration of Azure AD (AAD) group-based authentication and multi-tenant isolation capabilities.

## Overview

The system supports two authentication modes:
- **Demo Mode**: Email-based authentication with simple role assignment
- **AAD Groups Mode**: Azure AD group membership-based role assignment with tenant isolation

## Configuration

### Environment Variables

```bash
# Enable AAD groups authentication (default: disabled)
AUTH_GROUPS_MODE=enabled

# AAD application registration details
AAD_TENANT_ID=your-tenant-id
AAD_CLIENT_ID=your-client-id
AAD_CLIENT_SECRET=your-client-secret

# Group to role mapping (JSON format)
AAD_GROUP_MAP_JSON='{"group-id-1": "admin", "group-id-2": "lead", "group-id-3": "member"}'

# Optional tenant isolation
AAD_REQUIRE_TENANT_ISOLATION=true
AAD_ALLOWED_TENANT_IDS=tenant-id-1,tenant-id-2

# Cache configuration
AAD_CACHE_TTL_MINUTES=15
```

### AAD Application Setup

1. **Register Application** in Azure Portal
   - Name: AI Maturity Assessment
   - Supported account types: Organizational directory only
   - Redirect URI: https://your-domain.com/api/auth/callback/azure-ad

2. **API Permissions**
   - Microsoft Graph: Group.Read.All (Application)
   - Microsoft Graph: User.Read (Delegated)

3. **Certificates & Secrets**
   - Create client secret
   - Copy secret value to `AAD_CLIENT_SECRET`

4. **Authentication**
   - Platform configurations: Web
   - Redirect URIs: Configure for your environment

## Group Mapping

### Group Assignment Strategy

Groups should be assigned based on organizational structure:

```json
{
  "12345678-1234-1234-1234-123456789012": "admin",
  "87654321-4321-4321-4321-210987654321": "lead", 
  "abcdefgh-abcd-abcd-abcd-abcdefghijkl": "member"
}
```

### Role Hierarchy

- **Admin**: Full system access, can manage all engagements
- **Lead**: Can manage specific engagements, add members
- **Member**: Can participate in assigned engagements

## Multi-Tenant Isolation

### Tenant Validation

When `AAD_REQUIRE_TENANT_ISOLATION=true`:
- Validates AAD tenant ID from JWT claims
- Restricts access to allowed tenants only
- Prevents cross-tenant data access

### Configuration

```bash
# Enable tenant isolation
AAD_REQUIRE_TENANT_ISOLATION=true

# Allowed tenant IDs (comma-separated)
AAD_ALLOWED_TENANT_IDS=tenant-1,tenant-2,tenant-3
```

## API Usage

### Headers Required

```http
X-User-Email: user@company.com
X-Engagement-ID: engagement-123
X-Tenant-ID: tenant-id  # When tenant isolation enabled
```

### Group Information

Groups are automatically synced from AAD and cached for performance:

```python
# Get user groups
groups = await get_user_groups(ctx)

# Check specific role
if "admin" in get_user_roles(ctx):
    # Admin operations
    pass

# Require specific role
require_role(ctx, {"lead", "admin"})
```

## Troubleshooting

### Admin Diagnostics

Visit `/admin/auth` for comprehensive diagnostics:
- Current authentication mode
- Configuration status
- AAD service connectivity
- Group mappings
- User roles and permissions

### Common Issues

1. **Groups Not Loading**
   - Check AAD application permissions
   - Verify client secret is correct
   - Review cache settings

2. **Tenant Isolation Failures**
   - Validate tenant ID in JWT claims
   - Check allowed tenant configuration
   - Review AAD token issuer

3. **Role Assignment Issues**
   - Verify group mapping JSON format
   - Check user's AAD group membership
   - Review cache expiration

### Logging

Structured logs with correlation IDs:

```bash
# View AAD-related logs
kubectl logs deployment/api-app | grep "aad_groups"

# Check authentication logs
kubectl logs deployment/api-app | grep "auth_context"
```

## Security Considerations

### Access Control

- Groups are cached with short TTL (15 minutes)
- Cache keys include user identity for isolation
- All AAD calls use managed identity when possible

### Audit Trail

All authentication events are logged:
- Group membership changes
- Role assignments
- Failed authentication attempts
- Tenant isolation violations

### Best Practices

1. **Group Management**
   - Use dedicated AAD groups for application roles
   - Regular group membership audits
   - Document group purpose and owners

2. **Tenant Isolation**
   - Enable for multi-tenant scenarios
   - Regular validation of tenant configuration
   - Monitor cross-tenant access attempts

3. **Monitoring**
   - Set up alerts for authentication failures
   - Monitor group sync performance
   - Track role assignment changes

## Migration Guide

### From Demo Mode to AAD Groups

1. **Pre-Migration**
   - Export current user-role mappings
   - Create corresponding AAD groups
   - Assign users to appropriate groups

2. **Configuration**
   - Set up AAD application registration
   - Configure environment variables
   - Test group mappings

3. **Deployment**
   - Deploy with `AUTH_GROUPS_MODE=disabled`
   - Validate configuration via admin diagnostics
   - Enable groups mode: `AUTH_GROUPS_MODE=enabled`

4. **Post-Migration**
   - Verify user access patterns
   - Monitor authentication logs
   - Update documentation

### Rollback Procedure

1. Set `AUTH_GROUPS_MODE=disabled`
2. System falls back to email-based authentication
3. No data loss or user impact
4. All existing functionality preserved

## Performance

### Caching Strategy

- **L1 Cache**: In-memory cache (10 seconds)
- **L2 Cache**: Redis cache (15 minutes)
- **L3 Source**: Microsoft Graph API

### Monitoring

```bash
# Cache hit rates
cache_hit_rate = hits / (hits + misses)

# Group sync performance
avg_sync_time = total_sync_time / sync_requests

# Authentication latency
auth_p95_latency = percentile(auth_times, 95)
```

## API Reference

### Endpoints

- `GET /admin/auth-diagnostics` - Authentication diagnostics
- `POST /admin/auth/refresh-groups` - Force group refresh
- `GET /admin/auth/groups/{user_id}` - User group information

### Response Examples

```json
{
  "auth_mode": "aad_groups",
  "aad_status": "operational",
  "user_context": {
    "email": "user@company.com",
    "tenant_id": "tenant-123",
    "groups": ["group-1", "group-2"],
    "roles": ["lead", "member"]
  },
  "configuration": {
    "groups_enabled": true,
    "tenant_isolation": true,
    "cache_ttl": 900
  }
}
```