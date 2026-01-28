# AniWorld Downloader API Documentation

This document provides comprehensive documentation for all API endpoints available in the AniWorld Downloader web application.

## Base URL

```
http://localhost:5000
```

When running with `--web-expose`, the API is accessible on all network interfaces.

## Authentication

Most API endpoints require authentication via session cookies. After logging in, a session token is stored as an HTTP-only cookie with a 30-day expiration.

### Session Flow

1. POST to `/login` with credentials
2. Receive session cookie automatically
3. Include cookie in subsequent requests
4. Session expires after 30 days of inactivity

---

## Endpoints

### Health & System

#### Health Check

```http
GET /health
```

Check if the server is running.

**Authentication:** Not required

**Response:**
```json
{
  "status": "healthy"
}
```

**Example:**
```bash
curl http://localhost:5000/health
```

---

#### System Information

```http
GET /api/info
```

Get system information including version, uptime, and supported providers.

**Authentication:** Required

**Response:**
```json
{
  "version": "3.9.0",
  "status": "running",
  "uptime": "2 days, 3 hours, 45 minutes",
  "latest_version": "3.9.0",
  "is_newest": true,
  "supported_providers": [
    "LoadX",
    "VOE",
    "Vidmoly",
    "Filemoon",
    "Luluvdo",
    "Doodstream",
    "Vidoza",
    "SpeedFiles",
    "Streamtape"
  ],
  "platform": "linux"
}
```

**Example:**
```bash
curl -b cookies.txt http://localhost:5000/api/info
```

---

#### Test API

```http
GET /api/test
```

Simple endpoint to test API connectivity.

**Authentication:** Required

**Response:**
```json
{
  "message": "API is working!"
}
```

---

### Authentication

#### Login

```http
POST /login
```

Authenticate a user and create a session.

**Authentication:** Not required

**Content-Type:** `application/x-www-form-urlencoded` or `application/json`

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| username | string | Yes | Username |
| password | string | Yes | Password |

**Response (Success):**
```json
{
  "success": true,
  "redirect": "/"
}
```

**Response (Failure):**
```json
{
  "success": false,
  "message": "Invalid username or password"
}
```

**Example:**
```bash
# Login and save session cookie
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "yourpassword"}' \
  -c cookies.txt
```

---

#### Logout

```http
POST /logout
```

End the current session.

**Authentication:** Required

**Response:** Redirect to `/login`

**Example:**
```bash
curl -X POST http://localhost:5000/logout -b cookies.txt
```

---

#### First-Time Setup

```http
POST /setup
```

Create the initial admin account. Only available when no users exist.

**Authentication:** Not required

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| username | string | Yes | Admin username |
| password | string | Yes | Admin password |

**Response:**
```json
{
  "success": true,
  "message": "Admin account created successfully"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/setup \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "securepassword"}'
```

---

### User Management (Admin Only)

#### List Users

```http
GET /api/users
```

Get a list of all users.

**Authentication:** Required (Admin only)

**Response:**
```json
{
  "success": true,
  "users": [
    {
      "id": 1,
      "username": "admin",
      "is_admin": true,
      "is_original_admin": true,
      "created_at": "2026-01-28T10:30:00",
      "last_login": "2026-01-28T12:00:00"
    },
    {
      "id": 2,
      "username": "user1",
      "is_admin": false,
      "is_original_admin": false,
      "created_at": "2026-01-28T11:00:00",
      "last_login": null
    }
  ]
}
```

**Example:**
```bash
curl -b cookies.txt http://localhost:5000/api/users
```

---

#### Create User

```http
POST /api/users
```

Create a new user account.

**Authentication:** Required (Admin only)

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| username | string | Yes | New username |
| password | string | Yes | User password |
| is_admin | boolean | No | Grant admin privileges (default: false) |

**Response:**
```json
{
  "success": true,
  "message": "User created successfully"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/users \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"username": "newuser", "password": "password123", "is_admin": false}'
```

---

#### Update User

```http
PUT /api/users/<user_id>
```

Update an existing user.

**Authentication:** Required (Admin only)

**URL Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| user_id | integer | User ID to update |

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| password | string | No | New password |
| is_admin | boolean | No | Update admin status |

**Response:**
```json
{
  "success": true,
  "message": "User updated successfully"
}
```

