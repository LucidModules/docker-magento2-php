#!/usr/bin/env python3
"""Discover the latest PHP patch release for each maintained line (versions.json)
and emit a GitHub Actions build matrix."""
import json
import os
import re
import sys
import urllib.request

IMAGE = os.environ.get("IMAGE", "docker.io/lucidmodules/docker-magento2-php")


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "lucidmodules-ci"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def hub_tags(repo, name_filter):
    url = f"https://hub.docker.com/v2/repositories/{repo}/tags/?page_size=100&name={name_filter}"
    while url:
        data = get_json(url)
        yield from (t["name"] for t in data["results"])
        url = data.get("next")


def latest_php(line):
    pattern = re.compile(rf"{re.escape(line)}\.(\d+)-fpm")
    patches = [int(m.group(1)) for t in hub_tags("library/php", f"{line}.") if (m := pattern.fullmatch(t))]
    return f"{line}.{max(patches)}" if patches else None


def main():
    lines = json.load(open("versions.json"))["php_lines"]
    lines.sort(key=lambda l: tuple(map(int, l.split("."))))

    available = []
    for line in lines:
        php_version = latest_php(line)
        if not php_version:
            print(f"::warning::no php {line}.*-fpm tag found on Docker Hub, skipping {line}", file=sys.stderr)
            continue
        available.append((line, php_version))

    if not available:
        sys.exit("no buildable PHP lines discovered")

    newest = available[-1][0]
    entries = []
    for line, php_version in available:
        tags = [php_version, line]
        if line == newest:
            tags += [line.split(".")[0], "latest"]
        entries.append({
            "php_version": php_version,
            "tags": ",".join(f"{IMAGE}:{t}" for t in tags),
        })

    matrix = json.dumps({"include": entries})
    print(matrix)
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a") as fh:
            fh.write(f"matrix={matrix}\n")


if __name__ == "__main__":
    main()
