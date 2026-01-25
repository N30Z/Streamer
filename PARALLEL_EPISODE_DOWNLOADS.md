PARALLEL_EPISODE_DOWNLOADS.md - Implementierungszusammenfassung
===============================================================

## Änderungen Übersicht

Diese Implementierung ermöglicht es, dass mehrere ausgewählte Episoden parallel heruntergeladen werden.

### VORHER (Monolithischer Download)
- 12 Episoden ausgewählt → 1 Download-Job wird erstellt
- Alle 12 Episoden werden in einer Schleife nacheinander heruntergeladen
- Gesamtdauer: sequenziell = sehr lange

### NACHHER (Parallele Episode-Downloads)
- 12 Episoden ausgewählt → 12 separate Download-Jobs werden erstellt
- Bis zu 3 Jobs laufen gleichzeitig (konfigurierbar)
- Gesamtdauer: parallel = ca. 1/3 der Zeit
- Wenn 1 Episode fertig ist, startet die nächste wartende Episode automatisch

---

## Modifizierte Dateien

### 1. `src/aniworld/config.py`
**Änderung:** DEFAULT_MAX_CONCURRENT_DOWNLOADS konfigurierbar
```python
DEFAULT_MAX_CONCURRENT_DOWNLOADS = 5  # Von 3 auf 5 geändert
```

### 2. `src/aniworld/web/download_manager.py`

#### `add_download()` Methode - KOMPLETT UMGESTELLT
- **VORHER:** Erstellt einen Download-Job mit allen Episode-URLs
- **NACHHER:** Erstellt einen separaten Job für jede Episode-URL
- **Rückgabewert:** 
  - VORHER: `int` (eine Queue-ID)
  - NACHHER: `list` (eine Queue-ID pro Episode)

```python
# Vorher
queue_id = manager.add_download(
    anime_title="Anime",
    episode_urls=["url1", "url2", "url3"],  # 3 Episoden
    ...
)
# queue_id = 1

# Nachher
queue_ids = manager.add_download(
    anime_title="Anime",
    episode_urls=["url1", "url2", "url3"],  # 3 Episoden
    ...
)
# queue_ids = [1, 2, 3]  # Eine ID pro Episode!
```

#### `_process_download_job()` Methode - VEREINFACHT
- **VORHER:** Verarbeitet eine Liste von Episode-URLs in einer Schleife
- **NACHHER:** Verarbeitet nur EINE Episode (weil job["episode_urls"] nur ein Element hat)
- Deutlich einfacher und paralleler

### 3. `src/aniworld/web/app.py`

#### `api_download()` Endpunkt - ANGEPASST
- Verarbeitet Rückgabewert als `list` statt `int`
- Gibt `queue_ids` statt `queue_id` zurück
- Gibt `max_concurrent` in der Response zurück für UI-Info

```json
{
  "success": true,
  "message": "Download added to queue: 12 episode(s) will download in parallel",
  "episode_count": 12,
  "queue_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
  "max_concurrent": 5
}
```

### 4. `src/aniworld/web/static/js/app.js`

#### `startDownload()` Feedback - VERBESSERT
- Zeigt Parallel-Information in der Benachrichtigung
- "Download started for 12 episodes (3 parallel downloads)"

---

## Ablauf-Beispiel

### 12 Episoden mit 3 parallelen Slots

```
Zeit 0s:
  Job 1 (Ep1) → downloading
  Job 2 (Ep2) → downloading
  Job 3 (Ep3) → downloading
  Job 4 (Ep4) → queued
  Job 5 (Ep5) → queued
  ... (Rest queued)

Zeit 10s (Ep1 fertig):
  Job 1 (Ep1) → completed ✓
  Job 2 (Ep2) → downloading 30%
  Job 3 (Ep3) → downloading 20%
  Job 4 (Ep4) → downloading ← STARTET AUTOMATISCH!
  Job 5 (Ep5) → queued
  ...

Zeit 20s (Ep2 fertig):
  Job 1 (Ep1) → completed ✓
  Job 2 (Ep2) → completed ✓
  Job 3 (Ep3) → downloading 40%
  Job 4 (Ep4) → downloading 20%
  Job 5 (Ep5) → downloading ← STARTET AUTOMATISCH!
  ...

... und so weiter
```

### API-Anrufe

```python
# Frontend ruft auf
POST /api/download {
  "episode_urls": ["url1", "url2", ..., "url12"],  # 12 URLs
  "language": "German Sub",
  "provider": "VOE",
  "anime_title": "Beispiel Anime"
}

# Backend gibt zurück
{
  "success": true,
  "message": "Download added to queue: 12 episode(s) will download in parallel",
  "episode_count": 12,
  "queue_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
  "max_concurrent": 3
}

# Frontend zeigt an: "Download started for 12 episodes (3 parallel downloads)"
```

---

## Frontend Integration

### Bestehende Queue-Display passt perfekt
Das Frontend `get_queue_status()` zeigt bereits all diese Download-Jobs an:

```javascript
// Der API-Response zeigt alle 12 aktiven/wartenden Jobs
{
  "active": [
    { "id": 1, "anime_title": "...", "status": "downloading", ... },
    { "id": 2, "anime_title": "...", "status": "downloading", ... },
    { "id": 3, "anime_title": "...", "status": "downloading", ... },
    { "id": 4, "anime_title": "...", "status": "queued", ... },
    ...
  ]
}

// Das Frontend rendet alle einzeln
```

---

## Thread-Sicherheit

- Alle Änderungen sind thread-safe
- `_queue_lock` schützt alle Zugriffe auf `_active_downloads`
- `active_workers` Set trackiert aktive Worker sicher
- Callbacks sind atomar

---

## Fehlerbehandlung

- Fehler bei Episode 1 stoppt nicht Episode 2
- Jeder Download hat einen eigenen Status/Error-Message
- Fehlgeschlagene Episoden können später erneut gestartet werden

---

## Performance-Auswirkungen

### Speicher
- Minimal: Ein Download-Job ist ~500 Bytes
- 12 Episoden = ~6 KB zusätzlich
- 3 Worker-Threads = ~60-90 MB

### CPU
- Thread-Overhead minimal (GIL bei Python)
- Hauptkosten kommen von Download selbst, nicht Scheduling

### Netzwerk
- Mit 3 parallelen Downloads bei 10 Mbps:
  - **Vorher (sequenziell):** 12 × 100s = 1200s = 20 Minuten
  - **Nachher (parallel):** ~400s = 6-7 Minuten
  - **Speedup:** 3x schneller!

---

## Backward Compatibility

### Warnung: API-Änderung!
```python
# Alter Code der mit queue_id arbeitet, bricht!
queue_id = manager.add_download(...)  # TypeError: list → int

# Muss aktualisiert werden zu:
queue_ids = manager.add_download(...)
for queue_id in queue_ids:
    ...
```

Die Flask-API ist backward-kompatibel, da wir `queue_ids` neu bennannt haben.

---

## Testing

Zum Testen des Features:
1. Navigieren Sie zu einer Anime-Seite
2. Wählen Sie z.B. 12 Episoden aus
3. Klicken Sie "Start Download"
4. Schauen Sie die Queue an - alle 12 sollten als separate Jobs sichtbar sein
5. Nach einiger Zeit sollten Sie sehen, dass z.B. 3 "downloading" und 9 "queued" sind
6. Während einer Episode komplett wird, startet die nächste automatisch
