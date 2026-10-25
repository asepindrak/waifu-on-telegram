/**
 * Antigravity Telegram Bot - Music Player Server
 * Uses ytmusic-api to search songs & playlists with high precision.
 * Provides a local YouTube Iframe Web Player on PC with full remote control
 * (Play, Pause, Resume, Next, Prev, Stop, Link, Auto-play queues).
 */

const http = require('http');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');

let YTMusic;
try {
  YTMusic = require('ytmusic-api').default || require('ytmusic-api');
} catch (e) {
  console.error('[Music Server] Failed to import ytmusic-api:', e.message);
}

const PORT = parseInt(process.env.MUSIC_PLAYER_PORT || '8002', 10);
const HOST = process.env.MUSIC_PLAYER_HOST || '0.0.0.0';

// Initialize YTMusic API
const ytmusic = YTMusic ? new YTMusic() : null;
let ytmusicReady = false;

if (ytmusic) {
  ytmusic.initialize()
    .then(() => {
      ytmusicReady = true;
      console.log('✓ [Music Server] ytmusic-api initialized successfully.');
    })
    .catch((err) => {
      console.error('⚠️ [Music Server] Error initializing ytmusic-api:', err.message);
    });
}

// Player State
const state = {
  enabled: process.env.MUSIC_FEATURE_ENABLED !== 'false',
  autoPlayPC: process.env.MUSIC_AUTO_PLAY_PC !== 'false',
  playbackState: 'STOPPED', // 'PLAYING', 'PAUSED', 'STOPPED', 'BUFFERING'
  queue: [],
  currentIndex: -1,
  currentTime: 0,
  duration: 0,
  volume: 100,
  lastAction: null,
  browserConnected: false,
};

// Connected SSE clients for real-time web player sync
const sseClients = new Set();

function broadcast(action, data = {}) {
  const payload = `event: message\ndata: ${JSON.stringify({ action, ...data, timestamp: Date.now() })}\n\n`;
  for (const client of sseClients) {
    try {
      client.write(payload);
    } catch (e) {
      sseClients.delete(client);
    }
  }
}

