// AniWorld Downloader Web Interface JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('AniWorld Downloader Web Interface loaded');

    // Get UI elements
    // const versionDisplay = document.getElementById('version-display');
    const navTitle = document.getElementById('nav-title');
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const resultsSection = document.getElementById('results-section');
    const resultsContainer = document.getElementById('results-container');
    const loadingSection = document.getElementById('loading-section');
    const emptyState = document.getElementById('empty-state');
    const homeContent = document.getElementById('home-content');
    const localFiles = document.getElementById('local-files');
    const homeLoading = document.getElementById('home-loading');
    const popularNewSections = document.getElementById('popular-new-sections');
    const popularAnimeGrid = document.getElementById('popular-anime-grid');
    const newAnimeGrid = document.getElementById('new-anime-grid');

    // S.to and Movie4k grid elements
    const popularStoGrid = document.getElementById('popular-sto-grid');
    const newStoGrid = document.getElementById('new-sto-grid');
    const popularMovie4kGrid = document.getElementById('popular-movie4k-grid');
    const newMovie4kGrid = document.getElementById('new-movie4k-grid');

    // Provider column loading elements
    const aniworldLoading = document.getElementById('aniworld-loading');
    const aniworldContent = document.getElementById('aniworld-content');
    const stoLoading = document.getElementById('sto-loading');
    const stoContent = document.getElementById('sto-content');
    const movie4kLoading = document.getElementById('movie4k-loading');
    const movie4kContent = document.getElementById('movie4k-content');

    // Theme toggle elements
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');

    // Download modal elements
    const downloadModal = document.getElementById('download-modal');
    const closeDownloadModal = document.getElementById('close-download-modal');
    const cancelDownload = document.getElementById('cancel-download');
    const confirmDownload = document.getElementById('confirm-download');
    const selectAllBtn = document.getElementById('select-all');
    const deselectAllBtn = document.getElementById('deselect-all');
    const episodeTreeLoading = document.getElementById('episode-tree-loading');
    const episodeTree = document.getElementById('episode-tree');
    const selectedEpisodeCount = document.getElementById('selected-episode-count');
    const providerSelect = document.getElementById('provider-select');
    const languageSelect = document.getElementById('language-select');

    // Queue modal elements
    const queueModal = document.getElementById('queue-modal');
    const queueModalEmpty = document.getElementById('queue-modal-empty');
    const closeQueueModalBtn = document.getElementById('close-queue-modal');
    const downloadQueueBtn = document.getElementById('download-queue-btn');
    const downloadBadge = document.getElementById('download-badge');
    const activeDownloads = document.getElementById('active-downloads');
    const completedDownloads = document.getElementById('completed-downloads');
    const activeQueueList = document.getElementById('active-queue-list');
    const completedQueueList = document.getElementById('completed-queue-list');

    // Current download data
    let currentDownloadData = null;
    let availableEpisodes = {};
    let availableMovies = [];
    let selectedEpisodes = new Set();
    let progressInterval = null;
    let availableProviders = [];

    // Saved user preferences (loaded from server)
    let userPreferences = {};

    // Load version info and providers on page load
    loadVersionInfo();

    // Load user preferences from server, then initialize UI
    loadUserPreferences();

    // Check for active downloads on page load
    checkQueueStatus();
    loadAvailableProviders();

    // Queue modal open/close
    if (downloadQueueBtn) {
        downloadQueueBtn.addEventListener('click', () => {
            queueModal.style.display = 'flex';
        });
    }
    if (closeQueueModalBtn) {
        closeQueueModalBtn.addEventListener('click', () => {
            queueModal.style.display = 'none';
        });
    }
    if (queueModal) {
        queueModal.addEventListener('click', (e) => {
            if (e.target === queueModal) queueModal.style.display = 'none';
        });
    }

    // Load popular and new anime on page load
    loadPopularAndNewAnime();

    // Initialize theme (default is dark mode)
    initializeTheme();

    // Initialize accent color from saved preferences
    initializeAccentColor();

    // Direct input functionality
    const directInput = document.getElementById('direct-input');
    const directBtn = document.getElementById('direct-btn');
    
    if (directBtn) {
        directBtn.addEventListener('click', handleDirectInput);
    }
    if (directInput) {
        directInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                handleDirectInput();
            }
        });
    }

    // Search functionality
    if (searchBtn) {
        searchBtn.addEventListener('click', performSearch);
    }
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }

    // Download modal functionality
    if (closeDownloadModal) {
        closeDownloadModal.addEventListener('click', hideDownloadModal);
    }
    if (cancelDownload) {
        cancelDownload.addEventListener('click', hideDownloadModal);
    }
    if (confirmDownload) {
        confirmDownload.addEventListener('click', startDownload);
    }
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', selectAllEpisodes);
    }
    if (deselectAllBtn) {
        deselectAllBtn.addEventListener('click', deselectAllEpisodes);
    }

    // Theme toggle functionality (only if element exists)
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    // Navbar title click functionality
    if (navTitle) {
        navTitle.addEventListener('click', function() {
            // Clear search input
            if (searchInput) {
                searchInput.value = '';
            }
            // Show home content (original state)
            showHomeContent();
            // Reload popular and new anime
            loadPopularAndNewAnime();
        });
    }

    // Close modal when clicking outside
    if (downloadModal) {
        downloadModal.addEventListener('click', function(e) {
            if (e.target === downloadModal) {
                hideDownloadModal();
            }
        });
    }

    function loadVersionInfo() {
        fetch('/api/info')
            .then(response => response.json())
            .then(data => {
                versionDisplay.textContent = `v${data.version}`;
            })
            .catch(error => {
                console.error('Failed to load version info:', error);
                versionDisplay.textContent = 'v?.?.?';
            });
    }

    function loadUserPreferences() {
        fetch('/api/preferences')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.preferences) {
                    userPreferences = data.preferences;
                    console.log('Loaded user preferences:', userPreferences);

                    // Sync accent color from server to localStorage
                    if (userPreferences.accent_color) {
                        localStorage.setItem('accentColor', userPreferences.accent_color);
                        applyAccentColor(userPreferences.accent_color);
                    }
                }
            })
            .catch(error => {
                console.error('Failed to load user preferences:', error);
            });
    }

    function loadAvailableProviders() {
        // This will be called from showDownloadModal with site-specific logic
        // Default providers for initial load (aniworld.to)
        populateProviderDropdown('aniworld.to');
    }

    function populateProviderDropdown(site, providers) {
        if (!providerSelect) {
            return;
        }

        // Use dynamic providers if available, otherwise fall back to site defaults
        let siteProviders = providers || [];
        if (siteProviders.length === 0) {
            if (site === 'movie4k.sx') {
                siteProviders = ['Filemoon', 'Doodstream', 'Streamtape', 'VOE', 'Vidoza'];
            } else if (site === 's.to') {
                siteProviders = ['VOE'];
            } else {
                siteProviders = ['VOE', 'Filemoon', 'Vidmoly'];
            }
        }

        providerSelect.innerHTML = '';

        siteProviders.forEach(provider => {
            const option = document.createElement('option');
            option.value = provider;
            option.textContent = provider;
            providerSelect.appendChild(option);
        });

        // Set default based on saved preference, fallback to VOE
        let defaultProvider = userPreferences.default_provider || '';
        if (defaultProvider && siteProviders.includes(defaultProvider)) {
            providerSelect.value = defaultProvider;
        } else if (siteProviders.length > 0) {
            providerSelect.value = siteProviders[0];
        }

        console.log(`Populated providers for ${site}:`, siteProviders);
    }

    function populateLanguageDropdown(site, languages) {
        if (!languageSelect) {
            console.error('Language select element not found!');
            return;
        }

        console.log('Populating language dropdown for site:', site);
        languageSelect.innerHTML = '';

        // Use dynamic languages if available, otherwise fall back to site defaults
        let availableLanguages = languages || [];
        let defaultLanguage = '';
        if (availableLanguages.length === 0) {
            if (site === 'movie4k.sx') {
                availableLanguages = ['Deutsch', 'English'];
                defaultLanguage = 'Deutsch';
            } else if (site === 's.to') {
                availableLanguages = ['German Dub', 'English Dub'];
                defaultLanguage = 'German Dub';
            } else {
                availableLanguages = ['German Dub', 'English Sub', 'German Sub'];
                defaultLanguage = 'German Sub';
            }
        } else {
            // Set default from dynamic list
            if (site === 'movie4k.sx') {
                defaultLanguage = 'Deutsch';
            } else if (site === 's.to') {
                defaultLanguage = 'German Dub';
            } else {
                defaultLanguage = 'German Sub';
            }
        }

        availableLanguages.forEach(language => {
            const option = document.createElement('option');
            option.value = language;
            option.textContent = language;
            languageSelect.appendChild(option);
        });

        // Set default based on saved preference, then site fallback
        setTimeout(() => {
            let defaultLang = userPreferences.default_language || '';
            if (defaultLang && availableLanguages.includes(defaultLang)) {
                languageSelect.value = defaultLang;
            } else if (defaultLanguage && availableLanguages.includes(defaultLanguage)) {
                languageSelect.value = defaultLanguage;
            } else if (availableLanguages.length > 0) {
                languageSelect.value = availableLanguages[0];
            }
            console.log('Set default language to:', languageSelect.value);
        }, 0);
    }

    function isDirectUrl(input) {
        return input.startsWith('http://') || input.startsWith('https://');
    }

    function getSelectedSites() {
        const checked = document.querySelectorAll('input[name="site"]:checked');
        return Array.from(checked).map(cb => cb.value);
    }

    function performSearch() {
        const query = searchInput.value.trim();
        if (!query) {
            showHomeContent();
            return;
        }

        // Show loading state
        showLoadingState();
        searchBtn.disabled = true;
        searchBtn.textContent = 'Searching...';

        // Detect if input is a direct URL
        if (isDirectUrl(query)) {
            fetch('/api/direct', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: query })
            })
            .then(response => {
                if (response.status === 401) { window.location.href = '/login'; return; }
                return response.json();
            })
            .then(data => {
                if (!data) return;
                if (data.success) {
                    displaySearchResults([data.result]);
                } else {
                    showNotification(data.error || 'Failed to load URL', 'error');
                    showEmptyState();
                }
            })
            .catch(error => {
                console.error('Direct URL error:', error);
                showNotification('Failed to load URL. Please check and try again.', 'error');
                showEmptyState();
            })
            .finally(() => {
                searchBtn.disabled = false;
                searchBtn.textContent = 'Search';
                hideLoadingState();
            });
            return;
        }

        // Normal search with selected site checkboxes
        const selectedSites = getSelectedSites();
        if (selectedSites.length === 0) {
            showNotification('Please select at least one site to search', 'error');
            searchBtn.disabled = false;
            searchBtn.textContent = 'Search';
            hideLoadingState();
            return;
        }

        fetch('/api/search', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query, sites: selectedSites })
        })
        .then(response => {
            if (response.status === 401) { window.location.href = '/login'; return; }
            return response.json();
        })
        .then(data => {
            if (!data) return;
            if (data.success) {
                displaySearchResults(data.results);
            } else {
                showNotification(data.error || 'Search failed', 'error');
                showEmptyState();
            }
        })
        .catch(error => {
            console.error('Search error:', error);
            showNotification('Search failed. Please try again.', 'error');
            showEmptyState();
        })
        .finally(() => {
            searchBtn.disabled = false;
            searchBtn.textContent = 'Search';
            hideLoadingState();
        });
    }

    function displaySearchResults(results) {
        if (!results || results.length === 0) {
            showEmptyState();
            return;
        }

        resultsContainer.innerHTML = '';

        results.forEach(anime => {
            const animeCard = createAnimeCard(anime);
            resultsContainer.appendChild(animeCard);
        });

        showResultsSection();
    }

    function createAnimeCard(anime) {
        const card = document.createElement('div');
        card.className = 'anime-card';

        // Handle cover image
        let coverStyle = '';
        if (anime.cover) {
            let coverUrl = anime.cover;
            // Make URL absolute if it's relative
            if (!coverUrl.startsWith('http')) {
                if (coverUrl.startsWith('//')) {
                    coverUrl = 'https:' + coverUrl;
                } else if (coverUrl.startsWith('/')) {
                    // Determine base URL based on site
                    let baseUrl = 'https://aniworld.to';
                    if (anime.site === 's.to') baseUrl = 'https://s.to';
                    else if (anime.site === 'movie4k.sx') baseUrl = 'https://movie4k.sx';
                    coverUrl = baseUrl + coverUrl;
                } else {
                    let baseUrl = 'https://aniworld.to';
                    if (anime.site === 's.to') baseUrl = 'https://s.to';
                    else if (anime.site === 'movie4k.sx') baseUrl = 'https://movie4k.sx';
                    coverUrl = baseUrl + '/' + coverUrl;
                }
            }

            // Upgrade image resolution from 150x225 to 220x330 for better quality
            coverUrl = coverUrl.replace("150x225", "220x330");

            coverStyle = `style="background-image: url('${coverUrl}')"`;
        }

        card.innerHTML = `
            <div class="anime-card-background" ${coverStyle}></div>
            <div class="anime-card-content">
                <div class="anime-title">${escapeHtml(anime.title)}</div>
            </div>
        `;

        // Make the entire card clickable to open download modal
        const episodeLabel = (anime.type === 'movie' || anime.is_movie) ? 'Movie' : 'Series';
        card.addEventListener('click', () => {
            showDownloadModal(anime.title, episodeLabel, anime.url, anime.cover);
        });

        return card;
    }

    function showDownloadModal(animeTitle, episodeTitle, episodeUrl, coverUrl) {
        // Detect site from URL
        let detectedSite = 'aniworld.to'; // default
        if (episodeUrl.includes('movie4k')) {
            detectedSite = 'movie4k.sx';
        } else if (episodeUrl.includes('/serie/') || episodeUrl.includes('s.to')) {
            detectedSite = 's.to';
        }

        currentDownloadData = {
            anime: animeTitle,
            episode: episodeTitle,
            url: episodeUrl,
            site: detectedSite,
            downloadPath: '/Downloads' // Default path - will be fetched from backend
        };

        // Reset selection state
        selectedEpisodes.clear();
        availableEpisodes = {};

        // Populate modal
        document.getElementById('download-anime-title').textContent = animeTitle;

        // Show cover image if available
        const coverContainer = document.getElementById('download-cover');
        const coverImg = document.getElementById('download-cover-img');
        if (coverUrl && coverContainer && coverImg) {
            coverImg.src = coverUrl;
            coverContainer.style.display = 'block';
        } else if (coverContainer) {
            coverContainer.style.display = 'none';
        }

        // Show loading state for provider and language dropdowns
        // They will be populated dynamically when episodes are fetched
        if (providerSelect) {
            providerSelect.innerHTML = '<option value="">Loading providers...</option>';
        }
        if (languageSelect) {
            languageSelect.innerHTML = '<option value="">Loading languages...</option>';
        }

        // Show loading state for episodes
        episodeTreeLoading.style.display = 'flex';
        episodeTree.style.display = 'none';
        updateSelectedCount();

        // Fetch download path from backend
        fetch('/api/download-path')
            .then(response => response.json())
            .then(data => {
                currentDownloadData.downloadPath = data.path;
                document.getElementById('download-path').textContent = data.path;
            })
            .catch(error => {
                console.error('Failed to fetch download path:', error);
                document.getElementById('download-path').textContent = 'Unknown';
            });

        // Fetch episodes for this series
        fetch('/api/episodes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                series_url: episodeUrl
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                availableEpisodes = data.episodes;
                availableMovies = data.movies || [];
                renderEpisodeTree();

                // Populate provider and language dropdowns with scanned data
                populateProviderDropdown(
                    currentDownloadData.site,
                    data.available_providers || []
                );
                populateLanguageDropdown(
                    currentDownloadData.site,
                    data.available_languages || []
                );
            } else {
                showNotification(data.error || 'Failed to load episodes', 'error');
                // Fall back to site defaults on error
                populateProviderDropdown(currentDownloadData.site);
                populateLanguageDropdown(currentDownloadData.site);
            }
        })
        .catch(error => {
            console.error('Failed to fetch episodes:', error);
            showNotification('Failed to load episodes', 'error');
            // Fall back to site defaults on network error
            populateProviderDropdown(currentDownloadData.site);
            populateLanguageDropdown(currentDownloadData.site);
        })
        .finally(() => {
            episodeTreeLoading.style.display = 'none';
            episodeTree.style.display = 'block';
        });

        downloadModal.style.display = 'flex';
    }

    function hideDownloadModal() {
        downloadModal.style.display = 'none';
        currentDownloadData = null;
        selectedEpisodes.clear();
        availableEpisodes = {};
        availableMovies = [];
    }

    function renderEpisodeTree() {
        episodeTree.innerHTML = '';

        const seasonNums = Object.keys(availableEpisodes).sort((a, b) => Number(a) - Number(b));
        let activeSeason = seasonNums.length > 0 ? seasonNums[0] : null;

        // Season pills navigation
        if (seasonNums.length > 0 || (availableMovies && availableMovies.length > 0)) {
            const seasonNav = document.createElement('div');
            seasonNav.className = 'season-nav';
            seasonNav.id = 'season-nav';

            const seasonLabel = document.createElement('span');
            seasonLabel.className = 'season-nav-label';
            seasonLabel.textContent = 'Seasons:';
            seasonNav.appendChild(seasonLabel);

            seasonNums.forEach(seasonNum => {
                const pill = document.createElement('button');
                pill.className = 'season-pill' + (seasonNum === activeSeason ? ' active' : '');
                pill.textContent = seasonNum;
                pill.dataset.season = seasonNum;
                pill.addEventListener('click', () => {
                    seasonNav.querySelectorAll('.season-pill').forEach(p => p.classList.remove('active'));
                    pill.classList.add('active');
                    activeSeason = seasonNum;
                    renderSeasonTable(seasonNum);
                });
                seasonNav.appendChild(pill);
            });

            // Movies pill
            if (availableMovies && availableMovies.length > 0) {
                const moviePill = document.createElement('button');
                moviePill.className = 'season-pill';
                moviePill.textContent = 'Movies';
                moviePill.dataset.season = 'movies';
                moviePill.addEventListener('click', () => {
                    seasonNav.querySelectorAll('.season-pill').forEach(p => p.classList.remove('active'));
                    moviePill.classList.add('active');
                    activeSeason = 'movies';
                    renderMoviesTable();
                });
                seasonNav.appendChild(moviePill);
            }

            episodeTree.appendChild(seasonNav);
        }

        // Episode table container
        const tableContainer = document.createElement('div');
        tableContainer.className = 'episode-table-wrap';
        tableContainer.id = 'episode-table-container';
        episodeTree.appendChild(tableContainer);

        // Render first season or movies
        if (activeSeason) {
            renderSeasonTable(activeSeason);
        } else if (availableMovies && availableMovies.length > 0) {
            renderMoviesTable();
        }

        updateSelectedCount();

        function renderSeasonTable(seasonNum) {
            const container = document.getElementById('episode-table-container');
            const season = availableEpisodes[seasonNum];
            if (!season) return;

            container.innerHTML = `
                <table class="episode-table">
                    <thead>
                        <tr>
                            <th class="episode-checkbox-cell">
                                <input type="checkbox" id="season-${seasonNum}" title="Select all">
                            </th>
                            <th class="episode-number-cell">#</th>
                            <th>Title</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            `;

            const tbody = container.querySelector('tbody');
            const seasonCheckbox = container.querySelector(`#season-${seasonNum}`);

            season.forEach(episode => {
                const episodeId = `${episode.season}-${episode.episode}`;
                const tr = document.createElement('tr');
                tr.className = 'episode-row';
                tr.innerHTML = `
                    <td class="episode-checkbox-cell">
                        <input type="checkbox" class="episode-checkbox" id="episode-${episodeId}" ${selectedEpisodes.has(episodeId) ? 'checked' : ''}>
                    </td>
                    <td class="episode-number-cell">${episode.episode}</td>
                    <td class="episode-title-cell">${escapeHtml(episode.title)}</td>
                `;

                const checkbox = tr.querySelector('.episode-checkbox');
                checkbox.addEventListener('change', () => {
                    toggleEpisode(episode, checkbox.checked);
                    updateHeaderCheckbox(seasonNum, seasonCheckbox);
                });

                tr.addEventListener('click', (e) => {
                    if (e.target.tagName === 'INPUT') return;
                    checkbox.checked = !checkbox.checked;
                    toggleEpisode(episode, checkbox.checked);
                    updateHeaderCheckbox(seasonNum, seasonCheckbox);
                });

                tbody.appendChild(tr);
            });

            updateHeaderCheckbox(seasonNum, seasonCheckbox);
            seasonCheckbox.addEventListener('change', () => {
                const isChecked = seasonCheckbox.checked;
                season.forEach(episode => {
                    const episodeId = `${episode.season}-${episode.episode}`;
                    const cb = container.querySelector(`#episode-${episodeId}`);
                    if (cb) {
                        cb.checked = isChecked;
                        toggleEpisode(episode, isChecked);
                    }
                });
            });
        }

        function renderMoviesTable() {
            const container = document.getElementById('episode-table-container');
            if (!availableMovies || availableMovies.length === 0) return;

            container.innerHTML = `
                <table class="episode-table">
                    <thead>
                        <tr>
                            <th class="episode-checkbox-cell">
                                <input type="checkbox" id="movies-section" title="Select all">
                            </th>
                            <th class="episode-number-cell">#</th>
                            <th>Title</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            `;

            const tbody = container.querySelector('tbody');
            const moviesCheckbox = container.querySelector('#movies-section');

            availableMovies.forEach((movie, index) => {
                const movieId = `movie-${movie.movie}`;
                const tr = document.createElement('tr');
                tr.className = 'episode-row';
                tr.innerHTML = `
                    <td class="episode-checkbox-cell">
                        <input type="checkbox" class="episode-checkbox" id="movie-${movieId}" ${selectedEpisodes.has(movieId) ? 'checked' : ''}>
                    </td>
                    <td class="episode-number-cell">${index + 1}</td>
                    <td class="episode-title-cell">${escapeHtml(movie.title)}</td>
                `;

                const checkbox = tr.querySelector('.episode-checkbox');
                checkbox.addEventListener('change', () => {
                    toggleMovie(movie, checkbox.checked);
                    updateMoviesHeader(moviesCheckbox);
                });

                tr.addEventListener('click', (e) => {
                    if (e.target.tagName === 'INPUT') return;
                    checkbox.checked = !checkbox.checked;
                    toggleMovie(movie, checkbox.checked);
                    updateMoviesHeader(moviesCheckbox);
                });

                tbody.appendChild(tr);
            });

            updateMoviesHeader(moviesCheckbox);
            moviesCheckbox.addEventListener('change', () => {
                const isChecked = moviesCheckbox.checked;
                availableMovies.forEach(movie => {
                    const movieId = `movie-${movie.movie}`;
                    const cb = container.querySelector(`#movie-${movieId}`);
                    if (cb) {
                        cb.checked = isChecked;
                        toggleMovie(movie, isChecked);
                    }
                });
            });
        }

        function updateHeaderCheckbox(seasonNum, checkbox) {
            const season = availableEpisodes[seasonNum];
            if (!checkbox || !season) return;
            const keys = season.map(ep => `${ep.season}-${ep.episode}`);
            const selected = keys.filter(key => selectedEpisodes.has(key));
            checkbox.checked = selected.length === keys.length;
            checkbox.indeterminate = selected.length > 0 && selected.length < keys.length;
        }

        function updateMoviesHeader(checkbox) {
            if (!checkbox || !availableMovies || availableMovies.length === 0) return;
            const keys = availableMovies.map(m => `movie-${m.movie}`);
            const selected = keys.filter(key => selectedEpisodes.has(key));
            checkbox.checked = selected.length === keys.length;
            checkbox.indeterminate = selected.length > 0 && selected.length < keys.length;
        }
    }

    function toggleSeason(seasonNum) {
        const season = availableEpisodes[seasonNum];
        const seasonCheckbox = document.getElementById(`season-${seasonNum}`);
        const isChecked = seasonCheckbox.checked;

        season.forEach(episode => {
            const episodeId = `${episode.season}-${episode.episode}`;
            const episodeCheckbox = document.getElementById(`episode-${episodeId}`);

            if (episodeCheckbox) {
                episodeCheckbox.checked = isChecked;
                toggleEpisode(episode, isChecked);
            }
        });
    }

    function toggleEpisode(episode, isSelected) {
        const episodeKey = `${episode.season}-${episode.episode}`;

        if (isSelected) {
            selectedEpisodes.add(episodeKey);
        } else {
            selectedEpisodes.delete(episodeKey);
        }

        // Update season checkbox state
        updateSeasonCheckboxState(episode.season);
        updateSelectedCount();
    }

    function updateSeasonCheckboxState(seasonNum) {
        const season = availableEpisodes[seasonNum];
        const seasonCheckbox = document.getElementById(`season-${seasonNum}`);

        if (!seasonCheckbox || !season) return;

        const seasonEpisodes = season.map(ep => `${ep.season}-${ep.episode}`);
        const selectedInSeason = seasonEpisodes.filter(key => selectedEpisodes.has(key));

        if (selectedInSeason.length === seasonEpisodes.length) {
            seasonCheckbox.checked = true;
            seasonCheckbox.indeterminate = false;
        } else if (selectedInSeason.length > 0) {
            seasonCheckbox.checked = false;
            seasonCheckbox.indeterminate = true;
        } else {
            seasonCheckbox.checked = false;
            seasonCheckbox.indeterminate = false;
        }
    }

    function toggleMovies() {
        const moviesCheckbox = document.getElementById('movies-section');
        const isChecked = moviesCheckbox.checked;

        availableMovies.forEach(movie => {
            const movieId = `movie-${movie.movie}`;
            const movieCheckbox = document.getElementById(`movie-${movieId}`);

            if (movieCheckbox) {
                movieCheckbox.checked = isChecked;
                toggleMovie(movie, isChecked);
            }
        });
    }

    function toggleMovie(movie, isSelected) {
        const movieKey = `movie-${movie.movie}`;

        if (isSelected) {
            selectedEpisodes.add(movieKey);
        } else {
            selectedEpisodes.delete(movieKey);
        }

        // Update movies section checkbox state
        updateMoviesCheckboxState();
        updateSelectedCount();
    }

    function updateMoviesCheckboxState() {
        const moviesCheckbox = document.getElementById('movies-section');

        if (!moviesCheckbox || !availableMovies || availableMovies.length === 0) return;

        const movieKeys = availableMovies.map(movie => `movie-${movie.movie}`);
        const selectedMovies = movieKeys.filter(key => selectedEpisodes.has(key));

        if (selectedMovies.length === movieKeys.length) {
            moviesCheckbox.checked = true;
            moviesCheckbox.indeterminate = false;
        } else if (selectedMovies.length > 0) {
            moviesCheckbox.checked = false;
            moviesCheckbox.indeterminate = true;
        } else {
            moviesCheckbox.checked = false;
            moviesCheckbox.indeterminate = false;
        }
    }

    function selectAllEpisodes() {
        // Select all episodes
        Object.values(availableEpisodes).flat().forEach(episode => {
            const episodeKey = `${episode.season}-${episode.episode}`;
            const episodeCheckbox = document.getElementById(`episode-${episodeKey}`);

            if (episodeCheckbox) {
                episodeCheckbox.checked = true;
                selectedEpisodes.add(episodeKey);
            }
        });

        // Select all movies
        availableMovies.forEach(movie => {
            const movieKey = `movie-${movie.movie}`;
            const movieCheckbox = document.getElementById(`movie-${movieKey}`);

            if (movieCheckbox) {
                movieCheckbox.checked = true;
                selectedEpisodes.add(movieKey);
            }
        });

        // Update all season checkboxes
        Object.keys(availableEpisodes).forEach(seasonNum => {
            updateSeasonCheckboxState(seasonNum);
        });

        // Update movies checkbox
        updateMoviesCheckboxState();

        updateSelectedCount();
    }

    function deselectAllEpisodes() {
        selectedEpisodes.clear();

        // Uncheck all checkboxes
        document.querySelectorAll('.episode-checkbox, .season-checkbox').forEach(checkbox => {
            checkbox.checked = false;
            checkbox.indeterminate = false;
        });

        updateSelectedCount();
    }

    function updateSelectedCount() {
        const count = selectedEpisodes.size;

        // Count episodes and movies separately for better display
        const episodeCount = Array.from(selectedEpisodes).filter(key => !key.startsWith('movie-')).length;
        const movieCount = Array.from(selectedEpisodes).filter(key => key.startsWith('movie-')).length;

        let countText = '';
        if (episodeCount > 0 && movieCount > 0) {
            countText = `${episodeCount} episode${episodeCount !== 1 ? 's' : ''} and ${movieCount} movie${movieCount !== 1 ? 's' : ''} selected`;
        } else if (episodeCount > 0) {
            countText = `${episodeCount} episode${episodeCount !== 1 ? 's' : ''} selected`;
        } else if (movieCount > 0) {
            countText = `${movieCount} movie${movieCount !== 1 ? 's' : ''} selected`;
        } else {
            countText = 'No items selected';
        }

        selectedEpisodeCount.textContent = countText;

        // Enable/disable download button based on selection
        confirmDownload.disabled = count === 0;
    }

    function startDownload() {
        if (!currentDownloadData || selectedEpisodes.size === 0) {
            showNotification('Please select at least one episode or movie to download', 'error');
            return;
        }

        // Show loading state
        confirmDownload.disabled = true;
        confirmDownload.textContent = 'Starting...';

        // Collect selected episode and movie URLs
        const selectedEpisodeUrls = [];
        selectedEpisodes.forEach(episodeKey => {
            if (episodeKey.startsWith('movie-')) {
                // Handle movie
                const movieNum = episodeKey.split('-')[1];
                const movieData = availableMovies.find(movie => movie.movie == movieNum);
                if (movieData) {
                    selectedEpisodeUrls.push(movieData.url);
                }
            } else {
                // Handle episode
                const [season, episode] = episodeKey.split('-').map(Number);
                const episodeData = availableEpisodes[season]?.find(ep => ep.season === season && ep.episode === episode);
                if (episodeData) {
                    selectedEpisodeUrls.push(episodeData.url);
                }
            }
        });

        // Get selected provider and language from dropdowns
        const selectedProvider = providerSelect.value || 'VOE';

        // Get language value without fallback first to see what's actually selected
        const rawLanguageValue = languageSelect.value;

        // Get language from dropdown - use site-appropriate fallback if empty
        const selectedLanguage = rawLanguageValue || (currentDownloadData.site === 's.to' ? 'German Dub' : 'German Sub');

        // Debug logging
        console.log('Raw language value:', rawLanguageValue);
        console.log('Selected language (final):', selectedLanguage);
        console.log('Selected provider:', selectedProvider);
        console.log('Site:', currentDownloadData.site);

        // Validate that we have a real selection
        if (!rawLanguageValue) {
            console.warn('Warning: No language selected from dropdown, using fallback');
        }

        // Create request payload and log it
        const requestPayload = {
            episode_urls: selectedEpisodeUrls,
            language: selectedLanguage,
            provider: selectedProvider,
            anime_title: currentDownloadData.anime
        };

        fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestPayload)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const count = selectedEpisodes.size;
                const maxConcurrent = data.max_concurrent || 3;
                let message = `Download started for ${count} episode${count !== 1 ? 's' : ''}`;
                
                // Add info about parallel downloads if multiple episodes selected
                if (count > 1 && maxConcurrent > 1) {
                    const parallelCount = Math.min(count, maxConcurrent);
                    message += ` (${parallelCount} parallel download${parallelCount !== 1 ? 's' : ''})`;
                }
                
                showNotification(message, 'success');
                hideDownloadModal();
                startQueueTracking();
                showQueueMiniPopup();
            } else {
                showNotification(data.error || 'Download failed to start', 'error');
            }
        })
        .catch(error => {
            console.error('Download error:', error);
            showNotification('Failed to start download', 'error');
        })
        .finally(() => {
            confirmDownload.disabled = false;
            confirmDownload.textContent = 'Start Download';
        });
    }

    function showLoadingState() {
        homeContent.style.display = 'none';
        localFiles.style.display = 'none';
        emptyState.style.display = 'none';
        resultsSection.style.display = 'none';
        loadingSection.style.display = 'block';
    }

    function hideLoadingState() {
        loadingSection.style.display = 'none';
    }

    function showResultsSection() {
        homeContent.style.display = 'none';
        localFiles.style.display = 'none';
        emptyState.style.display = 'none';
        loadingSection.style.display = 'none';
        resultsSection.style.display = 'block';
    }

    function showEmptyState() {
        homeContent.style.display = 'none';
        localFiles.style.display = 'none';
        resultsSection.style.display = 'none';
        loadingSection.style.display = 'none';
        emptyState.style.display = 'block';
    }

    function showHomeContent() {
        resultsSection.style.display = 'none';
        localFiles.style.display = 'none';
        loadingSection.style.display = 'none';
        emptyState.style.display = 'none';
        homeContent.style.display = 'block';
    }

    function toggleFolderIcon() {
    const icon = document.querySelector('#file-browser-btn i');
    if (!icon) return;

    icon.classList.toggle('fa-folder');
    icon.classList.toggle('fa-folder-open');
}

    function showLocalFiles() {
        homeContent.style.display = 'none';
        resultsSection.style.display = 'none';
        loadingSection.style.display = 'none';
        emptyState.style.display = 'none';
        localFiles.style.display = 'block';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function startQueueTracking() {
        // Start polling for queue status updates
        progressInterval = setInterval(updateQueueDisplay, 2000); // Poll every 2 seconds
        updateQueueDisplay(); // Initial update
    }

    function checkQueueStatus() {
        // Check queue status on page load to show any active downloads
        fetch('/api/queue-status')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.queue) {
                    const activeItems = data.queue.active || [];
                    const completedItems = data.queue.completed || [];

                    if (activeItems.length > 0 || completedItems.length > 0) {
                        // There are downloads to show, start tracking
                        startQueueTracking();
                    }
                }
            })
            .catch(error => {
                console.error('Initial queue status check error:', error);
            });
    }

    function updateQueueDisplay() {
        fetch('/api/queue-status')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.queue) {
                    const activeItems = data.queue.active || [];
                    const completedItems = data.queue.completed || [];
                    const hasContent = activeItems.length > 0 || completedItems.length > 0;

                    // Update modal content
                    if (hasContent) {
                        queueModalEmpty.style.display = 'none';

                        if (activeItems.length > 0) {
                            activeDownloads.style.display = 'block';
                            updateQueueList(activeQueueList, activeItems, 'active');
                        } else {
                            activeDownloads.style.display = 'none';
                        }

                        if (completedItems.length > 0) {
                            completedDownloads.style.display = 'block';
                            updateQueueList(completedQueueList, completedItems, 'completed');
                        } else {
                            completedDownloads.style.display = 'none';
                        }
                    } else {
                        queueModalEmpty.style.display = 'block';
                        activeDownloads.style.display = 'none';
                        completedDownloads.style.display = 'none';

                        if (progressInterval) {
                            clearInterval(progressInterval);
                            progressInterval = null;
                        }
                    }

                    // Update navbar button badge and animation
                    updateDownloadBadge(activeItems, completedItems);
                }
            })
            .catch(error => {
                console.error('Queue status update error:', error);
            });
    }

    function updateDownloadBadge(activeItems, completedItems) {
        const pendingCount = activeItems.length;
        const hasCompleted = completedItems.length > 0;

        if (pendingCount > 0) {
            // Active downloads: show count badge, pulse animation
            downloadBadge.textContent = pendingCount;
            downloadBadge.className = 'download-badge';
            downloadBadge.style.display = 'block';
            downloadQueueBtn.classList.add('downloading');
        } else if (hasCompleted) {
            // All done: show checkmark badge, no pulse
            downloadBadge.innerHTML = '<i class="fas fa-check" style="font-size: 0.55rem;"></i>';
            downloadBadge.className = 'download-badge completed';
            downloadBadge.style.display = 'block';
            downloadQueueBtn.classList.remove('downloading');
        } else {
            // Nothing: hide badge, no pulse
            downloadBadge.style.display = 'none';
            downloadQueueBtn.classList.remove('downloading');
        }
    }

    let miniPopupTimeout = null;

    function showQueueMiniPopup() {
        // Remove existing popup if any
        const existing = document.getElementById('queue-mini-popup');
        if (existing) {
            existing.remove();
            if (miniPopupTimeout) clearTimeout(miniPopupTimeout);
        }

        // Fetch current queue to show latest items
        fetch('/api/queue-status')
            .then(r => r.json())
            .then(data => {
                if (!data.success || !data.queue) return;

                const activeItems = data.queue.active || [];
                if (activeItems.length === 0) return;

                // Take the last 3 items
                const items = activeItems.slice(-3);

                const popup = document.createElement('div');
                popup.id = 'queue-mini-popup';
                popup.className = 'queue-mini-popup';

                let itemsHtml = items.map(item => `
                    <div class="queue-mini-item">
                        <div class="queue-mini-icon"><i class="fas fa-download"></i></div>
                        <div class="queue-mini-info">
                            <div class="queue-mini-title">${escapeHtml(item.anime_title)}</div>
                            <div class="queue-mini-status">${item.status}</div>
                        </div>
                    </div>
                `).join('');

                popup.innerHTML = itemsHtml;

                // Position below the download queue button
                const btn = document.getElementById('download-queue-btn');
                const rect = btn.getBoundingClientRect();
                popup.style.top = (rect.bottom + 8) + 'px';
                popup.style.right = (window.innerWidth - rect.right) + 'px';

                document.body.appendChild(popup);

                // Trigger entrance animation
                requestAnimationFrame(() => popup.classList.add('visible'));

                // Auto-close after 3 seconds
                miniPopupTimeout = setTimeout(() => {
                    popup.classList.remove('visible');
                    popup.addEventListener('transitionend', () => popup.remove(), { once: true });
                    // Fallback removal in case transitionend doesn't fire
                    setTimeout(() => { if (popup.parentNode) popup.remove(); }, 400);
                }, 3000);
            })
            .catch(() => {});
    }

    function updateQueueList(container, items, type) {
        container.innerHTML = '';

        items.forEach(item => {
            const queueItem = document.createElement('div');
            queueItem.className = 'queue-item';

            const overallProgress = item.progress_percentage || 0;
            const episodeProgress = item.current_episode_progress || 0;
            const showProgressBar = item.status === 'downloading' || item.status === 'queued';
            const isDownloading = item.status === 'downloading';


            // Create the HTML content
            const overallProgressClamped = Math.max(0, Math.min(100, overallProgress));
            const episodeProgressClamped = Math.max(0, Math.min(100, episodeProgress));

            const canCancel = item.status === 'downloading' || item.status === 'queued';

            queueItem.innerHTML = `
                <div class="queue-item-header">
                    <div class="queue-item-title">${escapeHtml(item.anime_title)}</div>
                    <div class="queue-item-header-right">
                        ${canCancel ? `<button class="queue-cancel-btn" data-id="${item.id}" title="Cancel download"><i class="fas fa-times"></i></button>` : ''}
                        <div class="queue-item-status ${item.status}">${item.status}</div>
                    </div>
                </div>
                ${showProgressBar ? `
                <div class="queue-item-progress">
                    <div class="queue-progress-bar">
                        <div class="queue-progress-fill" style="width: ${overallProgressClamped}%; transition: width 0.3s ease;"></div>
                    </div>
                    <div class="queue-progress-text">${overallProgressClamped.toFixed(1)}% | ${item.completed_episodes}/${item.total_episodes} episodes</div>
                </div>
                ${isDownloading ? `
                <div class="queue-item-progress episode-progress">
                    <div class="queue-progress-bar">
                        <div class="queue-progress-fill episode-progress-fill" style="width: ${episodeProgressClamped}%; transition: width 0.3s ease;"></div>
                    </div>
                    <div class="queue-progress-text episode-progress-text">Current Episode: ${episodeProgressClamped.toFixed(1)}%</div>
                </div>
                ` : ''}
                ` : `
                <div class="queue-item-progress">
                    <div class="queue-progress-text">${item.completed_episodes}/${item.total_episodes} episodes</div>
                </div>
                `}
                <div class="queue-item-details">
                    ${escapeHtml(item.current_episode || (item.status === 'completed' ? 'Download completed' : 'Waiting in queue'))}
                </div>
            `;

            // Attach cancel button handler
            const cancelBtn = queueItem.querySelector('.queue-cancel-btn');
            if (cancelBtn) {
                cancelBtn.addEventListener('click', () => {
                    const queueId = cancelBtn.dataset.id;
                    fetch(`/api/queue/cancel/${queueId}`, { method: 'POST' })
                        .then(r => r.json())
                        .then(data => {
                            if (data.success) {
                                showNotification('Download cancelled', 'info');
                                updateQueueDisplay();
                            } else {
                                showNotification(data.error || 'Failed to cancel', 'error');
                            }
                        })
                        .catch(() => showNotification('Failed to cancel download', 'error'));
                });
            }

            container.appendChild(queueItem);
        });
    }

    function loadPopularAndNewAnime() {
        console.log('Loading popular and new content from all providers...');

        // Show loading state for home content
        homeLoading.style.display = 'block';
        popularNewSections.style.display = 'none';

        let loadedCount = 0;
        const totalProviders = 3;

        function checkAllLoaded() {
            loadedCount++;
            if (loadedCount >= totalProviders) {
                homeLoading.style.display = 'none';
                popularNewSections.style.display = 'block';
                showHomeContent();
            }
        }

        // Load AniWorld
        if (aniworldLoading) aniworldLoading.style.display = 'flex';
        if (aniworldContent) aniworldContent.style.display = 'none';
        fetch('/api/popular-new')
            .then(response => {
                if (response.status === 401) { window.location.href = '/login'; return; }
                return response.json();
            })
            .then(data => {
                if (!data) return;
                if (data.success) {
                    displayProviderContent(
                        data.popular || [], data.new || [],
                        popularAnimeGrid, newAnimeGrid
                    );
                }
            })
            .catch(error => console.error('Error loading aniworld:', error))
            .finally(() => {
                if (aniworldLoading) aniworldLoading.style.display = 'none';
                if (aniworldContent) aniworldContent.style.display = 'block';
                checkAllLoaded();
            });

        // Load S.to
        if (stoLoading) stoLoading.style.display = 'flex';
        if (stoContent) stoContent.style.display = 'none';
        fetch('/api/popular-new-sto')
            .then(response => {
                if (response.status === 401) { window.location.href = '/login'; return; }
                return response.json();
            })
            .then(data => {
                if (!data) return;
                if (data.success) {
                    displayProviderContent(
                        data.popular || [], data.new || [],
                        popularStoGrid, newStoGrid
                    );
                }
            })
            .catch(error => console.error('Error loading s.to:', error))
            .finally(() => {
                if (stoLoading) stoLoading.style.display = 'none';
                if (stoContent) stoContent.style.display = 'block';
                checkAllLoaded();
            });

        // Load Movie4k
        if (movie4kLoading) movie4kLoading.style.display = 'flex';
        if (movie4kContent) movie4kContent.style.display = 'none';
        fetch('/api/popular-new-movie4k')
            .then(response => {
                if (response.status === 401) { window.location.href = '/login'; return; }
                return response.json();
            })
            .then(data => {
                if (!data) return;
                if (data.success) {
                    displayProviderContent(
                        data.popular || [], data.new || [],
                        popularMovie4kGrid, newMovie4kGrid
                    );
                }
            })
            .catch(error => console.error('Error loading movie4k:', error))
            .finally(() => {
                if (movie4kLoading) movie4kLoading.style.display = 'none';
                if (movie4kContent) movie4kContent.style.display = 'block';
                checkAllLoaded();
            });
    }

    function displayProviderContent(popularItems, newItems, popularGrid, newGrid) {
        if (popularGrid) {
            popularGrid.innerHTML = '';
            popularItems.slice(0, 8).forEach(item => {
                popularGrid.appendChild(createHomeAnimeCard(item));
            });
        }
        if (newGrid) {
            newGrid.innerHTML = '';
            newItems.slice(0, 8).forEach(item => {
                newGrid.appendChild(createHomeAnimeCard(item));
            });
        }
    }

    function createHomeAnimeCard(anime) {
        const card = document.createElement('div');
        card.className = 'home-anime-card';

        const defaultCover = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDIwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIyMDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMzMzIi8+CjxwYXRoIGQ9Ik0xMDAgMTUwTDEyMCAxNzBMMTAwIDE5MFY3MGwyMCAyMEwxMDAgMTEwVjE1MFoiIGZpbGw9IiM2NjYiLz4KPC9zdmc+';

        // Replace image size from 150x225 to 220x330 for higher resolution
        let coverUrl = anime.cover || defaultCover;
        if (coverUrl.includes('_150x225.png')) {
            coverUrl = coverUrl.replace('_150x225.png', '_220x330.png');
        }

        // Truncate title at word boundaries to stay under 68 characters total
        let displayTitle = anime.name;
        if (displayTitle.length > 65) { // Leave room for "..." (3 chars)
            // Find the last space before character 65
            let truncateAt = displayTitle.lastIndexOf(' ', 65);
            if (truncateAt === -1 || truncateAt < 30) {
                // If no space found or space is too early, just cut at 65
                truncateAt = 65;
            }
            displayTitle = displayTitle.substring(0, truncateAt) + '...';
        }

        card.innerHTML = `
            <div class="home-anime-cover">
                <img src="${coverUrl}" alt="${escapeHtml(anime.name)}" loading="lazy"
                     onerror="this.src='${defaultCover}'">
            </div>
            <div class="home-anime-title" title="${escapeHtml(anime.name)}">
                ${escapeHtml(displayTitle)}
            </div>
        `;

        // Add click handler to open download modal directly if URL is available
        card.addEventListener('click', () => {
            if (anime.url) {
                const isMovie = anime.url.includes('movie4k');
                const episodeLabel = isMovie ? 'Movie' : 'Series';
                showDownloadModal(anime.name, episodeLabel, anime.url, anime.cover);
            } else {
                searchInput.value = anime.name;
                performSearch();
            }
        });

        return card;
    }


    // Theme functions
    function initializeTheme() {
        // Check if user has a saved theme preference, default to dark mode
        const savedTheme = localStorage.getItem('theme') || 'dark';
        setTheme(savedTheme);
    }

    // Accent color functions
    function initializeAccentColor() {
        const savedColor = localStorage.getItem('accentColor') || 'purple';
        if (savedColor === 'custom') {
            const customColor = localStorage.getItem('customColor') || '#667eea';
            applyAccentColor(customColor, true);
        } else {
            applyAccentColor(savedColor);
        }
    }

    function applyAccentColor(color, isCustom = false) {
        const colors = {
            purple: { primary: '#667eea', secondary: '#764ba2', rgb: '102, 126, 234' },
            blue: { primary: '#3b82f6', secondary: '#1d4ed8', rgb: '59, 130, 246' },
            green: { primary: '#10b981', secondary: '#059669', rgb: '16, 185, 129' },
            orange: { primary: '#f59e0b', secondary: '#d97706', rgb: '245, 158, 11' },
            red: { primary: '#ef4444', secondary: '#dc2626', rgb: '239, 68, 68' },
            pink: { primary: '#ec4899', secondary: '#db2777', rgb: '236, 72, 153' },
            cyan: { primary: '#06b6d4', secondary: '#0891b2', rgb: '6, 182, 212' }
        };

        let selected;

        if (isCustom || color.startsWith('#')) {
            // Handle custom hex color
            const hex = color.replace('#', '');
            const r = parseInt(hex.substring(0, 2), 16);
            const g = parseInt(hex.substring(2, 4), 16);
            const b = parseInt(hex.substring(4, 6), 16);

            // Generate a darker shade for secondary (multiply by 0.8)
            const r2 = Math.floor(r * 0.8);
            const g2 = Math.floor(g * 0.8);
            const b2 = Math.floor(b * 0.8);
            const secondary = `#${r2.toString(16).padStart(2, '0')}${g2.toString(16).padStart(2, '0')}${b2.toString(16).padStart(2, '0')}`;

            selected = {
                primary: color,
                secondary: secondary,
                rgb: `${r}, ${g}, ${b}`
            };
        } else {
            selected = colors[color] || colors.purple;
        }

        document.documentElement.style.setProperty('--accent-primary', selected.primary);
        document.documentElement.style.setProperty('--accent-secondary', selected.secondary);
        document.documentElement.style.setProperty('--accent-primary-rgb', selected.rgb);
        document.body.style.setProperty('--accent-primary', selected.primary);
        document.body.style.setProperty('--accent-secondary', selected.secondary);
        document.body.style.setProperty('--accent-primary-rgb', selected.rgb);
    }

    // Export applyAccentColor to window so preferences modal can use it
    window.applyAccentColor = applyAccentColor;

    function toggleTheme() {
        console.log('Toggle theme clicked'); // Debug log
        const currentTheme = document.body.getAttribute('data-theme') || 'light';
        console.log('Current theme:', currentTheme); // Debug log
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        console.log('New theme:', newTheme); // Debug log
        setTheme(newTheme);
    }

    function setTheme(theme) {
        console.log('Setting theme to:', theme); // Debug log
        if (theme === 'light') {
            document.body.removeAttribute('data-theme');
            if (themeIcon) {
                themeIcon.className = 'fas fa-moon';
            }
            console.log('Switched to light mode'); // Debug log
        } else {
            document.body.setAttribute('data-theme', 'dark');
            if (themeIcon) {
                themeIcon.className = 'fas fa-sun';
            }
            console.log('Switched to dark mode'); // Debug log
        }
        localStorage.setItem('theme', theme);
    }

    // Make functions globally accessible
    window.showDownloadModal = showDownloadModal;
    window.showLocalFiles = showLocalFiles;
    window.showHomeContent = showHomeContent;
    window.toggleFolderIcon = toggleFolderIcon;
});

