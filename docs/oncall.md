# On-Call Procedures for AECMA Production

## On-Call Rotation
- **Primary**: First responder for all alerts
- **Secondary**: Backup for escalation
- **Rotation**: Weekly rotation, Monday 9 AM EST

## Response Times
- **Critical alerts**: 5 minutes
- **Warning alerts**: 15 minutes
- **After hours**: 10 minutes

## Escalation Matrix
1. **L1** (0-15 min): Primary on-call
2. **L2** (15-30 min): Secondary on-call + Team Lead
3. **L3** (30+ min): Management + Incident Commander

## Emergency Contacts
- **Primary On-call**: +1-555-0100
- **Secondary On-call**: +1-555-0101
- **Team Lead**: +1-555-0102
- **Incident Commander**: +1-555-0103

## Common Procedures
### Service Down
1. Check health endpoints
2. Review recent deployments
3. Check Azure service health
4. Restart containers if needed
5. Escalate if no resolution in 15 min

### High Error Rate
1. Check application logs
2. Review database performance
3. Validate external dependencies
4. Apply known fixes
5. Escalate if rate > 5%

### Performance Issues
1. Check resource utilization
2. Review slow query logs
3. Validate CDN performance
4. Scale resources if needed
5. Escalate if P95 > 5s