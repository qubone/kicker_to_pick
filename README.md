**Small python project to help map kickers to rookie draft picks in a Sleeper fantasy football start up draft.**

**Dependencies**

This project is using uv for project management
Installation guide:
https://docs.astral.sh/uv/getting-started/installation/

test

**Usage**

This script can be run manually using CLI. 

    uv run kicker_to_pick.py LEAGUE_ID

**Output**

    **20XX Rookie Pick Tracker: League Name**
    *Last Updated: 20XX-XX-XX XX:XX:XX*
    ---
    Pick 1.01 @User1 (via Kicker One)
    Pick 1.02 @User2 (via Kicker Two)
    Pick 1.03 @User2 (via Kicker Three)
    Pick 1.04 @User3 (via Kicker Four)
    Pick 1.05 @User4 (via Kicker Five)
    Pick 1.06 @User1 (via Kicker Six)
    ...

This information is printed as stdout in the terminal and also gets appended to a league-unique log file located in logs directory 
in the root directory of this project.


This can simply be copied and pasted into your league Sleeper chat.


**Periodic scheduling**

You can also set up a scheduler to run it periodically with cron (Linux),  Task Scheduler (Windows) or in a CI job (e.g GitHub Actions)
