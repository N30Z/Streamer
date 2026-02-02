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

    // Queue elements
    const queueSection = document.getElementById('queue-section');
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
        emptyState.style.display = 'none';
        resultsSection.style.display = 'none';
        loadingSection.style.display = 'block';
    }

    function hideLoadingState() {
        loadingSection.style.display = 'none';
    }

    function showResultsSection() {
        homeContent.style.display = 'none';
        emptyState.style.display = 'none';
        loadingSection.style.display = 'none';
        resultsSection.style.display = 'block';
    }

    function showEmptyState() {
        homeContent.style.display = 'none';
        resultsSection.style.display = 'none';
        loadingSection.style.display = 'none';
        emptyState.style.display = 'block';
    }

    function showHomeContent() {
        resultsSection.style.display = 'none';
        loadingSection.style.display = 'none';
        emptyState.style.display = 'none';
        homeContent.style.display = 'block';
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

                    // Show/hide queue section based on content
                    if (activeItems.length > 0 || completedItems.length > 0) {
                        queueSection.style.display = 'block';

                        // Update active downloads
                        if (activeItems.length > 0) {
                            activeDownloads.style.display = 'block';
                            updateQueueList(activeQueueList, activeItems, 'active');
                        } else {
                            activeDownloads.style.display = 'none';
                        }

                        // Update completed downloads
                        if (completedItems.length > 0) {
                            completedDownloads.style.display = 'block';
                            updateQueueList(completedQueueList, completedItems, 'completed');
                        } else {
                            completedDownloads.style.display = 'none';
                        }
                    } else {
                        // No downloads to show
                        queueSection.style.display = 'none';
                        if (progressInterval) {
                            clearInterval(progressInterval);
                            progressInterval = null;
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Queue status update error:', error);
            });
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

            queueItem.innerHTML = `
                <div class="queue-item-header">
                    <div class="queue-item-title">${escapeHtml(item.anime_title)}</div>
                    <div class="queue-item-status ${item.status}">${item.status}</div>
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

    // Make showDownloadModal globally accessible
    window.showDownloadModal = showDownloadModal;
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
// File Browser Functionality
// ========================================

(function() {
    // File browser elements
    const fileBrowserBtn = document.getElementById('file-browser-btn');
    const fileBrowserModal = document.getElementById('file-browser-modal');
    const closeFileBrowserModal = document.getElementById('close-file-browser-modal');
    const refreshFilesBtn = document.getElementById('refresh-files-btn');
    const currentPathEl = document.getElementById('current-path');
    const fileBrowserLoading = document.getElementById('file-browser-loading');
    const fileList = document.getElementById('file-list');
    const fileEmpty = document.getElementById('file-empty');

    // Cast controller elements
    const castControllerModal = document.getElementById('cast-controller-modal');
    const closeCastControllerModal = document.getElementById('close-cast-controller-modal');
    const scanDevicesBtn = document.getElementById('scan-devices-btn');
    const castDevicesLoading = document.getElementById('cast-devices-loading');
    const castDevicesList = document.getElementById('cast-devices-list');
    const castControls = document.getElementById('cast-controls');
    const castStatus = document.getElementById('cast-status');
    const castProgressFill = document.getElementById('cast-progress-fill');
    const castCurrentTime = document.getElementById('cast-current-time');
    const castDuration = document.getElementById('cast-duration');
    const castPlayPauseBtn = document.getElementById('cast-play-pause-btn');
    const castStopBtn = document.getElementById('cast-stop-btn');
    const castRewindBtn = document.getElementById('cast-rewind-btn');
    const castForwardBtn = document.getElementById('cast-forward-btn');
    const castVolumeSlider = document.getElementById('cast-volume-slider');

    // New cast controller elements
    const castNavBtn = document.getElementById('cast-btn');
    const castStepDevice = document.getElementById('cast-step-device');
    const castStepMedia = document.getElementById('cast-step-media');
    const castSelectedDevice = document.getElementById('cast-selected-device');
    const castSelectedDeviceName = document.getElementById('cast-selected-device-name');
    const changeDeviceBtn = document.getElementById('change-device-btn');
    const castMediaList = document.getElementById('cast-media-list');
    const castMediaLoading = document.getElementById('cast-media-loading');
    const castMediaEmpty = document.getElementById('cast-media-empty');
    const castNowPlayingFile = document.getElementById('cast-now-playing-file');
    const castProgressBarClickable = document.getElementById('cast-progress-bar-clickable');
    const castVolumeIcon = document.getElementById('cast-volume-icon');
    const castVolumeValue = document.getElementById('cast-volume-value');

    // State
    let currentCastFile = null;
    let currentCastDevice = null;
    let castStatusInterval = null;
    let castMediaFiles = [];
    let castDurationValue = 0;

    // Folder navigation state
    let currentFolderPath = '';
    let watchProgress = {};

    // Initialize file browser
    if (fileBrowserBtn) {
        fileBrowserBtn.addEventListener('click', openFileBrowser);
    }

    if (closeFileBrowserModal) {
        closeFileBrowserModal.addEventListener('click', closeFileBrowserModalFn);
    }

    if (refreshFilesBtn) {
        refreshFilesBtn.addEventListener('click', loadFiles);
    }

    if (fileBrowserModal) {
        fileBrowserModal.addEventListener('click', function(e) {
            if (e.target === fileBrowserModal) {
                closeFileBrowserModalFn();
            }
        });
    }

    // Initialize cast controller
    if (castNavBtn) {
        castNavBtn.addEventListener('click', openCastController);
    }

    if (closeCastControllerModal) {
        closeCastControllerModal.addEventListener('click', closeCastController);
    }

    if (castControllerModal) {
        castControllerModal.addEventListener('click', function(e) {
            if (e.target === castControllerModal) {
                closeCastController();
            }
        });
    }

    if (scanDevicesBtn) {
        scanDevicesBtn.addEventListener('click', scanChromecastDevices);
    }

    if (changeDeviceBtn) {
        changeDeviceBtn.addEventListener('click', changeDevice);
    }

    // Cast control buttons
    if (castPlayPauseBtn) {
        castPlayPauseBtn.addEventListener('click', toggleCastPlayPause);
    }
    if (castStopBtn) {
        castStopBtn.addEventListener('click', stopCasting);
    }
    if (castRewindBtn) {
        castRewindBtn.addEventListener('click', () => castControl('rewind'));
    }
    if (castForwardBtn) {
        castForwardBtn.addEventListener('click', () => castControl('forward'));
    }
    if (castVolumeSlider) {
        castVolumeSlider.addEventListener('input', (e) => {
            const value = parseInt(e.target.value);
            castControl('volume', value);
            updateVolumeDisplay(value);
        });
    }
    if (castProgressBarClickable) {
        castProgressBarClickable.addEventListener('click', (e) => {
            if (castDurationValue > 0) {
                const rect = castProgressBarClickable.getBoundingClientRect();
                const percentage = (e.clientX - rect.left) / rect.width;
                const seekTime = Math.floor(percentage * castDurationValue);
                castControl('seek', seekTime);
            }
        });
    }

    function openFileBrowser() {
        fileBrowserModal.style.display = 'flex';
        loadFiles();
    }

    function closeFileBrowserModalFn() {
        fileBrowserModal.style.display = 'none';
    }

    function loadFiles(folderPath = '') {
        fileBrowserLoading.style.display = 'flex';
        fileList.style.display = 'none';
        fileEmpty.style.display = 'none';

        currentFolderPath = folderPath;

        // Build URL with optional path parameter
        let url = '/api/files';
        if (folderPath) {
            url += `?path=${encodeURIComponent(folderPath)}`;
        }

        // Also load watch progress
        Promise.all([
            fetch(url).then(r => r.json()),
            fetch('/api/watch-progress').then(r => r.json())
        ])
            .then(([filesData, progressData]) => {
                if (filesData.success) {
                    watchProgress = progressData.success ? progressData.progress : {};
                    updateBreadcrumb(filesData.current_path, filesData.path);
                    renderFileList(filesData.folders, filesData.files, filesData.parent_path);
                } else {
                    showNotification(filesData.error || 'Failed to load files', 'error');
                }
            })
            .catch(error => {
                console.error('Failed to load files:', error);
                showNotification('Failed to load files', 'error');
            })
            .finally(() => {
                fileBrowserLoading.style.display = 'none';
            });
    }

    function updateBreadcrumb(currentPath, basePath) {
        // Update the path display with breadcrumb navigation
        if (!currentPath) {
            currentPathEl.innerHTML = `<i class="fas fa-home"></i> ${escapeHtmlFB(basePath)}`;
        } else {
            const parts = currentPath.split(/[\/\\]/);
            let breadcrumb = `<span class="breadcrumb-link" onclick="window.navigateToFolder('')"><i class="fas fa-home"></i> Root</span>`;

            let pathSoFar = '';
            parts.forEach((part, index) => {
                pathSoFar += (pathSoFar ? '/' : '') + part;
                const isLast = index === parts.length - 1;

                breadcrumb += ` <span class="breadcrumb-separator">/</span> `;
                if (isLast) {
                    breadcrumb += `<span class="breadcrumb-current">${escapeHtmlFB(part)}</span>`;
                } else {
                    const folderPathForClick = pathSoFar;
                    breadcrumb += `<span class="breadcrumb-link" onclick="window.navigateToFolder('${escapeHtmlFB(folderPathForClick)}')">${escapeHtmlFB(part)}</span>`;
                }
            });

            currentPathEl.innerHTML = breadcrumb;
        }
    }

    // Make navigateToFolder globally accessible
    window.navigateToFolder = function(path) {
        loadFiles(path);
    };

    function renderFileList(folders, files, parentPath) {
        const hasContent = (folders && folders.length > 0) || (files && files.length > 0);

        if (!hasContent && !currentFolderPath) {
            fileEmpty.style.display = 'block';
            fileList.style.display = 'none';
            return;
        }

        fileList.innerHTML = '';
        fileList.style.display = 'block';

        // Add back button if we're in a subfolder
        if (currentFolderPath) {
            const backItem = document.createElement('div');
            backItem.className = 'folder-item back-folder-item';
            backItem.innerHTML = `
                <div class="folder-icon">
                    <i class="fas fa-arrow-left"></i>
                </div>
                <div class="folder-info">
                    <div class="folder-name">.. Back</div>
                    <div class="folder-meta">Go to parent folder</div>
                </div>
            `;
            backItem.addEventListener('click', () => loadFiles(parentPath || ''));
            fileList.appendChild(backItem);
        }

        // Render folders
        if (folders && folders.length > 0) {
            folders.forEach(folder => {
                const folderItem = document.createElement('div');
                folderItem.className = 'folder-item';
                folderItem.innerHTML = `
                    <div class="folder-icon">
                        <i class="fas fa-folder"></i>
                    </div>
                    <div class="folder-info">
                        <div class="folder-name">${escapeHtmlFB(folder.name)}</div>
                        <div class="folder-meta">${folder.video_count} video${folder.video_count !== 1 ? 's' : ''}</div>
                    </div>
                    <div class="folder-arrow">
                        <i class="fas fa-chevron-right"></i>
                    </div>
                `;
                folderItem.addEventListener('click', () => loadFiles(folder.path));
                fileList.appendChild(folderItem);
            });
        }

        // Render files
        if (files && files.length > 0) {
            files.forEach(file => {
                const fileItem = document.createElement('div');
                fileItem.className = 'file-item';

                const extension = file.name.split('.').pop().toLowerCase();
                let iconClass = 'fas fa-video';
                if (['mkv', 'avi'].includes(extension)) {
                    iconClass = 'fas fa-film';
                }

                // Check watch progress for this file
                const progress = watchProgress[file.path] || null;
                let progressHtml = '';
                let continueBtn = '';

                if (progress) {
                    const percentage = progress.percentage || 0;
                    const isWatched = percentage > 95; // Consider watched if > 95%

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
                        continueBtn = `
                            <button class="file-action-btn continue-btn" title="Continue watching from ${formatTime(progress.current_time)}">
                                <i class="fas fa-play-circle"></i> Continue
                            </button>
                        `;
                    }
                }

                fileItem.innerHTML = `
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
                        ${continueBtn}
                        <button class="file-action-btn stream-btn" title="Stream in browser">
                            <i class="fas fa-play"></i> Stream
                        </button>
                        <button class="file-action-btn download-btn" title="Download file">
                            <i class="fas fa-download"></i> Download
                        </button>
                        <button class="file-action-btn delete-btn" title="Delete file">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                `;

                // Add event listeners
                const streamBtn = fileItem.querySelector('.stream-btn');
                const downloadBtn = fileItem.querySelector('.download-btn');
                const deleteBtn = fileItem.querySelector('.delete-btn');
                const continueBtnEl = fileItem.querySelector('.continue-btn');

                streamBtn.addEventListener('click', () => streamFile(file));
                downloadBtn.addEventListener('click', () => downloadFile(file));
                deleteBtn.addEventListener('click', () => deleteFile(file));
                if (continueBtnEl && progress) {
                    continueBtnEl.addEventListener('click', () => streamFile(file, progress.current_time));
                }

                fileList.appendChild(fileItem);
            });
        }

        // Show empty state if no content (but we are in a subfolder)
        if (!hasContent) {
            fileEmpty.style.display = 'block';
        } else {
            fileEmpty.style.display = 'none';
        }
    }

    function streamFile(file, startTime = 0) {
        // Open video in new tab or modal
        const streamUrl = `/api/files/stream/${encodeURIComponent(file.path)}`;

        // Create a video player modal
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

        // Set start time once video is ready
        video.addEventListener('loadedmetadata', () => {
            if (startTime > 0) {
                video.currentTime = startTime;
            }
        });

        // Save progress periodically
        video.addEventListener('play', () => {
            progressSaveInterval = setInterval(() => {
                saveWatchProgress(file.path, video.currentTime, video.duration);
            }, 5000); // Save every 5 seconds
        });

        video.addEventListener('pause', () => {
            if (progressSaveInterval) {
                clearInterval(progressSaveInterval);
                progressSaveInterval = null;
            }
            // Save immediately on pause
            saveWatchProgress(file.path, video.currentTime, video.duration);
        });

        const closeModal = () => {
            if (progressSaveInterval) {
                clearInterval(progressSaveInterval);
            }
            // Save final progress
            if (video.currentTime > 0) {
                saveWatchProgress(file.path, video.currentTime, video.duration);
            }
            video.pause();
            videoModal.remove();
        };

        const closeBtn = videoModal.querySelector('#close-video-player');
        closeBtn.addEventListener('click', closeModal);

        videoModal.addEventListener('click', (e) => {
            if (e.target === videoModal) {
                closeModal();
            }
        });
    }

    function saveWatchProgress(filePath, currentTime, duration) {
        fetch('/api/watch-progress', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                file: filePath,
                current_time: currentTime,
                duration: duration
            })
        })
        .catch(error => {
            console.error('Failed to save watch progress:', error);
        });
    }

    function openCastController() {
        castControllerModal.style.display = 'flex';

        // Reset to initial state
        resetCastController();

        // If we have a device already selected from a previous session, show it
        if (currentCastDevice) {
            showSelectedDevice();
            loadCastMediaFiles();
        }
    }

    function resetCastController() {
        // Show device selection step
        castStepDevice.style.display = 'block';
        castSelectedDevice.style.display = 'none';
        castDevicesList.innerHTML = '<p class="cast-devices-empty">Click "Scan" to find Chromecast devices</p>';

        // Hide media step if no device
        if (!currentCastDevice) {
            castStepMedia.style.display = 'none';
        }

        // Hide controls if not casting
        if (!currentCastFile) {
            castControls.style.display = 'none';
        }
    }

    function closeCastController() {
        castControllerModal.style.display = 'none';
        // Don't reset device/file - keep casting in background
    }

    function scanChromecastDevices() {
        castDevicesLoading.style.display = 'flex';
        castDevicesList.innerHTML = '';
        scanDevicesBtn.disabled = true;

        fetch('/api/chromecast/discover')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.devices.length > 0) {
                    renderDeviceList(data.devices);
                } else if (data.error) {
                    castDevicesList.innerHTML = `<p class="cast-devices-empty">${escapeHtmlFB(data.error)}</p>`;
                } else {
                    castDevicesList.innerHTML = '<p class="cast-devices-empty">No Chromecast devices found</p>';
                }
            })
            .catch(error => {
                console.error('Failed to scan devices:', error);
                castDevicesList.innerHTML = '<p class="cast-devices-empty">Failed to scan for devices</p>';
            })
            .finally(() => {
                castDevicesLoading.style.display = 'none';
                scanDevicesBtn.disabled = false;
            });
    }

    function renderDeviceList(devices) {
        castDevicesList.innerHTML = '';

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

            const selectBtn = deviceItem.querySelector('.cast-device-select-btn');
            selectBtn.addEventListener('click', () => selectDevice(device));

            castDevicesList.appendChild(deviceItem);
        });
    }

    function selectDevice(device) {
        currentCastDevice = device;
        showSelectedDevice();
        loadCastMediaFiles();
    }

    function showSelectedDevice() {
        // Hide device list, show selected device
        castDevicesList.style.display = 'none';
        castSelectedDevice.style.display = 'flex';
        castSelectedDeviceName.textContent = currentCastDevice.name;

        // Show media selection step
        castStepMedia.style.display = 'block';
    }

    function changeDevice() {
        // Show device list again
        castDevicesList.style.display = 'block';
        castSelectedDevice.style.display = 'none';

        // Hide media step
        castStepMedia.style.display = 'none';

        // Scan for devices
        scanChromecastDevices();
    }

    function loadCastMediaFiles(folderPath = '') {
        castMediaLoading.style.display = 'flex';
        castMediaList.innerHTML = '';
        castMediaEmpty.style.display = 'none';

        // Build URL with optional path parameter
        let url = '/api/files';
        if (folderPath) {
            url += `?path=${encodeURIComponent(folderPath)}`;
        }

        // Also load watch progress
        Promise.all([
            fetch(url).then(r => r.json()),
            fetch('/api/watch-progress').then(r => r.json())
        ])
            .then(([data, progressData]) => {
                const allProgress = progressData.success ? progressData.progress : {};
                if (data.success) {
                    // Combine folders and files
                    const folders = data.folders || [];
                    const files = data.files || [];
                    castMediaFiles = files;
                    renderCastMediaList(folders, files, allProgress, data.parent_path, folderPath);
                } else {
                    castMediaEmpty.style.display = 'block';
                }
            })
            .catch(error => {
                console.error('Failed to load media files:', error);
                castMediaEmpty.style.display = 'block';
            })
            .finally(() => {
                castMediaLoading.style.display = 'none';
            });
    }

    // Track current cast folder path
    let currentCastFolderPath = '';

    function renderCastMediaList(folders, files, allProgress, parentPath, currentPath) {
        castMediaList.innerHTML = '';
        currentCastFolderPath = currentPath || '';

        const hasContent = (folders && folders.length > 0) || (files && files.length > 0);

        if (!hasContent && !currentCastFolderPath) {
            castMediaEmpty.style.display = 'block';
            return;
        }

        castMediaEmpty.style.display = 'none';

        // Add back button if in subfolder
        if (currentCastFolderPath) {
            const backItem = document.createElement('div');
            backItem.className = 'cast-media-item back-folder-item';
            backItem.style.cursor = 'pointer';
            backItem.innerHTML = `
                <div class="cast-media-icon">
                    <i class="fas fa-arrow-left" style="color: #4299e1;"></i>
                </div>
                <div class="cast-media-info">
                    <div class="cast-media-name">.. Back</div>
                    <div class="cast-media-meta">Go to parent folder</div>
                </div>
            `;
            backItem.addEventListener('click', () => loadCastMediaFiles(parentPath || ''));
            castMediaList.appendChild(backItem);
        }

        // Render folders
        if (folders && folders.length > 0) {
            folders.forEach(folder => {
                const folderItem = document.createElement('div');
                folderItem.className = 'cast-media-item';
                folderItem.style.cursor = 'pointer';
                folderItem.innerHTML = `
                    <div class="cast-media-icon">
                        <i class="fas fa-folder" style="color: #ed8936;"></i>
                    </div>
                    <div class="cast-media-info">
                        <div class="cast-media-name">${escapeHtmlFB(folder.name)}</div>
                        <div class="cast-media-meta">${folder.video_count} video${folder.video_count !== 1 ? 's' : ''}</div>
                    </div>
                    <div style="color: var(--text-tertiary);">
                        <i class="fas fa-chevron-right"></i>
                    </div>
                `;
                folderItem.addEventListener('click', () => loadCastMediaFiles(folder.path));
                castMediaList.appendChild(folderItem);
            });
        }

        // Render files
        if (files && files.length > 0) {
            files.forEach(file => {
                const mediaItem = document.createElement('div');
                mediaItem.className = 'cast-media-item';

                const extension = file.name.split('.').pop().toLowerCase();
                let iconClass = 'fas fa-video';
                if (['mkv', 'avi'].includes(extension)) {
                    iconClass = 'fas fa-film';
                }

                const isCurrentlyPlaying = currentCastFile && currentCastFile.path === file.path;

                // Check watch progress
                const progress = allProgress[file.path] || null;
                let progressHtml = '';
                let actionButtons = '';

                // Credit time: 2 minutes = 120 seconds
                const CREDIT_TIME = 120;

                if (progress) {
                    const percentage = progress.percentage || 0;
                    const duration = progress.duration || 0;
                    const timeRemaining = duration - progress.current_time;
                    const isWatched = percentage > 95 || timeRemaining < CREDIT_TIME;

                    if (isWatched) {
                        progressHtml = `
                            <div class="cast-media-progress">
                                <span class="cast-media-watched"><i class="fas fa-check-circle"></i> Watched</span>
                            </div>
                        `;
                        // Add delete button for watched episodes
                        actionButtons = `
                            <button class="cast-delete-watched-btn" title="Delete watched episode">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        `;
                    } else if (percentage > 0) {
                        progressHtml = `
                            <div class="cast-media-progress">
                                <div class="cast-media-progress-bar">
                                    <div class="cast-media-progress-fill" style="width: ${percentage}%"></div>
                                </div>
                                <span class="cast-media-progress-text">${Math.round(percentage)}%</span>
                            </div>
                        `;
                    }
                }

                mediaItem.innerHTML = `
                    <div class="cast-media-icon">
                        <i class="${iconClass}"></i>
                    </div>
                    <div class="cast-media-info">
                        <div class="cast-media-name">${escapeHtmlFB(file.name)}</div>
                        <div class="cast-media-meta">
                            <span class="cast-media-size">${file.size_human}</span>
                        </div>
                        ${progressHtml}
                    </div>
                    ${actionButtons}
                    ${progress && progress.percentage > 0 && progress.percentage < 95 ? `
                        <button class="cast-media-btn" style="background: #ed8936; margin-right: 0.25rem;" title="Continue from ${formatTime(progress.current_time)}">
                            <i class="fas fa-play-circle"></i> Resume
                        </button>
                    ` : ''}
                    <button class="cast-media-btn ${isCurrentlyPlaying ? 'playing' : ''}" title="${isCurrentlyPlaying ? 'Currently Playing' : 'Cast this file'}">
                        <i class="fas ${isCurrentlyPlaying ? 'fa-broadcast-tower' : 'fa-play'}"></i>
                        ${isCurrentlyPlaying ? 'Playing' : 'Cast'}
                    </button>
                `;

                // Add event listeners
                const castBtns = mediaItem.querySelectorAll('.cast-media-btn');
                if (castBtns.length > 1 && progress && progress.percentage > 0 && progress.percentage < 95) {
                    // Resume button
                    castBtns[0].addEventListener('click', () => castFile(file, progress.current_time));
                    // Cast from start button
                    if (!isCurrentlyPlaying) {
                        castBtns[1].addEventListener('click', () => castFile(file, 0));
                    }
                } else if (castBtns.length > 0 && !isCurrentlyPlaying) {
                    castBtns[castBtns.length - 1].addEventListener('click', () => castFile(file, 0));
                }

                // Delete watched button
                const deleteWatchedBtn = mediaItem.querySelector('.cast-delete-watched-btn');
                if (deleteWatchedBtn) {
                    deleteWatchedBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        deleteWatchedFile(file);
                    });
                }

                castMediaList.appendChild(mediaItem);
            });
        }
    }

    function deleteWatchedFile(file) {
        if (!confirm(`Delete "${file.name}"?\n\nThis file appears to be fully watched.`)) {
            return;
        }

        fetch('/api/files/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                path: file.path
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Watched episode deleted', 'success');
                // Also delete watch progress
                fetch('/api/watch-progress', {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        file: file.path
                    })
                });
                // Refresh the list
                loadCastMediaFiles(currentCastFolderPath);
            } else {
                showNotification(data.error || 'Failed to delete file', 'error');
            }
        })
        .catch(error => {
            console.error('Delete error:', error);
            showNotification('Failed to delete file', 'error');
        });
    }

    function castFile(file, startTime = 0) {
        if (!currentCastDevice) {
            showNotification('No device selected', 'error');
            return;
        }

        currentCastFile = file;
        castStartTime = startTime;

        // Show loading state
        const startMsg = startTime > 0 ? ` (resuming from ${formatTime(startTime)})` : '';
        showNotification(`Casting "${file.name}" to ${currentCastDevice.name}${startMsg}...`, 'info');

        fetch('/api/chromecast/cast', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                device_uuid: currentCastDevice.uuid,
                file_path: file.path
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(`Now casting to ${currentCastDevice.name}`, 'success');

                // Show playback controls
                castControls.style.display = 'block';
                castStatus.textContent = `Casting to ${currentCastDevice.name}`;
                castNowPlayingFile.textContent = file.name;

                // If we have a start time, seek to it after a brief delay
                if (startTime > 0) {
                    setTimeout(() => {
                        castControl('seek', startTime);
                    }, 2000);
                }

                // Refresh media list to show current playing
                loadCastMediaFiles(currentCastFolderPath);

                // Start polling for status (which will also save progress)
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

    // Track cast start time for resume functionality
    let castStartTime = 0;

    function startCastStatusPolling() {
        if (castStatusInterval) {
            clearInterval(castStatusInterval);
        }

        castStatusInterval = setInterval(updateCastStatus, 1000);
        updateCastStatus();
    }

    // Track last saved progress time to avoid excessive saves
    let lastSavedCastTime = 0;

    function updateCastStatus() {
        if (!currentCastDevice) return;

        fetch(`/api/chromecast/status?device_uuid=${currentCastDevice.uuid}`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.status) {
                    const status = data.status;

                    // Store duration for seek calculations
                    castDurationValue = status.duration || 0;

                    // Update progress
                    if (status.duration > 0) {
                        const progress = (status.current_time / status.duration) * 100;
                        castProgressFill.style.width = `${progress}%`;
                    }

                    // Update time display
                    castCurrentTime.textContent = formatTime(status.current_time);
                    castDuration.textContent = formatTime(status.duration);

                    // Update play/pause button
                    const icon = castPlayPauseBtn.querySelector('i');
                    if (status.is_playing) {
                        icon.className = 'fas fa-pause';
                    } else {
                        icon.className = 'fas fa-play';
                    }

                    // Update volume (only if not being dragged)
                    if (document.activeElement !== castVolumeSlider) {
                        castVolumeSlider.value = status.volume;
                        updateVolumeDisplay(status.volume);
                    }

                    // Save watch progress periodically (every 10 seconds of playback)
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
        if (castVolumeValue) {
            castVolumeValue.textContent = `${value}%`;
        }
        if (castVolumeIcon) {
            if (value === 0) {
                castVolumeIcon.className = 'fas fa-volume-mute';
            } else if (value < 50) {
                castVolumeIcon.className = 'fas fa-volume-down';
            } else {
                castVolumeIcon.className = 'fas fa-volume-up';
            }
        }
    }

    function toggleCastPlayPause() {
        if (!currentCastDevice) return;

        const icon = castPlayPauseBtn.querySelector('i');
        const action = icon.className.includes('fa-play') ? 'play' : 'pause';
        castControl(action);
    }

    function stopCasting() {
        if (!currentCastDevice) return;

        // Save final progress before stopping
        if (currentCastFile && castDurationValue > 0) {
            const progressBar = castProgressFill;
            const widthPercent = parseFloat(progressBar.style.width) || 0;
            const currentTime = (widthPercent / 100) * castDurationValue;
            if (currentTime > 0) {
                saveWatchProgress(currentCastFile.path, currentTime, castDurationValue);
            }
        }

        castControl('stop');

        // Reset UI
        castControls.style.display = 'none';
        castStatus.textContent = 'Not casting';
        castProgressFill.style.width = '0%';
        castCurrentTime.textContent = '0:00';
        castDuration.textContent = '0:00';

        currentCastFile = null;
        castDurationValue = 0;
        lastSavedCastTime = 0;

        if (castStatusInterval) {
            clearInterval(castStatusInterval);
            castStatusInterval = null;
        }

        // Refresh media list to show updated progress
        loadCastMediaFiles(currentCastFolderPath);

        showNotification('Stopped casting', 'info');
    }

    function castControl(action, value = null) {
        if (!currentCastDevice) return;

        const body = {
            device_uuid: currentCastDevice.uuid,
            action: action
        };

        if (value !== null) {
            body.value = value;
        }

        fetch('/api/chromecast/control', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(body)
        })
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                console.error('Cast control error:', data.error);
            }
        })
        .catch(error => {
            console.error('Cast control error:', error);
        });
    }

    function downloadFile(file) {
        // Create a download link and trigger it
        const downloadUrl = `/api/files/download/${encodeURIComponent(file.path)}`;
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = file.name;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showNotification(`Downloading "${file.name}"...`, 'info');
    }

    function deleteFile(file) {
        if (!confirm(`Are you sure you want to delete "${file.name}"?`)) {
            return;
        }

        fetch('/api/files/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                path: file.path
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('File deleted successfully', 'success');
                loadFiles(); // Refresh the file list
            } else {
                showNotification(data.error || 'Failed to delete file', 'error');
            }
        })
        .catch(error => {
            console.error('Delete error:', error);
            showNotification('Failed to delete file', 'error');
        });
    }

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