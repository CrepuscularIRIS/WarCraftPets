# Agent Instructions (AGENTS.md)

This project uses **Gastown (gt)** for multi-agent orchestration and **bd** (beads) for issue tracking.

## Agent Roles

### ClaudeCode (Writer)
- **Primary Role**: Implementation, refactoring, feature development
- **Responsibilities**:
  - Writing code and tests
  - Running quality gates (tests, linters)
  - Committing and pushing changes
- **Exit Criteria**: Code implemented, tests passing, pushed to remote
- **Environment**: ClaudeCode CLI with full workspace access

### Codex (Reviewer)
- **Primary Role**: Code review, testing, debugging, quality assurance
- **Responsibilities**:
  - Reviewing code for logic errors and bugs
  - Running verification tests
  - Documenting issues and suggesting fixes
  - Validating "Landing the Plane" workflow completion
- **Exit Criteria**: Review complete, issues documented, fixes suggested
- **Environment**: Codex agent with review focus

## gt sling Command Examples

Gastown's `gt sling` command assigns tasks to agents:

```bash
# Feature implementation by ClaudeCode
gt sling "implement damage multiplier for rare pets" WarCraftPets --agent claude

# Bug fix by ClaudeCode
gt sling "fix heal calculation overflow at high stats" WarCraftPets --agent claude

# Code review by Codex
gt sling "review damage_pipeline.py for edge cases" WarCraftPets --agent codex-review

# Testing/debugging by Codex
gt sling "debug race condition in turn manager" WarCraftPets --agent codex-review

# Refactoring task
gt sling "refactor effect handlers to use base class" WarCraftPets --agent claude

# Full review with test verification
gt sling "review and test new ability executor" WarCraftPets --agent codex-review
```

### Task Assignment Format

When assigning tasks via Gastown:

```bash
# For implementation
gt sling "implement feature X" WarCraftPets --agent claude --args "details"

# For review
gt sling "review code for feature X" WarCraftPets --agent codex-review --args "focus areas"

# With priority
gt sling "critical bug fix for heal overflow" WarCraftPets --agent claude --priority high
```

## Work Distribution Guidelines

| Task Type | Primary Agent | Command |
|-----------|---------------|---------|
| Feature Implementation | ClaudeCode | `gt sling "implement X" WarCraftPets --agent claude` |
| Bug Fix | ClaudeCode | `gt sling "fix bug X" WarCraftPets --agent claude` |
| Refactoring | ClaudeCode | `gt sling "refactor X" WarCraftPets --agent claude` |
| Code Review | Codex | `gt sling "review X" WarCraftPets --agent codex-review` |
| Testing/Debugging | Codex | `gt sling "test X" WarCraftPets --agent codex-review` |
| Issue Investigation | Codex | `gt sling "investigate X" WarCraftPets --agent codex-review` |

### Work Assignment Principles

1. **ClaudeCode** handles all code writing tasks
2. **Codex** handles all review and testing tasks
3. Use `bd ready` to find available work
4. Use `bd show <id>` to view issue details
5. Use `bd update <id> --status in_progress` to claim work

## Code Review Checklist (Codex)

Before approving any code change, verify:

- [ ] **Tests pass (100% pass rate required)**: `pytest -q`
- [ ] **No obvious logic errors**: Walk through the main code paths
- [ ] **Code follows project conventions**: snake_case, PascalCase, type hints
- [ ] **No security vulnerabilities**: No hardcoded secrets, proper input validation
- [ ] **Edge cases handled**: Null values, empty collections, boundary conditions
- [ ] **Error handling present**: Exceptions caught, meaningful error messages
- [ ] **Documentation updated**: Docstrings for new/changed functions
- [ ] **Git conventions followed**: Conventional commits, descriptive messages

### Review Commands

```bash
# Run full test suite
pytest -v

# Run specific test file
pytest test_pet_stats.py -v

# Check for linting issues
flake8 engine/ --select=E9,F63,F7,F82 --show-source --statistics

# View git diff before review
git diff main...HEAD
```

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

### MANDATORY WORKFLOW

1. **File issues for remaining work** - Create issues for anything that needs follow-up:
   ```bash
   bd add "remaining task description"
   ```

2. **Run quality gates** (if code changed):
   ```bash
   pytest -q  # Quick test run
   ```

3. **Update issue status**:
   ```bash
   bd close <id>          # Close finished work
   bd update <id> --status blocked --note "waiting on X"  # Update blockers
   ```

4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase origin main
   bd sync
   git push origin main
   git status  # MUST show "up to date with origin/main"
   ```

5. **Clean up**:
   ```bash
   git stash drop  # Clear completed stashes
   git remote prune origin  # Prune stale remote branches
   ```

6. **Verify** - All changes committed AND pushed:
   ```bash
   git log --oneline -5  # Check recent commits
   git status            # Should show clean working tree
   ```

### Critical Rules

- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
- Codex must verify ClaudeCode completed "Landing the Plane" before approving

## Testing Requirements

### ClaudeCode Requirements

Before committing, run tests:
```bash
pytest -q
```

Ensure all tests pass before pushing.

### Codex Requirements

Before approving, verify:
```bash
pytest -v  # Full verbose output
```

Run additional verification for review tasks.

## Project Conventions

### Python

- `snake_case` for functions/variables
- `PascalCase` for classes
- Type hints required for public APIs
- Docstrings for public functions using Google style

### Git

- Conventional commits: `type: description`
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
- Pull before push, rebase on main
- Squash fixup commits before pushing

## Agent Handoff

When handing off between agents:

1. Document current state in issue notes
2. List completed work
3. List remaining work
4. Note any blockers or context
5. Use `gt handoff` to transfer context

### Handoff Checklist

```markdown
## Handoff: ClaudeCode -> Codex

### Completed
- Implemented damage multiplier for rare pets
- Added unit tests for new calculation
- All tests passing (20/20)

### Remaining
- Integration testing with battle loop
- Performance validation

### Context
- See PR #42 for full context
- Tests in test_pet_stats.py::TestRarityMultiplier
```

## Quick Reference

```bash
# Find available work
bd ready

# View issue details
bd show <id>

# Claim work
bd update <id> --status in_progress

# Complete work
bd close <id>

# Sync with git
bd sync

# Run tests
pytest -q

# Quick test
pytest -v
```

## Project Structure Reference

```
WarCraftPets/
├── engine/
│   ├── core/           # Battle engine core
│   ├── effects/        # Effect system (100+ handlers)
│   ├── model/          # Data models
│   ├── pets/           # Pet system
│   ├── resolver/       # Battle resolvers
│   ├── constants/      # Constants
│   └── data/           # Data access
├── data/               # Data files
└── test_pet_stats.py   # Test suite (20 tests passing)
```
