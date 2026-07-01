// ─── THEMES ───────────────────────────────────────────────────────────────────
const THEMES = [
    { id: 'default',          name: 'Midnight Horizon',  desc: 'Default cool indigo & teal on dark blue',               bg: '#0b0f19', primary: '#6366f1', accent: '#0ea5e9' },
    { id: 'cyberpunk',        name: 'Cyberpunk Neon',    desc: 'High-octane neon pink & cyan on absolute black',        bg: '#030203', primary: '#ff007f', accent: '#00f0ff' },
    { id: 'synthwave',        name: 'Synthwave Sunset',  desc: 'Retro hot pink & sunset orange over deep purple',       bg: '#0c021a', primary: '#ff00a0', accent: '#ff8c00' },
    { id: 'nord',             name: 'Nordic Frost',      desc: 'Cool arctic blues & mint slate accents',                bg: '#1e222a', primary: '#88c0d0', accent: '#8fbcbb' },
    { id: 'matrix',           name: 'Matrix Code',       desc: 'Glowing phosphor green on pitch black',                 bg: '#000000', primary: '#00ff41', accent: '#10ef90' },
    { id: 'volcano',          name: 'Volcanic Ash',      desc: 'Fiery red & orange on dark charcoal',                   bg: '#0c0808', primary: '#ef4444', accent: '#f97316' },
    { id: 'forest',           name: 'Forest Moss',       desc: 'Sage emerald & gold on deep woodland green',            bg: '#080f09', primary: '#10b981', accent: '#ea580c' },
    { id: 'sakura',           name: 'Sakura Blossom',    desc: 'Cherry blossom pink & orchid over dark plum',           bg: '#14050e', primary: '#ec4899', accent: '#a855f7' },
    { id: 'luxury',           name: 'Luxury Gold',       desc: 'Champagne gold on dark chocolate',                      bg: '#0e0c0a', primary: '#d4af37', accent: '#f3e5ab' },
    { id: 'solarized',        name: 'Solarized Dark',    desc: 'Teal & amber on deep blue-green',                       bg: '#002b36', primary: '#2aa198', accent: '#cb4b16' },
    { id: 'lavender',         name: 'Lavender Fields',   desc: 'Soothing lavender & amethyst on dark purple',           bg: '#0a0718', primary: '#c084fc', accent: '#a78bfa' },
    { id: 'monochrome-light', name: 'Minimal Light',     desc: 'Clean slate & cobalt on elegant off-white',             bg: '#f8fafc', primary: '#4f46e5', accent: '#0ea5e9' },
    { id: 'cyber-light',      name: 'Neon Light',        desc: 'Neon pink & electric cyan on clean white',              bg: '#f5f6f8', primary: '#ff007f', accent: '#00b8e6' },
    { id: 'retro-amber',      name: 'CRT Amber',         desc: 'Phosphor amber glow on deep brown-black',               bg: '#0a0704', primary: '#ffb000', accent: '#ffcc00' },
    { id: 'pitch-black',      name: 'OLED Black',        desc: 'True black with electric cyan & royal violet',          bg: '#000000', primary: '#8b5cf6', accent: '#06b6d4' },
    { id: 'arctic-light',     name: 'Arctic Snow',       desc: 'Polar blue & glacial teal on pristine white',           bg: '#f8fafc', primary: '#3b82f6', accent: '#14b8a6' },
    { id: 'autumn',           name: 'Autumn Leaves',     desc: 'Copper, rust & maple orange on woody charcoal',         bg: '#120b08', primary: '#f97316', accent: '#ea580c' },
    { id: 'rose-gold',        name: 'Rose Gold Glam',    desc: 'Rose gold & bronze on deep luxury plum',                bg: '#110b0f', primary: '#f472b6', accent: '#fda4af' },
    { id: 'coffee',           name: 'Coffee Roast',      desc: 'Caramel & cream on rich espresso brown',                bg: '#110b08', primary: '#b45309', accent: '#d97706' },
    { id: 'ocean',            name: 'Abyssal Deep',      desc: 'Luminescent sea aquamarine & bio-teal on ink-black',    bg: '#020509', primary: '#0ea5e9', accent: '#06b6d4' },
    { id: 'dracula',          name: 'Dracula Goth',      desc: 'Gothic hot pink & electric purple on slate',            bg: '#1e1f29', primary: '#ff79c6', accent: '#bd93f9' },
    { id: 'bubblegum',        name: 'Bubblegum Pop',     desc: 'Pastel pink & baby turquoise on creamy white',          bg: '#fffafc', primary: '#f06292', accent: '#4dd0e1' },
    { id: 'slate',            name: 'Steel Slate',       desc: 'Industrial steel & cobalt on dark charcoal',            bg: '#111622', primary: '#38bdf8', accent: '#94a3b8' },
    { id: 'cyber-lime',       name: 'Lime Toxic',        desc: 'Radioactive neon green & cyber yellow on dark slate',   bg: '#070d0a', primary: '#84cc16', accent: '#22c55e' },
    { id: 'royal',            name: 'Royal Velvet',      desc: 'Deep royal blue & imperial purple on dark navy',        bg: '#060517', primary: '#8b5cf6', accent: '#3b82f6' },
];

