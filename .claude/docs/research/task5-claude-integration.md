# Claude Code MCP Server Integration Research

## 1. Configuration File Locations & Scopes

| Scope | Location | Description |
|-------|----------|-------------|
| **Local** (default) | `~/.claude.json` (under project path) | Private to you, current project only |
| **Project** | `.mcp.json` (project root) | Shared via version control, team-wide |
| **User** | `~/.claude.json` (global section) | Available across all projects |

## 2. `.mcp.json` Format (Project Scope - Recommended for Team Sharing)

```json
{
  "mcpServers": {
    "spec-workflow": {
      "command": "uvx",
      "args": ["@pimzino/spec-workflow-mcp@latest"],
      "env": {}
    }
  }
}
```

Key points:
- The `"type": "stdio"` field is optional for stdio servers (it's the default)
- `command` is the executable (`uvx`, `npx`, `node`, `python`, etc.)
- `args` is an array of arguments passed to the command
- `env` is an object of environment variables
- Supports `${VAR}` and `${VAR:-default}` environment variable expansion

## 3. `claude mcp add` Command

### Syntax

```bash
claude mcp add [options] <name> -- <command> [args...]
```

**Important**: All options must come BEFORE the server name. The `--` separates server name from command/args.

### Options

| Option | Description |
|--------|-------------|
| `--transport <type>` | Transport type: `stdio` (default), `http`, `sse` |
| `--env KEY=value` | Set environment variable (repeatable) |
| `--scope <scope>` | `local` (default), `project`, `user` |
| `--header "Key: Value"` | HTTP headers (for http/sse transport) |

### Examples for uvx-based Servers

```bash
# Add a uvx MCP server (stdio transport, local scope - default)
claude mcp add spec-workflow -- uvx @pimzino/spec-workflow-mcp@latest

# Add with project scope (creates .mcp.json)
claude mcp add --scope project spec-workflow -- uvx @pimzino/spec-workflow-mcp@latest

# Add with environment variables
claude mcp add --env API_KEY=xxx spec-workflow -- uvx @pimzino/spec-workflow-mcp@latest

# Add with env-file (uvx feature)
claude mcp add my-server -- uvx --env-file /path/to/.env my-package
```

### JSON-based Addition

```bash
claude mcp add-json spec-workflow '{"type":"stdio","command":"uvx","args":["@pimzino/spec-workflow-mcp@latest"],"env":{}}'
```

### Management Commands

```bash
claude mcp list              # List all configured servers
claude mcp get <name>        # Get details for a specific server
claude mcp remove <name>     # Remove a server
/mcp                         # Check server status (within Claude Code)
```

## 4. Gotchas & Troubleshooting

### Common Issues

1. **Option ordering**: All flags (`--transport`, `--env`, `--scope`) MUST come before the server name. The `--` separates server name from command args. Wrong order causes silent failures.

2. **Startup timeout**: Default timeout may be too short for uvx servers that need to download packages on first run. Set `MCP_TIMEOUT` environment variable:
   ```bash
   MCP_TIMEOUT=10000 claude   # 10-second timeout
   ```

3. **Output token limit**: Warning at 10,000 tokens, default max 25,000. Adjust with:
   ```bash
   MAX_MCP_OUTPUT_TOKENS=50000 claude
   ```

4. **Windows `npx` issue**: On native Windows (not WSL), `npx` requires `cmd /c` wrapper. Not applicable to macOS/Linux.

5. **Project scope approval**: Claude Code prompts for approval before using project-scoped servers from `.mcp.json`. Reset with `claude mcp reset-project-choices`.

6. **Scope precedence**: Local > Project > User. Local overrides project overrides user.

### uvx-Specific Notes

- `uvx` creates isolated environments; first run may be slower due to package download
- Use `@latest` suffix to always get the latest version
- `uvx` is a command from the `uv` package manager (Astral) - must be installed
- Environment variable expansion works in `.mcp.json`: `${VAR:-default}`

## 5. Recommended Setup for spec-workflow-mcp

### Option A: CLI Command (Quick Setup)

```bash
claude mcp add --scope project spec-workflow -- uvx @pimzino/spec-workflow-mcp@latest
```

This creates a `.mcp.json` file in the project root that can be committed to git.

### Option B: Manual .mcp.json (More Control)

Create `.mcp.json` at project root:

```json
{
  "mcpServers": {
    "spec-workflow": {
      "command": "uvx",
      "args": ["@pimzino/spec-workflow-mcp@latest"],
      "env": {}
    }
  }
}
```

### Option C: Dashboard Mode

```bash
# Run with dashboard
npx -y @pimzino/spec-workflow-mcp@latest --dashboard
# Dashboard URL: http://localhost:5000
```

For MCP server mode (without dashboard), use `uvx` as shown above.

## Sources

- [Claude Code MCP Official Docs](https://code.claude.com/docs/en/mcp)
- [Configuring MCP Tools in Claude Code - Scott Spence](https://scottspence.com/posts/configuring-mcp-tools-in-claude-code)
- [Claude Code Tips & Tricks: Setting Up MCP Servers](https://cloudartisan.com/posts/2025-04-12-adding-mcp-servers-claude-code/)
- [MCPcat: Add MCP Servers to Claude Code](https://mcpcat.io/guides/adding-an-mcp-server-to-claude-code/)
