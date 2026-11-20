"""Part 2: the same tool on the sheet's side, as an MCP server.  Run: python mcp_server.py
The steps are in README.md."""
import csv, io, socket
from typing import Annotated
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


# Any app can now reach it at http://localhost:8000/mcp
if __name__ == "__main__":
    if socket.socket().connect_ex(("127.0.0.1", 8000)) == 0:
        raise SystemExit("Port 8000 is already in use, probably by a server you started earlier. "
                         "Stop it with Ctrl+C in its terminal, or run: kill $(lsof -t -i:8000)")
    mcp.run(transport="http", port=8000)
