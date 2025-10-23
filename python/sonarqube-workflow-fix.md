# Instructions to modify GitHub Actions workflow for vulnerability testing

## Problem
The SonarQube Quality Gate is failing because it detects the intentional vulnerabilities, 
but the specific issues aren't visible because the pipeline stops at the quality gate check.

## Solution
Modify the workflow to:
1. Run SonarQube scan (to detect vulnerabilities)  
2. Skip or make quality gate non-blocking
3. Continue pipeline to show all detected issues

## Changes needed in .github/workflows/deploy.yml:

### Option 1: Make Quality Gate non-blocking (Recommended)
Replace the "SonarQube Quality Gate" step with:

```yaml
- name: SonarQube Quality Gate (Non-blocking for testing)
  uses: SonarSource/sonarqube-quality-gate-action@v1
  timeout-minutes: 15
  continue-on-error: true  # This allows pipeline to continue even if quality gate fails
  env:
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
    SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}

- name: Display SonarQube Results Summary
  if: always()
  run: |
    echo "=== SonarQube Analysis Complete ==="
    echo "Check SonarQube dashboard for detected vulnerabilities:"
    echo "${{ secrets.SONAR_HOST_URL }}/dashboard?id=swft-python"
    echo ""
    echo "Expected findings in this test project:"
    echo "- Security Hotspots: Hardcoded credentials, command injection, SQL injection"
    echo "- Code Smells: Weak cryptography, information disclosure"
    echo "- Bugs: Insecure deserialization, path traversal"
```

### Option 2: Skip Quality Gate entirely
Replace the quality gate step with:

```yaml
- name: SonarQube Analysis Results
  run: |
    echo "SonarQube scan completed. Quality gate check skipped for vulnerability testing."
    echo "View results at: ${{ secrets.SONAR_HOST_URL }}/dashboard?id=swft-python"
```

### Option 3: Custom Quality Gate Check
```yaml
- name: Custom Quality Gate Check (Allow Security Issues)
  run: |
    # Custom logic to check quality gate but allow security hotspots
    echo "Checking SonarQube results..."
    # You can add custom API calls here to get specific metrics
    echo "Quality gate check customized for vulnerability testing"
```

## Why this works:
- SonarQube will still scan and detect all vulnerabilities
- Issues will be visible in the SonarQube dashboard
- Pipeline won't fail due to intentional security issues  
- You can see all detected vulnerabilities for testing purposes

## To implement:
1. Choose one of the options above
2. Update your .github/workflows/deploy.yml file
3. Commit and push the changes
4. Re-run the pipeline

The vulnerabilities will then be visible in your SonarQube dashboard while allowing the CI/CD pipeline to complete successfully.