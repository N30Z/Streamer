// AnyLoader Web Interface JavaScript

document.addEventListener('DOMContentLoaded', function() {
    console.log('AnyLoader Web Interface loaded');

    // Get UI elements
    const versionDisplay = document.getElementById('version-display');
    const navTitle = document.getElementById('nav-title');
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    const resultsSection = document.getElementById('results-section');
    const resultsContainer = document.getElementById('results-container');
    const loadingSection = document.getElementById('loading-section');
    const emptyState = document.getElementById('empty-state');
    const homeContent = document.getElementById('home-content');
    const localFiles = document.getElementById('local-files');
    const subscriptionsPanel = document.getElementById('subscriptions-panel');
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
    let selectionMode = null; // 'local' | 'online' | null
    let currentDescription = '';
    let modalWatchProgress = {}; // watch progress for episodes in download modal
    let progressPollInterval = null;

    // Description section elements
    const descriptionSection = document.getElementById('description-section');
    const descriptionToggle = document.getElementById('description-toggle');
    const descriptionContent = document.getElementById('description-content');
    const descriptionText = document.getElementById('description-text');
    const episodeSelection = document.getElementById('episode-selection');

    // Language flag image mapping (all sites)
    const LANGUAGE_FLAGS = {
        "German Dub": "https://aniworld.to/public/img/german.svg",
        "Deutsch": "https://aniworld.to/public/img/german.svg",
        "English Sub": "https://aniworld.to/public/img/japanese-english.svg",
        "German Sub": "https://aniworld.to/public/img/japanese-german.svg",
        "English Dub": "https://upload.wikimedia.org/wikipedia/commons/0/0b/English_language.svg",
        "English": "https://upload.wikimedia.org/wikipedia/commons/0/0b/English_language.svg",
    };

    // Track which queue groups are expanded (persists across poll updates)
    let expandedGroups = new Set();
    let queueGroupsInitialized = false;

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

    // Load "Continue Watching" section (defined in IIFE, exported to window)
    if (window.loadContinueWatching) window.loadContinueWatching();

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

    // Update modal close handlers
    const updateModal = document.getElementById('update-modal');
    const closeUpdateModal = document.getElementById('close-update-modal');
    const closeUpdateModalBtn = document.getElementById('close-update-modal-btn');
    const _hideUpdateModal = () => { if (updateModal) updateModal.style.display = 'none'; };
    if (closeUpdateModal) closeUpdateModal.addEventListener('click', _hideUpdateModal);
    if (closeUpdateModalBtn) closeUpdateModalBtn.addEventListener('click', _hideUpdateModal);
    if (updateModal) updateModal.addEventListener('click', e => { if (e.target === updateModal) _hideUpdateModal(); });

    // Provider refresh buttons
    const refreshAniworldBtn = document.getElementById('refresh-aniworld');
    const refreshStoBtn = document.getElementById('refresh-sto');
    const refreshMovie4kBtn = document.getElementById('refresh-movie4k');
    if (refreshAniworldBtn) refreshAniworldBtn.addEventListener('click', () => loadProviderAniworld(true));
    if (refreshStoBtn) refreshStoBtn.addEventListener('click', () => loadProviderSto(true));
    if (refreshMovie4kBtn) refreshMovie4kBtn.addEventListener('click', () => loadProviderMovie4k(true));

    // Navbar title click functionality
    if (navTitle) {
        navTitle.addEventListener('click', function() {
            // Clear search input
            if (searchInput) {
                searchInput.value = '';
            }
            if (localshown) {
                localshown = false;
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
                if (versionDisplay) versionDisplay.textContent = `v${data.version}`;
                if (!data.is_newest && data.latest_version) {
                    const curEl = document.getElementById('update-current-version');
                    const newEl = document.getElementById('update-latest-version');
                    if (curEl) curEl.textContent = `v${data.version}`;
                    if (newEl) newEl.textContent = `v${data.latest_version}`;
                    if (updateModal) updateModal.style.display = 'flex';
                }
            })
            .catch(error => {
                console.error('Failed to load version info:', error);
                if (versionDisplay) versionDisplay.textContent = 'v?.?.?';
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
        // Provider is now auto-detected on backend - no UI needed
    }

    function populateLanguageDropdown(site, languages) {
        if (!languageSelect) {
            console.error('Language select element not found!');
            return;
        }

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
            if (site === 'movie4k.sx') {
                defaultLanguage = 'Deutsch';
            } else if (site === 's.to') {
                defaultLanguage = 'German Dub';
            } else {
                defaultLanguage = 'German Sub';
            }
        }

        // Determine which language to select
        let selectedLang = userPreferences.default_language || '';
        if (!selectedLang || !availableLanguages.includes(selectedLang)) {
            selectedLang = defaultLanguage && availableLanguages.includes(defaultLanguage) ? defaultLanguage : availableLanguages[0] || '';
        }

        // Create flag image buttons instead of dropdown options
        availableLanguages.forEach(lang => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'language-btn' + (lang === selectedLang ? ' active' : '');
            btn.dataset.language = lang;
            btn.title = lang;
            const flagUrl = LANGUAGE_FLAGS[lang] || '';
            if (flagUrl) {
                btn.innerHTML = `<img src="${flagUrl}" alt="${lang}" height="30">`;
            } else {
                btn.textContent = lang;
            }
            btn.addEventListener('click', () => {
                languageSelect.querySelectorAll('.language-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
            languageSelect.appendChild(btn);
        });
    }

    function getSelectedLanguage() {
        const activeBtn = languageSelect ? languageSelect.querySelector('.language-btn.active') : null;
        return activeBtn ? activeBtn.dataset.language : '';
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

    function showDownloadModal(animeTitle, episodeTitle, episodeUrl, coverUrl, folderPath) {
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
            cover: coverUrl || '',
            folderPath: folderPath || '',
            downloadPath: '/Downloads'
        };

        // Reset selection state
        selectedEpisodes.clear();
        selectionMode = null;
        availableEpisodes = {};
        currentDescription = '';

        // Populate modal
        document.getElementById('download-anime-title').textContent = animeTitle;

        // Show cover image if available
        const coverContainer = document.getElementById('download-cover');
        const coverImg = document.getElementById('download-cover-img');
        if (coverUrl && coverContainer && coverImg) {
            // Normalize relative remote URLs to absolute
            if (coverUrl && !coverUrl.startsWith('http') && !coverUrl.startsWith('/api/')) {
                if (coverUrl.startsWith('//')) {
                    coverUrl = 'https:' + coverUrl;
                } else if (coverUrl.startsWith('/')) {
                    let baseUrl = 'https://aniworld.to';
                    if (detectedSite === 's.to') baseUrl = 'https://s.to';
                    else if (detectedSite === 'movie4k.sx') baseUrl = 'https://movie4k.sx';
                    coverUrl = baseUrl + coverUrl;
                }
            }
            coverImg.src = coverUrl;
            coverContainer.style.display = 'block';
        } else if (coverContainer) {
            coverContainer.style.display = 'none';
        }

        // Reset language buttons
        if (languageSelect) {
            languageSelect.innerHTML = '';
        }

        // Reset description section
        if (descriptionSection) descriptionSection.style.display = 'none';
        if (descriptionContent) descriptionContent.style.display = 'none';
        if (descriptionToggle) {
            descriptionToggle.classList.remove('expanded');
            const icon = descriptionToggle.querySelector('i');
            if (icon) icon.className = 'fas fa-chevron-down';
        }

        // Reset episode selection visibility
        if (episodeSelection) episodeSelection.style.display = '';

        // Reset action button
        confirmDownload.textContent = 'Start Download';
        confirmDownload.className = 'primary-btn';
        confirmDownload.disabled = true;

        // Show loading state for episodes
        episodeTreeLoading.style.display = 'flex';
        episodeTree.style.display = 'none';
        updateSelectedCount();

        // Fetch download path from backend
        fetch('/api/download-path')
            .then(response => response.json())
            .then(data => {
                currentDownloadData.downloadPath = data.path;
                const pathEl = document.getElementById('download-path');
                if (pathEl) pathEl.textContent = data.path;
            })
            .catch(error => {
                console.error('Failed to fetch download path:', error);
            });

        // Build request body
        const reqBody = { series_url: episodeUrl };
        if (folderPath) {
            reqBody.folder_path = folderPath;
        }

        // Fetch episodes and watch progress in parallel
        Promise.all([
            fetch('/api/episodes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(reqBody)
            }).then(r => r.json()),
            fetch('/api/watch-progress').then(r => r.json()).catch(() => ({ success: false }))
        ])
        .then(([data, progressData]) => {
            modalWatchProgress = progressData.success ? (progressData.progress || {}) : {};
            if (data.success) {
                availableEpisodes = data.episodes;
                availableMovies = data.movies || [];
                currentDescription = data.description || '';
                renderEpisodeTree();

                // Start polling watch progress while modal is open
                if (progressPollInterval) clearInterval(progressPollInterval);
                progressPollInterval = setInterval(refreshModalProgress, 10000);

                // Populate language buttons
                populateLanguageDropdown(
                    currentDownloadData.site,
                    data.available_languages || []
                );

                // Show description
                if (currentDescription && descriptionSection && descriptionText) {
                    descriptionText.textContent = currentDescription;
                    descriptionSection.style.display = 'block';

                    // For single movies, show description expanded and hide episode tree
                    const isSingleMovie = Object.keys(availableEpisodes).length === 0
                        && availableMovies && availableMovies.length <= 1;
                    if (isSingleMovie) {
                        if (episodeSelection) episodeSelection.style.display = 'none';
                        if (descriptionContent) descriptionContent.style.display = 'block';
                        if (descriptionToggle) {
                            descriptionToggle.classList.add('expanded');
                            const icon = descriptionToggle.querySelector('i');
                            if (icon) icon.className = 'fas fa-chevron-up';
                        }
                        // Auto-select the single movie
                        if (availableMovies.length === 1) {
                            toggleMovie(availableMovies[0], true);
                        }
                    }
                }
            } else {
                showNotification(data.error || 'Failed to load episodes', 'error');
                populateLanguageDropdown(currentDownloadData.site);
            }
        })
        .catch(error => {
            console.error('Failed to fetch episodes:', error);
            showNotification('Failed to load episodes', 'error');
            populateLanguageDropdown(currentDownloadData.site);
        })
        .finally(() => {
            episodeTreeLoading.style.display = 'none';
            episodeTree.style.display = 'block';
        });

        // Setup description toggle handler (remove old listeners by replacing)
        const currentToggle = document.getElementById('description-toggle');
        if (currentToggle && currentToggle.parentNode) {
            const newToggle = currentToggle.cloneNode(true);
            currentToggle.parentNode.replaceChild(newToggle, currentToggle);
            newToggle.addEventListener('click', () => {
                const content = document.getElementById('description-content');
                if (!content) return;
                const isVisible = content.style.display !== 'none';
                content.style.display = isVisible ? 'none' : 'block';
                newToggle.classList.toggle('expanded', !isVisible);
                const icon = newToggle.querySelector('i');
                if (icon) icon.className = isVisible ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
            });
        }

        downloadModal.style.display = 'flex';

        // Show subscribe button for series (not for single movies), and check subscription status
        const subscribeBtn = document.getElementById('subscribe-btn');
        const subscriptionOptions = document.getElementById('subscription-options');
        const isMovie = currentDownloadData.site === 'movie4k.sx';

        if (subscribeBtn && !isMovie) {
            subscribeBtn.style.display = 'inline-flex';
            subscribeBtn.classList.remove('is-subscribed');
            subscribeBtn.innerHTML = '<i class="fas fa-star"></i> Subscribe';
            if (subscriptionOptions) subscriptionOptions.style.display = 'none';

            // Check if already subscribed
            fetch('/api/subscriptions/check-url', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ series_url: episodeUrl })
            })
            .then(r => r.json())
            .then(d => {
                if (d.success && d.subscribed && d.subscription) {
                    subscribeBtn.classList.add('is-subscribed');
                    subscribeBtn.innerHTML = '<i class="fas fa-star"></i> Subscribed';
                    // Pre-fill options from existing sub
                    const notifyCheck = document.getElementById('sub-opt-notify');
                    const autoCheck = document.getElementById('sub-opt-auto-download');
                    if (notifyCheck) notifyCheck.checked = d.subscription.notify;
                    if (autoCheck) autoCheck.checked = d.subscription.auto_download;
                }
            })
            .catch(() => {});
        } else if (subscribeBtn) {
            subscribeBtn.style.display = 'none';
            if (subscriptionOptions) subscriptionOptions.style.display = 'none';
        }
    }

    // Subscribe button toggle logic
    const subscribeBtn = document.getElementById('subscribe-btn');
    const subOptNotify = document.getElementById('sub-opt-notify');
    const subOptAutoDownload = document.getElementById('sub-opt-auto-download');
    const subConfirmBtn = document.getElementById('sub-confirm-btn');
    const subUnsubscribeBtn = document.getElementById('sub-unsubscribe-btn');
    const subCancelBtn = document.getElementById('sub-cancel-btn');
    const subscriptionOptionsPanel = document.getElementById('subscription-options');

    if (subscribeBtn) {
        subscribeBtn.addEventListener('click', () => {
            if (!subscriptionOptionsPanel) return;
            const isVisible = subscriptionOptionsPanel.style.display !== 'none';
            subscriptionOptionsPanel.style.display = isVisible ? 'none' : 'block';
            // Show/hide unsubscribe button based on subscription status
            if (subUnsubscribeBtn) {
                subUnsubscribeBtn.style.display = subscribeBtn.classList.contains('is-subscribed') ? 'inline-flex' : 'none';
            }
        });
    }

    if (subCancelBtn) {
        subCancelBtn.addEventListener('click', () => {
            if (subscriptionOptionsPanel) subscriptionOptionsPanel.style.display = 'none';
        });
    }

    if (subConfirmBtn) {
        subConfirmBtn.addEventListener('click', () => {
            if (!currentDownloadData) return;
            const notify = subOptNotify ? subOptNotify.checked : true;
            const autoDownload = subOptAutoDownload ? subOptAutoDownload.checked : false;
            const isCurrentlySubscribed = subscribeBtn && subscribeBtn.classList.contains('is-subscribed');

            if (isCurrentlySubscribed) {
                // Update existing subscription
                fetch('/api/subscriptions/check-url', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ series_url: currentDownloadData.url })
                })
                .then(r => r.json())
                .then(d => {
                    if (d.success && d.subscription) {
                        return fetch(`/api/subscriptions/${d.subscription.id}`, {
                            method: 'PUT',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ notify, auto_download: autoDownload })
                        });
                    }
                })
                .then(r => r ? r.json() : null)
                .then(d => {
                    if (d && d.success) {
                        showNotification('Subscription updated', 'success');
                        if (subscriptionOptionsPanel) subscriptionOptionsPanel.style.display = 'none';
                    }
                })
                .catch(() => showNotification('Failed to update subscription', 'error'));
            } else {
                // New subscription
                const coverUrl = currentDownloadData.cover || '';
                fetch('/api/subscriptions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        series_url: currentDownloadData.url,
                        title: currentDownloadData.anime,
                        cover: coverUrl,
                        site: currentDownloadData.site,
                        language: getSelectedLanguage() || currentDownloadData.language || '',
                        notify,
                        auto_download: autoDownload
                    })
                })
                .then(r => r.json())
                .then(d => {
                    if (d.success) {
                        showNotification(`Subscribed to ${currentDownloadData.anime}`, 'success');
                        if (subscribeBtn) {
                            subscribeBtn.classList.add('is-subscribed');
                            subscribeBtn.innerHTML = '<i class="fas fa-star"></i> Subscribed';
                        }
                        if (subscriptionOptionsPanel) subscriptionOptionsPanel.style.display = 'none';
                    } else {
                        showNotification(d.error || 'Failed to subscribe', 'error');
                    }
                })
                .catch(() => showNotification('Failed to subscribe', 'error'));
            }
        });
    }

    if (subUnsubscribeBtn) {
        subUnsubscribeBtn.addEventListener('click', () => {
            if (!currentDownloadData) return;
            fetch('/api/subscriptions/check-url', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ series_url: currentDownloadData.url })
            })
            .then(r => r.json())
            .then(d => {
                if (d.success && d.subscription) {
                    return fetch(`/api/subscriptions/${d.subscription.id}`, { method: 'DELETE' });
                }
            })
            .then(r => r ? r.json() : null)
            .then(d => {
                if (d && d.success) {
                    showNotification('Unsubscribed', 'success');
                    if (subscribeBtn) {
                        subscribeBtn.classList.remove('is-subscribed');
                        subscribeBtn.innerHTML = '<i class="fas fa-star"></i> Subscribe';
                    }
                    if (subscriptionOptionsPanel) subscriptionOptionsPanel.style.display = 'none';
                }
            })
            .catch(() => showNotification('Failed to unsubscribe', 'error'));
        });
    }

    function refreshModalProgress() {
        if (!downloadModal || downloadModal.style.display === 'none') return;
        fetch('/api/watch-progress')
            .then(r => r.json())
            .then(data => {
                if (!data.success) return;
                modalWatchProgress = data.progress || {};
                episodeTree.querySelectorAll('tr[data-local-path]').forEach(tr => {
                    const localPath = tr.dataset.localPath;
                    const prog = modalWatchProgress[localPath] || null;
                    if (!prog) return; // No data for this path — preserve existing UI

                    const pct = prog.percentage || 0;
                    const titleCell = tr.querySelector('.episode-title-cell');
                    const playBtn = tr.querySelector('.episode-play-btn');
                    if (!titleCell || !playBtn) return;

                    // Update progress/watched badge in-place
                    titleCell.querySelectorAll('.ep-progress-inline, .ep-watched-badge').forEach(el => el.remove());
                    if (pct > 95) {
                        titleCell.insertAdjacentHTML('beforeend', `<span class="ep-watched-badge" title="Watched"><i class="fas fa-check"></i></span>`);
                        playBtn.className = 'episode-play-btn';
                        playBtn.title = 'Watched - Play again';
                        playBtn.innerHTML = '<i class="fas fa-play"></i>';
                    } else if (pct > 5) {
                        titleCell.insertAdjacentHTML('beforeend', `<span class="ep-progress-inline" title="${Math.round(pct)}% watched"><span class="ep-progress-bar"><span class="ep-progress-fill" style="width:${Math.round(pct)}%"></span></span></span>`);
                        playBtn.className = 'episode-play-btn episode-resume-btn';
                        playBtn.title = `Resume from ${Math.round(pct)}%`;
                        playBtn.innerHTML = '<i class="fas fa-redo"></i>';
                    } else {
                        playBtn.className = 'episode-play-btn';
                        playBtn.title = 'Play';
                        playBtn.innerHTML = '<i class="fas fa-play"></i>';
                    }
                });
            })
            .catch(() => {});
    }

    function hideDownloadModal() {
        downloadModal.style.display = 'none';
        if (progressPollInterval) { clearInterval(progressPollInterval); progressPollInterval = null; }
        currentDownloadData = null;
        selectedEpisodes.clear();
        selectionMode = null;
        availableEpisodes = {};
        availableMovies = [];
        currentDescription = '';
        // Reset subscription options
        if (subscriptionOptionsPanel) subscriptionOptionsPanel.style.display = 'none';
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
                            <th style="width:40px"></th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            `;

            const tbody = container.querySelector('tbody');
            const seasonCheckbox = container.querySelector(`#season-${seasonNum}`);

            season.forEach(episode => {
                const episodeId = `${episode.season}-${episode.episode}`;
                const isLocal = episode.local || false;
                const tr = document.createElement('tr');
                tr.className = 'episode-row' + (isLocal ? ' local-episode' : '');
                if (isLocal && episode.local_path) tr.dataset.localPath = episode.local_path;

                // Watch progress for this episode (by local_path)
                const epProgress = (isLocal && episode.local_path) ? (modalWatchProgress[episode.local_path] || null) : null;
                const epPct = epProgress ? (epProgress.percentage || 0) : 0;

                let localBadge = '';
                let playBtn = '';
                let progressHtml = '';
                if (isLocal) {
                    localBadge = ' <span class="episode-local-badge"><i class="fas fa-check-circle"></i></span>';
                    if (epPct > 95) {
                        playBtn = `<button class="episode-play-btn" title="Watched - Play again"><i class="fas fa-play"></i></button>`;
                        progressHtml = `<span class="ep-watched-badge" title="Watched"><i class="fas fa-check"></i></span>`;
                    } else if (epPct > 5) {
                        playBtn = `<button class="episode-play-btn episode-resume-btn" title="Resume from ${Math.round(epPct)}%"><i class="fas fa-redo"></i></button>`;
                        progressHtml = `<span class="ep-progress-inline" title="${Math.round(epPct)}% watched">
                            <span class="ep-progress-bar"><span class="ep-progress-fill" style="width:${Math.round(epPct)}%"></span></span>
                        </span>`;
                    } else {
                        playBtn = `<button class="episode-play-btn" title="Play"><i class="fas fa-play"></i></button>`;
                    }
                }

                tr.innerHTML = `
                    <td class="episode-checkbox-cell">
                        <input type="checkbox" class="episode-checkbox" id="episode-${episodeId}" data-local="${isLocal}" ${selectedEpisodes.has(episodeId) ? 'checked' : ''}>
                    </td>
                    <td class="episode-number-cell">${episode.episode}</td>
                    <td class="episode-title-cell">${escapeHtml(episode.title)}${localBadge}${progressHtml}</td>
                    <td>${playBtn}</td>
                `;

                const checkbox = tr.querySelector('.episode-checkbox');
                checkbox.addEventListener('change', () => {
                    if (!canSelectEpisode(isLocal, checkbox.checked)) {
                        checkbox.checked = false;
                        return;
                    }
                    toggleEpisode(episode, checkbox.checked);
                    updateHeaderCheckbox(seasonNum, seasonCheckbox);
                    updateCheckboxDimming();
                });

                tr.addEventListener('click', (e) => {
                    if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON' || e.target.closest('.episode-play-btn')) return;
                    if (!canSelectEpisode(isLocal, !checkbox.checked)) return;
                    checkbox.checked = !checkbox.checked;
                    toggleEpisode(episode, checkbox.checked);
                    updateHeaderCheckbox(seasonNum, seasonCheckbox);
                    updateCheckboxDimming();
                });

                // Play/resume button for local episodes
                const playButton = tr.querySelector('.episode-play-btn');
                if (playButton && isLocal && episode.local_path) {
                    playButton.addEventListener('click', (e) => {
                        e.stopPropagation();
                        // Always read live progress so resume position is current
                        const liveProg = modalWatchProgress[episode.local_path] || null;
                        const livePct = liveProg ? (liveProg.percentage || 0) : 0;
                        const startTime = (livePct > 5 && livePct < 95 && liveProg) ? liveProg.current_time : 0;
                        window.streamFile({ path: episode.local_path, name: episode.title }, startTime);
                    });
                }

                tbody.appendChild(tr);
            });

            updateHeaderCheckbox(seasonNum, seasonCheckbox);
            seasonCheckbox.addEventListener('change', () => {
                const isChecked = seasonCheckbox.checked;
                season.forEach(episode => {
                    const episodeId = `${episode.season}-${episode.episode}`;
                    const isLocal = episode.local || false;
                    const cb = container.querySelector(`#episode-${episodeId}`);
                    if (cb) {
                        if (canSelectEpisode(isLocal, isChecked)) {
                            cb.checked = isChecked;
                            toggleEpisode(episode, isChecked);
                        }
                    }
                });
                updateCheckboxDimming();
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
                            <th style="width:40px"></th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            `;

            const tbody = container.querySelector('tbody');
            const moviesCheckbox = container.querySelector('#movies-section');

            availableMovies.forEach((movie, index) => {
                const movieId = `movie-${movie.movie}`;
                const isLocal = movie.local || false;
                const tr = document.createElement('tr');
                tr.className = 'episode-row' + (isLocal ? ' local-episode' : '');
                if (isLocal && movie.local_path) tr.dataset.localPath = movie.local_path;

                // Watch progress for this movie
                const mvProgress = (isLocal && movie.local_path) ? (modalWatchProgress[movie.local_path] || null) : null;
                const mvPct = mvProgress ? (mvProgress.percentage || 0) : 0;

                let localBadge = '';
                let playBtn = '';
                let progressHtml = '';
                if (isLocal) {
                    localBadge = ' <span class="episode-local-badge"><i class="fas fa-check-circle"></i></span>';
                    if (mvPct > 95) {
                        playBtn = `<button class="episode-play-btn" title="Watched - Play again"><i class="fas fa-play"></i></button>`;
                    } else if (mvPct > 5) {
                        playBtn = `<button class="episode-play-btn episode-resume-btn" title="Resume from ${Math.round(mvPct)}%"><i class="fas fa-redo"></i></button>`;
                        progressHtml = `<span class="ep-progress-inline" title="${Math.round(mvPct)}% watched">
                            <span class="ep-progress-bar"><span class="ep-progress-fill" style="width:${Math.round(mvPct)}%"></span></span>
                        </span>`;
                    } else {
                        playBtn = `<button class="episode-play-btn" title="Play"><i class="fas fa-play"></i></button>`;
                    }
                }

                tr.innerHTML = `
                    <td class="episode-checkbox-cell">
                        <input type="checkbox" class="episode-checkbox" id="movie-${movieId}" data-local="${isLocal}" ${selectedEpisodes.has(movieId) ? 'checked' : ''}>
                    </td>
                    <td class="episode-number-cell">${index + 1}</td>
                    <td class="episode-title-cell">${escapeHtml(movie.title)}${localBadge}${progressHtml}</td>
                    <td>${playBtn}</td>
                `;

                const checkbox = tr.querySelector('.episode-checkbox');
                checkbox.addEventListener('change', () => {
                    if (!canSelectEpisode(isLocal, checkbox.checked)) {
                        checkbox.checked = false;
                        return;
                    }
                    toggleMovie(movie, checkbox.checked);
                    updateMoviesHeader(moviesCheckbox);
                    updateCheckboxDimming();
                });

                tr.addEventListener('click', (e) => {
                    if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON' || e.target.closest('.episode-play-btn')) return;
                    if (!canSelectEpisode(isLocal, !checkbox.checked)) return;
                    checkbox.checked = !checkbox.checked;
                    toggleMovie(movie, checkbox.checked);
                    updateMoviesHeader(moviesCheckbox);
                    updateCheckboxDimming();
                });

                // Play/resume button for local movies
                const playButton = tr.querySelector('.episode-play-btn');
                if (playButton && isLocal && movie.local_path) {
                    playButton.addEventListener('click', (e) => {
                        e.stopPropagation();
                        const liveProg = modalWatchProgress[movie.local_path] || null;
                        const livePct = liveProg ? (liveProg.percentage || 0) : 0;
                        const startTime = (livePct > 5 && livePct < 95 && liveProg) ? liveProg.current_time : 0;
                        window.streamFile({ path: movie.local_path, name: movie.title }, startTime);
                    });
                }

                tbody.appendChild(tr);
            });

            updateMoviesHeader(moviesCheckbox);
            moviesCheckbox.addEventListener('change', () => {
                const isChecked = moviesCheckbox.checked;
                availableMovies.forEach(movie => {
                    const movieId = `movie-${movie.movie}`;
                    const isLocal = movie.local || false;
                    const cb = container.querySelector(`#movie-${movieId}`);
                    if (cb) {
                        if (canSelectEpisode(isLocal, isChecked)) {
                            cb.checked = isChecked;
                            toggleMovie(movie, isChecked);
                        }
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
        updateSelectionMode();
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
        updateSelectionMode();
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

    // Selection mode logic: local episodes → delete mode, online → download mode
    function canSelectEpisode(isLocal, wantChecked) {
        if (!wantChecked) return true; // Always allow unchecking
        if (selectionMode === null) return true; // No mode set yet
        if (isLocal && selectionMode === 'local') return true;
        if (!isLocal && selectionMode === 'online') return true;
        return false; // Mismatched mode
    }

    function updateSelectionMode() {
        if (selectedEpisodes.size === 0) {
            selectionMode = null;
            updateActionButton();
            updateCheckboxDimming();
            return;
        }
        // Determine mode from first selected item
        // Check all episodes and movies for a local match
        let hasLocal = false;
        selectedEpisodes.forEach(key => {
            if (key.startsWith('movie-')) {
                const movie = availableMovies.find(m => `movie-${m.movie}` === key);
                if (movie && movie.local) hasLocal = true;
            } else {
                const [s, e] = key.split('-').map(Number);
                const season = availableEpisodes[s];
                if (season) {
                    const ep = season.find(ep => ep.season === s && ep.episode === e);
                    if (ep && ep.local) hasLocal = true;
                }
            }
        });
        selectionMode = hasLocal ? 'local' : 'online';
        updateActionButton();
        updateCheckboxDimming();
    }

    function updateActionButton() {
        if (selectionMode === 'local') {
            confirmDownload.textContent = 'Delete Selected';
            confirmDownload.className = 'primary-btn danger-btn';
        } else {
            confirmDownload.textContent = 'Start Download';
            confirmDownload.className = 'primary-btn';
        }
    }

    function updateCheckboxDimming() {
        const allCheckboxCells = document.querySelectorAll('#episode-tree .episode-checkbox-cell');
        allCheckboxCells.forEach(cell => {
            const cb = cell.querySelector('.episode-checkbox');
            if (!cb) return;
            const isLocal = cb.dataset.local === 'true';
            if (selectionMode === null || (isLocal && selectionMode === 'local') || (!isLocal && selectionMode === 'online')) {
                cell.classList.remove('dimmed');
            } else {
                cell.classList.add('dimmed');
            }
        });
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
            showNotification('Please select at least one episode or movie', 'error');
            return;
        }

        // DELETE MODE: handle local file deletion
        if (selectionMode === 'local') {
            if (!confirm(`Delete ${selectedEpisodes.size} selected file(s)?`)) return;

            confirmDownload.disabled = true;
            confirmDownload.textContent = 'Deleting...';

            // Collect local file paths from selected episodes/movies
            const localPaths = [];
            selectedEpisodes.forEach(key => {
                if (key.startsWith('movie-')) {
                    const movieNum = key.split('-')[1];
                    const movie = availableMovies.find(m => m.movie == movieNum);
                    if (movie && movie.local_path) localPaths.push(movie.local_path);
                } else {
                    const [s, e] = key.split('-').map(Number);
                    const ep = availableEpisodes[s]?.find(ep => ep.season === s && ep.episode === e);
                    if (ep && ep.local_path) localPaths.push(ep.local_path);
                }
            });

            const deletions = localPaths.map(path =>
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
                    // Re-open modal to refresh state
                    const d = currentDownloadData;
                    hideDownloadModal();
                    showDownloadModal(d.anime, d.episode, d.url, d.cover, d.folderPath);
                })
                .catch(error => {
                    console.error('Delete error:', error);
                    showNotification('Failed to delete some files', 'error');
                })
                .finally(() => {
                    confirmDownload.disabled = false;
                    confirmDownload.textContent = 'Delete Selected';
                });
            return;
        }

        // DOWNLOAD MODE
        confirmDownload.disabled = true;
        confirmDownload.textContent = 'Starting...';

        // Collect selected episode and movie URLs
        const selectedEpisodeUrls = [];
        selectedEpisodes.forEach(episodeKey => {
            if (episodeKey.startsWith('movie-')) {
                const movieNum = episodeKey.split('-')[1];
                const movieData = availableMovies.find(movie => movie.movie == movieNum);
                if (movieData) {
                    selectedEpisodeUrls.push(movieData.url);
                }
            } else {
                const [season, episode] = episodeKey.split('-').map(Number);
                const episodeData = availableEpisodes[season]?.find(ep => ep.season === season && ep.episode === episode);
                if (episodeData) {
                    selectedEpisodeUrls.push(episodeData.url);
                }
            }
        });

        // Get language from flag buttons
        const selectedLanguage = getSelectedLanguage() || (currentDownloadData.site === 's.to' ? 'German Dub' : 'German Sub');

        const requestPayload = {
            episode_urls: selectedEpisodeUrls,
            language: selectedLanguage,
            provider: 'auto',
            anime_title: currentDownloadData.anime,
            cover: currentDownloadData.cover || ''
        };

        fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestPayload)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
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
        if (subscriptionsPanel) subscriptionsPanel.style.display = 'none';
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
        if (subscriptionsPanel) subscriptionsPanel.style.display = 'none';
        emptyState.style.display = 'none';
        loadingSection.style.display = 'none';
        resultsSection.style.display = 'block';
    }

    function showEmptyState() {
        homeContent.style.display = 'none';
        localFiles.style.display = 'none';
        if (subscriptionsPanel) subscriptionsPanel.style.display = 'none';
        resultsSection.style.display = 'none';
        loadingSection.style.display = 'none';
        emptyState.style.display = 'block';
    }

    function showHomeContent() {
        resultsSection.style.display = 'none';
        localFiles.style.display = 'none';
        if (subscriptionsPanel) subscriptionsPanel.style.display = 'none';
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
        if (subscriptionsPanel) subscriptionsPanel.style.display = 'none';
        localFiles.style.display = 'block';
    }

    function showSubscriptionsPanel() {
        homeContent.style.display = 'none';
        resultsSection.style.display = 'none';
        loadingSection.style.display = 'none';
        emptyState.style.display = 'none';
        localFiles.style.display = 'none';
        if (subscriptionsPanel) subscriptionsPanel.style.display = 'block';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function groupItemsByTitle(items) {
        const groups = {};
        const order = [];
        items.forEach(item => {
            const title = item.anime_title;
            if (!groups[title]) {
                groups[title] = [];
                order.push(title);
            }
            groups[title].push(item);
        });
        return order.map(title => ({
            title: title,
            items: groups[title],
            isSingle: groups[title].length === 1
        }));
    }

    function computeGroupStats(groupItems) {
        const totalEpisodes = groupItems.length;
        const completedEpisodes = groupItems.filter(i => i.status === 'completed').length;
        const failedEpisodes = groupItems.filter(i => i.status === 'failed' || i.status === 'cancelled').length;
        const downloadingItems = groupItems.filter(i => i.status === 'downloading');
        const queuedItems = groupItems.filter(i => i.status === 'queued');

        let totalProgress = 0;
        groupItems.forEach(item => {
            if (item.status === 'completed') {
                totalProgress += 100;
            } else if (item.status === 'downloading') {
                totalProgress += (item.current_episode_progress || 0);
            }
        });
        const aggregateProgress = totalEpisodes > 0 ? totalProgress / totalEpisodes : 0;

        let groupStatus;
        if (downloadingItems.length > 0) {
            groupStatus = 'downloading';
        } else if (queuedItems.length > 0) {
            groupStatus = 'queued';
        } else if (completedEpisodes === totalEpisodes) {
            groupStatus = 'completed';
        } else if (failedEpisodes > 0) {
            groupStatus = 'failed';
        } else {
            groupStatus = 'queued';
        }

        return { totalEpisodes, completedEpisodes, aggregateProgress, groupStatus };
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

                    // Clean up expandedGroups for titles no longer in the queue
                    const currentTitles = new Set([
                        ...activeItems.map(i => i.anime_title),
                        ...completedItems.map(i => i.anime_title)
                    ]);
                    expandedGroups.forEach(title => {
                        if (!currentTitles.has(title)) {
                            expandedGroups.delete(title);
                        }
                    });
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
        const groups = groupItemsByTitle(items);

        // Auto-expand all groups on first render
        if (!queueGroupsInitialized && groups.some(g => !g.isSingle)) {
            groups.forEach(g => {
                if (!g.isSingle) expandedGroups.add(g.title);
            });
            queueGroupsInitialized = true;
        }

        groups.forEach(group => {
            if (group.isSingle) {
                container.appendChild(renderSingleQueueItem(group.items[0]));
            } else {
                container.appendChild(renderQueueGroup(group));
            }
        });
    }

    function renderSingleQueueItem(item) {
        const queueItem = document.createElement('div');
        queueItem.className = 'queue-item';

        const overallProgress = item.progress_percentage || 0;
        const episodeProgress = item.current_episode_progress || 0;
        const showProgressBar = item.status === 'downloading' || item.status === 'queued';
        const isDownloading = item.status === 'downloading';
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

        return queueItem;
    }

    function renderQueueGroup(group) {
        const stats = computeGroupStats(group.items);
        const isExpanded = expandedGroups.has(group.title);
        const progressClamped = Math.max(0, Math.min(100, stats.aggregateProgress));
        const showProgressBar = stats.groupStatus === 'downloading' || stats.groupStatus === 'queued';
        const canCancelAll = group.items.some(i => i.status === 'downloading' || i.status === 'queued');

        const sortedItems = [...group.items].sort((a, b) => (a.episode_number || 0) - (b.episode_number || 0));

        const groupEl = document.createElement('div');
        groupEl.className = 'queue-group' + (isExpanded ? ' expanded' : '');

        groupEl.innerHTML = `
            <div class="queue-group-header">
                <div class="queue-group-header-left">
                    <i class="fas fa-chevron-right queue-group-chevron"></i>
                    <div class="queue-group-title">${escapeHtml(group.title)}</div>
                </div>
                <div class="queue-group-header-right">
                    <span class="queue-group-count">${stats.completedEpisodes}/${stats.totalEpisodes} episodes</span>
                    ${canCancelAll ? `<button class="queue-cancel-btn queue-group-cancel-btn" title="Cancel all episodes"><i class="fas fa-times"></i></button>` : ''}
                    <div class="queue-item-status ${stats.groupStatus}">${stats.groupStatus}</div>
                </div>
            </div>
            ${showProgressBar ? `
            <div class="queue-group-progress">
                <div class="queue-progress-bar">
                    <div class="queue-progress-fill" style="width: ${progressClamped}%; transition: width 0.3s ease;"></div>
                </div>
                <div class="queue-progress-text">${progressClamped.toFixed(1)}%</div>
            </div>
            ` : ''}
            <div class="queue-group-children" style="display: ${isExpanded ? 'block' : 'none'};"></div>
        `;

        const childrenContainer = groupEl.querySelector('.queue-group-children');
        sortedItems.forEach(item => {
            childrenContainer.appendChild(renderGroupChildItem(item));
        });

        // Expand/collapse toggle
        const header = groupEl.querySelector('.queue-group-header');
        header.addEventListener('click', (e) => {
            if (e.target.closest('.queue-cancel-btn')) return;
            if (expandedGroups.has(group.title)) {
                expandedGroups.delete(group.title);
            } else {
                expandedGroups.add(group.title);
            }
            const children = groupEl.querySelector('.queue-group-children');
            const isNowExpanded = expandedGroups.has(group.title);
            children.style.display = isNowExpanded ? 'block' : 'none';
            groupEl.classList.toggle('expanded', isNowExpanded);
        });

        // Cancel-all handler
        const cancelAllBtn = groupEl.querySelector('.queue-group-cancel-btn');
        if (cancelAllBtn) {
            cancelAllBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const cancellable = group.items.filter(i => i.status === 'downloading' || i.status === 'queued');
                Promise.all(cancellable.map(item =>
                    fetch(`/api/queue/cancel/${item.id}`, { method: 'POST' }).then(r => r.json())
                )).then(results => {
                    const successCount = results.filter(r => r.success).length;
                    showNotification(`Cancelled ${successCount} download(s)`, 'info');
                    updateQueueDisplay();
                }).catch(() => {
                    showNotification('Failed to cancel downloads', 'error');
                });
            });
        }

        return groupEl;
    }

    function renderGroupChildItem(item) {
        const childEl = document.createElement('div');
        childEl.className = 'queue-group-child';

        const episodeProgress = item.current_episode_progress || 0;
        const episodeProgressClamped = Math.max(0, Math.min(100, episodeProgress));
        const isDownloading = item.status === 'downloading';
        const canCancel = item.status === 'downloading' || item.status === 'queued';
        const episodeLabel = item.episode_number ? `Episode ${item.episode_number}` : `Download #${item.id}`;

        childEl.innerHTML = `
            <div class="queue-group-child-header">
                <span class="queue-group-child-label">${escapeHtml(episodeLabel)}</span>
                <div class="queue-item-header-right">
                    ${canCancel ? `<button class="queue-cancel-btn" data-id="${item.id}" title="Cancel download"><i class="fas fa-times"></i></button>` : ''}
                    <div class="queue-item-status ${item.status}">${item.status}</div>
                </div>
            </div>
            ${isDownloading ? `
            <div class="queue-item-progress episode-progress">
                <div class="queue-progress-bar">
                    <div class="queue-progress-fill episode-progress-fill" style="width: ${episodeProgressClamped}%; transition: width 0.3s ease;"></div>
                </div>
                <div class="queue-progress-text episode-progress-text">${episodeProgressClamped.toFixed(1)}%</div>
            </div>
            ` : ''}
            ${item.current_episode && isDownloading ? `
            <div class="queue-item-details">${escapeHtml(item.current_episode)}</div>
            ` : ''}
        `;

        const cancelBtn = childEl.querySelector('.queue-cancel-btn');
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

        return childEl;
    }

    function loadPopularAndNewAnime() {
        // Show sections immediately; each column manages its own spinner.
        popularNewSections.style.display = 'block';
        showHomeContent();
        loadProviderAniworld();
        loadProviderSto();
        loadProviderMovie4k();
    }

    function _providerFetch(apiUrl, popularGrid, newGrid, loadingEl, contentEl, btnId, force) {
        if (force) apiUrl += '?force=true';
        if (loadingEl) loadingEl.style.display = 'flex';
        if (contentEl) contentEl.style.display = 'none';
        const btn = document.getElementById(btnId);
        if (btn) { btn.disabled = true; btn.querySelector('i').classList.add('fa-spin'); }
        fetch(apiUrl)
            .then(response => {
                if (response.status === 401) { window.location.href = '/login'; return; }
                return response.json();
            })
            .then(data => {
                if (!data || !data.success) return;
                displayProviderContent(data.popular || [], data.new || [], popularGrid, newGrid);
            })
            .catch(error => console.error('Error loading', apiUrl, error))
            .finally(() => {
                if (loadingEl) loadingEl.style.display = 'none';
                if (contentEl) contentEl.style.display = 'block';
                if (btn) { btn.disabled = false; btn.querySelector('i').classList.remove('fa-spin'); }
            });
    }

    function loadProviderAniworld(force) {
        _providerFetch('/api/popular-new', popularAnimeGrid, newAnimeGrid,
            aniworldLoading, aniworldContent, 'refresh-aniworld', force);
    }

    function loadProviderSto(force) {
        _providerFetch('/api/popular-new-sto', popularStoGrid, newStoGrid,
            stoLoading, stoContent, 'refresh-sto', force);
    }

    function loadProviderMovie4k(force) {
        _providerFetch('/api/popular-new-movie4k', popularMovie4kGrid, newMovie4kGrid,
            movie4kLoading, movie4kContent, 'refresh-movie4k', force);
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
        // Normalize relative/protocol-relative URLs (same as download modal)
        if (coverUrl && !coverUrl.startsWith('data:') && !coverUrl.startsWith('http') && !coverUrl.startsWith('/api/')) {
            if (coverUrl.startsWith('//')) {
                coverUrl = 'https:' + coverUrl;
            } else if (coverUrl.startsWith('/')) {
                const siteBase = { 'aniworld.to': 'https://aniworld.to', 's.to': 'https://s.to', 'movie4k.sx': 'https://movie4k.sx' };
                coverUrl = (siteBase[anime.site] || 'https://aniworld.to') + coverUrl;
            }
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
    window.showSubscriptionsPanel = showSubscriptionsPanel;

    // ===== Plex Watchlist Integration =====
    const plexBtn = document.getElementById('plex-btn');
    const plexModal = document.getElementById('plex-modal');
    const closePlexModal = document.getElementById('close-plex-modal');

    if (plexBtn && plexModal) {
        const plexLoading = document.getElementById('plex-loading');
        const plexError = document.getElementById('plex-error');
        const plexErrorMessage = document.getElementById('plex-error-message');
        const plexEmpty = document.getElementById('plex-empty');
        const plexWatchlist = document.getElementById('plex-watchlist');
        const plexSearchResults = document.getElementById('plex-search-results');
        const plexSearchLoading = document.getElementById('plex-search-loading');
        const plexSearchGrid = document.getElementById('plex-search-grid');
        const plexSearchTitle = document.getElementById('plex-search-title');
        const plexBackBtn = document.getElementById('plex-back-btn');

        plexBtn.addEventListener('click', () => {
            plexModal.style.display = 'flex';
            loadPlexWatchlist();
        });

        closePlexModal.addEventListener('click', () => {
            plexModal.style.display = 'none';
        });

        plexModal.addEventListener('click', (e) => {
            if (e.target === plexModal) plexModal.style.display = 'none';
        });

        if (plexBackBtn) {
            plexBackBtn.addEventListener('click', () => {
                plexSearchResults.style.display = 'none';
                plexWatchlist.style.display = 'block';
            });
        }

        function loadPlexWatchlist() {
            // Reset state
            plexLoading.style.display = 'flex';
            plexError.style.display = 'none';
            plexEmpty.style.display = 'none';
            plexWatchlist.style.display = 'none';
            plexSearchResults.style.display = 'none';

            fetch('/api/plex/watchlist')
                .then(response => response.json())
                .then(data => {
                    plexLoading.style.display = 'none';

                    if (!data.success) {
                        plexError.style.display = 'block';
                        plexErrorMessage.textContent = data.error || 'Failed to load watchlist';
                        return;
                    }

                    const items = data.items || [];
                    if (items.length === 0) {
                        plexEmpty.style.display = 'block';
                        return;
                    }

                    renderPlexWatchlist(items);
                    plexWatchlist.style.display = 'block';
                })
                .catch(error => {
                    plexLoading.style.display = 'none';
                    plexError.style.display = 'block';
                    plexErrorMessage.textContent = 'Failed to connect to Plex: ' + error.message;
                });
        }

        function renderPlexWatchlist(items) {
            plexWatchlist.innerHTML = '';

            items.forEach(item => {
                const el = document.createElement('div');
                el.className = 'plex-watchlist-item';

                let thumbUrl = '';
                if (item.thumb) {
                    if (item.thumb.startsWith('http')) {
                        thumbUrl = item.thumb;
                    } else if (item.thumb.startsWith('/')) {
                        thumbUrl = `https://metadata-static.plex.tv${item.thumb}`;
                    } else {
                        thumbUrl = item.thumb;
                    }
                }

                const typeLabel = item.type === 'movie' ? 'Film' : item.type === 'show' ? 'Serie' : item.type;
                const yearText = item.year ? ` (${item.year})` : '';

                el.innerHTML = `
                    ${thumbUrl ? `<img class="plex-watchlist-item-thumb" src="${thumbUrl}" alt="" onerror="this.style.display='none'">` : '<div class="plex-watchlist-item-thumb"></div>'}
                    <div class="plex-watchlist-item-info">
                        <div class="plex-watchlist-item-title">${escapeHtml(item.title)}</div>
                        <div class="plex-watchlist-item-meta">${typeLabel}${yearText}</div>
                    </div>
                    <div class="plex-watchlist-item-arrow"><i class="fas fa-chevron-right"></i></div>
                `;

                el.addEventListener('click', () => {
                    searchPlexTitle(item.title);
                });

                plexWatchlist.appendChild(el);
            });
        }

        function searchPlexTitle(title) {
            // Switch to search results view
            plexWatchlist.style.display = 'none';
            plexSearchResults.style.display = 'block';
            plexSearchTitle.textContent = `Results for "${title}"`;
            plexSearchGrid.innerHTML = '';
            plexSearchLoading.style.display = 'flex';

            fetch('/api/plex/search-and-download', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: title })
            })
            .then(response => response.json())
            .then(data => {
                plexSearchLoading.style.display = 'none';

                if (!data.success) {
                    plexSearchGrid.innerHTML = `<div class="plex-no-results"><i class="fas fa-search"></i>Search failed: ${escapeHtml(data.error)}</div>`;
                    return;
                }

                const results = data.results || [];

                if (results.length === 0) {
                    plexSearchGrid.innerHTML = '<div class="plex-no-results"><i class="fas fa-search"></i>No results found on any site</div>';
                    return;
                }

                // If exactly one result, go directly to download modal
                if (results.length === 1) {
                    const result = results[0];
                    plexModal.style.display = 'none';
                    showDownloadModal(result.title, 'Series', result.url, result.cover);
                    // Auto-select all episodes after the modal loads
                    setTimeout(() => {
                        selectAllEpisodesAuto();
                    }, 2000);
                    return;
                }

                // Multiple results - show selection
                renderPlexSearchResults(results);
            })
            .catch(error => {
                plexSearchLoading.style.display = 'none';
                plexSearchGrid.innerHTML = `<div class="plex-no-results"><i class="fas fa-exclamation-triangle"></i>Error: ${escapeHtml(error.message)}</div>`;
            });
        }

        function renderPlexSearchResults(results) {
            plexSearchGrid.innerHTML = '';

            results.forEach(result => {
                const card = document.createElement('div');
                card.className = 'plex-search-card';

                let coverStyle = '';
                if (result.cover) {
                    let coverUrl = result.cover;
                    if (!coverUrl.startsWith('http')) {
                        if (coverUrl.startsWith('//')) {
                            coverUrl = 'https:' + coverUrl;
                        } else if (coverUrl.startsWith('/')) {
                            let baseUrl = 'https://aniworld.to';
                            if (result.site === 's.to') baseUrl = 'https://s.to';
                            coverUrl = baseUrl + coverUrl;
                        }
                    }
                    coverUrl = coverUrl.replace("150x225", "220x330");
                    coverStyle = `background-image: url('${coverUrl}')`;
                }

                card.innerHTML = `
                    <div class="plex-search-card-bg" style="${coverStyle}"></div>
                    <div class="plex-search-card-content">
                        <div class="plex-search-card-title">${escapeHtml(result.title)}</div>
                        <div class="plex-search-card-site">${escapeHtml(result.site)}</div>
                    </div>
                `;

                card.addEventListener('click', () => {
                    plexModal.style.display = 'none';
                    showDownloadModal(result.title, 'Series', result.url, result.cover);
                    // Auto-select all episodes after the modal loads
                    setTimeout(() => {
                        selectAllEpisodesAuto();
                    }, 2000);
                });

                plexSearchGrid.appendChild(card);
            });
        }

        function selectAllEpisodesAuto() {
            // Select all episode checkboxes in the download modal
            const checkboxes = document.querySelectorAll('#episode-tree .episode-checkbox');
            checkboxes.forEach(cb => {
                if (!cb.checked) {
                    cb.checked = true;
                    cb.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });
            // Also check all season header checkboxes
            const seasonCheckboxes = document.querySelectorAll('#episode-tree thead input[type="checkbox"]');
            seasonCheckboxes.forEach(cb => {
                cb.checked = true;
            });
        }
    }
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
    let subshown = false;

    // ---- Subscriptions Button ----
    const subscriptionsBtn = document.getElementById('subscriptions-btn');
    const subscriptionsBackBtn = document.getElementById('subscriptions-back-btn');
    const subscriptionsRefreshBtn = document.getElementById('subscriptions-refresh-btn');

    if (subscriptionsBtn) {
        subscriptionsBtn.addEventListener('click', () => {
            if (!subshown) {
                subshown = true;
                localshown = false;
                window.showSubscriptionsPanel();
                loadSubscriptionsPanel();
            } else {
                subshown = false;
                window.showHomeContent();
            }
        });
    }

    if (subscriptionsBackBtn) {
        subscriptionsBackBtn.addEventListener('click', () => {
            subshown = false;
            window.showHomeContent();
        });
    }

    if (subscriptionsRefreshBtn) {
        subscriptionsRefreshBtn.addEventListener('click', () => {
            fetch('/api/subscriptions/check', { method: 'POST' })
                .then(r => r.json())
                .then(() => {
                    showNotification('Checking for new episodes...', 'info');
                    setTimeout(() => loadSubscriptionsPanel(), 3000);
                })
                .catch(() => showNotification('Check failed', 'error'));
        });
    }

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

        const defaultCover = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDIwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIyMDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMzMzIi8+CjxwYXRoIGQ9Ik0xMDAgMTUwTDEyMCAxNzBMMTAwIDE5MFY3MGwyMCAyMEwxMDAgMTEwVjE1MFoiIGZpbGw9IiM2NjYiLz4KPC9zdmc+';

        localFilesGrid.innerHTML = '';
        localFilesGrid.style.display = 'grid';

        // Render folders as home-anime-card style cards
        if (folders && folders.length > 0) {
            folders.forEach(folder => {
                const card = document.createElement('div');
                card.className = 'home-anime-card';

                const coverUrl = folder.local_cover || folder.cover || defaultCover;
                card.innerHTML = `
                    <div class="home-anime-cover">
                        <img src="${coverUrl}" alt="${escapeHtmlFB(folder.name)}" loading="lazy"
                             onerror="this.src='${defaultCover}'">
                        <span class="video-count-badge">${folder.video_count} video${folder.video_count !== 1 ? 's' : ''}</span>
                    </div>
                    <div class="home-anime-title" title="${escapeHtmlFB(folder.name)}">
                        ${escapeHtmlFB(folder.name)}
                    </div>
                `;
                card.addEventListener('click', () => {
                    if (folder.series_url) {
                        const isMovie = folder.series_url.includes('movie4k');
                        const episodeLabel = isMovie ? 'Movie' : 'Series';
                        showDownloadModal(folder.name, episodeLabel, folder.series_url, folder.local_cover || folder.cover, folder.path);
                    } else {
                        openFileModal(folder.name, folder.path);
                    }
                });
                localFilesGrid.appendChild(card);
            });
        }

        // Render loose files (root-level videos) as a single card if present
        if (files && files.length > 0) {
            const card = document.createElement('div');
            card.className = 'home-anime-card';
            card.innerHTML = `
                <div class="home-anime-cover">
                    <img src="${defaultCover}" alt="Unsorted Files" loading="lazy">
                    <span class="video-count-badge">${files.length} video${files.length !== 1 ? 's' : ''}</span>
                </div>
                <div class="home-anime-title" title="Unsorted Files">
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
                        ${(progress && progress.percentage > 5 && progress.percentage < 95)
                            ? `<button class="file-action-btn continue-btn" title="Resume from ${Math.round(progress.percentage)}%"><i class="fas fa-redo"></i></button>`
                            : ''}
                        <button class="file-action-btn stream-btn" title="${(progress && progress.percentage > 5 && progress.percentage < 95) ? 'Play from beginning' : 'Stream in browser'}">
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

                // Continue (resume) button
                const continueBtn = item.querySelector('.continue-btn');
                if (continueBtn) {
                    continueBtn.addEventListener('click', () => {
                        streamFile(file, progress.current_time);
                    });
                }

                // Stream button (always from beginning when there's also a continue btn)
                const streamBtn = item.querySelector('.stream-btn');
                streamBtn.addEventListener('click', () => {
                    const startTime = (progress && progress.percentage > 0 && progress.percentage < 95 && !continueBtn)
                        ? progress.current_time : 0;
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

    // ========================================
    // Continue Watching Section
    // ========================================

    function loadContinueWatching() {
        const section = document.getElementById('continue-watching-section');
        const grid = document.getElementById('continue-watching-grid');
        if (!section || !grid) return;

        Promise.all([
            fetch('/api/watch-progress').then(r => r.json()),
            fetch('/api/files').then(r => r.json())
        ]).then(([progressData, filesData]) => {
            if (!progressData.success) return;
            const progress = progressData.progress || {};

            // Filter to in-progress files (5% < progress < 95%)
            const inProgress = Object.entries(progress)
                .filter(([, p]) => p.percentage > 5 && p.percentage < 95)
                .sort((a, b) => new Date(b[1].last_watched) - new Date(a[1].last_watched))
                .slice(0, 10);

            if (inProgress.length === 0) {
                section.style.display = 'none';
                return;
            }

            // Build a flat file map for path lookup
            const fileMap = {};
            // Build a folder cover map: normalized folder path -> cover URL
            const folderCoverMap = {};
            if (filesData.success) {
                (filesData.files || []).forEach(f => { fileMap[f.path] = f; });
                (filesData.folders || []).forEach(folder => {
                    if (folder.files) folder.files.forEach(f => { fileMap[f.path] = f; });
                    // Prefer local cover (served via API), fall back to remote cover
                    const cover = folder.local_cover || folder.cover || '';
                    if (cover) folderCoverMap[folder.path.replace(/\\/g, '/')] = cover;
                });
            }

            grid.innerHTML = '';
            const defaultCover = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDIwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIyMDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMzMzIi8+PHRleHQgeD0iMTAwIiB5PSIxNTUiIGZpbGw9IiM2NjYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZvbnQtc2l6ZT0iMjQiPuKWtjwvdGV4dD48L3N2Zz4=';

            inProgress.forEach(([filePath, prog]) => {
                const fileName = filePath.split('/').pop().split('\\').pop();
                // Look up folder cover by parent directory
                const parentPath = filePath.replace(/\\/g, '/').split('/').slice(0, -1).join('/');
                const seriesTitle = parentPath.split('/')[0] || '';
                const cardCover = folderCoverMap[parentPath] || defaultCover;
                const card = document.createElement('div');
                card.className = 'cw-card';
                card.innerHTML = `
                    <img src="${cardCover}" alt="${escapeHtmlFB(fileName)}" loading="lazy"
                         onerror="this.onerror=null;this.src='${defaultCover}'">
                    <div class="cw-play-overlay"><i class="fas fa-redo"></i></div>
                    ${seriesTitle ? `<div class="cw-card-series">${escapeHtmlFB(seriesTitle)}</div>` : ''}
                    <div class="cw-card-info">
                        <div class="cw-card-title" title="${escapeHtmlFB(fileName)}">${escapeHtmlFB(fileName)}</div>
                        <div class="cw-card-progress">
                            <div class="cw-card-progress-fill" style="width: ${Math.round(prog.percentage)}%"></div>
                        </div>
                    </div>
                `;
                card.title = `Resume from ${Math.round(prog.percentage)}%`;
                card.addEventListener('click', () => {
                    // Build a minimal file object for streamFile
                    const fileObj = fileMap[filePath] || { path: filePath, name: fileName };
                    streamFile(fileObj, prog.current_time);
                });
                grid.appendChild(card);
            });

            section.style.display = 'block';
        }).catch(err => {
            console.error('Failed to load continue watching:', err);
        });
    }

    // ========================================
    // Subscriptions Panel
    // ========================================

    const subscriptionBadge = document.getElementById('subscription-badge');

    function updateSubscriptionBadge(count) {
        if (!subscriptionBadge) return;
        if (count > 0) {
            subscriptionBadge.textContent = count > 9 ? '9+' : count;
            subscriptionBadge.style.display = 'flex';
        } else {
            subscriptionBadge.style.display = 'none';
        }
    }

    function loadSubscriptionsPanel() {
        const loading = document.getElementById('subscriptions-loading');
        const grid = document.getElementById('subscriptions-grid');
        const empty = document.getElementById('subscriptions-empty');
        if (!grid) return;

        if (loading) loading.style.display = 'block';
        grid.style.display = 'none';
        if (empty) empty.style.display = 'none';

        fetch('/api/subscriptions')
            .then(r => r.json())
            .then(data => {
                if (!data.success) throw new Error(data.error || 'Failed');
                const subs = data.subscriptions || [];
                const notes = data.notifications || [];

                // Show notification badge for new episodes
                const newSubIds = new Set(notes.map(n => n.sub_id));
                if (notes.length > 0) {
                    notes.forEach(n => showNotification(`${n.title}: ${n.new_count} new episode(s)!`, 'success'));
                }
                updateSubscriptionBadge(notes.length);

                if (loading) loading.style.display = 'none';

                if (subs.length === 0) {
                    if (empty) empty.style.display = 'block';
                    grid.style.display = 'none';
                    return;
                }

                grid.innerHTML = '';
                grid.style.display = 'grid';

                const defaultCover = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjMwMCIgdmlld0JveD0iMCAwIDIwMCAzMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIyMDAiIGhlaWdodD0iMzAwIiBmaWxsPSIjMzMzIi8+CjxwYXRoIGQ9Ik0xMDAgMTUwTDEyMCAxNzBMMTAwIDE5MFY3MGwyMCAyMEwxMDAgMTEwVjE1MFoiIGZpbGw9IiM2NjYiLz4KPC9zdmc+';

                subs.forEach(sub => {
                    const card = document.createElement('div');
                    card.className = 'home-anime-card subscription-card';
                    const hasNew = newSubIds.has(sub.id);
                    const coverUrl = sub.cover || defaultCover;

                    card.innerHTML = `
                        ${hasNew ? `<span class="sub-new-badge"><i class="fas fa-bell"></i> New</span>` : ''}
                        <div class="home-anime-cover">
                            <img src="${escapeHtmlFB(coverUrl)}" alt="${escapeHtmlFB(sub.title)}" loading="lazy"
                                 onerror="this.src='${defaultCover}'">
                        </div>
                        <div class="home-anime-title" title="${escapeHtmlFB(sub.title)}">${escapeHtmlFB(sub.title)}</div>
                        <div class="sub-info-chips">
                            ${sub.notify ? `<span class="sub-chip active"><i class="fas fa-bell"></i> Notify</span>` : ''}
                            ${sub.auto_download ? `<span class="sub-chip active"><i class="fas fa-download"></i> Auto</span>` : ''}
                            <span class="sub-chip"><i class="fas fa-film"></i> ${sub.last_episode_count} ep</span>
                        </div>
                        <div class="sub-card-overlay">
                            <button class="sub-card-btn open-btn" title="Open series"><i class="fas fa-external-link-alt"></i></button>
                            <button class="sub-card-btn settings-btn" title="Settings"><i class="fas fa-cog"></i></button>
                            <button class="sub-card-btn danger remove-btn" title="Unsubscribe"><i class="fas fa-times"></i></button>
                        </div>
                    `;

                    card.querySelector('.open-btn').addEventListener('click', (e) => {
                        e.stopPropagation();
                        const isMovie = sub.series_url.includes('movie4k');
                        const label = isMovie ? 'Movie' : 'Series';
                        window.showDownloadModal(sub.title, label, sub.series_url, sub.cover);
                        subshown = false;
                    });

                    card.querySelector('.settings-btn').addEventListener('click', (e) => {
                        e.stopPropagation();
                        openSubscriptionSettingsModal(sub);
                    });

                    card.querySelector('.remove-btn').addEventListener('click', (e) => {
                        e.stopPropagation();
                        if (!confirm(`Unsubscribe from "${sub.title}"?`)) return;
                        fetch(`/api/subscriptions/${sub.id}`, { method: 'DELETE' })
                            .then(r => r.json())
                            .then(d => {
                                if (d.success) {
                                    showNotification('Unsubscribed', 'success');
                                    loadSubscriptionsPanel();
                                } else {
                                    showNotification(d.error || 'Failed', 'error');
                                }
                            });
                    });

                    card.addEventListener('click', () => {
                        const isMovie = sub.series_url.includes('movie4k');
                        const label = isMovie ? 'Movie' : 'Series';
                        window.showDownloadModal(sub.title, label, sub.series_url, sub.cover);
                        subshown = false;
                    });

                    grid.appendChild(card);
                });
            })
            .catch(err => {
                if (loading) loading.style.display = 'none';
                showNotification('Failed to load subscriptions', 'error');
                console.error('Subscriptions error:', err);
            });
    }

    function openSubscriptionSettingsModal(sub) {
        // Simple inline settings overlay
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay';
        overlay.style.display = 'flex';
        overlay.innerHTML = `
            <div class="modal-content" style="max-width: 380px;">
                <div class="modal-header download-info">
                    <strong>${escapeHtmlFB(sub.title)}</strong>
                    <button class="close-btn" id="sub-settings-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="subscription-options-inner">
                        <h4><i class="fas fa-star"></i> Subscription Settings</h4>
                        <label class="sub-option-row">
                            <input type="checkbox" id="sub-settings-notify" ${sub.notify ? 'checked' : ''}>
                            <span>Notify when new episodes are available</span>
                        </label>
                        <label class="sub-option-row">
                            <input type="checkbox" id="sub-settings-auto" ${sub.auto_download ? 'checked' : ''}>
                            <span>Auto-download new episodes</span>
                        </label>
                        <div class="sub-option-actions">
                            <button id="sub-settings-save" class="primary-btn sub-save-btn"><i class="fas fa-save"></i> Save</button>
                            <button id="sub-settings-cancel" class="secondary-btn">Cancel</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        const close = () => overlay.remove();
        overlay.querySelector('#sub-settings-close').addEventListener('click', close);
        overlay.querySelector('#sub-settings-cancel').addEventListener('click', close);
        overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });

        overlay.querySelector('#sub-settings-save').addEventListener('click', () => {
            const notify = overlay.querySelector('#sub-settings-notify').checked;
            const autoDownload = overlay.querySelector('#sub-settings-auto').checked;
            fetch(`/api/subscriptions/${sub.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notify, auto_download: autoDownload })
            })
            .then(r => r.json())
            .then(d => {
                if (d.success) {
                    showNotification('Settings saved', 'success');
                    close();
                    loadSubscriptionsPanel();
                } else {
                    showNotification(d.error || 'Failed', 'error');
                }
            });
        });
    }

    // Poll for subscription notifications every 5 minutes
    setInterval(() => {
        fetch('/api/subscriptions/notifications')
            .then(r => r.json())
            .then(data => {
                if (data.success && data.notifications && data.notifications.length > 0) {
                    data.notifications.forEach(n => {
                        showNotification(`${n.title}: ${n.new_count} new episode(s) available!`, 'success');
                    });
                    updateSubscriptionBadge(data.notifications.length);
                }
            })
            .catch(() => {});
    }, 5 * 60 * 1000);

    // Export functions so the DOMContentLoaded scope can use them
    window.streamFile = streamFile;
    window.loadContinueWatching = loadContinueWatching;
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