// ─── STORAGE KEYS ────────────────────────────────────────────────────────────
const STORAGE_KEY       = 'router-migrate-theme';
const HISTORY_KEY       = 'router-migrate-history';
const SAVED_SOURCES_KEY = 'router-migrate-saved-sources';
const HISTORY_MAX       = 50;

// ─── HOSTNAME EXTRACTION ─────────────────────────────────────────────────────
function extractHostname(config) {
    const patterns = [
        /^hostname\s+(\S+)/m,            // Cisco, Arista, Brocade, MLX
        /^sysname\s+(\S+)/m,             // Huawei
        /set system host-name\s+(\S+)/m, // Juniper
        /<hostname>([^<\s]+)/,            // PAN-OS
    ];
    for (const re of patterns) {
        const m = config.match(re);
        if (m) return m[1];
    }
    return '';
}

// ─── HISTORY ─────────────────────────────────────────────────────────────────
function getHistory() {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'); }
    catch { return []; }
}

function saveToHistory(entry) {
    const history = getHistory();
    history.unshift({ id: Date.now().toString(), savedAt: new Date().toISOString(), ...entry });
    if (history.length > HISTORY_MAX) history.splice(HISTORY_MAX);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}

function deleteMigration(id) {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(getHistory().filter(h => h.id !== id)));
}

// ─── SAVED SOURCES ───────────────────────────────────────────────────────────
function getSavedSources() {
    try { return JSON.parse(localStorage.getItem(SAVED_SOURCES_KEY) || '[]'); }
    catch { return []; }
}

function saveSource(entry) {
    const sources = getSavedSources();
    sources.unshift({ id: Date.now().toString(), savedAt: new Date().toISOString(), ...entry });
    localStorage.setItem(SAVED_SOURCES_KEY, JSON.stringify(sources));
}

function deleteSource(id) {
    localStorage.setItem(SAVED_SOURCES_KEY, JSON.stringify(getSavedSources().filter(s => s.id !== id)));
}

// ─── TIME UTILITIES ───────────────────────────────────────────────────────────
function relativeTime(iso) {
    const diff = Date.now() - new Date(iso).getTime();
    const m = Math.floor(diff / 60000);
    const h = Math.floor(diff / 3600000);
    const d = Math.floor(diff / 86400000);
    if (m < 1)  return 'just now';
    if (m < 60) return m + 'm ago';
    if (h < 24) return h + 'h ago';
    if (d === 1) return 'yesterday';
    return d + ' days ago';
}

function freshnessClass(iso) {
    const d = (Date.now() - new Date(iso).getTime()) / 86400000;
    if (d < 7)  return 'fresh';
    if (d < 30) return 'stale';
    return 'old';
}

function formatDate(iso) {
    return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
}

const VENDOR_LABELS = { mlx: 'MLX', arista: 'Arista', cisco: 'Cisco', juniper: 'Juniper', brocade: 'Brocade', huawei: 'Huawei', panos: 'PAN-OS' };