function formatDuration(seconds) {
  if (!seconds || isNaN(seconds)) return '00:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins < 10 ? '0' : ''}${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

function normalizeTrack(raw) {
  if (!raw) return null;
  const videoId = raw.videoId || raw.id;
  if (!videoId) return null;

  let artistName = 'Unknown Artist';
  if (raw.artist) {
    artistName = typeof raw.artist === 'string' ? raw.artist : (raw.artist.name || 'Unknown Artist');
  } else if (raw.artists && raw.artists.length > 0) {
    artistName = raw.artists.map(a => typeof a === 'string' ? a : a.name).join(', ');
  }

  let albumName = '';
  if (raw.album) {
    albumName = typeof raw.album === 'string' ? raw.album : (raw.album.name || '');
  }

  let thumbnail = '';
  if (Array.isArray(raw.thumbnails) && raw.thumbnails.length > 0) {
    thumbnail = raw.thumbnails[raw.thumbnails.length - 1].url;
  } else if (typeof raw.thumbnail === 'string') {
    thumbnail = raw.thumbnail;
  } else {
    thumbnail = `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;
  }

  const duration = parseInt(raw.duration || 0, 10);

  return {
    videoId,
    title: raw.name || raw.title || 'Untitled Track',
    artist: artistName,
    album: albumName,
    duration,
    durationFormatted: formatDuration(duration),
    thumbnail,
    youtubeUrl: `https://www.youtube.com/watch?v=${videoId}`,
    ytMusicUrl: `https://music.youtube.com/watch?v=${videoId}`,
  };
}

function openPlayerInBrowser() {
  const playerUrl = `http://localhost:${PORT}/player`;
  const platform = process.platform;
  console.log(`[Music Server] Launching browser for: ${playerUrl}`);

  if (platform === 'win32') {
    // On Windows, 'start' via cmd or explorer uses the active desktop shell and avoids Chrome ProcessSingleton lockouts
    exec(`cmd.exe /c start "" "${playerUrl}"`, (err) => {
      if (err) {
        exec(`powershell -NoProfile -Command "Start-Process '${playerUrl}'"`, (err2) => {
          if (err2) {
            exec(`explorer.exe "${playerUrl}"`);
          }
        });
      }
    });
  } else if (platform === 'darwin') {
    exec(`open "${playerUrl}"`);
  } else {
    exec(`xdg-open "${playerUrl}"`);
  }
}

// Helpers for Searching and Playlist Creation
async function searchSongsWithRetry(query, limit = 10) {
  if (!ytmusicReady && ytmusic) {
    try {
      await ytmusic.initialize();
      ytmusicReady = true;
    } catch (e) {}
  }
  if (!ytmusicReady) {
    throw new Error('ytmusic-api is not ready. Please try again in a few moments.');
  }

  const results = await ytmusic.searchSongs(query);
  const songs = (results || []).slice(0, limit).map(normalizeTrack).filter(Boolean);
  return songs;
}

async function createPlaylistFromQuery(query, limit = 10) {
  if (!ytmusicReady && ytmusic) {
    try {
      await ytmusic.initialize();
      ytmusicReady = true;
    } catch (e) {}
  }

  let tracks = [];
  let playlistTitle = query;

  try {
    const playlists = await ytmusic.searchPlaylists(query);
    if (playlists && playlists.length > 0) {
      const topPl = playlists[0];
      playlistTitle = topPl.name || query;
      const plVideos = await ytmusic.getPlaylistVideos(topPl.playlistId);
      if (plVideos && plVideos.length > 0) {
        tracks = plVideos.slice(0, limit).map(normalizeTrack).filter(Boolean);
      }
    }
  } catch (err) {
    console.warn('[Music Server] searchPlaylists warning:', err.message);
  }

  if (!tracks || tracks.length === 0) {
    const songs = await ytmusic.searchSongs(query);
    tracks = (songs || []).slice(0, limit).map(normalizeTrack).filter(Boolean);
  }

  return {
    title: playlistTitle,
    tracks,
  };
}

// Embedded Web Player HTML/CSS/JS Template
function getPlayerHtml() {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Antigravity PC Music Player</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-gradient: radial-gradient(circle at 50% 0%, #1e1035 0%, #0d0b18 50%, #06050b 100%);
      --accent-primary: #8a2be2;
      --accent-neon: #00f2fe;
      --accent-glow: rgba(0, 242, 254, 0.35);
      --card-bg: rgba(22, 19, 38, 0.85);
      --border-color: rgba(255, 255, 255, 0.1);
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Outfit', sans-serif;
      background: var(--bg-gradient);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      overflow-x: hidden;
      padding: 24px;
    }

    .ambient-glow {
      position: fixed;
      width: 500px;
      height: 500px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(138, 43, 226, 0.25) 0%, rgba(0, 242, 254, 0.1) 60%, transparent 80%);
      filter: blur(80px);
      z-index: 0;
      pointer-events: none;
      animation: floatGlow 12s infinite alternate ease-in-out;
    }

    @keyframes floatGlow {
      0% { transform: translate(-20%, -20%) scale(1); }
      100% { transform: translate(20%, 20%) scale(1.15); }
    }

    .player-app {
      position: relative;
      z-index: 10;
      width: 100%;
      max-width: 960px;
      background: var(--card-bg);
      backdrop-filter: blur(24px);
      -webkit-backdrop-filter: blur(24px);
      border: 1px solid var(--border-color);
      border-radius: 28px;
      box-shadow: 0 25px 60px rgba(0, 0, 0, 0.6), 0 0 40px var(--accent-glow);
      overflow: hidden;
      display: grid;
      grid-template-columns: 1fr 340px;
    }

    @media (max-width: 840px) {
      .player-app {
        grid-template-columns: 1fr;
      }
    }

    .main-player {
      padding: 32px;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      border-right: 1px solid var(--border-color);
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 16px;
      border-radius: 999px;
      background: rgba(0, 242, 254, 0.12);
      border: 1px solid rgba(0, 242, 254, 0.3);
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--accent-neon);
      margin-bottom: 20px;
      letter-spacing: 0.5px;
    }

    .pulse-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accent-neon);
      box-shadow: 0 0 10px var(--accent-neon);
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    /* YouTube Video / Visual Screen */
    .screen-wrapper {
      position: relative;
      width: 100%;
      max-width: 480px;
      aspect-ratio: 16 / 9;
      border-radius: 20px;
      overflow: hidden;
      margin-bottom: 20px;
      background: #000;
      border: 1px solid var(--border-color);
      box-shadow: 0 16px 36px rgba(0, 0, 0, 0.5), 0 0 25px rgba(138, 43, 226, 0.35);
    }

    #ytplayer {
      width: 100%;
      height: 100%;
      border: none;
    }

    .view-toggle {
      display: flex;
      gap: 10px;
      margin-bottom: 16px;
    }

    .btn-toggle {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--border-color);
      color: var(--text-muted);
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 0.75rem;
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-toggle.active {
      background: rgba(0, 242, 254, 0.15);
      border-color: var(--accent-neon);
      color: var(--accent-neon);
    }

    .song-title {
      font-size: 1.4rem;
      font-weight: 700;
      margin-bottom: 6px;
      color: #fff;
      max-width: 100%;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .song-artist {
      font-size: 1rem;
      color: var(--accent-neon);
      font-weight: 500;
      margin-bottom: 20px;
    }

    .progress-container {
      width: 100%;
      margin-bottom: 20px;
    }

    .progress-bar {
      width: 100%;
      height: 6px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.12);
      cursor: pointer;
      position: relative;
      overflow: hidden;
    }

    .progress-fill {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, var(--accent-primary), var(--accent-neon));
      border-radius: 999px;
      box-shadow: 0 0 10px var(--accent-neon);
      transition: width 0.2s linear;
    }

    .time-labels {
      display: flex;
      justify-content: space-between;
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 8px;
    }

    .controls {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 18px;
      margin-bottom: 18px;
    }

    .btn-ctrl {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--border-color);
      color: #fff;
      width: 48px;
      height: 48px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.2s ease;
      font-size: 1.2rem;
    }

    .btn-ctrl:hover {
      background: rgba(255, 255, 255, 0.15);
      transform: scale(1.08);
      border-color: var(--accent-neon);
      color: var(--accent-neon);
      box-shadow: 0 0 15px var(--accent-glow);
    }

    .btn-play {
      width: 60px;
      height: 60px;
      background: linear-gradient(135deg, var(--accent-primary), #4facfe);
      border: none;
      box-shadow: 0 8px 24px var(--accent-glow);
      font-size: 1.5rem;
    }

    .btn-play:hover {
      transform: scale(1.1);
      box-shadow: 0 12px 30px rgba(0, 242, 254, 0.6);
      color: #fff;
    }

    .volume-row {
      display: flex;
      align-items: center;
      gap: 12px;
      width: 70%;
      color: var(--text-muted);
      font-size: 0.85rem;
    }

    .volume-slider {
      flex: 1;
      accent-color: var(--accent-neon);
      cursor: pointer;
    }

    /* Queue Sidebar */
    .queue-sidebar {
      padding: 30px 24px;
      background: rgba(10, 8, 20, 0.6);
      display: flex;
      flex-direction: column;
      max-height: 600px;
    }

    .queue-header {
      font-size: 1.1rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 18px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-color);
    }

    .queue-count {
      font-size: 0.8rem;
      color: var(--accent-neon);
      background: rgba(0, 242, 254, 0.1);
      padding: 2px 8px;
      border-radius: 999px;
    }

    .queue-list {
      flex: 1;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding-right: 4px;
    }

    .queue-list::-webkit-scrollbar {
      width: 5px;
    }

    .queue-list::-webkit-scrollbar-thumb {
      background: rgba(255, 255, 255, 0.15);
      border-radius: 10px;
    }

    .queue-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid transparent;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .queue-item:hover {
      background: rgba(255, 255, 255, 0.08);
      border-color: rgba(255, 255, 255, 0.15);
      transform: translateX(4px);
    }

    .queue-item.active {
      background: rgba(138, 43, 226, 0.25);
      border-color: var(--accent-neon);
      box-shadow: 0 0 15px rgba(0, 242, 254, 0.2);
    }

    .queue-thumb {
      width: 42px;
      height: 42px;
      border-radius: 8px;
      object-fit: cover;
    }

    .queue-details {
      flex: 1;
      min-width: 0;
      text-align: left;
    }

    .queue-song-name {
      font-size: 0.88rem;
      font-weight: 600;
      color: #fff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .queue-artist-name {
      font-size: 0.78rem;
      color: var(--text-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* Unmute Banner */
    .unmute-banner {
      display: none;
      position: fixed;
      top: 20px;
      background: linear-gradient(135deg, #ff0844, #ffb199);
      color: #fff;
      font-weight: 600;
      padding: 12px 24px;
      border-radius: 30px;
      box-shadow: 0 10px 25px rgba(255, 8, 68, 0.5);
      z-index: 1000;
      cursor: pointer;
      animation: pulse 1.5s infinite;
    }
  </style>
</head>
<body>
  <div class="ambient-glow"></div>

  <div class="unmute-banner" id="unmuteBanner" onclick="enableAudioOutput()">
    🔊 Klik di sini untuk mengaktifkan suara PC (Autoplay Policy)
  </div>

  <div class="player-app">
    <div class="main-player">
      <div class="status-badge">
        <span class="pulse-dot"></span>
        <span id="remoteStatusText">Telegram Remote Connected</span>
      </div>

      <!-- Real YouTube Video Player Screen -->
      <div class="screen-wrapper" id="screenWrapper">
        <div id="ytplayer"></div>
      </div>

      <h1 class="song-title" id="songTitle">Ready to Play</h1>
      <p class="song-artist" id="songArtist">Send /play <song> to Telegram Bot</p>

      <div class="progress-container">
        <div class="progress-bar" id="progressBar" onclick="seekTo(event)">
          <div class="progress-fill" id="progressFill"></div>
        </div>
        <div class="time-labels">
          <span id="currentTime">00:00</span>
          <span id="totalDuration">00:00</span>
        </div>
      </div>

      <div class="controls">
        <button class="btn-ctrl" onclick="sendRemoteAction('prev')" title="Previous Track">⏮</button>
        <button class="btn-ctrl btn-play" id="btnPlayPause" onclick="togglePlayPause()" title="Play / Pause">▶</button>
        <button class="btn-ctrl" onclick="sendRemoteAction('next')" title="Next Track">⏭</button>
        <button class="btn-ctrl" onclick="sendRemoteAction('stop')" title="Stop Playback">⏹</button>
      </div>

      <div class="volume-row">
        <span>🔈</span>
        <input type="range" class="volume-slider" id="volumeSlider" min="0" max="100" value="100" oninput="changeVolume(this.value)">
        <span>🔊</span>
      </div>
    </div>

    <!-- Queue Sidebar -->
    <div class="queue-sidebar">
      <div class="queue-header">
        <span>Up Next Queue</span>
        <span class="queue-count" id="queueCount">0 tracks</span>
      </div>
      <div class="queue-list" id="queueList">
        <div style="color: var(--text-muted); font-size: 0.85rem; padding: 20px 0; text-align: center;">
          Queue is empty.<br>Ask bot for single song or playlist!
        </div>
      </div>
    </div>
  </div>

  <!-- YouTube Iframe API -->
  <script src="https://www.youtube.com/iframe_api"></script>

  <script>
    let ytPlayer = null;
    let isYtReady = false;
    let currentTrack = null;
    let queue = [];
    let currentIndex = -1;
    let isPlaying = false;
    let progressTimer = null;
    let pendingTrack = null;

    // Connect SSE and initialize immediately
    window.addEventListener('DOMContentLoaded', () => {
      connectEventSource();
      fetchInitialStatus();
      setInterval(pollStatusBackup, 2500);
    });

    // YouTube Iframe API Callback
    function onYouTubeIframeAPIReady() {
      console.log('Initializing YouTube Iframe Player...');
      ytPlayer = new YT.Player('ytplayer', {
        height: '100%',
        width: '100%',
        playerVars: {
          'autoplay': 1,
          'controls': 1,
          'disablekb': 0,
          'enablejsapi': 1,
          'origin': window.location.origin
        },
        events: {
          'onReady': onPlayerReady,
          'onStateChange': onPlayerStateChange,
          'onError': onPlayerError
        }
      });
    }

    function onPlayerReady(event) {
      isYtReady = true;
      console.log('✓ YouTube Player API is Ready!');
      if (pendingTrack) {
        playTrack(pendingTrack, currentIndex);
        pendingTrack = null;
      }
    }

    function onPlayerStateChange(event) {
      const stateId = event.data;
      if (stateId === YT.PlayerState.PLAYING) {
        setPlayingUI(true);
        postStateUpdate('PLAYING');
        document.getElementById('unmuteBanner').style.display = 'none';
      } else if (stateId === YT.PlayerState.PAUSED) {
        setPlayingUI(false);
        postStateUpdate('PAUSED');
      } else if (stateId === YT.PlayerState.ENDED) {
        setPlayingUI(false);
        postStateUpdate('STOPPED');
        console.log('Track ended, auto-advancing next track in queue...');
        notifySongEnded();
      }
    }

    function onPlayerError(event) {
      console.error('YouTube Player Error code:', event.data);
      // Automatically advance to next song if video is restricted or unavailable
      setTimeout(notifySongEnded, 2000);
    }

    function enableAudioOutput() {
      if (ytPlayer && ytPlayer.unMute) {
        ytPlayer.unMute();
        ytPlayer.playVideo();
      }
      document.getElementById('unmuteBanner').style.display = 'none';
    }

    // Window click unlocks browser autoplay audio policy
    window.addEventListener('click', () => {
      if (ytPlayer && ytPlayer.isMuted && ytPlayer.isMuted()) {
        enableAudioOutput();
      }
    });

    function setPlayingUI(playing) {
      isPlaying = playing;
      const btn = document.getElementById('btnPlayPause');
      if (playing) {
        btn.textContent = '⏸';
        startProgressLoop();
      } else {
        btn.textContent = '▶';
        stopProgressLoop();
      }
    }

    function startProgressLoop() {
      stopProgressLoop();
      progressTimer = setInterval(() => {
        if (!ytPlayer || !ytPlayer.getCurrentTime) return;
        const cur = ytPlayer.getCurrentTime() || 0;
        const dur = ytPlayer.getDuration() || (currentTrack ? currentTrack.duration : 0);
        updateProgressUI(cur, dur);
        postStateUpdate('PLAYING', cur, dur);
      }, 1000);
    }

    function stopProgressLoop() {
      if (progressTimer) clearInterval(progressTimer);
    }

    function updateProgressUI(currentTime, duration) {
      const fill = document.getElementById('progressFill');
      const curLabel = document.getElementById('currentTime');
      const durLabel = document.getElementById('totalDuration');

      const pct = duration > 0 ? (currentTime / duration) * 100 : 0;
      fill.style.width = Math.min(100, Math.max(0, pct)) + '%';

      curLabel.textContent = formatSec(currentTime);
      durLabel.textContent = formatSec(duration);
    }

    function formatSec(s) {
      if (!s || isNaN(s)) return '00:00';
      const m = Math.floor(s / 60);
      const sec = Math.floor(s % 60);
      return (m < 10 ? '0' : '') + m + ':' + (sec < 10 ? '0' : '') + sec;
    }

    function seekTo(e) {
      if (!ytPlayer || !ytPlayer.getDuration) return;
      const bar = document.getElementById('progressBar');
      const rect = bar.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const ratio = Math.max(0, Math.min(1, clickX / rect.width));
      const targetTime = ratio * (ytPlayer.getDuration() || 0);
      ytPlayer.seekTo(targetTime, true);
    }

    function changeVolume(val) {
      if (ytPlayer && ytPlayer.setVolume) {
        ytPlayer.setVolume(val);
      }
    }

    function playTrack(track, idx) {
      if (!track || !track.videoId) return;
      currentTrack = track;
      currentIndex = idx !== undefined ? idx : currentIndex;

      document.getElementById('songTitle').textContent = track.title;
      document.getElementById('songArtist').textContent = track.artist;
      document.getElementById('totalDuration').textContent = track.durationFormatted || '00:00';

      renderQueueList();

      if (isYtReady && ytPlayer && ytPlayer.loadVideoById) {
        try {
          ytPlayer.loadVideoById(track.videoId);
          ytPlayer.playVideo();
          setPlayingUI(true);
        } catch (err) {
          console.warn('Direct play error:', err);
        }
      } else {
        pendingTrack = track;
      }
    }

    function togglePlayPause() {
      if (!ytPlayer) return;
      if (isPlaying) {
        sendRemoteAction('pause');
      } else {
        sendRemoteAction('resume');
      }
    }

    function renderQueueList() {
      const list = document.getElementById('queueList');
      const count = document.getElementById('queueCount');
      count.textContent = queue.length + ' tracks';

      if (!queue || queue.length === 0) {
        list.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem; padding: 20px 0; text-align: center;">Queue is empty.<br>Ask bot for single song or playlist!</div>';
        return;
      }

      list.innerHTML = '';
      queue.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'queue-item' + (index === currentIndex ? ' active' : '');
        div.onclick = () => {
          fetch('/api/jump', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ index })
          });
        };

        div.innerHTML = \`
          <img src="\${item.thumbnail || 'https://i.ytimg.com/vi/' + item.videoId + '/default.jpg'}" class="queue-thumb" alt="">
          <div class="queue-details">
            <div class="queue-song-name">\${item.title}</div>
            <div class="queue-artist-name">\${item.artist} • \${item.durationFormatted || ''}</div>
          </div>
          \${index === currentIndex ? '<span style="color:var(--accent-neon); font-size:0.9rem;">🔊</span>' : ''}
        \`;
        list.appendChild(div);
      });
    }

    function connectEventSource() {
      const evtSource = new EventSource('/api/events');

      evtSource.onopen = () => {
        console.log('✓ SSE connected to Antigravity Music Server');
        document.getElementById('remoteStatusText').textContent = 'Telegram Remote Connected';
      };

      evtSource.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          handleServerCommand(msg);
        } catch (err) {
          console.error('Error handling SSE message:', err);
        }
      };

      evtSource.onerror = () => {
        console.warn('SSE disconnected, reconnecting in 3s...');
        document.getElementById('remoteStatusText').textContent = 'Reconnecting...';
        evtSource.close();
        setTimeout(connectEventSource, 3000);
      };
    }

    function handleServerCommand(msg) {
      console.log('[Remote Command]', msg);
      if (msg.action === 'play') {
        if (msg.queue) queue = msg.queue;
        playTrack(msg.track, msg.index);
      } else if (msg.action === 'load_queue') {
        queue = msg.queue || [];
        currentIndex = msg.currentIndex !== undefined ? msg.currentIndex : 0;
        renderQueueList();
      } else if (msg.action === 'pause') {
        if (ytPlayer && ytPlayer.pauseVideo) ytPlayer.pauseVideo();
        setPlayingUI(false);
      } else if (msg.action === 'resume') {
        if (ytPlayer && ytPlayer.playVideo) ytPlayer.playVideo();
        setPlayingUI(true);
      } else if (msg.action === 'stop') {
        if (ytPlayer && ytPlayer.stopVideo) ytPlayer.stopVideo();
        setPlayingUI(false);
        queue = [];
        currentIndex = -1;
        currentTrack = null;
        document.getElementById('songTitle').textContent = 'Playback Stopped';
        document.getElementById('songArtist').textContent = 'Send /play <song> to Telegram Bot';
        renderQueueList();
        updateProgressUI(0, 0);
      }
    }

    function sendRemoteAction(action, extra = {}) {
      fetch('/api/' + action, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(extra)
      }).catch(console.error);
    }

    function postStateUpdate(playbackState, cur = 0, dur = 0) {
      fetch('/api/player/state', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          playbackState,
          currentTime: cur,
          duration: dur
        })
      }).catch(() => {});
    }

    function notifySongEnded() {
      fetch('/api/player/ended', { method: 'POST' }).catch(console.error);
    }

    function fetchInitialStatus() {
      fetch('/api/status')
        .then(res => res.json())
        .then(data => {
          if (data.queue) queue = data.queue;
          if (data.currentIndex !== undefined) currentIndex = data.currentIndex;
          renderQueueList();
          if (data.current_track) {
            playTrack(data.current_track, data.currentIndex);
            if (data.playbackState === 'PAUSED' && ytPlayer && ytPlayer.pauseVideo) {
              ytPlayer.pauseVideo();
              setPlayingUI(false);
            }
          }
        })
        .catch(console.error);
    }

    function pollStatusBackup() {
      fetch('/api/status')
        .then(res => res.json())
        .then(data => {
          if (data.current_track && (!currentTrack || currentTrack.videoId !== data.current_track.videoId)) {
            queue = data.queue || [];
            playTrack(data.current_track, data.currentIndex);
          }
        })
        .catch(() => {});
    }
  </script>
</body>
</html>`;
}

