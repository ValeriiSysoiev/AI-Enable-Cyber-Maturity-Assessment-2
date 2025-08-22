# UAT Consent and Privacy Enhancement

Enhanced consent validation and PII scrubbing for audio transcription in UAT/staging environments.

## Overview

This implementation provides stricter consent requirements and automatic PII scrubbing for audio transcription when running in UAT or staging environments, ensuring compliance with privacy regulations and UAT validation requirements.

## Features

### Enhanced Consent Validation

#### Standard Environment
- Basic consent flag validation
- Optional consent type specification
- Standard error messages

#### UAT/Staging Environment
- **Strict consent requirements**: Explicit consent flag required
- **Mandatory consent type**: Must specify one of: `workshop`, `interview`, `meeting`, `general`
- **Participant documentation**: Required participant consent documentation
- **Enhanced logging**: Detailed consent validation logging for audit trails

### Automatic PII Scrubbing

#### PII Pattern Detection
The system automatically detects and scrubs the following PII patterns:

- **Email addresses**: `user@domain.com` → `[EMAIL_REDACTED]`
- **Phone numbers**: `555-123-4567` → `[PHONE_REDACTED]`
- **Social Security Numbers**: `123-45-6789` → `[SSN_REDACTED]`
- **Credit card numbers**: `1234 5678 9012 3456` → `[CREDIT_CARD_REDACTED]`
- **Name introductions**: `My name is John Smith` → `My name is [NAME_REDACTED]`

#### UAT Enforcement
- Automatic activation when `PII_SCRUB_ENABLED=true` in UAT/staging
- Cannot be disabled in UAT environments
- Comprehensive scrubbing of both main text and timestamp segments

## Configuration

### Environment Variables

```bash
# UAT Mode Activation
UAT_MODE=true
STAGING_ENV=true

# Consent Requirements
UAT_CONSENT_REQUIRED=true
UAT_AUDIO_CONSENT_STRICT=true
UAT_PARTICIPANT_DOCUMENTATION=required

# PII Scrubbing
PII_SCRUB_ENABLED=true
UAT_PII_SCRUB_MANDATORY=true
```

### Payload Structure

#### Standard Consent (Production)
```json
{
  "audio_data": "base64_encoded_audio",
  "mime_type": "audio/wav",
  "consent": true,
  "consent_type": "general"
}
```

#### UAT Consent (Staging/UAT)
```json
{
  "audio_data": "base64_encoded_audio",
  "mime_type": "audio/wav",
  "consent": true,
  "consent_type": "workshop",
  "participant_consent": {
    "documented": true,
    "participants": [
      "participant1@uat.local",
      "participant2@uat.local"
    ]
  },
  "pii_scrub": {
    "enabled": true
  }
}
```

## API Response

### Enhanced Metadata

UAT responses include additional metadata for compliance tracking:

```json
{
  "success": true,
  "transcription": {
    "text": "Scrubbed transcription with [EMAIL_REDACTED] and [PHONE_REDACTED]",
    "pii_scrubbing": {
      "applied": true,
      "patterns_used": ["email", "phone", "name_patterns"],
      "original_length": 150,
      "scrubbed_length": 145,
      "auto_enabled_uat": true,
      "timestamp": "2025-08-21T20:30:00Z"
    }
  },
  "consent": {
    "provided": true,
    "type": "workshop",
    "timestamp": "2025-08-21T20:30:00Z"
  },
  "pii_scrub_enabled": true,
  "pii_scrub_config": {
    "enabled": true,
    "auto_enabled_uat": true
  },
  "uat_enhanced_validation": true
}
```

## Error Handling

### UAT Consent Validation Errors

```javascript
// Missing consent in UAT
{
  "error": "UAT/Staging environment requires explicit audio transcription consent. Set 'consent': true in payload with appropriate consent_type."
}

// Missing consent type in UAT
{
  "error": "UAT environment requires consent_type to be specified. Valid types: workshop, interview, meeting, general"
}

// Missing participant documentation
{
  "error": "UAT environment requires documented participant consent. Set 'participant_consent': {'documented': true, 'participants': [...]} in payload."
}
```

## Testing

### Unit Tests
- Comprehensive test suite in `tests/test_uat_consent_privacy.py`
- Tests for standard vs UAT consent validation
- PII scrubbing pattern validation
- Environment detection and logging

### UAT Validation
```bash
# Run UAT-specific tests
pytest tests/test_uat_consent_privacy.py -v

# Test with UAT environment
UAT_MODE=true UAT_CONSENT_REQUIRED=true python -m pytest tests/test_uat_consent_privacy.py::TestUATConsentPrivacy::test_uat_enhanced_consent_validation
```

## Compliance Features

### Audit Logging
- All consent validations logged with correlation IDs
- PII scrubbing operations tracked with metadata
- UAT mode detection and enforcement logged

### Privacy Protection
- Automatic PII detection and redaction
- Configurable pattern matching
- Preserved text structure with redaction markers

### UAT Requirements
- Strict consent validation for test scenarios
- Participant documentation requirements
- Enhanced privacy protection for test data

## Integration

### MCP Gateway Integration
The enhanced consent and privacy features integrate seamlessly with the MCP gateway:

1. **Request Processing**: Enhanced validation applied before transcription
2. **Response Enhancement**: Additional metadata included in responses
3. **Error Handling**: Clear error messages for UAT compliance failures
4. **Logging**: Comprehensive audit trail for compliance verification

### CI/CD Pipeline
- Automated testing of UAT consent requirements
- PII scrubbing validation in staging deployments
- Compliance checks in release validation

## Security Considerations

### Data Protection
- PII scrubbing applied before response generation
- Original audio data not persisted in UAT environments
- Consent metadata included for audit compliance

### Access Control
- UAT mode enforces stricter validation
- Participant consent documentation required
- Enhanced logging for security monitoring

### Privacy by Design
- Default PII scrubbing in UAT environments
- Consent validation before processing
- Comprehensive redaction patterns

## Monitoring

### Metrics
- Consent validation success/failure rates
- PII scrubbing effectiveness metrics
- UAT compliance validation rates

### Alerts
- Failed consent validations in UAT
- PII scrubbing bypass attempts
- Enhanced validation failures

This enhancement ensures that audio transcription in UAT and staging environments meets the highest standards for consent validation and privacy protection while maintaining full functionality for production use cases.