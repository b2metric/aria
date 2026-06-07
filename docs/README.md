# ARIA Documentation

Architecture, API reference, runbooks, and design decisions.

## Core Documents

| Document | Description |
|----------|-------------|
| [technical-architecture.md](./technical-architecture.md) | Tech stack, data model, resolved decisions |
| [pipeline-flow.md](./pipeline-flow.md) | End-to-end query pipeline, component interactions |
| [vault-schema.md](./vault-schema.md) | Semantic vault file format, keywords, relationships |

## Setup Guides

| Document | Description |
|----------|-------------|
| [oracle-instant-client-setup.md](./oracle-instant-client-setup.md) | Oracle DB connection setup |
| [traefik-ssl-setup.md](./traefik-ssl-setup.md) | Traefik reverse proxy + SSL configuration |

## Project Management

| Document | Description |
|----------|-------------|
| [schedule.md](./schedule.md) | Sprint timeline and milestones |
| [codebase-audit.md](./codebase-audit.md) | Code quality notes |
| [build-execution.md](./build-execution.md) | Build and deployment notes |

## Semantic Vaults

Schema metadata lives in `docs/vaults/{workspace_id}/tables/*.md`.

Each table has a markdown file with:
- YAML frontmatter: table name, schema, keywords, columns, relationships
- Body: business context, example queries, notes

**Full specification:** [vault-schema.md](./vault-schema.md)

See [pipeline-flow.md](./pipeline-flow.md#stage-2-vault-matching-obsidian-semantic-vault) for how vaults are used in query processing.
