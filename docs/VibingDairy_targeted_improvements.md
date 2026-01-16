# VibingDairy - targeted_improvements
**Timestamp:** 2026-01-16
## Prompty użyte
- "deliver targeted improvements, and start tightening areas"
- "and update plane via mcp"

## Problemy
- Rozbieżności w README/OPERATOR_GUIDE/USAGE dla komend CLI i przykładowej konfiguracji.
- Brak ostrzeżenia przy włączeniu `allow_shell`.
- Brak testu na observer summary.
- Brak wzmianki o `pip install -e ".[dev]"` w `docs/USAGE.md`.

## Rozwiązania
- Zaktualizowano README/OPERATOR_GUIDE/USAGE pod aktualne komendy i konfigurację.
- Dodano ostrzeżenie log/CLI przy `allow_shell=true`.
- Dodano test observer summary w `tests/test_backend_context.py`.
- Dodano dev install hint w `docs/USAGE.md`.

## Status: Done
