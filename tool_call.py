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
# My reading list, a CSV file next to this one: one row per book.
BOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.csv")

def get_book(title):
    with open(BOOKS, newline="") as f:
        for row in csv.DictReader(f):
            if title.strip().lower() in row["title"].lower():
                return row
    return {"error": f"{title!r} is not on my reading list."}

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

# My own data: the card for get_book.
book_card = {"type": "function", "function": {
    "name": "get_book",
    "description": (                                                      # Use it when
        "Looks up one book on my personal reading list and returns its author, my status "
        "(finished, reading, want to read, abandoned), my rating out of 5, when I finished it, and my note. "
        "Use it when someone asks about my reading, my rating or my opinion of a specific book, "
        "or whether I have read it. Do not use it for general questions about books, such as who wrote "
        "a book or what it is about, or for book recommendations."
    ),
    "parameters": {"type": "object",
                   "properties": {"title": {"type": "string",                                    # It needs
                                            "description": "The book's title, or a distinctive part of it, e.g. 'Sapiens'."}},
                   "required": ["title"]},
}}

cards = [card, book_card]
TOOLS = {"get_lecture": get_lecture, "get_book": get_book}               # the name the model asks for -> my function

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
