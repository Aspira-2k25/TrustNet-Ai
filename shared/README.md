# Shared Package (shared)

Cross-service package for common contracts and utilities.

## Purpose

Avoid duplication between services by centralizing:

- Pydantic schemas
- Constants and enums
- JWT verification helper
- Logging setup
- Base settings
- Interface contracts

## Main Modules

- `shared/auth/` - token verification helper
- `shared/config/` - base settings class
- `shared/constants/` - module/status/topic constants
- `shared/interfaces/` - detector base interface
- `shared/logging/` - structured logging setup
- `shared/schemas/` - API response, events, detection result models
- `shared/utils/` - id generation helpers

## Install Editable During Development

```bash
pip install -e shared/
```

## Tests

```bash
python -m pytest shared/tests -v
```
