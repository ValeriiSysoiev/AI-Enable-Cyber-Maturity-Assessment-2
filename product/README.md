# Product Management

This directory contains the canonical product backlog and sprint management artifacts for the AI-Enabled Cyber Maturity Assessment platform.

## Directory Structure

```
/product/
├── backlog.yaml        # Source of truth - machine-readable backlog
├── backlog.md          # Human-friendly view of the backlog
├── sprint_notes/       # Sprint close-out summaries
│   └── README.md       # Template and process for sprint notes
└── README.md           # This file
```

## Key Files

### backlog.yaml
The **canonical source of truth** for all product planning:
- Epics with success criteria
- Sprints with stories and acceptance criteria
- Story points and dependencies
- Current status of all work items

**Important:** All backlog changes must be made to `backlog.yaml` first, then regenerate `backlog.md`.

### backlog.md
Human-readable version of the backlog with:
- Epic summaries and status
- Sprint overview tables
- UAT scripts
- Metrics and governance information

### sprint_notes/
Historical record of each sprint's execution:
- Velocity (planned vs actual)
- Key decisions and blockers
- Retrospective findings
- Action items for improvement

## Workflow

### 1. Sprint Planning
```bash
# Review current backlog
cat /product/backlog.yaml

# Check previous sprint notes
ls /product/sprint_notes/

# Update story status to 'in_progress'
# Edit backlog.yaml, then commit
```

### 2. During Sprint
- Track progress in daily standups
- Update story status as work progresses
- Document blockers in draft sprint notes

### 3. Sprint Close
```bash
# Create sprint notes
touch /product/sprint_notes/sprint_N.md

# Update backlog with completed stories
# Change status from 'in_progress' to 'done'

# Create status update PR
git add /product/
git commit -m "Sprint N backlog status update"
```

### 4. Claude Code Integration

When using Claude Code for sprint execution:

```yaml
# Claude will:
1. Load /product/backlog.yaml
2. Execute current sprint stories
3. Deploy via Actions with SHA proof
4. Update backlog.yaml statuses
5. Write /product/sprint_notes/sprint_N.md
6. Open "backlog status update" PR
```

## Status Values

Stories and epics use these status values:
- `planned` - Not yet started
- `in_progress` - Currently being worked on
- `done` - Completed and verified

## Backlog Maintenance

### Adding New Stories
1. Edit `backlog.yaml`
2. Add story under appropriate sprint
3. Include: id, title, epic_ref, points, acceptance_criteria
4. Regenerate `backlog.md` if needed

### Moving Stories Between Sprints
1. Cut story from current sprint in `backlog.yaml`
2. Paste into target sprint
3. Update any dependencies
4. Document reason in sprint notes

### Updating Story Points
1. Update points value in `backlog.yaml`
2. Document estimation change rationale
3. Recalculate sprint velocity if needed

## Metrics Tracking

Key metrics tracked per sprint:
- **Velocity:** Points planned vs completed
- **Quality:** UAT pass rate, test coverage
- **Reliability:** GitHub Actions success rate
- **Security:** Findings closed, scans passed

## Integration Points

### With CI/CD
- Each story completion triggers deployment
- SHA verification required (`/api/version`)
- UAT Gate must pass

### With Documentation
- `/docs/` updated as stories complete
- Architecture decisions recorded
- Operations runbooks maintained

### With Development Guidelines
- All changes follow `/DEVELOPMENT_GUIDELINES.md`
- PRs limited to 300 LOC
- No workarounds, fix root causes

## Commands

```bash
# View current sprint stories
grep -A 20 "number: $(date +%U)" /product/backlog.yaml

# Count total story points
grep "points:" /product/backlog.yaml | awk '{sum+=$2} END {print sum}'

# Find stories by epic
grep -B 2 "epic_ref: E4" /product/backlog.yaml

# Check story status
grep -A 1 "id: S3-2" /product/backlog.yaml
```

## Best Practices

1. **Single Source of Truth:** Always update `backlog.yaml` first
2. **Small Batches:** Keep stories under 5 points when possible
3. **Clear Acceptance:** Use Given/When/Then format
4. **Track Everything:** Document decisions in sprint notes
5. **Regular Updates:** Status changes committed daily
6. **Retrospectives:** Always create sprint close-out notes

## Support

For questions about the backlog or process:
1. Review this README
2. Check `/DEVELOPMENT_GUIDELINES.md`
3. See sprint notes for precedents
4. Contact the Product Owner

---

*The product backlog is a living document that evolves with each sprint. Keep it current, clear, and actionable.*