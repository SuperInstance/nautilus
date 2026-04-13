#!/usr/bin/env python3
"""
Fleet Health Scanner — Scans SuperInstance repos for health indicators.

Usage:
    GITHUB_TOKEN=ghp_xxx python3 health_check.py
    GITHUB_TOKEN=ghp_xxx python3 health_check.py --org SuperInstance --max-repos 20

Checks: health-check files, test directories, CI workflows, recent commits.
Zero external deps — stdlib only (urllib.request, json).
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta


GITHUB_API = "https://api.github.com"


def github_get(path, token):
    """GET from GitHub API. Returns parsed JSON or None on error."""
    url = f"{GITHUB_API}{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"  HTTP {e.code} on {path}: {body[:120]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  Error on {path}: {e}", file=sys.stderr)
        return None


def scan_repohealth(owner, repo, token):
    """Scan a single repo for health indicators."""
    full = f"{owner}/{repo}"
    health = {
        "repo": full,
        "health_check": False,
        "tests": False,
        "ci": False,
        "recent_commit_days": None,
        "open_issues": None,
        "score": 0,
    }

    # 1. Check for health-check file (HEALTH.md, .health, or .fleet/health)
    contents = github_get(f"/repos/{full}/contents/", token)
    if isinstance(contents, list):
        names = {item["name"] for item in contents}
        if "HEALTH.md" in names or ".health" in names or ".fleet" in names:
            health["health_check"] = True

    # 2. Check for test directory
    if isinstance(contents, list):
        names_lower = {item["name"].lower() for item in contents}
        if any(d in names_lower for d in ("tests", "test", "__tests__", "spec")):
            health["tests"] = True

    # 3. Check for CI workflows (.github/workflows/)
    workflows = github_get(f"/repos/{full}/contents/.github/workflows", token)
    if isinstance(workflows, list) and len(workflows) > 0:
        health["ci"] = True

    # 4. Most recent commit
    commits = github_get(f"/repos/{full}/commits?per_page=1", token)
    if isinstance(commits, list) and len(commits) > 0:
        date_str = commits[0].get("commit", {}).get("committer", {}).get("date", "")
        if date_str:
            commit_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            days_ago = (datetime.now(timezone.utc) - commit_date).days
            health["recent_commit_days"] = days_ago

    # 5. Open issues count
    repo_info = github_get(f"/repos/{full}", token)
    if isinstance(repo_info, dict):
        health["open_issues"] = repo_info.get("open_issues_count", "?")

    # 6. Score: each indicator worth 1, recent commit within 7 days worth 1
    score = 0
    if health["health_check"]:
        score += 1
    if health["tests"]:
        score += 1
    if health["ci"]:
        score += 1
    if health["recent_commit_days"] is not None and health["recent_commit_days"] <= 7:
        score += 1
    health["score"] = score

    return health


def main():
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("Error: Set GITHUB_TOKEN environment variable.", file=sys.stderr)
        sys.exit(1)

    # Parse args
    org = "SuperInstance"
    max_repos = 30
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--org" and i + 1 < len(args):
            org = args[i + 1]
            i += 2
        elif args[i] == "--max-repos" and i + 1 < len(args):
            max_repos = int(args[i + 1])
            i += 2
        else:
            i += 1

    # Fetch repos
    print(f"Scanning {org} for fleet health...\n")
    repos_data = github_get(f"/orgs/{org}/repos?per_page={max_repos}&sort=updated", token)
    if not isinstance(repos_data, list):
        print(f"Failed to fetch repos for {org}.")
        sys.exit(1)

    # Scan each repo
    results = []
    for repo in repos_data:
        name = repo["name"]
        health = scan_repohealth(org, name, token)
        results.append(health)
        status = _status_icon(health["score"])
        commit_str = f"{health['recent_commit_days']}d ago" if health['recent_commit_days'] is not None else "?"
        print(f"  {status} {name:40s}  score={health['score']}/4  "
              f"hc={'Y' if health['health_check'] else '-'}  "
              f"tests={'Y' if health['tests'] else '-'}  "
              f"ci={'Y' if health['ci'] else '-'}  "
              f"commit={commit_str}  "
              f"issues={health['open_issues']}")

    # Summary
    total = len(results)
    healthy = sum(1 for r in results if r["score"] >= 3)
    needs_attention = sum(1 for r in results if r["score"] == 2)
    critical = sum(1 for r in results if r["score"] <= 1)

    print(f"\n{'=' * 80}")
    print(f"  Total repos: {total}")
    print(f"  Healthy (3-4): {healthy}")
    print(f"  Needs attention (2): {needs_attention}")
    print(f"  Critical (0-1): {critical}")
    print(f"{'=' * 80}")

    # Write JSON report
    report = {
        "org": org,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "healthy": healthy,
        "needs_attention": needs_attention,
        "critical": critical,
        "repos": results,
    }
    report_path = "fleet_health_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nFull report written to {report_path}")


def _status_icon(score):
    if score >= 3:
        return "OK"
    elif score == 2:
        return "!!"
    return "XX"


if __name__ == "__main__":
    main()