**Example:**
```bash
curl -X PUT http://localhost:5000/api/users/2 \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"is_admin": true}'
```

---

#### Delete User

```http
DELETE /api/users/<user_id>
```

Delete a user account.

**Authentication:** Required (Admin only)

**URL Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| user_id | integer | User ID to delete |

**Response:**
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:5000/api/users/2 -b cookies.txt
```

---

#### Change Password

```http
POST /api/change-password
```

Change the current user's password.

**Authentication:** Required

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| current_password | string | Yes | Current password |
| new_password | string | Yes | New password |

**Response:**
```json
{
  "success": true,
  "message": "Password changed successfully"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/change-password \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"current_password": "oldpass", "new_password": "newpass"}'
```

---

### Search & Browse

#### Search Anime

```http
POST /api/search
```

Search for anime/series across supported sites.

**Authentication:** Required

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| query | string | Yes | Search query |
| site | string | No | Site to search: "aniworld.to", "s.to", or "both" (default: "both") |

**Response:**
```json
{
  "success": true,
  "results": [
    {
      "name": "Demon Slayer: Kimetsu no Yaiba",
      "link": "demon-slayer-kimetsu-no-yaiba",
      "cover": "https://aniworld.to/public/img/cover/demon-slayer.jpg",
      "description": "A young boy becomes a demon slayer after his family is killed...",
      "productionYear": 2019,
      "site": "aniworld.to"
    },
    {
      "name": "Demon Slayer Movie",
      "link": "demon-slayer-movie",
      "cover": "https://aniworld.to/public/img/cover/demon-slayer-movie.jpg",
      "description": "The Mugen Train arc...",
      "productionYear": 2020,
      "site": "aniworld.to"
    }
  ]
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"query": "Demon Slayer", "site": "both"}'
```

---

#### Direct URL Input

```http
POST /api/direct
```

Process a direct anime/series URL.

**Authentication:** Required

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| url | string | Yes | Full URL to the anime/series page |

**Response:**
```json
{
  "success": true,
  "result": {
    "title": "Demon Slayer: Kimetsu no Yaiba 2019",
    "url": "https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba",
    "slug": "demon-slayer-kimetsu-no-yaiba",
    "site": "aniworld.to",
    "cover": "https://aniworld.to/public/img/cover/demon-slayer.jpg",
    "description": "A young boy becomes a demon slayer..."
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/direct \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"url": "https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba"}'
```

---

#### Popular & New Anime

```http
GET /api/popular-new
```

Get lists of popular and newly added anime.

**Authentication:** Required

**Response:**
```json
{
  "success": true,
  "popular": [
    {
      "name": "One Piece",
      "link": "one-piece",
      "cover": "...",
      "site": "aniworld.to"
    }
  ],
  "new": [
    {
      "name": "New Anime 2026",
      "link": "new-anime-2026",
      "cover": "...",
      "site": "aniworld.to"
    }
  ]
}
```

**Example:**
```bash
curl -b cookies.txt http://localhost:5000/api/popular-new
```

---

### Episodes & Series

#### Get Episodes

```http
POST /api/episodes
```

Get all episodes for a series, organized by season.

**Authentication:** Required

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| series_url | string | Yes | URL of the anime/series page |

**Response:**
```json
{
  "success": true,
  "episodes": {
    "1": [
      {
        "season": 1,
        "episode": 1,
        "title": "Cruelty",
        "url": "https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba/staffel-1/episode-1"
      },
      {
        "season": 1,
        "episode": 2,
        "title": "Trainer Sakonji Urokodaki",
        "url": "https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba/staffel-1/episode-2"
      }
    ],
    "2": [
      {
        "season": 2,
        "episode": 1,
        "title": "Flame Hashira Kyojuro Rengoku",
        "url": "https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba/staffel-2/episode-1"
      }
    ]
  },
  "movies": [
    {
      "movie": 1,
      "title": "Mugen Train",
      "url": "https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba/filme/film-1"
    }
  ],
  "slug": "demon-slayer-kimetsu-no-yaiba"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/episodes \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"series_url": "https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba"}'
```

---

### Downloads

#### Start Download

```http
POST /api/download
```

Add episode(s) to the download queue.

**Authentication:** Required

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| episode_urls | array | Yes | List of episode URLs to download |
| anime_title | string | Yes | Title of the anime |
| language | string | No | Language: "German Sub", "German Dub", "English Sub" (default: "German Sub") |
| provider | string | No | Streaming provider (default: first available) |

**Supported Providers:**
- LoadX
- VOE
- Vidmoly
- Filemoon
- Luluvdo
- Doodstream
- Vidoza
- SpeedFiles
- Streamtape

**Response:**
```json
{
  "success": true,
  "message": "Download added to queue: 3 episode(s) will download in parallel",
  "episode_count": 3,
  "language": "German Sub",
  "provider": "VOE",
  "queue_ids": [1, 2, 3],
  "max_concurrent": 3
}
```

**Example:**
```bash
# Download multiple episodes
curl -X POST http://localhost:5000/api/download \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "episode_urls": [
      "https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba/staffel-1/episode-1",
      "https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba/staffel-1/episode-2",
      "https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba/staffel-1/episode-3"
    ],
    "anime_title": "Demon Slayer",
    "language": "German Sub",
    "provider": "VOE"
  }'