// ─── INTERFACE EXTRACTION ────────────────────────────────────────────────────
function extractInterfaces(config, vendor) {
    if (!config) return [];
    const ifaces = new Set();
    if (vendor === 'juniper') {
        // set interfaces ge-0/0/0 { ... } or set interfaces ae0 ...
        for (const m of config.matchAll(/^set interfaces (\S+)/gm)) {
            if (m[1] && !m[1].startsWith('[')) ifaces.add(m[1]);
        }
    } else if (vendor === 'panos') {
        for (const m of config.matchAll(/name="([^"]+)"/g)) ifaces.add(m[1]);
    } else {
        // Cisco, Arista, Huawei, Brocade, MLX — all use "interface <name>"
        for (const m of config.matchAll(/^interface\s+(.+)/gim)) {
            ifaces.add(m[1].trim());
        }
    }
    return [...ifaces];
}

function ifaceChipsHTML(ifaces) {
    if (!ifaces || ifaces.length === 0) return '';
    const MAX = 6;
    const shown = ifaces.slice(0, MAX);
    const extra = ifaces.length - MAX;
    return '<div class="history-ifaces">' +
        shown.map(i => '<span class="history-iface-chip">' + escapeHtml(i) + '</span>').join('') +
        (extra > 0 ? '<span class="history-iface-chip history-iface-more">+' + extra + ' more</span>' : '') +
    '</div>';
}

