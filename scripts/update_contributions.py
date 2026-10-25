"""Refresh only the public contribution block; never read private repositories."""

import html
import json
import os
from pathlib import Path
import re
import urllib.parse
import urllib.request

OWNER = "DatenpflegeNordHL"
EXCLUDED = {OWNER.lower(), "datenpflegenord-de"}
START = "<!-- CONTRIBUTIONS:START -->"
END = "<!-- CONTRIBUTIONS:END -->"


def api(path):
    # Actions' repository-scoped token avoids shared-runner rate limits.
    # Public search and the explicit visibility check remain mandatory.
    headers = {"Accept": "application/vnd.github+json", "User-Agent": OWNER + "-profile"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    request = urllib.request.Request(
        "https://api.github.com/" + path,
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def contribution(pr):
    repo = pr["base"]["repo"]
    if (repo["private"] is not False or not pr.get("merged_at")
            or pr["user"]["login"].lower() != OWNER.lower()
            or repo["owner"]["login"].lower() in EXCLUDED):
        return None
    name = repo["full_name"]
    number = pr["number"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name):
        raise ValueError("Invalid repository name")
    if type(number) is not int or number < 1:
        raise ValueError("Invalid pull-request number")
    date = pr["merged_at"][:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError("Invalid merge date")
    title = html.escape(" ".join(pr["title"].split()), quote=True)
    title = re.sub(r"([\\`*_{\[\]}()!|])", r"\\\1", title)
    return date, f"- {date} · [{name} #{number}](https://github.com/{name}/pull/{number}) — {title}"


def refresh(readme, prs):
    if readme.count(START) != 1 or readme.count(END) != 1:
        raise ValueError("Expected exactly one contribution block")
    before, remaining = readme.split(START)
    _, after = remaining.split(END)
    rows = sorted(filter(None, (contribution(pr) for pr in prs)), reverse=True)[:10]
    block = "\n".join(row[1] for row in rows)
    if not rows:
        block = "No public merged upstream pull requests found."
    return before + START + "\n" + block + "\n" + END + after


def main():
    query = f"author:{OWNER} is:pr is:merged is:public -user:{OWNER} -user:datenpflegenord-de"
    result = api("search/issues?" + urllib.parse.urlencode({
        "q": query, "sort": "updated", "order": "desc", "per_page": 30,
    }))
    if result.get("incomplete_results"):
        raise RuntimeError("Incomplete search; keeping existing README")
    prs = []
    for item in result["items"]:
        url = item["pull_request"]["url"]
        if not re.fullmatch(r"https://api.github.com/repos/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pulls/\d+", url):
            raise ValueError("Unexpected pull-request API URL")
        prs.append(api(url.removeprefix("https://api.github.com/")))
    path = Path(__file__).resolve().parents[1] / "README.md"
    current = path.read_text(encoding="utf-8")
    updated = refresh(current, prs)
    if current != updated:
        path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
