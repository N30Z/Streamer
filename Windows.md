# Windows Installation Guide

This guide provides detailed instructions for installing and running AniWorld Downloader on Windows.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
  - [Method 1: pip Install (Recommended)](#method-1-pip-install-recommended)
  - [Method 2: Executable Release](#method-2-executable-release)
  - [Method 3: Development Installation](#method-3-development-installation)
- [Additional Tools](#additional-tools)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Python Installation

1. Download Python 3.9 or higher from [python.org](https://www.python.org/downloads/)
2. During installation, **check "Add Python to PATH"**
3. Verify installation by opening Command Prompt or PowerShell:
   ```powershell
   python --version
   pip --version
   ```

**Important for ARM-based Windows devices**: Use the AMD64 (x64) Python version instead of the ARM version to avoid issues with the curses module.

### Git Installation (Optional)

If you want to install the development version or contribute:

1. Download Git from [git-scm.com](https://git-scm.com/downloads)
2. Run the installer with default settings
3. Verify installation:
   ```powershell
   git --version
   ```

## Installation Methods

### Method 1: pip Install (Recommended)

Open Command Prompt or PowerShell as Administrator and run:

```powershell
pip install --upgrade aniworld
```

To update to the latest version:

```powershell
pip install --upgrade aniworld
```

### Method 2: Executable Release

If you don't want to install Python:

1. Go to the [Releases page](https://github.com/phoenixthrush/AniWorld-Downloader/releases/latest)
2. Download the Windows executable (`.exe` file)
3. Run the executable directly - no installation required

### Method 3: Development Installation

For developers or those who want the latest features:

```powershell
# Clone the repository
git clone https://github.com/phoenixthrush/AniWorld-Downloader.git aniworld

# Navigate to the directory
cd aniworld

# Install in editable mode
pip install -e .
```

To update:

```powershell
cd aniworld
git pull
```

## Additional Tools

AniWorld Downloader can automatically download required tools on Windows:

### MPV Player

MPV is used for streaming. AniWorld will automatically download it on first use, or you can:

1. Download from [mpv.io](https://mpv.io/installation/)
2. Or let AniWorld auto-install: `aniworld --update mpv`

MPV files are stored in: `%APPDATA%\mpv`

### Syncplay

For synchronized watching with friends:

1. Download from [syncplay.pl](https://syncplay.pl/)
2. Or let AniWorld auto-install when needed

### yt-dlp

yt-dlp is installed automatically as a Python dependency. To update:

```powershell
aniworld --update yt-dlp
```

Or manually:

```powershell
pip install --upgrade yt-dlp
```

## Configuration

### Data Locations

AniWorld stores data in the following Windows locations:

| Data Type | Location |
|-----------|----------|
| Application Data | `%APPDATA%\aniworld\` |
| MPV Configuration | `%APPDATA%\mpv\` |
| Downloads (default) | `%USERPROFILE%\Downloads\` |
| Log Files | `%TEMP%\aniworld.log` |
| Database (Web UI) | `%APPDATA%\aniworld\aniworld.db` |

### Anime4K Setup

For enhanced anime quality, configure Anime4K:

**High-Performance GPUs** (GTX 1080, RTX series, etc.):
```powershell
aniworld --anime4k High
```

**Low-Performance GPUs** (GTX 1060, integrated GPUs, etc.):
```powershell
aniworld --anime4k Low
```

**Remove Anime4K**:
```powershell
aniworld --anime4k Remove
```

## Running AniWorld

### Interactive Menu

```powershell
aniworld
```

### Web Interface

```powershell
aniworld --web-ui
```

Access at: `http://localhost:5000`

### Command Line Examples

Download an episode:
```powershell
aniworld --episode "https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba/staffel-1/episode-1"
```

Watch with auto-skip:
```powershell
aniworld --episode "https://aniworld.to/anime/stream/demon-slayer-kimetsu-no-yaiba/staffel-1/episode-1" --action Watch --aniskip
```

## Troubleshooting

### "aniworld" is not recognized

If `aniworld` is not found after installation:

**Option 1**: Add Python Scripts to PATH
1. Find your Python Scripts folder (usually `%USERPROFILE%\AppData\Local\Programs\Python\Python3X\Scripts`)
2. Add it to your system PATH:
   - Press `Win + X` and select "System"
   - Click "Advanced system settings"
   - Click "Environment Variables"
   - Under "User variables", select "Path" and click "Edit"
   - Add the Scripts folder path

**Option 2**: Use Python module syntax
```powershell
python -m aniworld
```

### Permission Errors

Run Command Prompt or PowerShell as Administrator:
1. Right-click on Command Prompt or PowerShell
2. Select "Run as administrator"
3. Run your installation command

### SSL Certificate Errors

If you encounter SSL errors:
```powershell
pip install --upgrade certifi
```

### Curses Module Issues

If you see errors related to the curses module:
1. Ensure `windows-curses` is installed:
   ```powershell
   pip install windows-curses
   ```
2. If on ARM Windows, use the AMD64 Python version

### Debug Mode

To enable detailed logging for troubleshooting:
```powershell
aniworld --debug
```

This opens a PowerShell window showing real-time logs from `%TEMP%\aniworld.log`.

### Firewall Issues

If the web interface isn't accessible:
1. Allow Python through Windows Firewall
2. Or manually allow port 5000 (or your configured port)

## Uninstallation

To completely remove AniWorld Downloader:

```powershell
aniworld --uninstall
```

Or manually:
```powershell
pip uninstall aniworld
```

To remove configuration files:
1. Delete `%APPDATA%\aniworld\`
2. Delete `%APPDATA%\mpv\` (if you want to remove MPV config)

## Support

If you encounter issues:
- Check the [GitHub Issues](https://github.com/phoenixthrush/AniWorld-Downloader/issues)
- Open a new issue with your Windows version and error details
- Contact: contact@phoenixthrush.com or Discord: `phoenixthrush`