function escapeHtml(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─── THEME FUNCTIONS ─────────────────────────────────────────────────────────
function applyTheme(themeId) {
    document.body.className = document.body.className
        .split(' ').filter(c => !c.startsWith('theme-')).join(' ');
    if (themeId !== 'default') document.body.classList.add('theme-' + themeId);
    localStorage.setItem(STORAGE_KEY, themeId);
    const theme = THEMES.find(t => t.id === themeId) || THEMES[0];
    const label = document.getElementById('theme-label');
    if (label) label.textContent = theme.name;
    document.querySelectorAll('.theme-card').forEach(card => {
        const isActive = card.dataset.themeId === themeId;
        card.classList.toggle('active', isActive);
        card.style.borderColor = isActive ? theme.primary : '';
        const check = card.querySelector('.theme-card-check');
        if (check) check.style.backgroundColor = isActive ? theme.primary : '';
    });
}

function buildThemeGrid() {
    const grid = document.getElementById('theme-grid');
    if (!grid) return;
    const currentThemeId = localStorage.getItem(STORAGE_KEY) || 'default';
    grid.innerHTML = THEMES.map(theme => {
        const isActive = theme.id === currentThemeId;
        const isLight = ['monochrome-light','cyber-light','arctic-light','bubblegum'].includes(theme.id);
        const textColor = isLight ? '#1e293b' : '#f8fafc';
        const descColor = isLight ? '#475569' : 'rgba(248,250,252,0.6)';
        return '<div class="theme-card ' + (isActive ? 'active' : '') + '" data-theme-id="' + theme.id + '" style="background:' + theme.bg + ';border-color:' + (isActive ? theme.primary : 'rgba(255,255,255,0.1)') + ';color:' + textColor + '">' +
            '<div class="theme-card-check" style="background-color:' + (isActive ? theme.primary : 'transparent') + '">&#x2713;</div>' +
            '<div class="theme-card-swatches">' +
                '<div class="theme-swatch large" style="background:' + theme.bg + ';border-color:rgba(255,255,255,0.2)"></div>' +
                '<div class="theme-swatch" style="background:' + theme.primary + '"></div>' +
                '<div class="theme-swatch" style="background:' + theme.accent + '"></div>' +
            '</div>' +
            '<div class="theme-card-name" style="color:' + textColor + '">' + theme.name + '</div>' +
            '<div class="theme-card-desc" style="color:' + descColor + '">' + theme.desc + '</div>' +
        '</div>';
    }).join('');
    grid.querySelectorAll('.theme-card').forEach(card => {
        card.addEventListener('click', () => applyTheme(card.dataset.themeId));
    });
}

// ─── HISTORY MODAL ───────────────────────────────────────────────────────────
let activeHistoryTab = 'migrations';

function buildHistoryContent() {
    const container = document.getElementById('history-content');
    if (!container) return;

    // Update tab active state
    document.querySelectorAll('.history-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === activeHistoryTab);
    });

    if (activeHistoryTab === 'migrations') {
        const history = getHistory();
        if (history.length === 0) {
            container.innerHTML = '<div class="history-empty"><svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg><p>No migrations yet.<br>Run a migration to see it here.</p></div>';
            return;
        }
        container.innerHTML = history.map(entry => {
            const fc = freshnessClass(entry.savedAt);
            const srcLabel = VENDOR_LABELS[entry.sourceVendor] || entry.sourceVendor;
            const tgtLabel = VENDOR_LABELS[entry.targetVendor] || entry.targetVendor;
            const ifaces   = extractInterfaces(entry.sourceConfig, entry.sourceVendor);
            return '<div class="history-entry" data-id="' + entry.id + '">' +
                '<div class="history-entry-main">' +
                    '<div class="history-entry-left">' +
                        '<span class="freshness-dot ' + fc + '" title="' + (fc === 'fresh' ? 'Fresh (< 7 days)' : fc === 'stale' ? 'Getting old (< 30 days)' : 'Old (30+ days)') + '"></span>' +
                        '<div>' +
                            '<div class="history-hostname">' + escapeHtml(entry.hostname || '') + (entry.hostname ? '' : '<span class="history-no-hostname">unknown host</span>') + '</div>' +
                            '<div class="history-vendors">' + srcLabel + ' <span class="history-arrow">&#x2192;</span> ' + tgtLabel + '</div>' +
                        '</div>' +
                    '</div>' +
                    '<div class="history-entry-right">' +
                        '<div class="history-date" title="' + new Date(entry.savedAt).toLocaleString() + '">' + relativeTime(entry.savedAt) + '</div>' +
                        '<div class="history-entry-actions">' +
                            '<button class="history-load-btn" data-id="' + entry.id + '">Load</button>' +
                            '<button class="history-delete-btn" data-id="' + entry.id + '" title="Delete">&#x2715;</button>' +
                        '</div>' +
                    '</div>' +
                '</div>' +
                ifaceChipsHTML(ifaces) +
            '</div>';
        }).join('');
    } else {
        const sources = getSavedSources();
        if (sources.length === 0) {
            container.innerHTML = '<div class="history-empty"><svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg><p>No saved sources yet.<br>Use the &#x1F4BE; button in the Source panel to save a config.</p></div>';
            return;
        }
        container.innerHTML = sources.map(src => {
            const fc = freshnessClass(src.savedAt);
            const vendorLabel = VENDOR_LABELS[src.vendor] || src.vendor;
            const ifaces = extractInterfaces(src.config, src.vendor);
            return '<div class="history-entry" data-id="' + src.id + '">' +
                '<div class="history-entry-main">' +
                    '<div class="history-entry-left">' +
                        '<span class="freshness-dot ' + fc + '" title="' + (fc === 'fresh' ? 'Fresh (< 7 days)' : fc === 'stale' ? 'Getting old (< 30 days)' : 'Old (30+ days)') + '"></span>' +
                        '<div>' +
                            '<div class="history-hostname">' + escapeHtml(src.hostname || '') + (src.hostname ? '' : '<span class="history-no-hostname">unknown host</span>') + '</div>' +
                            '<div class="history-vendors">' + vendorLabel + '</div>' +
                        '</div>' +
                    '</div>' +
                    '<div class="history-entry-right">' +
                        '<div class="history-date" title="Saved ' + new Date(src.savedAt).toLocaleString() + '">Saved ' + formatDate(src.savedAt) + '</div>' +
                        '<div class="history-entry-actions">' +
                            '<button class="history-load-btn source-load-btn" data-id="' + src.id + '">Load</button>' +
                            '<button class="history-delete-btn source-delete-btn" data-id="' + src.id + '" title="Delete">&#x2715;</button>' +
                        '</div>' +
                    '</div>' +
                '</div>' +
                ifaceChipsHTML(ifaces) +
            '</div>';
        }).join('');
    }
}