```

---

#### Queue Status

```http
GET /api/queue-status
```

Get the current download queue status.

**Authentication:** Required

**Response:**
```json
{
  "success": true,
  "queue": {
    "active": [
      {
        "id": 1,
        "anime_title": "Demon Slayer",
        "total_episodes": 1,
        "completed_episodes": 0,
        "status": "downloading",
        "current_episode": "Downloading Demon Slayer - Episode 1 (Season 1)",
        "progress_percentage": 45.5,
        "current_episode_progress": 45.5,
        "error_message": "",
        "created_at": "2026-01-28T10:30:00"
      }
    ],
    "completed": [
      {
        "id": 0,
        "anime_title": "One Piece",
        "total_episodes": 1,
        "completed_episodes": 1,
        "status": "completed",
        "progress_percentage": 100.0,
        "completed_at": "2026-01-28T09:30:00"
      }
    ]
  }
}
```

**Example:**
```bash
curl -b cookies.txt http://localhost:5000/api/queue-status
```

---

#### Get Download Path

```http
GET /api/download-path
```

Get the configured download directory path.

**Authentication:** Required

**Response:**
```json
{
  "success": true,
  "path": "/home/user/Downloads"
}
```

**Example:**
```bash
curl -b cookies.txt http://localhost:5000/api/download-path
```

---

### File Management

#### List Files

```http
GET /api/files
```

List downloaded files and folders with navigation support.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| path | string | No | Relative path within downloads directory |

**Response:**
```json
{
  "success": true,
  "path": "/home/user/Downloads",
  "current_path": "Demon Slayer",
  "parent_path": "",
  "folders": [
    {
      "name": "Season 1",
      "path": "Demon Slayer/Season 1",
      "type": "folder",
      "video_count": 26
    },
    {
      "name": "Season 2",
      "path": "Demon Slayer/Season 2",
      "type": "folder",
      "video_count": 18
    }
  ],
  "files": [
    {
      "name": "Special Episode.mkv",
      "path": "Demon Slayer/Special Episode.mkv",
      "full_path": "/home/user/Downloads/Demon Slayer/Special Episode.mkv",
      "type": "file",
      "size": 1073741824,
      "size_human": "1.0 GB",
      "modified": 1706451000.0,
      "modified_human": "2026-01-28 10:30"
    }
  ]
}
```

**Example:**
```bash
# List root directory
curl -b cookies.txt "http://localhost:5000/api/files"

# Navigate to subfolder
curl -b cookies.txt "http://localhost:5000/api/files?path=Demon%20Slayer/Season%201"
```

---

#### Stream Video

```http
GET /api/files/stream/<path>
```

Stream a video file with HTTP range request support for seeking.

**Authentication:** Required

**URL Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| path | string | URL-encoded relative path to the video file |

**Headers:**
| Header | Description |
|--------|-------------|
| Range | Optional. Byte range for partial content (e.g., "bytes=0-1023") |

**Response:**
- **200 OK** - Full file content
- **206 Partial Content** - Partial file content (when Range header is present)

**Response Headers:**
| Header | Description |
|--------|-------------|
| Content-Type | video/mp4, video/x-matroska, etc. |
| Content-Length | Size of response |
| Content-Range | Byte range (for 206 responses) |
| Accept-Ranges | bytes |

**Example:**
```bash
# Stream full file
curl -b cookies.txt "http://localhost:5000/api/files/stream/Demon%20Slayer/Episode%201.mkv" -o video.mkv

