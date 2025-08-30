# Sprint Notes

This directory contains sprint close-out summaries and retrospective notes for each completed sprint.

## Purpose

Sprint notes document:
- What was delivered vs. planned
- Key decisions and trade-offs made
- Blockers encountered and how they were resolved
- Lessons learned and process improvements
- Metrics (velocity, quality, incidents)

## File Naming Convention

Each sprint gets its own markdown file:
- `sprint_1.md` - Sprint 1 close-out notes
- `sprint_2.md` - Sprint 2 close-out notes
- etc.

## Template

When closing a sprint, create a new file using this template:

```markdown
# Sprint [N] Close-Out

**Sprint Name:** [Name from backlog.yaml]  
**Dates:** [Start] - [End]  
**Velocity:** [Planned points] / [Completed points]

## Stories Completed

| Story ID | Title | Points | Status | Notes |
|----------|-------|--------|--------|-------|
| S[N]-1 | ... | ... | ✅ Done | ... |

## Stories Not Completed

| Story ID | Title | Reason | Carried To |
|----------|-------|--------|------------|
| ... | ... | ... | Sprint [N+1] |

## Key Achievements
- 
- 

## Blockers & Resolutions
- 
- 

## Technical Decisions
- 
- 

## UAT Results
- **Passed:** [List]
- **Failed:** [List with remediation]

## Demo Highlights
- 
- 

## Metrics
- **GitHub Actions:** [Pass rate]
- **Test Coverage:** [Delta]
- **Production Incidents:** [Count]
- **SHA Verification:** [Pass/Fail]

## Retrospective Notes

### What Went Well
- 
- 

### What Could Be Improved
- 
- 

### Action Items
- [ ] 
- [ ] 

## Next Sprint Preview
- Focus areas:
- Key risks:
```

## Process

1. **During Sprint:** Team members can add notes to a draft file
2. **Sprint Close:** Finalize the notes during retrospective
3. **Post-Sprint:** Update `/product/backlog.yaml` with status changes
4. **Archive:** Notes remain here as historical record

## Updating Backlog Status

After each sprint, update the backlog:
1. Change completed story statuses from `planned` to `done`
2. Update sprint velocity actuals
3. Move incomplete stories to next sprint if needed
4. Create PR with title: "Sprint [N] backlog status update"

---

*These notes are part of the continuous improvement process and should be referenced when planning future sprints.*