// Show notification function
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 6px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        animation: slideIn 0.3s ease-out;
        max-width: 300px;
        word-wrap: break-word;
    `;

    // Set background color based on type
    switch(type) {
        case 'success':
            notification.style.background = '#48bb78';
            break;
        case 'error':
            notification.style.background = '#f56565';
            break;
        default:
            notification.style.background = '#4299e1';
    }

    // Add to page
    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// Show info modal function
function showInfoModal(data) {
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        z-index: 1001;
        display: flex;
        justify-content: center;
        align-items: center;
        animation: fadeIn 0.3s ease-out;
    `;

    // Create modal content
    const modal = document.createElement('div');
    modal.style.cssText = `
        background: white;
        border-radius: 12px;
        padding: 2rem;
        max-width: 500px;
        width: 90%;
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
        animation: scaleIn 0.3s ease-out;
    `;

    modal.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
            <h2 style="color: #4a5568; margin: 0;">Application Info</h2>
            <button id="close-modal" style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #718096;">&times;</button>
        </div>
        <div style="color: #718096;">
            <p><strong>Version:</strong> ${data.version || 'N/A'}</p>
            <p><strong>Status:</strong> ${data.status || 'Running'}</p>
            <p><strong>Uptime:</strong> ${data.uptime || 'N/A'}</p>
            <p><strong>Mode:</strong> Web Interface</p>
        </div>
    `;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // Close modal functionality
    const closeBtn = modal.querySelector('#close-modal');
    const closeModal = () => {
        overlay.style.animation = 'fadeOut 0.3s ease-in';
        setTimeout(() => {
            if (overlay.parentNode) {
                overlay.parentNode.removeChild(overlay);
            }
        }, 300);
    };

    closeBtn.addEventListener('click', closeModal);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeModal();
        }
    });
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }

    @keyframes fadeOut {
        from {
            opacity: 1;
        }
        to {
            opacity: 0;
        }
    }

    @keyframes scaleIn {
        from {
            transform: scale(0.8);
            opacity: 0;
        }
        to {
            transform: scale(1);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);

// ========================================
// File Browser on Index + File Modal + Cast Modal
// ========================================

(function() {
    // Local files section elements
    const fileBrowserBtn = document.getElementById('file-browser-btn');
    const localFilesSection = document.getElementById('local-files');
    const localFilesLoading = document.getElementById('local-files-loading');
    const localFilesGrid = document.getElementById('local-files-grid');
    const localFilesEmpty = document.getElementById('local-files-empty');
    const localFilesBackBtn = document.getElementById('local-files-back-btn');
    const localFilesRefreshBtn = document.getElementById('local-files-refresh-btn');

    // File modal elements
    const fileModal = document.getElementById('file-modal');
    const closeFileModal = document.getElementById('close-file-modal');
    const fileModalTitle = document.getElementById('file-modal-title');
    const fileModalLoading = document.getElementById('file-modal-loading');
    const fileModalList = document.getElementById('file-modal-list');
    const fileModalEmpty = document.getElementById('file-modal-empty');
    const fileModalSelectAll = document.getElementById('file-modal-select-all');
    const fileModalSelectedCount = document.getElementById('file-modal-selected-count');
    const fileModalDeleteSelected = document.getElementById('file-modal-delete-selected');

    // Cast modal elements
    const castModal = document.getElementById('cast-modal');
    const closeCastModalBtn = document.getElementById('close-cast-modal');
    const castModalScanBtn = document.getElementById('cast-modal-scan-btn');
    const castModalDevicesLoading = document.getElementById('cast-modal-devices-loading');
    const castModalDevicesList = document.getElementById('cast-modal-devices-list');
    const castModalSelectedDevice = document.getElementById('cast-modal-selected-device');
    const castModalSelectedDeviceName = document.getElementById('cast-modal-selected-device-name');
    const castModalChangeDeviceBtn = document.getElementById('cast-modal-change-device-btn');
    const castModalControls = document.getElementById('cast-modal-controls');
    const castModalStatus = document.getElementById('cast-modal-status');
    const castModalProgressFill = document.getElementById('cast-modal-progress-fill');
    const castModalCurrentTime = document.getElementById('cast-modal-current-time');
    const castModalDuration = document.getElementById('cast-modal-duration');
    const castModalPlayPauseBtn = document.getElementById('cast-modal-play-pause-btn');
    const castModalStopBtn = document.getElementById('cast-modal-stop-btn');
    const castModalRewindBtn = document.getElementById('cast-modal-rewind-btn');
    const castModalForwardBtn = document.getElementById('cast-modal-forward-btn');
    const castModalVolumeSlider = document.getElementById('cast-modal-volume-slider');
    const castModalProgressBar = document.getElementById('cast-modal-progress-bar');
    const castModalVolumeIcon = document.getElementById('cast-modal-volume-icon');
    const castModalVolumeValue = document.getElementById('cast-modal-volume-value');
    const castModalNowPlayingFile = document.getElementById('cast-modal-now-playing-file');

    // State
    let watchProgress = {};
    let selectedFiles = new Set();
    let currentFileModalFolder = '';
    let currentCastDevice = null;
    let currentCastFile = null;
    let castStatusInterval = null;
    let castDurationValue = 0;
    let castStartTime = 0;
    let lastSavedCastTime = 0;
    let localshown = false;

    // ---- File Browser Button -> show local-files on index ----
    if (fileBrowserBtn) {
        fileBrowserBtn.addEventListener('click', () => {
            window.toggleFolderIcon();
            if (!localshown) {
                window.showLocalFiles();
                localshown = true;
                loadLocalFiles()
            }
            else {
                window.showHomeContent();
                localshown = false;
            }
            ;
        });
    }

    if (localFilesBackBtn) {
        localFilesBackBtn.addEventListener('click', () => {
            window.showHomeContent();
            window.toggleFolderIcon();
            localshown = false;
        });
    }

    if (localFilesRefreshBtn) {
        localFilesRefreshBtn.addEventListener('click', () => {
            loadLocalFiles();
        });
    }

    // ---- File Modal events ----
    if (closeFileModal) {
        closeFileModal.addEventListener('click', closeFileModalFn);
    }
    if (fileModal) {
        fileModal.addEventListener('click', (e) => {
            if (e.target === fileModal) closeFileModalFn();
        });
    }
    if (fileModalSelectAll) {
        fileModalSelectAll.addEventListener('change', () => {
            const checkboxes = fileModalList.querySelectorAll('.file-checkbox');
            checkboxes.forEach(cb => { cb.checked = fileModalSelectAll.checked; });
            updateFileModalSelection();
        });
    }
    if (fileModalDeleteSelected) {
        fileModalDeleteSelected.addEventListener('click', deleteSelectedFiles);
    }

    // ---- Cast Modal events ----
    if (closeCastModalBtn) {
        closeCastModalBtn.addEventListener('click', closeCastModal);
    }
    if (castModal) {
        castModal.addEventListener('click', (e) => {
            if (e.target === castModal) closeCastModal();
        });
    }
    if (castModalScanBtn) {
        castModalScanBtn.addEventListener('click', scanChromecastDevices);
    }
    if (castModalChangeDeviceBtn) {
        castModalChangeDeviceBtn.addEventListener('click', changeDevice);
    }
    if (castModalPlayPauseBtn) {
        castModalPlayPauseBtn.addEventListener('click', toggleCastPlayPause);
    }
    if (castModalStopBtn) {
        castModalStopBtn.addEventListener('click', stopCasting);
    }
    if (castModalRewindBtn) {
        castModalRewindBtn.addEventListener('click', () => castControl('rewind'));
    }
    if (castModalForwardBtn) {
        castModalForwardBtn.addEventListener('click', () => castControl('forward'));
    }
    if (castModalVolumeSlider) {
        castModalVolumeSlider.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            castControl('volume', value);
            updateVolumeDisplay(value);
        });
    }
    if (castModalProgressBar) {
        castModalProgressBar.addEventListener('click', (e) => {
            if (castDurationValue > 0) {
                const rect = castModalProgressBar.getBoundingClientRect();
                const percentage = (e.clientX - rect.left) / rect.width;
                const seekTime = Math.floor(percentage * castDurationValue);
                castControl('seek', seekTime);
            }
        });
    }

    // ========================================
    // Local Files (card view on index)
    // ========================================

    function loadLocalFiles() {
        localFilesLoading.style.display = 'block';
        localFilesGrid.style.display = 'none';
        localFilesEmpty.style.display = 'none';

        fetch('/api/files')
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    renderLocalFilesGrid(data.folders, data.files);
                } else {
                    showNotification(data.error || 'Failed to load files', 'error');
                }
            })
            .catch(error => {
                console.error('Failed to load local files:', error);
                showNotification('Failed to load files', 'error');
            })
            .finally(() => {
                localFilesLoading.style.display = 'none';
            });
    }

    function renderLocalFilesGrid(folders, files) {
        const hasContent = (folders && folders.length > 0) || (files && files.length > 0);

        if (!hasContent) {
            localFilesEmpty.style.display = 'block';
            localFilesGrid.style.display = 'none';
            return;
        }

        localFilesGrid.innerHTML = '';
        localFilesGrid.style.display = 'grid';

        // Render folders as cards
        if (folders && folders.length > 0) {
            folders.forEach(folder => {
                const card = document.createElement('div');
                card.className = 'local-file-card';
                card.innerHTML = `
                    <div class="local-file-card-cover">
                        <i class="fas fa-folder"></i>
                        <span class="video-count-badge">${folder.video_count} video${folder.video_count !== 1 ? 's' : ''}</span>
                    </div>
                    <div class="local-file-card-title" title="${escapeHtmlFB(folder.name)}">
                        ${escapeHtmlFB(folder.name)}
                    </div>
                `;
                card.addEventListener('click', () => {
                    openFileModal(folder.name, folder.path);
                });
                localFilesGrid.appendChild(card);
            });
        }

        // Render loose files (root-level videos) as a single card if present
        if (files && files.length > 0) {
            const card = document.createElement('div');
            card.className = 'local-file-card';
            card.innerHTML = `
                <div class="local-file-card-cover">
                    <i class="fas fa-video"></i>
                    <span class="video-count-badge">${files.length} video${files.length !== 1 ? 's' : ''}</span>
                </div>
                <div class="local-file-card-title" title="Unsorted Files">
                    Unsorted Files
                </div>
            `;
            card.addEventListener('click', () => {
                openFileModal('Unsorted Files', '');
            });
            localFilesGrid.appendChild(card);
        }
    }

    // ========================================
    // File Modal
    // ========================================

    function openFileModal(title, folderPath) {
        fileModalTitle.textContent = title;
        currentFileModalFolder = folderPath;
        selectedFiles.clear();
        fileModalSelectAll.checked = false;
        updateFileModalSelectionCount();

        fileModalLoading.style.display = 'flex';
        fileModalList.style.display = 'none';
        fileModalEmpty.style.display = 'none';

        fileModal.style.display = 'flex';

        // Load files for this folder
        let url = '/api/files';
        if (folderPath) {
            url += `?path=${encodeURIComponent(folderPath)}`;
        }

        Promise.all([
            fetch(url).then(r => r.json()),
            fetch('/api/watch-progress').then(r => r.json())
        ])
        .then(([filesData, progressData]) => {
            if (filesData.success) {
                watchProgress = progressData.success ? progressData.progress : {};
                renderFileModalList(filesData.files || [], filesData.folders || [], filesData.parent_path);
            } else {
                showNotification(filesData.error || 'Failed to load files', 'error');
            }
        })
        .catch(error => {
            console.error('Failed to load files for modal:', error);
            showNotification('Failed to load files', 'error');
        })
        .finally(() => {
            fileModalLoading.style.display = 'none';
        });
    }

    function closeFileModalFn() {
        fileModal.style.display = 'none';
        selectedFiles.clear();
        // Refresh the local files grid in case deletions happened
        loadLocalFiles();
    }

    function renderFileModalList(files, folders, parentPath) {
        // For the file modal, show subfolders (navigate into them) and files
        const hasFiles = files && files.length > 0;
        const hasFolders = folders && folders.length > 0;

        if (!hasFiles && !hasFolders) {
            fileModalEmpty.style.display = 'block';
            fileModalList.style.display = 'none';
            return;
        }

        fileModalList.innerHTML = '';
        fileModalList.style.display = 'block';
        fileModalEmpty.style.display = 'none';

        // Render subfolders (navigable)
        if (hasFolders) {
            folders.forEach(folder => {
                const item = document.createElement('div');
                item.className = 'file-modal-item';
                item.style.cursor = 'pointer';
                item.innerHTML = `
                    <div class="file-icon" style="color: #ed8936;">
                        <i class="fas fa-folder"></i>
                    </div>
                    <div class="file-info">
                        <div class="file-name">${escapeHtmlFB(folder.name)}</div>
                        <div class="file-meta">${folder.video_count} video${folder.video_count !== 1 ? 's' : ''}</div>
                    </div>
                    <div style="color: var(--text-tertiary);"><i class="fas fa-chevron-right"></i></div>
                `;
                item.addEventListener('click', () => {
                    fileModalTitle.textContent = folder.name;
                    currentFileModalFolder = folder.path;
                    selectedFiles.clear();
                    fileModalSelectAll.checked = false;
                    updateFileModalSelectionCount();

                    fileModalLoading.style.display = 'flex';
                    fileModalList.style.display = 'none';
                    fileModalEmpty.style.display = 'none';

                    let url = `/api/files?path=${encodeURIComponent(folder.path)}`;
                    Promise.all([
                        fetch(url).then(r => r.json()),
                        fetch('/api/watch-progress').then(r => r.json())
                    ]).then(([fd, pd]) => {
                        if (fd.success) {
                            watchProgress = pd.success ? pd.progress : {};
                            renderFileModalList(fd.files || [], fd.folders || [], fd.parent_path);
                        }
                    }).finally(() => {
                        fileModalLoading.style.display = 'none';
                    });
                });
                fileModalList.appendChild(item);
            });
        }

        // Render files with checkboxes
        if (hasFiles) {
            files.forEach(file => {
                const item = document.createElement('div');
                item.className = 'file-modal-item';

                const extension = file.name.split('.').pop().toLowerCase();
                let iconClass = 'fas fa-video';
                if (['mkv', 'avi'].includes(extension)) {
                    iconClass = 'fas fa-film';
                }

                // Watch progress
                const progress = watchProgress[file.path] || null;
                let progressHtml = '';

                if (progress) {
                    const percentage = progress.percentage || 0;
                    const isWatched = percentage > 95;

                    if (isWatched) {
                        progressHtml = `
                            <div class="file-progress">
                                <span class="file-progress-watched"><i class="fas fa-check-circle"></i> Watched</span>
                            </div>
                        `;
                    } else if (percentage > 0) {
                        progressHtml = `
                            <div class="file-progress">
                                <div class="file-progress-bar">
                                    <div class="file-progress-fill" style="width: ${percentage}%"></div>
                                </div>
                                <span class="file-progress-text">${Math.round(percentage)}%</span>
                            </div>
                        `;
                    }
                }

                item.innerHTML = `
                    <input type="checkbox" class="file-checkbox" data-path="${escapeHtmlFB(file.path)}">
                    <div class="file-icon">
                        <i class="${iconClass}"></i>
                    </div>
                    <div class="file-info">
                        <div class="file-name">${escapeHtmlFB(file.name)}</div>
                        <div class="file-meta">
                            <span class="file-size">${file.size_human}</span>
                            <span class="file-date">${file.modified_human}</span>
                        </div>
                        ${progressHtml}
                    </div>
                    <div class="file-actions">
                        <button class="file-action-btn stream-btn" title="Stream in browser">
                            <i class="fas fa-play"></i>
                        </button>
                        <button class="file-action-btn cast-file-btn" title="Cast to Chromecast">
                            <i class="fas fa-tv"></i>
                        </button>
                    </div>
                `;

                // Checkbox change
                const checkbox = item.querySelector('.file-checkbox');
                checkbox.addEventListener('change', () => {
                    if (checkbox.checked) {
                        selectedFiles.add(file.path);
                    } else {
                        selectedFiles.delete(file.path);
                    }
                    updateFileModalSelectionCount();
                });

                // Stream button
                const streamBtn = item.querySelector('.stream-btn');
                streamBtn.addEventListener('click', () => {
                    const startTime = (progress && progress.percentage > 0 && progress.percentage < 95) ? progress.current_time : 0;
                    streamFile(file, startTime);
                });

                // Cast button
                const castBtn = item.querySelector('.cast-file-btn');
                castBtn.addEventListener('click', () => {
                    openCastModalForFile(file);
                });

                fileModalList.appendChild(item);
            });
        }
    }

    function updateFileModalSelection() {
        const checkboxes = fileModalList.querySelectorAll('.file-checkbox');
        selectedFiles.clear();
        checkboxes.forEach(cb => {
            if (cb.checked) {
                selectedFiles.add(cb.dataset.path);
            }
        });
        updateFileModalSelectionCount();
    }

    function updateFileModalSelectionCount() {
        const count = selectedFiles.size;
        fileModalSelectedCount.textContent = `${count} selected`;
        fileModalDeleteSelected.style.display = count > 0 ? 'inline-flex' : 'none';
    }

    function deleteSelectedFiles() {
        if (selectedFiles.size === 0) return;
        if (!confirm(`Delete ${selectedFiles.size} selected file(s)?`)) return;

        const deletions = Array.from(selectedFiles).map(path =>
            fetch('/api/files/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path })
            }).then(r => r.json())
        );

        Promise.all(deletions)
            .then(results => {
                const successCount = results.filter(r => r.success).length;
                showNotification(`${successCount} file(s) deleted`, 'success');
                selectedFiles.clear();
                fileModalSelectAll.checked = false;
                updateFileModalSelectionCount();
                // Reload the file modal content
                openFileModal(fileModalTitle.textContent, currentFileModalFolder);
            })
            .catch(error => {
                console.error('Delete error:', error);
                showNotification('Failed to delete some files', 'error');
            });
    }

    // ========================================
    // Stream file (video player modal)
    // ========================================

    function streamFile(file, startTime = 0) {
        const streamUrl = `/api/files/stream/${encodeURIComponent(file.path)}`;

        const videoModal = document.createElement('div');
        videoModal.className = 'modal-overlay';
        videoModal.id = 'video-player-modal';
        videoModal.innerHTML = `
            <div class="modal-content video-player-modal-content">
                <div class="modal-header">
                    <h3><i class="fas fa-play-circle"></i> ${escapeHtmlFB(file.name)}</h3>
                    <button class="close-btn" id="close-video-player">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="video-player-container">
                        <video controls autoplay>
                            <source src="${streamUrl}" type="video/mp4">
                            Your browser does not support the video tag.
                        </video>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(videoModal);
        videoModal.style.display = 'flex';

        const video = videoModal.querySelector('video');
        let progressSaveInterval = null;

        video.addEventListener('loadedmetadata', () => {
            if (startTime > 0) {
                video.currentTime = startTime;
            }
        });

        video.addEventListener('play', () => {
            progressSaveInterval = setInterval(() => {
                saveWatchProgress(file.path, video.currentTime, video.duration);
            }, 5000);
        });

        video.addEventListener('pause', () => {
            if (progressSaveInterval) {
                clearInterval(progressSaveInterval);
                progressSaveInterval = null;
            }
            saveWatchProgress(file.path, video.currentTime, video.duration);
        });

        const closeModal = () => {
            if (progressSaveInterval) clearInterval(progressSaveInterval);
            if (video.currentTime > 0) {
                saveWatchProgress(file.path, video.currentTime, video.duration);
            }
            video.pause();
            videoModal.remove();
        };

        videoModal.querySelector('#close-video-player').addEventListener('click', closeModal);
        videoModal.addEventListener('click', (e) => {
            if (e.target === videoModal) closeModal();
        });
    }

    function saveWatchProgress(filePath, currentTime, duration) {
        fetch('/api/watch-progress', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file: filePath, current_time: currentTime, duration: duration })
        }).catch(error => {
            console.error('Failed to save watch progress:', error);
        });
    }

    // ========================================
    // Cast Modal
    // ========================================

    // File that triggered the cast modal
    let pendingCastFile = null;

    function openCastModalForFile(file) {
        pendingCastFile = file;
        castModal.style.display = 'flex';

        // If device already selected, show it and auto-cast
        if (currentCastDevice) {
            castModalDevicesList.style.display = 'none';
            castModalSelectedDevice.style.display = 'flex';
            castModalSelectedDeviceName.textContent = currentCastDevice.name;

            // Auto-cast the file
            castFile(file, 0);
        } else {
            castModalDevicesList.style.display = 'block';
            castModalSelectedDevice.style.display = 'none';
        }

        // Show controls if already casting
        if (currentCastFile) {
            castModalControls.style.display = 'block';
        }
    }

    function closeCastModal() {
        castModal.style.display = 'none';
        // Don't reset device - keep casting in background
    }

    function scanChromecastDevices() {
        castModalDevicesLoading.style.display = 'flex';
        castModalDevicesList.innerHTML = '';
        castModalScanBtn.disabled = true;

        fetch('/api/chromecast/discover')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.devices.length > 0) {
                    renderDeviceList(data.devices);
                } else if (data.error) {
                    castModalDevicesList.innerHTML = `<p class="cast-devices-empty">${escapeHtmlFB(data.error)}</p>`;
                } else {
                    castModalDevicesList.innerHTML = '<p class="cast-devices-empty">No Chromecast devices found</p>';
                }
            })
            .catch(error => {
                console.error('Failed to scan devices:', error);
                castModalDevicesList.innerHTML = '<p class="cast-devices-empty">Failed to scan for devices</p>';
            })
            .finally(() => {
                castModalDevicesLoading.style.display = 'none';
                castModalScanBtn.disabled = false;
            });
    }

    function renderDeviceList(devices) {
        castModalDevicesList.innerHTML = '';

        devices.forEach(device => {
            const deviceItem = document.createElement('div');
            deviceItem.className = 'cast-device-item';
            deviceItem.innerHTML = `
                <div class="cast-device-icon">
                    <i class="fas fa-tv"></i>
                </div>
                <div class="cast-device-info">
                    <div class="cast-device-name">${escapeHtmlFB(device.name)}</div>
                    <div class="cast-device-model">${escapeHtmlFB(device.model)}</div>
                </div>
                <button class="cast-device-select-btn">Select</button>
            `;

            deviceItem.querySelector('.cast-device-select-btn').addEventListener('click', () => {
                selectDevice(device);
            });

            castModalDevicesList.appendChild(deviceItem);
        });
    }

    function selectDevice(device) {
        currentCastDevice = device;
        castModalDevicesList.style.display = 'none';
        castModalSelectedDevice.style.display = 'flex';
        castModalSelectedDeviceName.textContent = device.name;

        // If we had a pending file to cast, cast it now
        if (pendingCastFile) {
            castFile(pendingCastFile, 0);
            pendingCastFile = null;
        }
    }

    function changeDevice() {
        castModalDevicesList.style.display = 'block';
        castModalSelectedDevice.style.display = 'none';
        scanChromecastDevices();
    }

    function castFile(file, startTime = 0) {
        if (!currentCastDevice) {
            showNotification('No device selected', 'error');
            return;
        }

        currentCastFile = file;
        castStartTime = startTime;

        const startMsg = startTime > 0 ? ` (resuming from ${formatTime(startTime)})` : '';
        showNotification(`Casting "${file.name}" to ${currentCastDevice.name}${startMsg}...`, 'info');

        fetch('/api/chromecast/cast', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_uuid: currentCastDevice.uuid,
                file_path: file.path
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(`Now casting to ${currentCastDevice.name}`, 'success');

                castModalControls.style.display = 'block';
                castModalStatus.textContent = `Casting to ${currentCastDevice.name}`;
                castModalNowPlayingFile.textContent = file.name;

                if (startTime > 0) {
                    setTimeout(() => castControl('seek', startTime), 2000);
                }

                startCastStatusPolling();
            } else {
                showNotification(data.error || 'Failed to cast', 'error');
            }
        })
        .catch(error => {
            console.error('Cast error:', error);
            showNotification('Failed to cast', 'error');
        });
    }

    function startCastStatusPolling() {
        if (castStatusInterval) clearInterval(castStatusInterval);
        castStatusInterval = setInterval(updateCastStatus, 1000);
        updateCastStatus();
    }

    function updateCastStatus() {
        if (!currentCastDevice) return;

        fetch(`/api/chromecast/status?device_uuid=${currentCastDevice.uuid}`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.status) {
                    const status = data.status;
                    castDurationValue = status.duration || 0;

                    if (status.duration > 0) {
                        const progress = (status.current_time / status.duration) * 100;
                        castModalProgressFill.style.width = `${progress}%`;
                    }

                    castModalCurrentTime.textContent = formatTime(status.current_time);
                    castModalDuration.textContent = formatTime(status.duration);

                    const icon = castModalPlayPauseBtn.querySelector('i');
                    icon.className = status.is_playing ? 'fas fa-pause' : 'fas fa-play';

                    if (document.activeElement !== castModalVolumeSlider) {
                        castModalVolumeSlider.value = status.volume;
                        updateVolumeDisplay(status.volume);
                    }

                    if (currentCastFile && status.current_time > 0 && status.duration > 0) {
                        if (Math.abs(status.current_time - lastSavedCastTime) >= 10) {
                            lastSavedCastTime = status.current_time;
                            saveWatchProgress(currentCastFile.path, status.current_time, status.duration);
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Failed to get cast status:', error);
            });
    }

    function updateVolumeDisplay(value) {
        if (castModalVolumeValue) castModalVolumeValue.textContent = `${value}%`;
        if (castModalVolumeIcon) {
            if (value === 0) castModalVolumeIcon.className = 'fas fa-volume-mute';
            else if (value < 50) castModalVolumeIcon.className = 'fas fa-volume-down';
            else castModalVolumeIcon.className = 'fas fa-volume-up';
        }
    }

    function toggleCastPlayPause() {
        if (!currentCastDevice) return;
        const icon = castModalPlayPauseBtn.querySelector('i');
        const action = icon.className.includes('fa-play') ? 'play' : 'pause';
        castControl(action);
    }

    function stopCasting() {
        if (!currentCastDevice) return;

        if (currentCastFile && castDurationValue > 0) {
            const widthPercent = parseFloat(castModalProgressFill.style.width) || 0;
            const currentTime = (widthPercent / 100) * castDurationValue;
            if (currentTime > 0) {
                saveWatchProgress(currentCastFile.path, currentTime, castDurationValue);
            }
        }

        castControl('stop');

        castModalControls.style.display = 'none';
        castModalStatus.textContent = 'Not casting';
        castModalProgressFill.style.width = '0%';
        castModalCurrentTime.textContent = '0:00';
        castModalDuration.textContent = '0:00';

        currentCastFile = null;
        castDurationValue = 0;
        lastSavedCastTime = 0;

        if (castStatusInterval) {
            clearInterval(castStatusInterval);
            castStatusInterval = null;
        }

        showNotification('Stopped casting', 'info');
    }

    function castControl(action, value = null) {
        if (!currentCastDevice) return;

        const body = { device_uuid: currentCastDevice.uuid, action: action };
        if (value !== null) body.value = value;

        fetch('/api/chromecast/control', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) console.error('Cast control error:', data.error);
        })
        .catch(error => {
            console.error('Cast control error:', error);
        });
    }

    // ========================================
    // Utility functions
    // ========================================

    function formatTime(seconds) {
        if (!seconds || isNaN(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    function escapeHtmlFB(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
})();

// ========================================
// Preferences Modal Functionality
// ========================================

(function() {
    // Find all preferences links/buttons
    const preferencesLinks = document.querySelectorAll('a[href*="preferences"], .dropdown-item[href*="preferences"]');

    // Show preferences modal (modal is already embedded in page)
    function showPreferencesModal() {
        const modal = document.getElementById('preferences-modal-overlay');
        if (modal) {
            console.log('Showing preferences modal');
            modal.style.display = 'flex';
        } else {
            console.error('Preferences modal not found in DOM');
        }
    }

    // Add click handlers to all preferences links
    preferencesLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            showPreferencesModal();
        });
    });

    // Also check for preferences button by title
    const preferencesBtn = document.querySelector('[title="Preferences"]');
    if (preferencesBtn) {
        preferencesBtn.addEventListener('click', (e) => {
            e.preventDefault();
            showPreferencesModal();
        });
    }
})();