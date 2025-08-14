#!/usr/bin/env bash
set -euo pipefail

# Configuration
API=http://localhost:8000
EMAIL=you@company.com

echo "=== AI Maturity Assessment - Engagement & RBAC Smoke Test ==="
echo ""
echo "Configuration:"
echo "  API: $API"
echo "  User: $EMAIL (Admin)"
echo ""

# Bootstrap engagement
echo "1. Creating engagement..."
E=$(curl -s -X POST $API/engagements \
  -H "X-User-Email:$EMAIL" \
  -H "X-Engagement-ID:bootstrap" \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo AAA","client_code":"AAA"}')

if [ -z "$E" ]; then
  echo "ERROR: Failed to create engagement"
  exit 1
fi

EID=$(echo "$E" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'id' not in data:
        print('ERROR: Missing id in engagement response', file=sys.stderr)
        sys.exit(1)
    print(data['id'])
except (json.JSONDecodeError, KeyError) as e:
    print(f'ERROR: Failed to parse engagement ID: {e}', file=sys.stderr)
    sys.exit(1)
")
echo "  Created engagement: $EID"

# Add self as lead
echo ""
echo "2. Adding user as lead..."
# Capture response and status code
TEMP_RESPONSE=$(mktemp)
HTTP_STATUS=$(curl -s -w "%{http_code}" -o "$TEMP_RESPONSE" -X POST $API/engagements/$EID/members \
  -H "X-User-Email:$EMAIL" \
  -H "X-Engagement-ID:$EID" \
  -H "Content-Type: application/json" \
  -d "{\"user_email\":\"$EMAIL\",\"role\":\"lead\"}")

if [[ $HTTP_STATUS -ge 200 && $HTTP_STATUS -lt 300 ]]; then
  echo "  Added $EMAIL as lead"
else
  echo "ERROR: Failed to add member (HTTP $HTTP_STATUS)"
  cat "$TEMP_RESPONSE"
  rm -f "$TEMP_RESPONSE"
  exit 1
fi
rm -f "$TEMP_RESPONSE"

# Create assessment in engagement
echo ""
echo "3. Creating assessment..."
A=$(curl -s -X POST $API/domain-assessments \
  -H "X-User-Email:$EMAIL" \
  -H "X-Engagement-ID:$EID" \
  -H "Content-Type: application/json" \
  -d '{"name":"Local Demo","framework":"NIST-CSF"}')

AID=$(echo "$A" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'id' not in data:
        print('ERROR: Missing id in assessment response', file=sys.stderr)
        sys.exit(1)
    print(data['id'])
except (json.JSONDecodeError, KeyError) as e:
    print(f'ERROR: Failed to parse assessment ID: {e}', file=sys.stderr)
    sys.exit(1)
")
echo "  Created assessment: $AID"

# Run analyze
echo ""
echo "4. Running analysis..."
FINDINGS=$(curl -s -X POST $API/orchestrations/analyze \
  -H "X-User-Email:$EMAIL" \
  -H "X-Engagement-ID:$EID" \
  -H "Content-Type: application/json" \
  -d "{\"assessment_id\":\"$AID\",\"content\":\"No MFA for admins; no DLP; no IR runbooks\"}")

FINDING_COUNT=$(echo "$FINDINGS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    findings = data.get('findings', [])
    print(len(findings))
except (json.JSONDecodeError, KeyError) as e:
    print('ERROR: Failed to parse findings count', file=sys.stderr)
    print('0')
" || echo "0")
echo "  Found $FINDING_COUNT findings"

# Run recommend
echo ""
echo "5. Running recommendations..."
RECS=$(curl -s -X POST $API/orchestrations/recommend \
  -H "X-User-Email:$EMAIL" \
  -H "X-Engagement-ID:$EID" \
  -H "Content-Type: application/json" \
  -d "{\"assessment_id\":\"$AID\"}")

REC_COUNT=$(echo "$RECS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    recommendations = data.get('recommendations', [])
    print(len(recommendations))
except (json.JSONDecodeError, KeyError) as e:
    print('ERROR: Failed to parse recommendations count', file=sys.stderr)
    print('0')
" || echo "0")
echo "  Generated $REC_COUNT recommendations"

echo ""
echo "=== Smoke Test Complete ==="
echo ""
echo "Local URLs:"
echo "  Sign In:      http://localhost:3000/signin"
echo "  Engagements:  http://localhost:3000/engagements"
echo "  Demo:         http://localhost:3000/e/$EID/demo"
echo ""
echo "To start the full stack locally, run:"
echo "  ./scripts/dev_stack_local.sh"
echo ""
echo "To deploy to Azure (later):"
echo "  ./scripts/deploy_api_only.sh"
echo "  ./scripts/deploy_web_only.sh"
