'use client'

import { useState, useEffect, useRef, useCallback, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { api } from '@/lib/api'
import {
  Play, Pause, Maximize, Minimize, Volume2, VolumeX,
  SkipForward, SkipBack, Loader2, ChevronLeft, Settings,
  Subtitles, Monitor
} from 'lucide-react'
import styles from './page.module.scss'

interface StreamSource {
  url: string
  quality: string
  type: string
  provider: string
  referrer?: string
}

interface Subtitle {
  url: string
  lang: string
}

interface SourcesResponse {
  sources: StreamSource[]
  subtitles: Subtitle[]
}

export default function StreamPageWrapper() {
  return (
    <Suspense fallback={<div className={styles.loadingOverlay}><Loader2 size={40} className={styles.spinner} /><span>Loading...</span></div>}>
      <StreamPage />
    </Suspense>
  )
}

function StreamPage() {
  const searchParams = useSearchParams()
  const showId = searchParams.get('show_id') || ''
  const episode = searchParams.get('episode') || '1'
  const mode = searchParams.get('mode') || 'sub'
  const title = searchParams.get('title') || 'Untitled'

  const videoRef = useRef<HTMLVideoElement>(null)
  const hlsRef = useRef<any>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const controlsTimerRef = useRef<any>(null)

  const [sources, setSources] = useState<StreamSource[]>([])
  const [subtitles, setSubtitles] = useState<Subtitle[]>([])
  const [episodes, setEpisodes] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [currentSource, setCurrentSource] = useState<StreamSource | null>(null)

  // Player state
  const [playing, setPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)
  const [muted, setMuted] = useState(false)
  const [fullscreen, setFullscreen] = useState(false)
  const [showControls, setShowControls] = useState(true)
  const [showSettings, setShowSettings] = useState(false)
  const [activeSubtitle, setActiveSubtitle] = useState<number>(-1)
  const [hlsQualities, setHlsQualities] = useState<{ height: number; index: number }[]>([])
  const [currentQuality, setCurrentQuality] = useState(-1) // -1 = auto

  // Load episodes list
  useEffect(() => {
    if (!showId) return
    api<{ episodes: string[] }>(`/api/streaming/episodes?show_id=${showId}&mode=${mode}`)
      .then(r => {
        if (r.data?.episodes) setEpisodes(r.data.episodes)
      })
  }, [showId, mode])

  // Load sources for current episode
  useEffect(() => {
    if (!showId || !episode) return
    setLoading(true)
    setError('')
    setSources([])
    setCurrentSource(null)

    api<SourcesResponse>(`/api/streaming/sources?show_id=${showId}&episode=${episode}&mode=${mode}`)
      .then(r => {
        setLoading(false)
        if (r.data && r.data.sources.length > 0) {
          setSources(r.data.sources)
          setSubtitles(r.data.subtitles || [])
          // Pick best source: prefer HLS, then MP4
          const hls = r.data.sources.find(s => s.type === 'hls')
          const mp4 = r.data.sources.find(s => s.type === 'mp4')
          setCurrentSource(hls || mp4 || r.data.sources[0])
        } else {
          setError('No streaming sources found for this episode')
        }
      })
  }, [showId, episode, mode])

  // Attach video source
  useEffect(() => {
    if (!currentSource || !videoRef.current) return

    const video = videoRef.current

    // Cleanup previous HLS instance
    if (hlsRef.current) {
      hlsRef.current.destroy()
      hlsRef.current = null
    }
    setHlsQualities([])

    if (currentSource.type === 'hls') {
      import('hls.js').then(({ default: Hls }) => {
        if (!Hls.isSupported()) {
          // Try native HLS (Safari)
          video.src = currentSource.url
          return
        }
        const hls = new Hls({
          xhrSetup: (xhr: XMLHttpRequest) => {
            if (currentSource.referrer) {
              // Can't set Referer from browser, proxy if needed
            }
          },
        })
        hls.loadSource(currentSource.url)
        hls.attachMedia(video)
        hls.on(Hls.Events.MANIFEST_PARSED, () => {
          const levels = hls.levels.map((l: any, i: number) => ({
            height: l.height,
            index: i,
          })).filter((l: any) => l.height > 0)
          setHlsQualities(levels)
          video.play().catch(() => {})
        })
        hls.on(Hls.Events.ERROR, (_: any, data: any) => {
          if (data.fatal) {
            console.error('[HLS] Fatal error:', data)
            // Try to recover
            if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
              hls.startLoad()
            }
          }
        })
        hlsRef.current = hls
      })
    } else {
      // Direct MP4
      video.src = currentSource.url
      video.play().catch(() => {})
    }

    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy()
        hlsRef.current = null
      }
    }
  }, [currentSource])

  // Video event listeners
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const onTimeUpdate = () => setCurrentTime(video.currentTime)
    const onDurationChange = () => setDuration(video.duration)
    const onPlay = () => setPlaying(true)
    const onPause = () => setPlaying(false)

    video.addEventListener('timeupdate', onTimeUpdate)
    video.addEventListener('durationchange', onDurationChange)
    video.addEventListener('play', onPlay)
    video.addEventListener('pause', onPause)

    return () => {
      video.removeEventListener('timeupdate', onTimeUpdate)
      video.removeEventListener('durationchange', onDurationChange)
      video.removeEventListener('play', onPlay)
      video.removeEventListener('pause', onPause)
    }
  }, [])

  // Auto-hide controls
  const resetControlsTimer = useCallback(() => {
    setShowControls(true)
    if (controlsTimerRef.current) clearTimeout(controlsTimerRef.current)
    controlsTimerRef.current = setTimeout(() => {
      if (playing) setShowControls(false)
    }, 3000)
  }, [playing])

  // Keyboard shortcuts
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      const video = videoRef.current
      if (!video) return
      switch (e.key) {
        case ' ':
        case 'k':
          e.preventDefault()
          video.paused ? video.play() : video.pause()
          break
        case 'f':
          toggleFullscreen()
          break
        case 'ArrowLeft':
          e.preventDefault()
          video.currentTime = Math.max(0, video.currentTime - 10)
          break
        case 'ArrowRight':
          e.preventDefault()
          video.currentTime = Math.min(video.duration, video.currentTime + 10)
          break
        case 'ArrowUp':
          e.preventDefault()
          video.volume = Math.min(1, video.volume + 0.1)
          setVolume(video.volume)
          break
        case 'ArrowDown':
          e.preventDefault()
          video.volume = Math.max(0, video.volume - 0.1)
          setVolume(video.volume)
          break
        case 'm':
          video.muted = !video.muted
          setMuted(video.muted)
          break
      }
      resetControlsTimer()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [playing, resetControlsTimer])

  function toggleFullscreen() {
    if (!containerRef.current) return
    if (document.fullscreenElement) {
      document.exitFullscreen()
      setFullscreen(false)
    } else {
      containerRef.current.requestFullscreen()
      setFullscreen(true)
    }
  }

  function seek(e: React.MouseEvent<HTMLDivElement>) {
    const video = videoRef.current
    if (!video || !duration) return
    const rect = e.currentTarget.getBoundingClientRect()
    const pct = (e.clientX - rect.left) / rect.width
    video.currentTime = pct * duration
  }

  function changeQuality(levelIndex: number) {
    if (hlsRef.current) {
      hlsRef.current.currentLevel = levelIndex
      setCurrentQuality(levelIndex)
    }
    setShowSettings(false)
  }

  function changeSource(source: StreamSource) {
    setCurrentSource(source)
    setShowSettings(false)
  }

  function navigateEpisode(ep: string) {
    const url = new URL(window.location.href)
    url.searchParams.set('episode', ep)
    window.location.href = url.toString()
  }

  function formatTime(sec: number): string {
    if (!sec || isNaN(sec)) return '0:00'
    const h = Math.floor(sec / 3600)
    const m = Math.floor((sec % 3600) / 60)
    const s = Math.floor(sec % 60)
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    return `${m}:${String(s).padStart(2, '0')}`
  }

  const currentEpIndex = episodes.indexOf(episode)
  const prevEp = currentEpIndex > 0 ? episodes[currentEpIndex - 1] : null
  const nextEp = currentEpIndex < episodes.length - 1 ? episodes[currentEpIndex + 1] : null

  if (!showId) {
    return <div className={styles.errorPage}>Missing show_id parameter</div>
  }

  return (
    <div className={styles.streamPage}>
      {/* Top bar */}
      <div className={styles.topBar}>
        <button className={styles.backBtn} onClick={() => window.close()}>
          <ChevronLeft size={18} /> Back
        </button>
        <div className={styles.titleArea}>
          <span className={styles.showTitle}>{title}</span>
          {episodes.length > 1 && <span className={styles.epLabel}>Episode {episode}</span>}
        </div>
        <div className={styles.topActions}>
          {prevEp && (
            <button className={styles.navBtn} onClick={() => navigateEpisode(prevEp)}>
              <SkipBack size={14} /> Prev
            </button>
          )}
          {nextEp && (
            <button className={styles.navBtn} onClick={() => navigateEpisode(nextEp)}>
              Next <SkipForward size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Video container */}
      <div
        ref={containerRef}
        className={styles.videoContainer}
        onMouseMove={resetControlsTimer}
        onClick={(e) => {
          // Don't toggle play if clicking on controls
          if ((e.target as HTMLElement).closest(`.${styles.controls}`)) return
          if ((e.target as HTMLElement).closest(`.${styles.settingsPanel}`)) return
          const video = videoRef.current
          if (video) video.paused ? video.play() : video.pause()
        }}
      >
        {loading ? (
          <div className={styles.loadingOverlay}>
            <Loader2 size={40} className={styles.spinner} />
            <span>Loading stream...</span>
          </div>
        ) : error ? (
          <div className={styles.loadingOverlay}>
            <span className={styles.errorText}>{error}</span>
          </div>
        ) : null}

        <video
          ref={videoRef}
          className={styles.video}
          playsInline
          crossOrigin="anonymous"
        >
          {subtitles.map((sub, i) => (
            <track
              key={i}
              kind="subtitles"
              src={sub.url}
              srcLang={sub.lang.substring(0, 2).toLowerCase()}
              label={sub.lang}
              default={i === 0}
            />
          ))}
        </video>

        {/* Controls overlay */}
        <div className={`${styles.controls} ${showControls || !playing ? styles.visible : ''}`}>
          {/* Progress bar */}
          <div className={styles.progressBar} onClick={seek}>
            <div
              className={styles.progressFill}
              style={{ width: duration ? `${(currentTime / duration) * 100}%` : '0%' }}
            />
          </div>

          <div className={styles.controlsRow}>
            <div className={styles.controlsLeft}>
              <button className={styles.ctrlBtn} onClick={() => {
                const video = videoRef.current
                if (video) video.paused ? video.play() : video.pause()
              }}>
                {playing ? <Pause size={20} /> : <Play size={20} />}
              </button>

              {prevEp && (
                <button className={styles.ctrlBtn} onClick={() => navigateEpisode(prevEp)}>
                  <SkipBack size={16} />
                </button>
              )}
              {nextEp && (
                <button className={styles.ctrlBtn} onClick={() => navigateEpisode(nextEp)}>
                  <SkipForward size={16} />
                </button>
              )}

              <button className={styles.ctrlBtn} onClick={() => {
                const v = videoRef.current
                if (v) { v.muted = !v.muted; setMuted(v.muted) }
              }}>
                {muted ? <VolumeX size={16} /> : <Volume2 size={16} />}
              </button>

              <input
                type="range"
                className={styles.volumeSlider}
                min={0}
                max={1}
                step={0.05}
                value={muted ? 0 : volume}
                onChange={(e) => {
                  const v = parseFloat(e.target.value)
                  setVolume(v)
                  if (videoRef.current) {
                    videoRef.current.volume = v
                    videoRef.current.muted = v === 0
                    setMuted(v === 0)
                  }
                }}
              />

              <span className={styles.timeDisplay}>
                {formatTime(currentTime)} / {formatTime(duration)}
              </span>
            </div>

            <div className={styles.controlsRight}>
              {/* Subtitle toggle */}
              {subtitles.length > 0 && (
                <button
                  className={`${styles.ctrlBtn} ${activeSubtitle >= 0 ? styles.active : ''}`}
                  onClick={() => {
                    const video = videoRef.current
                    if (!video) return
                    if (activeSubtitle >= 0) {
                      // Turn off
                      for (let i = 0; i < video.textTracks.length; i++) {
                        video.textTracks[i].mode = 'hidden'
                      }
                      setActiveSubtitle(-1)
                    } else {
                      // Turn on first track
                      if (video.textTracks.length > 0) {
                        video.textTracks[0].mode = 'showing'
                        setActiveSubtitle(0)
                      }
                    }
                  }}
                >
                  <Subtitles size={16} />
                </button>
              )}

              {/* Settings (quality / source) */}
              <button
                className={styles.ctrlBtn}
                onClick={(e) => { e.stopPropagation(); setShowSettings(!showSettings) }}
              >
                <Settings size={16} />
              </button>

              <button className={styles.ctrlBtn} onClick={toggleFullscreen}>
                {fullscreen ? <Minimize size={16} /> : <Maximize size={16} />}
              </button>
            </div>
          </div>
        </div>

        {/* Settings panel */}
        {showSettings && (
          <div className={styles.settingsPanel} onClick={e => e.stopPropagation()}>
            {hlsQualities.length > 0 && (
              <div className={styles.settingsSection}>
                <div className={styles.settingsTitle}><Monitor size={14} /> Quality</div>
                <button
                  className={`${styles.settingsOption} ${currentQuality === -1 ? styles.activeOption : ''}`}
                  onClick={() => changeQuality(-1)}
                >
                  Auto
                </button>
                {hlsQualities.map(q => (
                  <button
                    key={q.index}
                    className={`${styles.settingsOption} ${currentQuality === q.index ? styles.activeOption : ''}`}
                    onClick={() => changeQuality(q.index)}
                  >
                    {q.height}p
                  </button>
                ))}
              </div>
            )}

            {sources.length > 1 && (
              <div className={styles.settingsSection}>
                <div className={styles.settingsTitle}>Source</div>
                {sources.map((s, i) => (
                  <button
                    key={i}
                    className={`${styles.settingsOption} ${currentSource === s ? styles.activeOption : ''}`}
                    onClick={() => changeSource(s)}
                  >
                    {s.provider} — {s.quality} ({s.type})
                  </button>
                ))}
              </div>
            )}

            {subtitles.length > 0 && (
              <div className={styles.settingsSection}>
                <div className={styles.settingsTitle}><Subtitles size={14} /> Subtitles</div>
                <button
                  className={`${styles.settingsOption} ${activeSubtitle === -1 ? styles.activeOption : ''}`}
                  onClick={() => {
                    const video = videoRef.current
                    if (video) {
                      for (let i = 0; i < video.textTracks.length; i++) {
                        video.textTracks[i].mode = 'hidden'
                      }
                    }
                    setActiveSubtitle(-1)
                    setShowSettings(false)
                  }}
                >
                  Off
                </button>
                {subtitles.map((sub, i) => (
                  <button
                    key={i}
                    className={`${styles.settingsOption} ${activeSubtitle === i ? styles.activeOption : ''}`}
                    onClick={() => {
                      const video = videoRef.current
                      if (video) {
                        for (let j = 0; j < video.textTracks.length; j++) {
                          video.textTracks[j].mode = j === i ? 'showing' : 'hidden'
                        }
                      }
                      setActiveSubtitle(i)
                      setShowSettings(false)
                    }}
                  >
                    {sub.lang}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Episode list (below video) */}
      {episodes.length > 1 && (
        <div className={styles.episodeBar}>
          <span className={styles.episodeBarTitle}>Episodes</span>
          <div className={styles.episodeGrid}>
            {episodes.map(ep => (
              <button
                key={ep}
                className={`${styles.epBtn} ${ep === episode ? styles.epBtnActive : ''}`}
                onClick={() => navigateEpisode(ep)}
              >
                {ep}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
