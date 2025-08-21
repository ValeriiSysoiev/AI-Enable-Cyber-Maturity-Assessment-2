#!/bin/bash
# AI Incident Response Drill Script

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

INCIDENT_TYPE="${1:-general}"

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  AI INCIDENT RESPONSE DRILL${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
}

run_hallucination_drill() {
    echo -e "${YELLOW}SCENARIO: AI Hallucination Detected${NC}"
    echo ""
    echo "CHECKLIST:"
    echo "[ ] 1. Isolate affected agent/model"
    echo "[ ] 2. Capture problematic prompts and responses"
    echo "[ ] 3. Review recent model updates or fine-tuning"
    echo "[ ] 4. Check temperature and sampling parameters"
    echo "[ ] 5. Validate ground truth data sources"
    echo "[ ] 6. Implement additional validation layer"
    echo "[ ] 7. Document incident in runbook"
    echo "[ ] 8. Notify affected users if necessary"
}

run_data_leakage_drill() {
    echo -e "${RED}SCENARIO: Potential Data Leakage${NC}"
    echo ""
    echo "IMMEDIATE ACTIONS:"
    echo "[ ] 1. STOP all AI processing immediately"
    echo "[ ] 2. Identify scope of potential exposure"
    echo "[ ] 3. Review audit logs for affected sessions"
    echo "[ ] 4. Check if PII/sensitive data was involved"
    echo "[ ] 5. Isolate affected data stores"
    echo "[ ] 6. Generate support bundle for forensics"
    echo "[ ] 7. Notify security team and legal"
    echo "[ ] 8. Prepare breach notification if required"
}

run_prompt_injection_drill() {
    echo -e "${RED}SCENARIO: Prompt Injection Attack${NC}"
    echo ""
    echo "RESPONSE STEPS:"
    echo "[ ] 1. Block suspicious user/IP immediately"
    echo "[ ] 2. Review prompt sanitization filters"
    echo "[ ] 3. Analyze attack vectors used"
    echo "[ ] 4. Check for system command execution"
    echo "[ ] 5. Audit all recent model interactions"
    echo "[ ] 6. Update WAF/input validation rules"
    echo "[ ] 7. Rotate any exposed credentials"
    echo "[ ] 8. File security incident report"
}

run_general_drill() {
    echo -e "${YELLOW}GENERAL AI INCIDENT CHECKLIST${NC}"
    echo ""
    echo "TRIAGE:"
    echo "[ ] Severity: [Critical|High|Medium|Low]"
    echo "[ ] Type: [Hallucination|Leakage|Injection|Performance|Other]"
    echo "[ ] Scope: [Single User|Multiple Users|System-wide]"
    echo ""
    echo "CONTAINMENT:"
    echo "[ ] Isolate affected components"
    echo "[ ] Preserve evidence (logs, prompts, outputs)"
    echo "[ ] Implement temporary mitigation"
    echo ""
    echo "INVESTIGATION:"
    echo "[ ] Root cause analysis"
    echo "[ ] Timeline reconstruction"
    echo "[ ] Impact assessment"
    echo ""
    echo "RECOVERY:"
    echo "[ ] Fix underlying issue"
    echo "[ ] Test remediation"
    echo "[ ] Gradual service restoration"
    echo "[ ] Monitor for recurrence"
    echo ""
    echo "POST-INCIDENT:"
    echo "[ ] Update runbooks"
    echo "[ ] Lessons learned session"
    echo "[ ] Preventive measures"
}

collect_diagnostics() {
    echo ""
    echo -e "${GREEN}Collecting diagnostic information...${NC}"
    echo ""
    echo "System Status:"
    echo "- Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
    echo "- Hostname: $(hostname)"
    echo "- Load: $(uptime | awk -F'load average:' '{print $2}')"
    
    if [[ -f "./scripts/support_bundle.sh" ]]; then
        echo ""
        echo -e "${GREEN}Run ./scripts/support_bundle.sh for full diagnostics${NC}"
    fi
}

main() {
    print_header
    
    case "$INCIDENT_TYPE" in
        hallucination)
            run_hallucination_drill
            ;;
        leakage|leak)
            run_data_leakage_drill
            ;;
        injection|prompt)
            run_prompt_injection_drill
            ;;
        *)
            run_general_drill
            ;;
    esac
    
    collect_diagnostics
    
    echo ""
    echo -e "${BLUE}Drill complete. Save this checklist for incident response.${NC}"
}

main "$@"