// HTTP Server
const server = http.createServer(async (req, res) => {
  const reqUrl = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  const pathname = reqUrl.pathname;

  // CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const readJsonBody = () => new Promise((resolve) => {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (e) {
        resolve({});
      }
    });
  });

  // 1. Web Player UI
  if (pathname === '/' || pathname === '/player') {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(getPlayerHtml());
    return;
  }

  // 2. Server-Sent Events Stream for Web Player
  if (pathname === '/api/events') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    });
    res.write('event: connected\ndata: {"status": "ok"}\n\n');
    sseClients.add(res);
    state.browserConnected = true;

    req.on('close', () => {
      sseClients.delete(res);
      state.browserConnected = sseClients.size > 0;
    });
    return;
  }

  // 3. Status Endpoint
  if (pathname === '/api/status' && req.method === 'GET') {
    const currentTrack = (state.currentIndex >= 0 && state.currentIndex < state.queue.length)
      ? state.queue[state.currentIndex]
      : null;

    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      enabled: state.enabled,
      autoPlayPC: state.autoPlayPC,
      is_playing: state.playbackState === 'PLAYING',
      playbackState: state.playbackState,
      current_track: currentTrack,
      currentIndex: state.currentIndex,
      queue: state.queue,
      currentTime: state.currentTime,
      duration: state.duration,
      browserConnected: sseClients.size > 0,
      ytmusicReady,
    }));
    return;
  }

  // 4. Feature Toggle (Enable / Disable)
  if (pathname === '/api/toggle' && req.method === 'POST') {
    const body = await readJsonBody();
    if (typeof body.enabled === 'boolean') {
      state.enabled = body.enabled;
    } else {
      state.enabled = !state.enabled;
    }
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ enabled: state.enabled }));
    return;
  }

  // 5. Toggle Auto-Play on PC
  if (pathname === '/api/autoplay' && req.method === 'POST') {
    const body = await readJsonBody();
    if (typeof body.autoPlayPC === 'boolean') {
      state.autoPlayPC = body.autoPlayPC;
    } else {
      state.autoPlayPC = !state.autoPlayPC;
    }
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ autoPlayPC: state.autoPlayPC }));
    return;
  }

  // 6. Search Songs using ytmusic-api
  if (pathname === '/api/search' && req.method === 'GET') {
    const q = reqUrl.searchParams.get('q');
    if (!q) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Query parameter "q" is required' }));
      return;
    }
    try {
      const limit = parseInt(reqUrl.searchParams.get('limit') || '10', 10);
      const results = await searchSongsWithRetry(q, limit);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ results }));
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // 7. Play Command (Single track or search query)
  if (pathname === '/api/play' && req.method === 'POST') {
    const body = await readJsonBody();
    try {
      let trackToPlay = null;

      if (body.videoId && body.title) {
        trackToPlay = normalizeTrack(body);
      } else if (body.query) {
        const found = await searchSongsWithRetry(body.query, 1);
        if (found && found.length > 0) {
          trackToPlay = found[0];
        } else {
          res.writeHead(404, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: `No matching music found on YouTube Music for: ${body.query}` }));
          return;
        }
      }

      if (!trackToPlay) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Missing track or query' }));
        return;
      }

      if (body.enqueue) {
        state.queue.push(trackToPlay);
        if (state.playbackState === 'STOPPED' || state.currentIndex === -1) {
          state.currentIndex = state.queue.length - 1;
          state.playbackState = 'PLAYING';
          broadcast('play', { track: trackToPlay, index: state.currentIndex, queue: state.queue });
        } else {
          broadcast('load_queue', { queue: state.queue, currentIndex: state.currentIndex });
        }
      } else {
        state.queue = [trackToPlay];
        state.currentIndex = 0;
        state.playbackState = 'PLAYING';
        broadcast('play', { track: trackToPlay, index: 0, queue: state.queue });
      }

      // If AutoPlayPC is true and browser is not connected, open it in default browser
      if (state.autoPlayPC && sseClients.size === 0) {
        openPlayerInBrowser();
      }

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        status: 'playing',
        track: trackToPlay,
        index: state.currentIndex,
        queue: state.queue,
        autoPlayPC: state.autoPlayPC
      }));
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // 8. Create and Auto-Play Playlist
  if (pathname === '/api/playlist' && req.method === 'POST') {
    const body = await readJsonBody();
    const query = body.query || body.theme || '';
    const limit = parseInt(body.limit || '10', 10);

    if (!query && (!body.tracks || body.tracks.length === 0)) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Query or tracks list is required to create a playlist' }));
      return;
    }

    try {
      let playlistTracks = [];
      let playlistTitle = query || 'Custom Playlist';

      if (body.tracks && Array.isArray(body.tracks) && body.tracks.length > 0) {
        playlistTracks = body.tracks.map(normalizeTrack).filter(Boolean);
      } else {
        const result = await createPlaylistFromQuery(query, limit);
        playlistTitle = result.title;
        playlistTracks = result.tracks;
      }

      if (!playlistTracks || playlistTracks.length === 0) {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: `Could not find enough tracks to create playlist for: ${query}` }));
        return;
      }

      state.queue = playlistTracks;
      state.currentIndex = 0;
      state.playbackState = 'PLAYING';

      broadcast('load_queue', { queue: state.queue, currentIndex: 0 });
      broadcast('play', { track: state.queue[0], index: 0, queue: state.queue });

      if (state.autoPlayPC && sseClients.size === 0) {
        openPlayerInBrowser();
      }

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        status: 'playlist_playing',
        title: playlistTitle,
        count: state.queue.length,
        tracks: state.queue,
        current_track: state.queue[0],
        autoPlayPC: state.autoPlayPC
      }));
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: e.message }));
    }
    return;
  }

  // 9. Playback Controls
  if (pathname === '/api/pause' && req.method === 'POST') {
    state.playbackState = 'PAUSED';
    broadcast('pause');
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'paused' }));
    return;
  }

  if (pathname === '/api/resume' && req.method === 'POST') {
    state.playbackState = 'PLAYING';
    broadcast('resume');
    if (state.autoPlayPC && sseClients.size === 0) {
      openPlayerInBrowser();
    }
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'resumed' }));
    return;
  }

  if (pathname === '/api/next' && req.method === 'POST') {
    if (state.currentIndex + 1 < state.queue.length) {
      state.currentIndex++;
      const nextTrack = state.queue[state.currentIndex];
      state.playbackState = 'PLAYING';
      broadcast('play', { track: nextTrack, index: state.currentIndex, queue: state.queue });
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'next_track', track: nextTrack, index: state.currentIndex }));
    } else {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'end_of_queue', track: null }));
    }
    return;
  }

  if (pathname === '/api/prev' && req.method === 'POST') {
    if (state.currentIndex > 0) {
      state.currentIndex--;
      const prevTrack = state.queue[state.currentIndex];
      state.playbackState = 'PLAYING';
      broadcast('play', { track: prevTrack, index: state.currentIndex, queue: state.queue });
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'prev_track', track: prevTrack, index: state.currentIndex }));
    } else {
      const currentTrack = state.queue[0] || null;
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'at_start', track: currentTrack, index: 0 }));
    }
    return;
  }

  if (pathname === '/api/stop' && req.method === 'POST') {
    state.playbackState = 'STOPPED';
    state.queue = [];
    state.currentIndex = -1;
    state.currentTime = 0;
    broadcast('stop');
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'stopped' }));
    return;
  }

  if (pathname === '/api/jump' && req.method === 'POST') {
    const body = await readJsonBody();
    const idx = parseInt(body.index, 10);
    if (!isNaN(idx) && idx >= 0 && idx < state.queue.length) {
      state.currentIndex = idx;
      const track = state.queue[idx];
      state.playbackState = 'PLAYING';
      broadcast('play', { track, index: idx, queue: state.queue });
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'playing', track, index: idx }));
      return;
    }
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Invalid index' }));
    return;
  }

  if (pathname === '/api/open' && req.method === 'POST') {
    openPlayerInBrowser();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'opening_browser' }));
    return;
  }

  // 10. Browser Client State Feedback
  if (pathname === '/api/player/state' && req.method === 'POST') {
    const body = await readJsonBody();
    if (body.playbackState) state.playbackState = body.playbackState;
    if (typeof body.currentTime === 'number') state.currentTime = body.currentTime;
    if (typeof body.duration === 'number') state.duration = body.duration;
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok' }));
    return;
  }

  // 11. Browser notifies that Current Song Ended -> Auto Advance!
  if (pathname === '/api/player/ended' && req.method === 'POST') {
    console.log(`[Music Server] Track finished: ${state.currentIndex + 1}/${state.queue.length}`);
    if (state.currentIndex + 1 < state.queue.length) {
      state.currentIndex++;
      const nextTrack = state.queue[state.currentIndex];
      state.playbackState = 'PLAYING';
      console.log(`[Music Server] Auto-playing next track: ${nextTrack.title} - ${nextTrack.artist}`);
      broadcast('play', { track: nextTrack, index: state.currentIndex, queue: state.queue });
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'next_track_started', track: nextTrack, index: state.currentIndex }));
    } else {
      console.log('[Music Server] Playlist queue finished.');
      state.playbackState = 'STOPPED';
      broadcast('stop');
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'playlist_finished' }));
    }
    return;
  }

  // Fallback 404
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not Found' }));
});

server.listen(PORT, HOST, () => {
  console.log(`=======================================================`);
  console.log(`🎵 Antigravity PC Music Player Server`);
  console.log(`• Web Player UI : http://localhost:${PORT}/player`);
  console.log(`• Remote API    : http://localhost:${PORT}/api`);
  console.log(`• Auto-Play PC  : ${state.autoPlayPC ? 'Enabled' : 'Disabled'}`);
  console.log(`• Status        : Active & ready for Telegram commands`);
  console.log(`=======================================================`);
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\nStopping Music Server...');
  server.close(() => process.exit(0));
});
process.on('SIGTERM', () => {
  server.close(() => process.exit(0));
});
