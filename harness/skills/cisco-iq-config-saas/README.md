# Cisco IQ Config SaaS

Operational agent skill for Cisco IQ Configuration SaaS workflows across `configbp-ai`, `cbp-engine`, and `cxp-cbp-etl`.

| Path | Description |
| --- | --- |
| [`SKILL.md`](SKILL.md) | Agent skill entrypoint |
| [`docs/`](docs/) | Runbooks and reference |
| [`scripts/`](scripts/) | Operational helper scripts |

## Install

Requires [Node.js](https://nodejs.org) and [GitHub CLI](https://cli.github.com) with access to this private repo (`gh auth login`).

```bash
gh repo clone aabhish2cisco/cisco-iq-config-saas-skill
npx skills add ./cisco-iq-config-saas-skill -g -y --all
```

`-g` installs user-wide; `--all` targets Cursor, Claude Code, OpenCode, and other supported agents. A PromptScript failure is expected and can be ignored. Restart your agent after install.

## Update

```bash
cd cisco-iq-config-saas-skill
git pull
cd ..
npx skills add ./cisco-iq-config-saas-skill -g -y --all
```

## Usage

Ask your agent to use the skill, for example:

> Use the cisco-iq-config-saas skill to check dev Postgres connectivity.

Operational details, scripts, and runbooks live in [`SKILL.md`](SKILL.md).

## Duplicate skills in Cursor

If you see many `/cisco-iq-config-saas` entries, a broken install nested copies inside itself. Clean and reinstall:

```bash
rm -rf ~/.agents/skills/cisco-iq-config-saas
rm -f ~/.cursor/skills/cisco-iq-config-saas ~/.claude/skills/cisco-iq-config-saas
cd ..
npx skills add ./cisco-iq-config-saas-skill -g -y --all
```

Run `npx skills add` from the **parent** of the clone (not from inside the repo). Restart Cursor after.
