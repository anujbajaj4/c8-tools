"""Part 2: the same tool on the sheet's side, as an MCP server.  Run: python mcp_server.py
The steps are in README.md."""
import csv, io, os, socket
from typing import Annotated, Literal
import requests
from fastmcp import FastMCP

SHEET = "https://docs.google.com/spreadsheets/d/1Kg6T-dJWaYx_JCPiRk3u0nBuAQcsCVRDPj1NFKP4WzM/gviz/tq?tqx=out:csv&headers=0&gid=368290478"

mcp = FastMCP("100x curriculum")

# Steps 1 and 2. get_lecture moved here from tool_call.py. FastMCP writes the card from it:
# the name is the function's name, "use it when" is the docstring, "it needs" is the type hint.
@mcp.tool
def get_lecture(
    number: Annotated[int, "The lecture number, 1 to 19, as a digit. Turn words into digits: 'seventh' is 7, 'ten' is 10."],
) -> dict:
    """Looks up one lecture of the 100xEngineers Cohort 8 curriculum by its number and returns its date, title, type (combined or separate session) and the tools it uses. Use it when someone asks about a specific 100xEngineers Cohort 8 lecture, class or session by its number, e.g. 'Lecture 12', 'the seventh class', 'session ten'. Do not use it for general questions (e.g. 'What is an API?') or for lectures of any other course (e.g. Harvard CS50)."""
    for row in csv.reader(io.StringIO(requests.get(SHEET).text)):
        if row[1].startswith(f"{number}. "):
            return {"date": row[0], "title": row[1], "type": row[2], "tools": row[3]}
    return {"error": f"There is no lecture {number}. Lectures run from 1 to 19."}


# My own data.
# Live numbers for my own GitHub projects, mainly wificonnector (my Mac app for VIT hostel Wi-Fi login).
# Stars, forks and releases come from ungh.cc, a GitHub mirror with no rate limit. Download counts only
# exist on GitHub's own API, which allows 60 requests an hour without a login, so they can be missing.
MY_REPOS = ["wificonnector", "c8-tools", "100x-ConcepChecker-Anuj", "100x-nailmail"]

@mcp.tool
def get_app_stats(
    repo: Annotated[Literal["wificonnector", "c8-tools", "100x-ConcepChecker-Anuj", "100x-nailmail"],
                    "Which of my projects. Use wificonnector unless another one is named."] = "wificonnector",
) -> dict:
    """Gets live numbers for one of my own GitHub projects, mainly wificonnector, my Mac menu-bar app that logs in to VIT hostel Wi-Fi: stars, watchers, forks, when it was created and last updated, how many releases it has, the latest release, and total downloads. Use it when someone asks how my app or project is doing, how many people downloaded or starred it, or what its latest version is. Do not use it for other people's projects, for general questions about GitHub, or for how to use the app."""
    if repo not in MY_REPOS:
        return {"error": f"{repo!r} is not one of my public projects: {', '.join(MY_REPOS)}."}
    info = requests.get(f"https://ungh.cc/repos/anujbajaj4/{repo}", timeout=10).json()["repo"]
    releases = requests.get(f"https://ungh.cc/repos/anujbajaj4/{repo}/releases", timeout=10).json()["releases"]
    stats = {"repo": info["repo"], "stars": info["stars"], "watchers": info["watchers"], "forks": info["forks"],
             "created": info["createdAt"][:10], "last_push": info["pushedAt"][:10], "releases": len(releases)}
    if releases:
        latest = releases[0]
        stats["latest_release"] = {"tag": latest["tag"], "name": latest["name"], "published": latest["publishedAt"][:10]}
    gh = requests.get(f"https://api.github.com/repos/anujbajaj4/{repo}/releases", timeout=10)
    if gh.status_code == 200:
        stats["total_downloads"] = sum(a["download_count"] for r in gh.json() for a in r["assets"])
    else:
        stats["total_downloads"] = "unknown right now: GitHub's rate limit for requests without a login was hit"
    return stats


# Any app can now reach it at http://localhost:8000/mcp
if __name__ == "__main__":
    if socket.socket().connect_ex(("127.0.0.1", 8000)) == 0:
        raise SystemExit("Port 8000 is already in use, probably by a server you started earlier. "
                         "Stop it with Ctrl+C in its terminal, or run: kill $(lsof -t -i:8000)")
    mcp.run(transport="http", port=8000)
