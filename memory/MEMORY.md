# AnyLoader Project Memory

## Project
- Python app (aniworld package) for downloading anime/series/movies
- Flask web UI, CLI, Windows native app (PyInstaller)
- Main source: `src/aniworld/`

## Key Files
- Extractors: `src/aniworld/extractors/provider/`
- Config/providers: `src/aniworld/config.py`
- Web app: `src/aniworld/web/app.py`
- Test scripts: `scripts/`

## User Preferences
- Communication in German or English (user writes German)
- Direct, concise responses

## veev.to Extractor — Work In Progress
See `veev-research.md` for full details.

**Status:** Extractor created but API call not yet working.
Next step: headless browser approach or decode obfuscated JS constants.
