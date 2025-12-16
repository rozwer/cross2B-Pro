# Project-local Codex setup

This repository keeps Codex CLI configuration and skills under `.codex/`.

## Use

From the repo root:

```bash
source .codex/env.sh
codex
```

This sets `CODEX_HOME` to this repo’s `.codex/`, so Codex loads:

- config: `.codex/config.toml`
- skills: `.codex/skills/*/SKILL.md`

## Adding / editing skills

- Each skill is a folder under `.codex/skills/<skill-name>/`.
- The `SKILL.md` file must start with YAML frontmatter delimited by `---`.
- Keep skills short and procedural; they are meant to be applied during work.

## Using skills in the Codex TUI

- Open the skill picker by typing `$` in the input prompt.
- Start typing after `$` to filter skills by name.
- You can also mention a skill name explicitly in your request to encourage selection.

## Note on MCP warnings

If you see MCP startup warnings (e.g., `chrome-devtools`), you are likely using your global Codex home/config. Re-run `source .codex/env.sh` before starting `codex` to ensure this repo's `.codex/` is used.
