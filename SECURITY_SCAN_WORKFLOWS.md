# Security Scan Workflows - Manual Setup Required

## Overview
Due to OAuth scope limitations, security scan workflows must be created manually.

## Weekly Workflows to Create

### 1. Secret Scanning (`weekly-secret-scan.yml`)
```yaml
name: Weekly Secret Scan
on:
  schedule:
    - cron: '0 6 * * 1'  # Monday 6 AM UTC
  workflow_dispatch:

jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run GitLeaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 2. SCA Scanning (`weekly-sca-scan.yml`)
```yaml
name: Weekly SCA Scan
on:
  schedule:
    - cron: '0 7 * * 1'  # Monday 7 AM UTC
  workflow_dispatch:

jobs:
  sca-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Dependency Check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          project: 'AECMA'
          path: '.'
          format: 'ALL'
```

### 3. IaC Scanning (`weekly-iac-scan.yml`)
```yaml
name: Weekly IaC Scan
on:
  schedule:
    - cron: '0 8 * * 1'  # Monday 8 AM UTC
  workflow_dispatch:

jobs:
  iac-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run TFSec
        uses: aquasecurity/tfsec-action@v1.0.0
      - name: Run Checkov
        uses: bridgecrewio/checkov-action@master
```

## Setup Instructions
1. Create each workflow file in `.github/workflows/`
2. Results appear in Security tab
3. Configure notifications in repository settings
4. Review weekly scan reports