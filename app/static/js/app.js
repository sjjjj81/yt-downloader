/**
 * YouTube Downloader - Frontend Application
 * Handles form interaction, real download job polling, and session management
 */

(function() {
    'use strict';

    // State management
    const state = {
        url: '',
        mode: 'video', // 'video' or 'audio'
        quality: 'best',
        audioFormat: 'mp3',
        isDownloading: false,
        currentJobId: null,
        pollInterval: null,
        recentDownloads: []
    };

    // DOM Elements
    const elements = {
        urlInput: null,
        urlWrapper: null,
        clearBtn: null,
        modeVideo: null,
        modeAudio: null,
        qualitySelect: null,
        audioFormatSelect: null,
        downloadBtn: null,
        cancelBtn: null,
        retryBtn: null,
        progressSection: null,
        progressBar: null,
        progressText: null,
        statusMessage: null,
        recentList: null,
        downloadDestination: null,
        metadataPreview: null,
        videoTitle: null,
        videoThumbnail: null
    };

    // Initialize application
    function init() {
        cacheElements();
        setupEventListeners();
        loadRecentDownloads();
        checkUrlInput();
    }

    // Cache DOM elements
    function cacheElements() {
        elements.urlInput = document.getElementById('url-input');
        elements.urlWrapper = document.getElementById('url-wrapper');
        elements.clearBtn = document.getElementById('clear-btn');
        elements.modeVideo = document.getElementById('mode-video');
        elements.modeAudio = document.getElementById('mode-audio');
        elements.qualitySelect = document.getElementById('quality-select');
        elements.audioFormatSelect = document.getElementById('audio-format-select');
        elements.downloadBtn = document.getElementById('download-btn');
        elements.cancelBtn = document.getElementById('cancel-btn');
        elements.retryBtn = document.getElementById('retry-btn');
        elements.progressSection = document.getElementById('progress-section');
        elements.progressBar = document.getElementById('progress-bar');
        elements.progressText = document.getElementById('progress-text');
        elements.statusMessage = document.getElementById('status-message');
        elements.recentList = document.getElementById('recent-list');
        elements.downloadDestination = document.getElementById('download-destination');
        elements.metadataPreview = document.getElementById('metadata-preview');
        elements.videoTitle = document.getElementById('video-title');
        elements.videoThumbnail = document.getElementById('video-thumbnail');
    }

    // HTML escape to prevent XSS from untrusted metadata
    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // Setup event listeners
    function setupEventListeners() {
        elements.urlInput.addEventListener('input', checkUrlInput);
        elements.urlInput.addEventListener('paste', handlePaste);
        elements.urlInput.addEventListener('keydown', handleEnterKey);

        elements.clearBtn.addEventListener('click', clearUrlInput);

        elements.modeVideo.addEventListener('click', () => setMode('video'));
        elements.modeAudio.addEventListener('click', () => setMode('audio'));

        elements.qualitySelect.addEventListener('change', (e) => {
            state.quality = e.target.value;
        });

        elements.audioFormatSelect.addEventListener('change', (e) => {
            state.audioFormat = e.target.value;
        });

        elements.downloadBtn.addEventListener('click', initiateDownload);
        elements.cancelBtn.addEventListener('click', cancelDownload);
        elements.retryBtn.addEventListener('click', retryDownload);
    }

    // Check URL input and update UI
    function checkUrlInput() {
        const hasValue = elements.urlInput.value.trim().length > 0;

        if (hasValue) {
            elements.urlWrapper.classList.add('has-value');
            state.url = elements.urlInput.value.trim();
            fetchMetadata(state.url);
        } else {
            elements.urlWrapper.classList.remove('has-value');
            state.url = '';
            hideMetadataPreview();
        }
    }

    // Fetch metadata from the server
    async function fetchMetadata(url) {
        if (!isValidUrl(url)) {
            hideMetadataPreview();
            return;
        }

        try {
            const response = await fetch(`/api/metadata?url=${encodeURIComponent(url)}`);
            const data = await response.json();

            if (!response.ok) {
                hideMetadataPreview();
                return;
            }

            showMetadataPreview(data);
        } catch (error) {
            console.error('Failed to fetch metadata:', error);
            hideMetadataPreview();
        }
    }

    // Show metadata preview in the UI
    function showMetadataPreview(data) {
        if (!elements.metadataPreview) return;

        // Set thumbnail (use default YouTube thumbnail format if not provided)
        const videoId = extractVideoId(state.url);
        const thumbnailUrl = data.thumbnail || (videoId ? `https://img.youtube.com/vi/${videoId}/hqdefault.jpg` : '');
        if (elements.videoThumbnail && thumbnailUrl) {
            elements.videoThumbnail.src = thumbnailUrl;
            elements.videoThumbnail.alt = escapeHtml(data.title || 'Video thumbnail');
        }

        // Set title
        if (elements.videoTitle) {
            elements.videoTitle.textContent = escapeHtml(data.title || 'Unknown title');
        }

        // Update quality options if formats are available
        if (data.formats && data.formats.length > 0) {
            updateQualityOptions(data.formats);
        }

        elements.metadataPreview.style.display = 'flex';
    }

    // Hide metadata preview
    function hideMetadataPreview() {
        if (elements.metadataPreview) {
            elements.metadataPreview.style.display = 'none';
        }
        resetQualityOptions();
    }

    // Extract video ID from URL
    function extractVideoId(url) {
        const patterns = [
            /youtube\.com\/watch\?v=([\w-]{11})/,
            /youtu\.be\/([\w-]{11})/,
            /youtube\.com\/shorts\/([\w-]{11})/,
            /youtube\.com\/embed\/([\w-]{11})/,
        ];
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match) return match[1];
        }
        return null;
    }

    // Update quality dropdown options from available formats
    function updateQualityOptions(formats) {
        if (!elements.qualitySelect) return;

        // Get current value to restore after update
        const currentValue = elements.qualitySelect.value;

        // Clear existing options except first (Best Available)
        while (elements.qualitySelect.options.length > 1) {
            elements.qualitySelect.remove(1);
        }

        // Add format options
        for (const format of formats) {
            const option = document.createElement('option');
            option.value = format.quality;
            option.textContent = `${format.quality} (${format.ext})`;
            elements.qualitySelect.appendChild(option);
        }

        // Restore previous selection if still valid
        if (currentValue !== 'best') {
            const exists = Array.from(elements.qualitySelect.options).some(o => o.value === currentValue);
            if (exists) {
                elements.qualitySelect.value = currentValue;
                state.quality = currentValue;
            }
        }
    }

    // Reset quality options to defaults
    function resetQualityOptions() {
        if (!elements.qualitySelect) return;

        const currentMode = state.mode;
        elements.qualitySelect.innerHTML = `
            <option value="best">Best Available</option>
            <option value="1080p">1080p</option>
            <option value="720p">720p</option>
            <option value="480p">480p</option>
        `;
        state.quality = 'best';

        // Restore disabled state based on mode
        elements.qualitySelect.disabled = currentMode === 'audio';
    }

    function handlePaste(e) {
        setTimeout(checkUrlInput, 10);
    }

    function clearUrlInput() {
        elements.urlInput.value = '';
        checkUrlInput();
        clearStatusMessage();
        resetProgress();
    }

    function handleEnterKey(e) {
        if (e.key === 'Enter') {
            if (!state.isDownloading && isValidUrl(state.url)) {
                initiateDownload();
            }
        }
    }

    function setMode(mode) {
        state.mode = mode;

        elements.modeVideo.classList.toggle('active', mode === 'video');
        elements.modeAudio.classList.toggle('active', mode === 'audio');

        if (mode === 'video') {
            elements.qualitySelect.disabled = false;
            elements.audioFormatSelect.disabled = true;
        } else {
            elements.qualitySelect.disabled = true;
            elements.audioFormatSelect.disabled = false;
        }
    }

    function isValidUrl(url) {
        if (!url) return false;
        const youtubePatterns = [
            /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/i,
            /^https?:\/\/(www\.)?youtube\.com\/watch\?v=[\w-]+(&\S*)?$/i,
            /^https?:\/\/youtu\.be\/[\w-]+$/i,
            /^https?:\/\/(www\.)?youtube\.com\/shorts\/[\w-]+$/i,
            /^https?:\/\/(www\.)?youtube\.com\/embed\/[\w-]+$/i
        ];
        return youtubePatterns.some(pattern => pattern.test(url));
    }

    function showError(message) {
        elements.statusMessage.textContent = escapeHtml(message);
        elements.statusMessage.className = 'status-message visible error';
    }

    function clearStatusMessage() {
        elements.statusMessage.className = 'status-message';
        elements.statusMessage.textContent = '';
    }

    function resetProgress() {
        if (state.pollInterval) {
            clearInterval(state.pollInterval);
            state.pollInterval = null;
        }
        elements.progressSection.classList.remove('visible');
        elements.progressBar.style.width = '0%';
        elements.progressText.textContent = '0%';
        elements.downloadBtn.disabled = false;
        elements.cancelBtn.style.display = 'none';
        elements.retryBtn.style.display = 'none';
        state.isDownloading = false;
        state.currentJobId = null;
    }

    function showSuccess(message, downloadInfo) {
        elements.statusMessage.textContent = escapeHtml(message);
        elements.statusMessage.className = 'status-message visible success';

        if (downloadInfo) {
            addDownloadToSession(downloadInfo);
        }

        elements.downloadBtn.disabled = false;
        elements.cancelBtn.style.display = 'none';
        elements.retryBtn.style.display = 'inline-block';
        state.isDownloading = false;
        if (state.pollInterval) {
            clearInterval(state.pollInterval);
            state.pollInterval = null;
        }
    }

    function addDownloadToSession(info) {
        const downloadItem = {
            id: info.job_id || Date.now(),
            title: info.title || 'YouTube Download',
            format: info.format || (state.mode === 'audio' ? state.audioFormat : state.quality),
            date: new Date().toLocaleString(),
            size: info.size || 'Ready',
            url: info.url || '#'
        };

        state.recentDownloads.unshift(downloadItem);
        if (state.recentDownloads.length > 10) {
            state.recentDownloads.pop();
        }
        saveRecentDownloads();
        renderRecentDownloads();
    }

    function saveRecentDownloads() {
        sessionStorage.setItem('recentDownloads', JSON.stringify(state.recentDownloads));
    }

    function loadRecentDownloads() {
        const saved = sessionStorage.getItem('recentDownloads');
        if (saved) {
            try {
                state.recentDownloads = JSON.parse(saved);
                renderRecentDownloads();
            } catch (e) {
                console.error('Failed to parse recent downloads:', e);
            }
        }
    }

    function renderRecentDownloads() {
        elements.recentList.innerHTML = '';

        if (state.recentDownloads.length === 0) {
            elements.recentList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⬇</div>
                    <p>No downloads in this session</p>
                </div>
            `;
            return;
        }

        state.recentDownloads.forEach(item => {
            const itemEl = document.createElement('div');
            itemEl.className = 'download-item';

            // Use textContent for safe rendering
            const titleDiv = document.createElement('div');
            titleDiv.className = 'download-item-title';
            titleDiv.textContent = item.title;
            titleDiv.title = item.title;

            const metaDiv = document.createElement('div');
            metaDiv.className = 'download-item-meta';

            const badgeSpan = document.createElement('span');
            badgeSpan.className = 'badge';
            badgeSpan.textContent = item.format;

            const dateSpan = document.createElement('span');
            dateSpan.textContent = item.date;

            metaDiv.appendChild(badgeSpan);
            metaDiv.appendChild(dateSpan);

            const infoDiv = document.createElement('div');
            infoDiv.className = 'download-item-info';
            infoDiv.appendChild(titleDiv);
            infoDiv.appendChild(metaDiv);

            const iconDiv = document.createElement('div');
            iconDiv.className = 'download-item-icon';
            iconDiv.textContent = '✓';

            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'download-item-actions';

            if (item.url && item.url !== '#') {
                const link = document.createElement('a');
                link.href = escapeHtml(item.url);
                link.className = 'btn btn-secondary';
                link.style.cssText = 'padding: 6px 12px; font-size: 12px; text-decoration: none;';
                link.download = '';
                link.textContent = 'Save';
                actionsDiv.appendChild(link);
            }

            itemEl.appendChild(iconDiv);
            itemEl.appendChild(infoDiv);
            itemEl.appendChild(actionsDiv);

            elements.recentList.appendChild(itemEl);
        });
    }

    function validateInput() {
        if (!isValidUrl(state.url)) {
            showError('Please enter a valid YouTube URL');
            return false;
        }
        return true;
    }

    async function initiateDownload() {
        clearStatusMessage();

        if (!validateInput()) {
            elements.urlInput.focus();
            return;
        }

        if (state.isDownloading) return;

        state.isDownloading = true;
        elements.downloadBtn.disabled = true;
        elements.cancelBtn.style.display = 'inline-block';
        elements.retryBtn.style.display = 'none';
        elements.progressSection.classList.add('visible');

        elements.statusMessage.className = 'status-message visible';
        elements.statusMessage.textContent = 'Starting download job...';
        elements.progressBar.style.width = '5%';
        elements.progressText.textContent = 'Connecting...';

        try {
            const response = await fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: state.url,
                    mode: state.mode,
                    quality: state.quality,
                    audio_format: state.audioFormat
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || `Server error: ${response.status}`);
            }

            state.currentJobId = result.job_id;
            elements.statusMessage.textContent = 'Downloading in progress...';
            startPolling(state.currentJobId);

        } catch (error) {
            showError(error.message || 'Failed to start download');
            resetProgress();
        }
    }

    function startPolling(jobId) {
        if (state.pollInterval) {
            clearInterval(state.pollInterval);
        }

        state.pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/status/${jobId}`);
                if (!res.ok) {
                    throw new Error('Failed to fetch job status');
                }
                const job = await res.json();

                if (job.status === 'complete') {
                    elements.progressBar.style.width = '100%';
                    elements.progressText.textContent = '100% • Complete';
                    showSuccess(`Successfully downloaded: ${job.title || 'Video'}`, {
                        job_id: job.job_id,
                        title: job.title || 'YouTube Download',
                        format: state.mode === 'audio' ? state.audioFormat : state.quality,
                        url: job.result_url
                    });
                } else if (job.status === 'failed') {
                    throw new Error(job.error || 'Download failed');
                } else if (job.status === 'cancelled') {
                    if (state.pollInterval) {
                        clearInterval(state.pollInterval);
                        state.pollInterval = null;
                    }
                    state.isDownloading = false;
                    elements.downloadBtn.disabled = false;
                    elements.cancelBtn.style.display = 'none';
                    elements.progressSection.classList.remove('visible');
                    elements.statusMessage.textContent = 'Download cancelled';
                    elements.statusMessage.className = 'status-message visible error';
                } else if (job.status === 'running' || job.status === 'pending') {
                    const pct = job.progress || 0;
                    elements.progressBar.style.width = `${Math.max(pct, 5)}%`;
                    let txt = `${pct}%`;
                    if (job.speed) txt += ` • ${escapeHtml(job.speed)}`;
                    if (job.eta) txt += ` • ETA: ${escapeHtml(job.eta)}`;
                    elements.progressText.textContent = txt;
                    if (job.title) {
                        elements.statusMessage.textContent = `Downloading: ${escapeHtml(job.title)}`;
                    }
                }
            } catch (err) {
                console.error('Polling error:', err);
                showError(err.message || 'Error checking download status');
                resetProgress();
            }
        }, 1000);
    }

    async function cancelDownload() {
        if (!state.currentJobId) {
            resetProgress();
            return;
        }

        try {
            await fetch(`/api/cancel/${state.currentJobId}`, {
                method: 'POST'
            });
        } catch (e) {
            console.error('Cancel request failed:', e);
        }

        resetProgress();
        elements.statusMessage.textContent = 'Download cancelled by user';
        elements.statusMessage.className = 'status-message visible error';
    }

    function retryDownload() {
        clearStatusMessage();
        initiateDownload();
    }

    window.YouTubeDownloader = {
        isValidUrl: isValidUrl,
        validateInput: validateInput
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
