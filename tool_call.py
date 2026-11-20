"""Part 1: your first tool call.  Run: python tool_call.py
The steps are in README.md. Each one adds a few lines to the bottom of this file."""
import csv, io, json, os, sys
import requests
from dotenv import load_dotenv

load_dotenv()
if not os.environ.get("GROQ_API_KEY"):
    raise SystemExit("No GROQ_API_KEY found. Make a file called .env next to tool_call.py with one line: GROQ_API_KEY=your key")

# ---------- THE SHEET (given) ----------
# Plain code, no model: one lecture of the course sheet, looked up by its number.
SHEET = "https://docs.google.com/spreadsheets/d/1Kg6T-dJWaYx_JCPiRk3u0nBuAQcsCVRDPj1NFKP4WzM/gviz/tq?tqx=out:csv&headers=0&gid=368290478"

def get_lecture(number):
    for row in csv.reader(io.StringIO(requests.get(SHEET).text)):
        if row[1].startswith(f"{number}. "):
            return {"date": row[0], "title": row[1], "type": row[2], "tools": row[3]}
    return {"error": f"There is no lecture {number}. Lectures run from 1 to 19."}

# ---------- MY OWN DATA ----------
# Live numbers for my own GitHub projects, mainly wificonnector (my Mac app for VIT hostel Wi-Fi login).
# Stars, forks and releases come from ungh.cc, a GitHub mirror with no rate limit. Download counts only
# exist on GitHub's own API, which allows 60 requests an hour without a login, so they can be missing.
MY_REPOS = ["wificonnector", "c8-tools", "100x-ConcepChecker-Anuj", "100x-nailmail"]

def get_app_stats(repo="wificonnector"):
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


# ---------- THE MODEL (given) ----------
# One message to Groq, one message back. Nothing is added that you do not send.
def ask_model(messages, tools=None):
    body = {"model": "openai/gpt-oss-120b", "messages": messages}
    if tools:
        body["tools"] = tools
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                      headers={"Authorization": "Bearer " + os.environ["GROQ_API_KEY"]}, json=body)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]

# ---------- YOUR SERVER (yours to write) ----------
# python tool_call.py                      asks the question below
# python tool_call.py "What is an API?"    asks your own
question = " ".join(sys.argv[1:]) or "When is Lecture 12 of 100xEngineers Cohort 8, and what is it about?"
messages = [{"role": "user", "content": question}]

# Step 2. The card: what the model reads instead of the function itself.
card = {"type": "function", "function": {
    "name": "get_lecture",
    "description": (                                                      # Use it when
        "Looks up one lecture of the 100xEngineers Cohort 8 curriculum by its number and returns "
        "its date, title, type (combined or separate session) and the tools it uses. "
        "Use it when someone asks about a specific 100xEngineers Cohort 8 lecture, class or session "
        "by its number, e.g. 'Lecture 12', 'the seventh class', 'session ten'. "
        "Do not use it for general questions (e.g. 'What is an API?') or for lectures of any other "
        "course (e.g. Harvard CS50)."
    ),
    "parameters": {"type": "object",
                   "properties": {"number": {"type": "integer",
                                             "description": (     # It needs
                                                 "The lecture number, 1 to 19, as a digit. "
                                                 "Turn words into digits: 'seventh' is 7, 'ten' is 10."
                                             )}},
                   "required": ["number"]},
}}

# My own data: the card for get_app_stats.
stats_card = {"type": "function", "function": {
    "name": "get_app_stats",
    "description": (                                                      # Use it when
        "Gets live numbers for one of my own GitHub projects, mainly wificonnector, my Mac menu-bar app "
        "that logs in to VIT hostel Wi-Fi: stars, watchers, forks, when it was created and last updated, "
        "how many releases it has, the latest release, and total downloads. Use it when someone asks how my "
        "app or project is doing, how many people downloaded or starred it, or what its latest version is. "
        "Do not use it for other people's projects, for general questions about GitHub, or for how to use the app."
    ),
    "parameters": {"type": "object",
                   "properties": {"repo": {"type": "string", "enum": MY_REPOS,                   # It needs
                                           "description": "Which of my projects. Use wificonnector unless another one is named."}},
                   "required": ["repo"]},
}}

cards = [card, stats_card]
TOOLS = {"get_lecture": get_lecture, "get_app_stats": get_app_stats}     # the name the model asks for -> my function

# Steps 3 to 5. While the model asks for a tool, run each request (step 3),
# hand the result back as a "tool" message (step 4), and ask again. When it stops asking, print its answer.
reply = ask_model(messages, cards)

while reply.get("tool_calls"):
    messages.append(reply)                                                # the model's request
    for call in reply["tool_calls"]:
        name = call["function"]["name"]
        args = json.loads(call["function"]["arguments"])                  # arguments arrive as text
        print("The model asked for:", name, args)
        result = TOOLS[name](**args) if name in TOOLS else {"error": f"There is no tool called {name}."}
        messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})
    reply = ask_model(messages, cards)

print("\n" + reply["content"])
