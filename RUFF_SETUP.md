# Ruff Linter & Formatter Setup

## Overview

This project uses **Ruff**, a modern Python linter and formatter written in Rust that's significantly faster than traditional tools like flake8 and black.

## Installation

Ruff is already configured in the project. To install it:

```bash
pip install -r requirements-dev.txt
```

Or install it directly:

```bash
pip install ruff>=0.1.0
```

## Configuration

Ruff is configured in `pyproject.toml` with the following settings:

### Lint Rules

**Enabled Rules:**
- `E` - pycodestyle errors
- `W` - pycodestyle warnings
- `F` - Pyflakes (undefined variables, unused imports)
- `I` - isort (import sorting)
- `B` - flake8-bugbear (common bugs and design problems)
- `C4` - flake8-comprehensions (list/dict/set comprehension optimization)
- `UP` - pyupgrade (syntax modernization)
- `SIM` - flake8-simplify (code simplification)

**Ignored Rules:**
- `E501` - Line too long (handled by formatter)
- `B008` - Function call in default argument (required for FastAPI `Depends()`)

### Formatter Settings

- **Line length:** 88 characters
- **Quote style:** Double quotes
- **Indent style:** Space (4 spaces)
- **Target Python version:** 3.10+

## Usage

### Check Code for Issues

Run the linter to check for code quality issues:

```bash
ruff check .
```

### Fix Issues Automatically

Ruff can automatically fix many common issues:

```bash
ruff check . --fix
```

### Format Code

Format code according to configured style rules:

```bash
ruff format .
```

### Check Formatting Without Applying

Preview formatting changes without applying them:

```bash
ruff format . --check
```

## Common Commands

### Full Quality Check (Lint + Format Check)

```bash
# Check lint issues
ruff check .

# Check formatting without applying
ruff format . --check
```

### Fix and Format All

```bash
# Fix linting issues and format code
ruff check . --fix
ruff format .
```

### Check Specific File

```bash
ruff check app/routers/prices.py
ruff format app/routers/prices.py
```

## Integration with IDE

### VS Code

Add to `.vscode/settings.json`:

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": "explicit"
    }
  }
}
```

### PyCharm

1. Go to Settings → Editor → Code Style
2. Set line length to 88
3. Install the Ruff plugin from PyCharm marketplace
4. Configure Ruff as the formatter

## Recent Improvements

The following issues were automatically fixed and fixed manually:

### Auto-Fixed Issues (18)

- Unused imports removed
- Import ordering fixed (isort)
- Code simplified where possible
- Missing type annotations

### Manual Fixes (1)

- **Exception chaining:** Updated `raise HTTPException(...) from e` in `app/routers/prices.py` for proper exception context

## Test Results

After linting and formatting:

```
✅ All 116 tests passing
✅ All ruff checks passed
✅ Code properly formatted
```

## Best Practices

1. **Run before committing:** Always run `ruff check . --fix && ruff format .` before committing
2. **Use with CI/CD:** Include ruff checks in your CI/CD pipeline
3. **Configure IDE:** Set up your IDE to format on save
4. **Review fixes:** Review automatically fixed issues before committing

## Why Ruff?

- **Speed:** 10-100x faster than flake8 + black
- **Batteries included:** Combines multiple tools (linter + formatter)
- **Easy configuration:** Single `pyproject.toml` section
- **Active development:** Actively maintained and improving
- **Drop-in replacement:** Works as a replacement for flake8 + black + isort

## References

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Ruff Rules Reference](https://docs.astral.sh/ruff/rules/)
- [pyproject.toml Configuration](https://docs.astral.sh/ruff/configuration/)
