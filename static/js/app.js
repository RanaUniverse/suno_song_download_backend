let selectedFormat = "mp3";
let currentFilename = "";
let currentTotalDuration = 0;
let selectedPreset = "auto";

function setWave(id, isPlaying) {
    const el = document.getElementById(id);
    if (el) {
        if (isPlaying) el.classList.add('playing');
        else el.classList.remove('playing');
    }
}

function setFormat(fmt) {
    selectedFormat = fmt;
    document.getElementById('tabMp3').classList.toggle('active', fmt === 'mp3');
    document.getElementById('tabM4a').classList.toggle('active', fmt === 'm4a');
    document.getElementById('tabWav').classList.toggle('active', fmt === 'wav');
}

async function pasteFromClipboard() {
    try {
        const text = await navigator.clipboard.readText();
        if (text) {
            document.getElementById('sunoUrl').value = text.trim();
        }
    } catch (err) {
        alert('Tap and hold the text box to paste.');
    }
}

function selectPreset(preset, btnElement) {
    selectedPreset = preset;
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
    if (btnElement) {
        btnElement.classList.add('active');
    }
}

// Allow Enter to be pressed in the input
document.addEventListener("DOMContentLoaded", () => {
    const inp = document.getElementById('sunoUrl');
    if (inp) {
        inp.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                e.preventDefault();
                startDownload();
            }
        });
    }
});

async function startDownload() {
    const urlInput = document.getElementById('sunoUrl');
    const url = urlInput.value.trim();
    if (!url) {
        alert('Please paste a Suno link.');
        return;
    }

    const btn = document.getElementById('btnDownload');
    const statusBadge = document.getElementById('statusBadge');
    const resultBox = document.getElementById('resultBox');
    const stemResultBox = document.getElementById('stemResultBox');
    const sampleResultBox = document.getElementById('sampleResultBox');

    btn.disabled = true;
    btn.innerHTML = `<div class="spinner"></div> Processing audio (${selectedFormat.toUpperCase()})...`;
    statusBadge.style.display = 'block';
    statusBadge.innerText = `Connecting to Suno and decrypting audio (${selectedFormat.toUpperCase()})...`;

    stemResultBox.style.display = 'none';
    sampleResultBox.style.display = 'none';

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000);

        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url, format: selectedFormat }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        const data = await response.json();

        if (!response.ok || data.error) {
            throw new Error(data.error || 'Error processing the song.');
        }

        currentFilename = data.filename;
        currentTotalDuration = data.duration_seconds || 0;

        // Show results & fill player
        document.getElementById('resTitle').innerText = data.title;
        document.getElementById('resTags').innerText = data.tags || 'Suno AI Track';
        document.getElementById('resCover').src = data.cover_url || '';
        document.getElementById('resDuration').innerText = `⏱️ ${data.duration_formatted || '0:00'}`;
        document.getElementById('resFormat').innerText = (data.format || selectedFormat).toUpperCase();

        const audioPlayer = document.getElementById('resAudio');
        audioPlayer.src = data.download_url;
        try { audioPlayer.load(); } catch (e) { }

        const dlLink = document.getElementById('resDownloadLink');
        dlLink.href = data.download_url;
        dlLink.setAttribute('download', data.filename);
        dlLink.innerHTML = `📥 Save Full Song (${(data.format || selectedFormat).toUpperCase()})`;

        // Update sample description with suggested duration
        const suggestedDur = data.suggested_sample_formatted || '1-2 minutes';
        document.getElementById('sampleDescText').innerText =
            `Song duration: ${data.duration_formatted || 'standard duration'}. Suggested sample duration: ${suggestedDur}.`;

        statusBadge.innerText = `✅ Song ready to listen to and download in ${selectedFormat.toUpperCase()}!`;
        resultBox.style.display = 'block';
        resultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        try { await loadHistory(); } catch (e) { }

    } catch (err) {
        console.error(err);
        const isAbort = err.name === 'AbortError';
        const msg = isAbort ? 'The server took too long to respond. Check whether the file is already in the list below.' : err.message;
        alert('Notice: ' + msg);
        statusBadge.innerText = '⚠️ ' + msg;
        try { await loadHistory(); } catch (e) { }
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>🎧 LOAD, LISTEN, AND DOWNLOAD</span>';
    }
}

