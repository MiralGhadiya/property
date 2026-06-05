Summary of automated and manual lint fixes

What I ran:
- Installed and ran `ruff --fix`, `isort .`, and `black .` to auto-fix style issues.
- Re-ran `flake8` to collect remaining warnings/errors.

Manual edits applied:
- Replaced `print()` with `logger.info()` in `app/inspect_redis.py`.
- Moved `load_dotenv()` to after imports in `app/routes/auth.py` to fix E402.
- Avoided name collision by changing `import app.celery_app` to `import app.celery_app as celery_app` in `app/main.py` to resolve F811.
- Added `# noqa: F401,F403` to wildcard re-exports in `app/schemas/__init__.py` and `app/models/__init__.py` to silence wildcard-import flake8 warnings.

Remaining notable issues (from `flake8`):
- Many `E712` items: comparisons to `True`/`False` (recommend replacing `x == True` with `if x:` and `x == False` with `if not x:`). Files affected: many under `app/routes/*`, `app/services/*`, `app/tasks/*`.
- Long lines (`E501`) in `app/routes/unified_payment.py`, `app/scripts/generate_postman_collection.py`, `app/services/valuation_report_builder.py`.
- Some minor whitespace/trailing spaces and indentation in `app/llm/*` and `app/utils/*`.
- Unused imports/variables (F401/F841) in a few modules.

Suggested next steps (what I can do next):
1. Run `ruff --select=E712 --fix` or a targeted script to replace boolean comparisons automatically where safe.
2. Break long lines manually or with `black`/`ruff` config adjustments.
3. Remove unused imports/variables and run tests.
4. Create a dedicated branch and commit changes, then open a PR with this report and a checklist of remaining items.

Git commands to create branch and commit my changes locally:

```bash
git checkout -b lint/auto-fixes
git add -A
git commit -m "chore: auto-format and fix lint issues (ruff/isort/black) + small manual fixes"
git push origin lint/auto-fixes
```

If you want, I can proceed to automatically apply the remaining `E712` fixes and attempt to shorten long lines where possible. Reply with `auto-more` to continue automated fixes, `manual` to pick files to fix by hand, or `pr` to create the branch/patch only.
