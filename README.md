# Viz-Reels Automation Pipeline

Automated HTML animation & native Web Audio API sound effects to 9:16 vertical video (Reels / Shorts / TikTok) generation and social publishing pipeline.

## 🚀 Key Features

- **Native Web Audio API SFX Capture**: Intercepts in-browser audio synthesis (`AudioContext`, `createOscillator`, `createGain`, `createBiquadFilter`) via `MediaStreamAudioDestinationNode` and captures high-fidelity lossless sound effects synced from $t=0$.
- **True 1080x1920 @ 60 FPS**: Automatically scales 540x960 logical canvas stages by 2x to full vertical resolution with crisp text rendering.
- **Google Drive Auto-Sync**: Automatically syncs newly added HTML files from Google Drive (`1OnHqUxj0B9TEBuu1Qq0RTHqoqgXbvr_G`) and music tracks (`19zTCpkmKpZwUm8j8gnvfHZqVJqfwEz9I`).
- **Canonical Weighted LRU Selection**: Strict priority to unpublished items; applies exponential inverse weights $\max(1, \lfloor 1000 / 3^{\min(N, 6)} \rfloor)$ in recirculation mode.
- **Pollinations AI Metadata**: Dynamic high-engagement social media titles, Instagram captions, Facebook captions, and trending tech hashtags.
- **Meta Resumable Reels Upload**: Streams video bytes directly to Meta servers (`rupload.facebook.com`) targeting the **`kreggscode`** Facebook Page (`503243842882427`) and **`@kreggscode`** Instagram Account (`17841452339411557`).
- **Daily Automated Cloud Execution**: Scheduled via GitHub Actions (`0 9 * * *` UTC / 14:30 IST) with full history committed back to master.

## 📁 Project Structure

```
viz-reels/
├── .github/workflows/
│   └── automate.yml           # Once-daily scheduled GitHub Actions workflow
├── html_sources/              # Downloaded HTML animations
├── music/                     # Looping background music tracks
├── output/                    # Local renders (.gitignored)
├── upload/                    # Meta Graph API uploaders
│   ├── upload_facebook.py     # Facebook Page Reels Resumable Uploader
│   ├── upload_instagram.py    # Instagram Reels Resumable Uploader
│   └── upload_threads.py      # Threads Uploader
├── converter.py               # Playwright + Web Audio SFX capture + FFmpeg muxer
├── generate_metadata.py       # Pollinations AI metadata generation
├── orchestrator.py            # Daily pipeline coordinator with Weighted LRU
├── publish.py                 # Multi-platform social publisher
├── sync_gdrive.py             # Google Drive Service Account synchronizer
└── requirements.txt
```

## 🛠️ Local Usage

### Convert a Single HTML File to 1080x1920 Video with Sound Effects
```bash
python converter.py "html_sources/01-kafka-vs-rabbitmq.html"
```

### Run Full Automation Cycle (Render + Pollinations AI Metadata + Publish)
```bash
python orchestrator.py --publish
```
