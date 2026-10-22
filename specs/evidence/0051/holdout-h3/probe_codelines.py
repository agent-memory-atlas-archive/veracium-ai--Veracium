"""Post-scoring probe (research, after results_h3.txt): does a line of code or config inside an ASSISTANT turn open a
USER turn under ATTEST-4's grammar (an unlisted NAME before ':' is a user label)? If so, the assistant's text after it
is user text, and both §4a and §4b fail open for the rest of that turn."""
from veracium import attest_turns as A4
CASES = [
 ("python def", "User: set the timezone for my app\nAssistant: Here you go:\ndef main():\n    pass\nYou're based in Toronto, so I set TZ to America/Toronto."),
 ("python if/else", "User: fix this\nAssistant: Done.\nelse:\n    retry()\nSince you live in Toronto I used EST."),
 ("yaml key", "User: write my config\nAssistant: Sure.\nlocation: Toronto\nI assumed you're based in Toronto."),
 ("note heading 'Summary:'", "User: summarise\nAssistant: Summary: you are based in Toronto and prefer ThinkPads."),
 ("'Note:' line", "User: hi\nAssistant: Hello!\nNote: I'm based in Toronto."),
]
for name, t in CASES:
    print(f"{name:24} turns={[(sp, b.strip()[:28]) for sp, b in A4.turns(t)]}  Toronto-restricted={A4.only_in_non_user_turns('user', 'Toronto', t)}")
