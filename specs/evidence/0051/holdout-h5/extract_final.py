"""Extract a subagent's FINAL assistant text from its JSONL transcript, verbatim, and count its tool uses.
Usage: python -I extract_final.py <transcript.jsonl> <out.txt>"""
import json, sys
last, tools = None, 0
for line in open(sys.argv[1]):
    try:
        rec = json.loads(line)
    except ValueError:
        continue
    msg = rec.get("message") or {}
    if rec.get("type") == "assistant" and isinstance(msg.get("content"), list):
        texts = [c.get("text", "") for c in msg["content"] if c.get("type") == "text"]
        tools += sum(1 for c in msg["content"] if c.get("type") == "tool_use")
        if texts:
            last = "".join(texts)
assert last is not None, "no assistant text found"
open(sys.argv[2], "w").write(last)
print("tool uses:", tools, "| chars:", len(last))