# Stream with range request (for seeking)
curl -b cookies.txt \
  -H "Range: bytes=0-1048575" \
  "http://localhost:5000/api/files/stream/Demon%20Slayer/Episode%201.mkv"
```

---

#### Download File

```http
GET /api/files/download/<path>
```

Download a file with Content-Disposition header for browser download.

**Authentication:** Required

**URL Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| path | string | URL-encoded relative path to the file |

**Response Headers:**
| Header | Value |
|--------|-------|
| Content-Disposition | attachment; filename="filename.ext" |

**Example:**
```bash
curl -b cookies.txt \
  "http://localhost:5000/api/files/download/Demon%20Slayer/Episode%201.mkv" \
  -o "Episode 1.mkv"
```

---

#### Delete File

```http
POST /api/files/delete
```

Delete a file from the downloads directory.

**Authentication:** Required

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| path | string | Yes | Relative path to the file to delete |

**Response:**
```json
{
  "success": true,
  "message": "File deleted successfully"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/files/delete \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"path": "Demon Slayer/Season 1/Episode 1.mkv"}'
```

---

### Watch Progress

#### Get Watch Progress

```http
GET /api/watch-progress
```

Get watch progress for files.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file | string | No | Specific file path. If omitted, returns all progress |

**Response (Single File):**
```json
{
  "success": true,
  "progress": {
    "current_time": 1234.5,
    "duration": 1440.0,
    "last_watched": "2026-01-28T10:30:00",
    "percentage": 85.7
  }
}
```

**Response (All Files):**
```json
{
  "success": true,
  "progress": {
    "Demon Slayer/Episode 1.mkv": {
      "current_time": 1234.5,
      "duration": 1440.0,
      "last_watched": "2026-01-28T10:30:00",
      "percentage": 85.7
    },
    "Demon Slayer/Episode 2.mkv": {
      "current_time": 600.0,
      "duration": 1440.0,
      "last_watched": "2026-01-28T11:00:00",
      "percentage": 41.7
    }
  }
}
```

**Example:**
```bash
# Get all progress
curl -b cookies.txt http://localhost:5000/api/watch-progress

# Get progress for specific file
curl -b cookies.txt "http://localhost:5000/api/watch-progress?file=Demon%20Slayer/Episode%201.mkv"
```

---

#### Save Watch Progress

```http
POST /api/watch-progress
```

Save watch progress for a file.

**Authentication:** Required

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file | string | Yes | Relative path to the video file |
| current_time | number | Yes | Current playback position in seconds |
| duration | number | Yes | Total video duration in seconds |

**Response:**
```json
{
  "success": true,
  "message": "Progress saved"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/watch-progress \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "file": "Demon Slayer/Episode 1.mkv",
    "current_time": 1234.5,
    "duration": 1440.0
  }'
```

---

#### Clear Watch Progress

```http
DELETE /api/watch-progress
```

Clear watch progress for a specific file.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file | string | Yes | File path to clear progress for |

**Response:**
```json
{
  "success": true,
  "message": "Progress cleared"
}
```

**Example:**
```bash
curl -X DELETE -b cookies.txt \
  "http://localhost:5000/api/watch-progress?file=Demon%20Slayer/Episode%201.mkv"
