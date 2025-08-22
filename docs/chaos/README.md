# Chaos Engineering for AECMA Staging

## Overview
Controlled failure injection to validate system resilience and alert mechanisms in staging environment only.

## Chaos Probes

### API Container Failure
- **Test**: Kill API container for 30 seconds
- **Expected**: Auto-restart, alerts fire, recovery within 1 minute
- **Guard**: `CHAOS_ENABLED=1` and staging environment only

## Usage
```bash
export CHAOS_ENABLED=1
export ENVIRONMENT=staging
./scripts/chaos/staging_chaos.sh
```

## Safety Guards
- Production environment blocked
- Requires explicit enable flag
- Limited to staging infrastructure
- Short duration failures (30s default)

## Expected Outcomes
- Container Apps auto-restart
- Health check alerts trigger
- Monitoring dashboards show blip
- Recovery within RTO targets