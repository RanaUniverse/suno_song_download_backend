# 🎵 Suno AI Downloader, WAV & Stem Separator HQ

A comprehensive tool to download and decrypt shared songs from **Suno.com** in **MP3 320 kbps** or **WAV Lossless (Uncompressed Audio)**, extract **audio samples (clips)**, and **separate instrumental tracks from vocals (acapella)** with high-fidelity stereo DSP processing.

---

## ✨ New Features

- 💿 **WAV Lossless Download (PCM 16-bit)**: Maximum audio fidelity for editing, production, and mixing.
- 🎵 **Standard MP3 Download (320 kbps HQ)**: Full compatibility with players and mobile devices.
- 🎤 **Track & Vocal Separator (Stems)**:
  - 🎹 **Instrumental Track**: Isolates the music/karaoke while preserving kicks, bass, and rhythmic frequencies.
  - 🎙️ **Vocals Only (Acapella)**: Isolates clean vocals and vocal formants for remixes or studio use.
- ✂️ **Sample Extractor (Previews)**: Generates automatic clips (30s, 1m, 2m) with fade-in and fade-out effects.

---

## 🚀 How to Use

### 1. From Your Mobile Phone / Web Browser (Recommended for Mobile)
Double-click on:
👉 `start_for_mobile.bat`

- Open the displayed IP address or scan the QR code with your phone.
- Choose your desired format: **MP3 (320 kbps)** or **WAV (Lossless)**.
- **🎤 Track & Vocal Separator**: Tap *✨ SEPARATE TRACK AND VOCALS* to generate and listen individually to the instrumental track and vocals, with direct download buttons for your phone.
- **✂️ Samples**: Extract clips of 30s, 1 min, 2 min, or Auto.

---

### 2. Using the Desktop Interface (GUI)
Double-click on:
👉 `start_suno_downloader.bat`

- Select the **MP3** or **WAV** format.
- Paste the Suno link using the **📋 Paste** button.
- Download the complete song along with its cover art and lyrics.
- Use the **🎤 TRACK & VOCAL SEPARATOR** section to generate and playback the Instrumental Track and Vocals separately.
- Use the **✂️ DOWNLOAD SAMPLE** section to save short clips.

---

### 3. From the Terminal / Console

#### Open the graphical interface:
```bash
python suno_downloader.py --gui
```

#### Download in uncompressed WAV:
```bash
python suno_downloader.py https://suno.com/song/SONG_ID -f wav
```

#### Download and immediately separate into Instrumental Track and Vocals:
```bash
python suno_downloader.py https://suno.com/song/SONG_ID --separate
```

#### Download in WAV, separate track/vocals, and generate a sample:
```bash
python suno_downloader.py https://suno.com/song/SONG_ID -f wav --separate --sample 60
```

---

## 🔗 Compatible Link Formats

- `https://suno.com/song/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- `https://suno.com/s/xxxxxx` (shortened links)
- `https://app.suno.ai/song/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
- Or directly the UUID: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`