# Skill Development Workflow

- **Storage**: Vault/Obsidian skills → `~/Developer/second-brain-skills/<skill>/SKILL.md`; others → `~/Developer/agent-skills/<skill>/SKILL.md`
- **Deployment**: Commit and push to GitHub
- **Installation**: `npx skills add <owner/repo> -s <skill-name> [-g] -y` — `-g` for global, omit for project-local; never manually copy into `.claude/skills/`
- **Sync to vault**: `/sync-skills` inside a vault project