```

---

### Chromecast

#### Discover Devices

```http
GET /api/chromecast/discover
```

Discover available Chromecast devices on the network.

**Authentication:** Required

**Response:**
```json
{
  "success": true,
  "devices": [
    {
      "uuid": "aabbccdd-1234-5678-90ab-cdef12345678",
      "name": "Living Room TV",
      "model": "Chromecast with Google TV"
    },
    {
      "uuid": "11223344-5566-7788-99aa-bbccddeeff00",
      "name": "Bedroom TV",
      "model": "Chromecast"
    }
  ]
}
```

**Example:**
```bash
curl -b cookies.txt http://localhost:5000/api/chromecast/discover
```

---

#### Cast to Device

```http
POST /api/chromecast/cast
```

Cast a video file to a Chromecast device.

**Authentication:** Required

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| device_uuid | string | Yes | UUID of the Chromecast device |
| file_path | string | Yes | Relative path to the video file |
| title | string | No | Display title on Chromecast |

**Response:**
```json
{
  "success": true,
  "message": "Casting to Living Room TV"
}
```

**Example:**
```bash
curl -X POST http://localhost:5000/api/chromecast/cast \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "device_uuid": "aabbccdd-1234-5678-90ab-cdef12345678",
    "file_path": "Demon Slayer/Episode 1.mkv",
    "title": "Demon Slayer - Episode 1"
  }'
```

---

#### Control Playback

```http
POST /api/chromecast/control
```

Control Chromecast playback.

**Authentication:** Required

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| device_uuid | string | Yes | UUID of the Chromecast device |
| action | string | Yes | Action: "play", "pause", "stop", "volume" |
| value | number | No | Value for volume action (0-100) |

**Actions:**
- `play` - Resume playback
- `pause` - Pause playback
- `stop` - Stop playback
- `volume` - Set volume (requires `value` parameter)

**Response:**
```json
{
  "success": true,
  "message": "Playback paused"
}
```

**Example:**
```bash
# Pause playback
curl -X POST http://localhost:5000/api/chromecast/control \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"device_uuid": "aabbccdd-1234-5678-90ab-cdef12345678", "action": "pause"}'

# Set volume to 50%
curl -X POST http://localhost:5000/api/chromecast/control \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"device_uuid": "aabbccdd-1234-5678-90ab-cdef12345678", "action": "volume", "value": 50}'
```

---

#### Device Status

```http
GET /api/chromecast/status
```

Get the status of a Chromecast device.

**Authentication:** Required

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| device_uuid | string | Yes | UUID of the Chromecast device |

**Response:**
```json
{
  "success": true,
  "status": {
    "player_state": "PLAYING",
    "current_time": 120.5,
    "duration": 1440.0,
    "volume_level": 0.5,
    "volume_muted": false,
    "title": "Demon Slayer - Episode 1"
  }
}
```

**Example:**
```bash
curl -b cookies.txt \
  "http://localhost:5000/api/chromecast/status?device_uuid=aabbccdd-1234-5678-90ab-cdef12345678"
```

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "success": false,
  "message": "Error description"
}
```

### Common HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 206 | Partial Content (for range requests) |
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Not logged in |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error |

---

## Complete Workflow Example

Here's a complete example workflow using curl:

```bash
#!/bin/bash

BASE_URL="http://localhost:5000"
COOKIES="cookies.txt"

# 1. Login
echo "Logging in..."
curl -s -X POST "$BASE_URL/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "yourpassword"}' \
  -c "$COOKIES"

# 2. Search for anime
echo "Searching for Demon Slayer..."
curl -s -X POST "$BASE_URL/api/search" \
  -H "Content-Type: application/json" \
  -b "$COOKIES" \
  -d '{"query": "Demon Slayer", "site": "both"}'

# 3. Get episodes for the series
echo "Getting episodes..."
curl -s -X POST "$BASE_URL/api/episodes" \
  -H "Content-Type: application/json" \
  -b "$COOKIES" \
  -d '{"series_url": "https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba"}'

# 4. Start downloading episodes
echo "Starting download..."
curl -s -X POST "$BASE_URL/api/download" \
  -H "Content-Type: application/json" \
  -b "$COOKIES" \
  -d '{
    "episode_urls": [
      "https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba/staffel-1/episode-1"
    ],
    "anime_title": "Demon Slayer",
    "language": "German Sub",
    "provider": "VOE"
  }'

# 5. Check download progress
echo "Checking queue status..."
curl -s -b "$COOKIES" "$BASE_URL/api/queue-status"

# 6. List downloaded files
echo "Listing files..."
curl -s -b "$COOKIES" "$BASE_URL/api/files"

# 7. Logout
echo "Logging out..."
curl -s -X POST "$BASE_URL/logout" -b "$COOKIES"

# Cleanup
rm -f "$COOKIES"
```

---

## Python Example