async function separateStems() {
    if (!currentFilename) {
        alert('Load a song first.');
        return;
    }

    const btn = document.getElementById('btnCreateStem');
    const stemResultBox = document.getElementById('stemResultBox');
    const instAudio = document.getElementById('instAudioPlayer');
    const instDlLink = document.getElementById('instDownloadLink');
    const vocalAudio = document.getElementById('vocalAudioPlayer');
    const vocalDlLink = document.getElementById('vocalDownloadLink');

    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div> Separating Track and Vocals with DSP...';

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 90000);

        const response = await fetch('/api/separate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: currentFilename,
                format: selectedFormat
            }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);

        const data = await response.json();

        if (!response.ok || data.error) {
            throw new Error(data.error || 'Error separating the track and vocals.');
        }

        instAudio.src = data.instrumental_url;
        try { instAudio.load(); } catch (e) { }
        instDlLink.href = data.instrumental_url;
        instDlLink.setAttribute('download', data.instrumental_filename);

        vocalAudio.src = data.vocals_url;
        try { vocalAudio.load(); } catch (e) { }
        vocalDlLink.href = data.vocals_url;
        vocalDlLink.setAttribute('download', data.vocals_filename);

        stemResultBox.style.display = 'block';
        stemResultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        try { await loadHistory(); } catch (e) { }

    } catch (err) {
        console.error(err);
        alert('Error separating: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>✨ SEPARATE INTO TRACK AND VOCALS</span>';
    }
}

async function generateSample() {
    if (!currentFilename) {
        alert('Load a song first.');
        return;
    }

    const btn = document.getElementById('btnCreateSample');
    const sampleResultBox = document.getElementById('sampleResultBox');
    const sampleAudio = document.getElementById('sampleAudioPlayer');
    const sampleDlLink = document.getElementById('sampleDownloadLink');
    const sampleLabel = document.getElementById('sampleResultLabel');

    btn.disabled = true;
    btn.innerHTML = '<div class="spinner spinner-dark"></div> Trimming sample with FFmpeg...';

    try {
        const response = await fetch('/api/sample', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: currentFilename,
                preset: selectedPreset
            })
        });

        const data = await response.json();

        if (!response.ok || data.error) {
            throw new Error(data.error || 'Error generating the sample.');
        }

        sampleAudio.src = data.sample_url;
        try { sampleAudio.load(); } catch (e) { }
        sampleDlLink.href = data.sample_url;
        sampleDlLink.setAttribute('download', data.filename);
        sampleLabel.innerText = `🎧 Sample ready (${Math.round(data.sample_duration)}s):`;

        sampleResultBox.style.display = 'block';
        sampleResultBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        try { await loadHistory(); } catch (e) { }

    } catch (err) {
        alert('Error generating sample: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span>✂️ GENERATE SAMPLE</span>';
    }
}

async function loadHistory() {
    try {
        const res = await fetch('/api/files');
        const files = await res.json();
        const list = document.getElementById('historyList');
        list.innerHTML = '';

        if (files.length === 0) {
            list.innerHTML = '<div style="color:#71717a; font-size:12px; text-align:center;">No recent downloads yet.</div>';
            return;
        }

        files.forEach(f => {
            const item = document.createElement('div');
            const isInst = f.name.includes('_instrumental_track');
            const isVocal = f.name.includes('_vocals_only');
            const isSample = f.name.includes('_sample');
            const isWav = f.filename.endsWith('.wav');
            const isM4a = f.filename.endsWith('.m4a');

            let itemClass = 'history-item';
            let badge = '';

            if (isInst) {
                itemClass += ' is-inst';
                badge += '<span class="history-badge inst">🎹 Instrumental</span>';
            } else if (isVocal) {
                itemClass += ' is-vocal';
                badge += '<span class="history-badge vocal">🎙️ Vocals</span>';
            } else if (isSample) {
                itemClass += ' is-sample';
                badge += '<span class="history-badge sample">✂️ Sample</span>';
            }

            if (isWav) {
                badge += '<span class="history-badge wav">WAV</span>';
            } else if (isM4a) {
                badge += '<span class="history-badge m4a">M4A</span>';
            } else {
                badge += '<span class="history-badge mp3">MP3</span>';
            }

            item.className = itemClass;
            item.innerHTML = `
                        <span class="history-name">${badge} ${f.name}</span>
                        <a class="history-btn" href="/downloads/${encodeURIComponent(f.filename)}" download>Download</a>
                    `;
            list.appendChild(item);
        });
    } catch (e) {
        console.error(e);
    }
}

// Load history at startup
loadHistory();
