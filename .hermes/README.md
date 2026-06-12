# .hermes/ — repo-local Hermes profile (config-as-code)

This directory IS the Hermes profile for this project (the equivalent of Claude Code's
`.claude/`). Config, persona, and skills are version-controlled here; secrets and runtime
state are gitignored.

## Activate
```bash
# point the Hermes gateway at this repo-local profile
HERMES_HOME="$PWD/.hermes" hermes gateway install   # (re)installs the launchd service
HERMES_HOME="$PWD/.hermes" hermes gateway status
```
Always run `hermes gateway ...` with `HERMES_HOME="$PWD/.hermes"` exported (a `.envrc`/direnv
is convenient) so a later `hermes update`/`gateway install` does not revert HERMES_HOME to
`~/.hermes`.

## Secrets
Copy `.env.example` to `.env` and fill in real values. `.env` is gitignored and never
committed. `config.yaml` references secrets as `${VAR}` — Hermes expands them at load.

## Committed vs ignored
- committed: `config.yaml`, `SOUL.md`, `skills/`, `agents/`, `.env.example`, `README.md`
- ignored:   `.env`, `auth.json`, `*.lock`, `gateway*`, `cache/`, `logs/`, `home/`, `memories/`, `cron/`, `bin/`, `lsp/`, `pastes/`, `plans/`, `backups/`
