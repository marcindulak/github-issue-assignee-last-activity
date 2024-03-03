import datetime
import http.client
import json
import time
import urllib.request

# Run the script: python3 github-issue-assignee-last-activity.py | tee -a issue-summaries.txt

issue_state = "open"

# Replace with your personal access token
access_token = ""
# https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api?apiVersion=2022-11-28
# The primary rate limit for unauthenticated requests is 60 requests per hour.
# All of these requests count towards your personal rate limit of 5,000 requests per hour.
if access_token:
    headers = {"Authorization": f"token {access_token}"}
else:
    headers = {}

# Replace with the owner and repo
owner = "MicrosoftDocs"
repo = "azure-docs"

# Provice list of issues, or to fetch all issues from the repo
issue_numbers = None
# issue_numbers = ["1"]


def fetch_issues_page(url, headers):
    request = urllib.request.Request(url, headers=headers)
    response = urllib.request.urlopen(request)
    issues = json.loads(response.read().decode())

    # Check if there are more pages of results
    link_header = response.getheader("Link")
    next_url = None
    if link_header:
        # Extract the URL for the next page of results
        links = link_header.split(", ")
        next_link = [link for link in links if 'rel="next"' in link]
        if next_link:
            next_url = next_link[0].split("; ")[0].strip("<>")

    return issues, next_url


def fetch_all_issues(owner, repo, headers):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues?state={issue_state}&per_page=100"
    all_issues = []

    count = 0
    while url and (count < 1000):
        try:
            issues, url = fetch_issues_page(url, headers)
            all_issues.extend(issues)
        except http.client.IncompleteRead as e:
            print("IncompleteRead:", e)
        time.sleep(0.5)
        count = count + 1

    return all_issues


def get_days_since_date(date):
    date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    now = datetime.datetime.now(datetime.timezone.utc)
    return (now - date).days


# If issue_numbers list is provided, use it. Otherwise, fetch all issues.
if issue_numbers:
    issues_data = []
    for issue_number in issue_numbers:
        issue_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
        request = urllib.request.Request(issue_url, headers=headers)
        response = urllib.request.urlopen(request)
        issue_data = json.loads(response.read().decode())
        issues_data.append(issue_data)
        time.sleep(0.5)
else:
    issues_data = fetch_all_issues(owner, repo, headers)
if 1 != 1:
    print(f"Total open issues: {len(issues_data)}")

issue_summaries = []
for issue in issues_data:
    issue_url = f"https://github.com/{owner}/{repo}/issues/{issue['number']}"
    issue_created_at = issue["created_at"]

    if not issue["assignee"]:
        assignee_username = None
        assignee_url = None
        assignee_exists = True
        last_assignee_activity_date = None
    else:
        assignee_username = issue["assignee"]["login"]
        assignee_url = f"https://github.com/{assignee_username}"
        user_url = f"https://api.github.com/users/{assignee_username}/events"
        request = urllib.request.Request(user_url, headers=headers)
        try:
            response = urllib.request.urlopen(request)
            user_data = json.loads(response.read().decode())
            assignee_exists = True
        except urllib.error.HTTPError as e:
            print("HTTPError:", e)
            user_data = []
            assignee_exists = False
        except http.client.IncompleteRead as e:
            print("IncompleteRead:", e)
            user_data = []
            assignee_exists = False
        if user_data:
            last_assignee_activity_date = user_data[0]["created_at"]
        else:
            # https://docs.github.com/en/rest/activity/events?apiVersion=2022-11-28#about-github-events
            # Only events created within the past 90 days will be included in timelines.
            last_assignee_activity_date = None

    issue_summary = {
        "issue_url": issue_url,
        "issue_created_at": issue_created_at,
        "assignee_url": assignee_url,
        "assignee_exists": assignee_exists,
        "last_assignee_activity_date": last_assignee_activity_date,
        "days_since_last_assignee_activity": (
            get_days_since_date(last_assignee_activity_date) if last_assignee_activity_date else 90
        ),
    }

    print(issue_summary)
    issue_summaries.append(issue_summary)
    time.sleep(0.5)

with open(f"{owner}-{repo}-issue-{issue_state}-data.json", "w") as fh:
    json.dump(issues_data, fh, indent=4)
with open(f"{owner}-{repo}-issue-{issue_state}-summaries.json", "w") as fh:
    json.dump(issue_summaries, fh, indent=4)
