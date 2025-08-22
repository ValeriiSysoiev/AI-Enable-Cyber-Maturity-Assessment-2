# TASK FOR CLAUDE 🤖

## Request from Cursor
**Date**: $(date)
**Priority**: High
**Estimated Time**: 5 minutes

## Task Description
Create a simple API status checker script that:

1. **File**: `scripts/api_status_check.sh`
2. **Function**: Check if our API endpoints are responding
3. **Endpoints to check**:
   - http://localhost:8000/health
   - http://localhost:8000/api/health  
   - http://localhost:3000 (web)
4. **Output**: Simple pass/fail status for each endpoint
5. **Make it executable**: `chmod +x scripts/api_status_check.sh`

## Success Criteria
- Script exists and is executable
- Tests 3 endpoints with curl
- Returns clear status for each
- Includes basic error handling

## Handoff to Cursor
When complete, create `tasks/TASK_FOR_CURSOR.md` with:
- Test the script you created
- Verify it works with our current setup
- Add it to our CI/CD pipeline if appropriate

## Status
- [ ] Script created
- [ ] Made executable  
- [ ] Tested locally
- [ ] Handoff task created

**Ready for Claude pickup!** 🚀
