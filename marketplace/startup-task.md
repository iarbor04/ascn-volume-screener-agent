# Startup task (runs when the agent starts)

Put the prompt below into the public agent's start prompt. The marketplace copies the whole workspace, so the package files, AGENTS.md and skills are already in place; the data folder `files/screener/` is excluded on publish, and `package.py init` recreates it from `defaults/` for each new user.

## Prompt

```
A new user has just hired you. Set up the workspace quietly and start onboarding.
1. If python3 is missing, install it (apk add python3).
2. Run: python3 files/scripts/package.py start
3. Your whole reply is the text between "SAY:" and "THEN:" in its output, exactly as printed, with its line breaks and emojis. Do not translate it: it is the language choice. Nothing else: no setup details, file names, commands or check results.
4. When the user answers, do what the "THEN:" line says.
If the command could not run at all, reply only: "Setup isn't finished yet. Write me any message and I'll finish it."
Do not create cron jobs.
```

## Before publishing

In the workspace you publish from, ask the agent to run `python3 files/scripts/package.py prepublish` right before you press Publish. It moves this workspace's data (profile, posts, test runs) into the data folder's archive and starts the data folder over, so a copy greets its new user even if the marketplace does not exclude the data folder. Then fill «Исключаемые пути» from `marketplace/publish-exclude.txt`.

## Check after install

- `grep -c "screener-addon:v1" AGENTS.md` returns 1, including after a restart.
- `skills_manage list` shows all 5 skills.