```python
import requests

class AniWorldAPI:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()

    def login(self, username, password):
        """Authenticate with the API."""
        response = self.session.post(
            f"{self.base_url}/login",
            json={"username": username, "password": password}
        )
        return response.json()

    def search(self, query, site="both"):
        """Search for anime/series."""
        response = self.session.post(
            f"{self.base_url}/api/search",
            json={"query": query, "site": site}
        )
        return response.json()

    def get_episodes(self, series_url):
        """Get all episodes for a series."""
        response = self.session.post(
            f"{self.base_url}/api/episodes",
            json={"series_url": series_url}
        )
        return response.json()

    def download(self, episode_urls, anime_title, language="German Sub", provider="VOE"):
        """Start downloading episodes."""
        response = self.session.post(
            f"{self.base_url}/api/download",
            json={
                "episode_urls": episode_urls,
                "anime_title": anime_title,
                "language": language,
                "provider": provider
            }
        )
        return response.json()

    def get_queue_status(self):
        """Get download queue status."""
        response = self.session.get(f"{self.base_url}/api/queue-status")
        return response.json()

    def list_files(self, path=""):
        """List downloaded files."""
        response = self.session.get(
            f"{self.base_url}/api/files",
            params={"path": path} if path else {}
        )
        return response.json()

    def logout(self):
        """End the session."""
        self.session.post(f"{self.base_url}/logout")


# Usage example
if __name__ == "__main__":
    api = AniWorldAPI()

    # Login
    api.login("admin", "yourpassword")

    # Search for anime
    results = api.search("Demon Slayer")
    print(f"Found {len(results['results'])} results")

    # Get episodes
    if results['results']:
        first_result = results['results'][0]
        series_url = f"https://aniworld.to/anime/stream/{first_result['link']}"
        episodes = api.get_episodes(series_url)
        print(f"Found {len(episodes.get('episodes', {}).get('1', []))} episodes in season 1")

    # Logout
    api.logout()
```

---

## JavaScript/TypeScript Example

```typescript
class AniWorldAPI {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:5000") {
    this.baseUrl = baseUrl;
  }

  async login(username: string, password: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ username, password })
    });
    return response.json();
  }

  async search(query: string, site: string = "both"): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ query, site })
    });
    return response.json();
  }

  async getEpisodes(seriesUrl: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/episodes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ series_url: seriesUrl })
    });
    return response.json();
  }

  async download(
    episodeUrls: string[],
    animeTitle: string,
    language: string = "German Sub",
    provider: string = "VOE"
  ): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        episode_urls: episodeUrls,
        anime_title: animeTitle,
        language,
        provider
      })
    });
    return response.json();
  }

  async getQueueStatus(): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/queue-status`, {
      credentials: "include"
    });
    return response.json();
  }

  async listFiles(path: string = ""): Promise<any> {
    const url = new URL(`${this.baseUrl}/api/files`);
    if (path) url.searchParams.set("path", path);

    const response = await fetch(url.toString(), {
      credentials: "include"
    });
    return response.json();
  }
}

// Usage
const api = new AniWorldAPI();

async function main() {
  await api.login("admin", "yourpassword");

  const results = await api.search("Demon Slayer");
  console.log(`Found ${results.results.length} results`);

  if (results.results.length > 0) {
    const seriesUrl = `https://aniworld.to/anime/stream/${results.results[0].link}`;
    const episodes = await api.getEpisodes(seriesUrl);
    console.log(`Found ${episodes.episodes["1"]?.length || 0} episodes in season 1`);
  }
}

main();
```

---

## Rate Limiting

The API does not currently implement rate limiting, but clients should implement reasonable delays between requests to avoid overloading the server or upstream providers.

**Recommended practices:**
- Wait 1-2 seconds between search requests
- Limit concurrent downloads to 3 (server default)
- Implement exponential backoff for failed requests

---

## Supported Video Formats

The file streaming endpoint supports the following video formats:

| Extension | MIME Type |
|-----------|-----------|
| .mp4 | video/mp4 |
| .mkv | video/x-matroska |
| .avi | video/x-msvideo |
| .webm | video/webm |
| .mov | video/quicktime |
| .m4v | video/x-m4v |
| .flv | video/x-flv |
| .wmv | video/x-ms-wmv |
