# Scripts

Run commands from the repository root unless a module says otherwise. Daily entry points are `setup.bat`, `start-dev.bat` and `stop-dev.bat` in the root.

| Folder | Use |
| --- | --- |
| `setup/` | One-time environment and checksummed artifact installation |
| `ops/` | Service launch/stop and infrastructure administration |
| `checks/` | Readiness, model integrity, report contracts and real integration checks |
| `packaging/` | Explicit model and runtime export builders |
| `research/` | Training, collection, evaluation and historical experiments |

Research commands are optional. Some require old datasets/checkpoints, research dependencies or network access; they are not teammate setup steps. Model promotion is explicit. Do not run training or promotion scripts merely to start the app.

Current setup commands and supported environment versions: [team setup](../docs/TEAM_SETUP.md). Ownership and verification: [repository structure](../docs/REPOSITORY_STRUCTURE.md).