// ─── DOM READY ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {

    // ── Theme Picker ─────────────────────────────────────────────────────────
    const themeBtn      = document.getElementById('theme-btn');
    const themeModal    = document.getElementById('theme-modal');
    const themeBackdrop = document.getElementById('theme-backdrop');
    const themeClose    = document.getElementById('theme-close');

    const savedTheme = localStorage.getItem(STORAGE_KEY) || 'default';
    applyTheme(savedTheme);

    function openThemeModal()  { buildThemeGrid(); themeModal.classList.remove('hidden'); }
    function closeThemeModal() { themeModal.classList.add('hidden'); }

    if (themeBtn)      themeBtn.addEventListener('click', openThemeModal);
    if (themeClose)    themeClose.addEventListener('click', closeThemeModal);
    if (themeBackdrop) themeBackdrop.addEventListener('click', closeThemeModal);

    // ── History Modal ────────────────────────────────────────────────────────
    const historyBtn      = document.getElementById('history-btn');
    const historyModal    = document.getElementById('history-modal');
    const historyBackdrop = document.getElementById('history-backdrop');
    const historyClose    = document.getElementById('history-close');
    const historyContent  = document.getElementById('history-content');

    function openHistoryModal() {
        activeHistoryTab = 'migrations';
        buildHistoryContent();
        historyModal.classList.remove('hidden');
    }
    function closeHistoryModal() { historyModal.classList.add('hidden'); }

    if (historyBtn)      historyBtn.addEventListener('click', openHistoryModal);
    if (historyClose)    historyClose.addEventListener('click', closeHistoryModal);
    if (historyBackdrop) historyBackdrop.addEventListener('click', closeHistoryModal);

    // Tab switching
    document.querySelectorAll('.history-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            activeHistoryTab = btn.dataset.tab;
            buildHistoryContent();
        });
    });

    // Event delegation for load/delete buttons inside history modal
    if (historyContent) {
        historyContent.addEventListener('click', e => {
            const loadBtn   = e.target.closest('.history-load-btn');
            const deleteBtn = e.target.closest('.history-delete-btn');

            if (loadBtn) {
                const id = loadBtn.dataset.id;
                if (loadBtn.classList.contains('source-load-btn')) {
                    // Load saved source
                    const src = getSavedSources().find(s => s.id === id);
                    if (src) {
                        document.getElementById('source-vendor').value = src.vendor;
                        document.getElementById('source-config').value = src.config;
                        closeHistoryModal();
                        showToast('Source loaded: ' + (src.hostname || src.vendor), 'success');
                    }
                } else {
                    // Load full migration
                    const entry = getHistory().find(h => h.id === id);
                    if (entry) {
                        document.getElementById('source-vendor').value  = entry.sourceVendor;
                        document.getElementById('target-vendor').value  = entry.targetVendor;
                        document.getElementById('source-config').value  = entry.sourceConfig;
                        document.getElementById('target-config').value  = entry.targetConfig;
                        const outputConfig   = document.getElementById('output-config');
                        const resultsSection = document.getElementById('results-section');
                        if (entry.output && outputConfig && resultsSection) {
                            outputConfig.textContent = entry.output;
                            resultsSection.classList.remove('hidden');
                        }
                        closeHistoryModal();
                        showToast('Migration loaded: ' + (entry.hostname || entry.sourceVendor + ' → ' + entry.targetVendor), 'success');
                    }
                }
            }

            if (deleteBtn) {
                const id = deleteBtn.dataset.id;
                if (deleteBtn.classList.contains('source-delete-btn')) {
                    deleteSource(id);
                } else {
                    deleteMigration(id);
                }
                buildHistoryContent();
            }
        });
    }

    // ── Save Source Dialog ───────────────────────────────────────────────────
    const saveSourceBtn     = document.getElementById('save-source-btn');
    const saveSourceModal   = document.getElementById('save-source-modal');
    const saveSourceBackdrop = document.getElementById('save-source-backdrop');
    const saveSourceClose   = document.getElementById('save-source-close');
    const saveSourceCancel  = document.getElementById('save-source-cancel');
    const saveSourceConfirm = document.getElementById('save-source-confirm');
    const saveSourceHostnameInput = document.getElementById('save-source-hostname');

    function openSaveSourceDialog() {
        const config = document.getElementById('source-config').value.trim();
        if (!config) { showToast('Paste a source config first.', 'error'); return; }
        const extracted = extractHostname(config);
        saveSourceHostnameInput.value = extracted;
        saveSourceModal.classList.remove('hidden');
        saveSourceHostnameInput.focus();
        saveSourceHostnameInput.select();
    }

    function closeSaveSourceDialog() { saveSourceModal.classList.add('hidden'); }

    if (saveSourceBtn)      saveSourceBtn.addEventListener('click', openSaveSourceDialog);
    if (saveSourceClose)    saveSourceClose.addEventListener('click', closeSaveSourceDialog);
    if (saveSourceCancel)   saveSourceCancel.addEventListener('click', closeSaveSourceDialog);
    if (saveSourceBackdrop) saveSourceBackdrop.addEventListener('click', closeSaveSourceDialog);

    if (saveSourceConfirm) {
        saveSourceConfirm.addEventListener('click', () => {
            const config    = document.getElementById('source-config').value.trim();
            const vendor    = document.getElementById('source-vendor').value;
            const hostname  = saveSourceHostnameInput.value.trim() || extractHostname(config) || vendor;
            saveSource({ vendor, config, hostname });
            closeSaveSourceDialog();
            showToast('Source saved: ' + hostname, 'success');
        });
    }

    // Confirm on Enter in hostname field
    if (saveSourceHostnameInput) {
        saveSourceHostnameInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') saveSourceConfirm && saveSourceConfirm.click();
            if (e.key === 'Escape') closeSaveSourceDialog();
        });
    }

    // Global Escape key
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
            closeThemeModal();
            closeHistoryModal();
            closeSaveSourceDialog();
        }
    });

    // ── Migration Logic ───────────────────────────────────────────────────────
    const migrateBtn     = document.getElementById('migrate-btn');
    const sourceVendor   = document.getElementById('source-vendor');
    const targetVendor   = document.getElementById('target-vendor');
    const sourceConfig   = document.getElementById('source-config');
    const targetConfig   = document.getElementById('target-config');
    const resultsSection = document.getElementById('results-section');
    const outputConfig   = document.getElementById('output-config');
    const copyBtn        = document.getElementById('copy-btn');
    const loadingOverlay = document.getElementById('loading-overlay');
    const toast          = document.getElementById('toast');

    function showToast(message, type) {
        if (!toast) return;
        toast.textContent = message;
        toast.className = 'toast ' + (type || 'success');
        toast.classList.remove('hidden');
        setTimeout(() => toast.classList.add('hidden'), 3000);
    }

    // Make showToast available to the closure above
    window._showToast = showToast;

    if (copyBtn) {
        copyBtn.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(outputConfig.textContent);
                showToast('Copied to clipboard!', 'success');
            } catch {
                showToast('Failed to copy text', 'error');
            }
        });
    }

    if (migrateBtn) {
        migrateBtn.addEventListener('click', async () => {
            const sVendor = sourceVendor.value;
            const tVendor = targetVendor.value;
            const sConfig = sourceConfig.value.trim();
            const tConfig = targetConfig.value.trim();

            if (!sConfig || !tConfig) {
                showToast('Please provide both source and target configurations.', 'error');
                return;
            }

            loadingOverlay.classList.remove('hidden');
            resultsSection.classList.add('hidden');

            try {
                const response = await fetch('/api/migrate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        source_vendor: sVendor,
                        target_vendor: tVendor,
                        source_config: sConfig,
                        target_config: tConfig
                    })
                });

                const data = await response.json();
                if (!response.ok) throw new Error(data.detail || 'Migration failed');

                outputConfig.textContent = data.output;
                resultsSection.classList.remove('hidden');
                resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                showToast('Migration successful!', 'success');

                // Auto-save to history
                saveToHistory({
                    sourceVendor: sVendor,
                    targetVendor: tVendor,
                    sourceConfig: sConfig,
                    targetConfig: tConfig,
                    output:       data.output,
                    hostname:     extractHostname(sConfig),
                });

            } catch (error) {
                showToast(error.message, 'error');
                console.error('Migration error:', error);
            } finally {
                loadingOverlay.classList.add('hidden');
            }
        });
    }
});

// Patch showToast for event-delegation callbacks defined before DOM ready
function showToast(message, type) {
    if (window._showToast) { window._showToast(message, type); }
}
