'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { api } from '@/lib/api'
import {
  Film, Tv, Clapperboard, MonitorPlay, Play, Clock, Star,
  CheckCircle, Loader2, ChevronRight
} from 'lucide-react'
import styles from './page.module.scss'

interface MediaOverview {
  counts: { MovieCount: number; SeriesCount: number; EpisodeCount: number } | null
  continue_watching: {
    id: string; name: string; type: string; progress: number;
    runtime_min: number; poster: string
  }[]
  now_playing: {
    user: string; client: string; device: string; title: string;
    type: string; progress: number; poster: string; is_paused: boolean
  }[]
  next_up: {
    id: string; series_name: string; season: number; episode: number;
    name: string; overview: string; runtime_min: number; poster: string
  }[]
  recently_added: {
    id: string; name: string; type: string; year: string; rating: number | null;
    runtime_min: number | null; genres: string[]; overview: string;
    poster: string; played: boolean; season_count: number | null
  }[]
  genres: { name: string; count: number }[]
}

export default function MediaPage() {
  const [data, setData] = useState<MediaOverview | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      const r = await api<MediaOverview>('/api/jellyfin-media/overview')
      setLoading(false)
      if (r.data) setData(r.data)
    }
    load()
  }, [])

  if (loading) {
    return (
      <>
        <header className="page-header"><h1 className="page-title">Media</h1></header>
        <div className="page-body">
          <div className={styles.loadingState}><Loader2 size={20} className={styles.spinner} /> Loading library...</div>
        </div>
      </>
    )
  }

  if (!data || !data.counts) {
    return (
      <>
        <header className="page-header"><h1 className="page-title">Media</h1></header>
        <div className="page-body"><div className="empty-state">Jellyfin unavailable</div></div>
      </>
    )
  }

  const { counts, continue_watching, now_playing, next_up, recently_added, genres } = data
  const topGenres = genres.slice(0, 8)
  const maxGenreCount = topGenres[0]?.count || 1

  return (
    <>
      <header className="page-header">
        <h1 className="page-title">Media</h1>
        <div className="page-meta">
          {now_playing.length > 0 && (
            <span className="badge green"><MonitorPlay size={12} /> {now_playing.length} streaming</span>
          )}
        </div>
      </header>

      <div className="page-body">
        {/* Stats */}
        <div className="section">
          <div className={styles.statsGrid}>
            {[
              { n: counts.MovieCount ?? 0, l: 'Movies', Icon: Film, color: '#0a84ff' },
              { n: counts.SeriesCount ?? 0, l: 'Series', Icon: Tv, color: '#30d158' },
              { n: counts.EpisodeCount ?? 0, l: 'Episodes', Icon: Clapperboard, color: '#bf5af2' },
            ].map(s => (
              <div key={s.l} className={styles.statCard}>
                <div className={styles.statIcon} style={{ color: s.color }}><s.Icon size={20} /></div>
                <div className={styles.statNum}>{s.n.toLocaleString()}</div>
                <div className={styles.statLabel}>{s.l}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Now Playing */}
        {now_playing.length > 0 && (
          <div className="section">
            <h3 className="section-title"><MonitorPlay size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Now Playing</h3>
            <div className={styles.nowPlayingList}>
              {now_playing.map((s, i) => (
                <div key={i} className={styles.npCard}>
                  {s.poster ? (
                    <img src={s.poster} alt={s.title} className={styles.npPoster} />
                  ) : (
                    <div className={styles.npPosterEmpty}><Film size={20} /></div>
                  )}
                  <div className={styles.npInfo}>
                    <span className={styles.npTitle}>{s.title}</span>
                    <span className={styles.npMeta}>{s.user} on {s.device}</span>
                    <div className={styles.npProgress}>
                      <div className="progress" style={{ flex: 1 }}>
                        <div className="progress-fill green" style={{ width: `${s.progress}%` }} />
                      </div>
                      <span className={styles.npPct}>{s.progress}%</span>
                      {s.is_paused && <span className="badge gray">Paused</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Continue Watching */}
        {continue_watching.length > 0 && (
          <div className="section">
            <h3 className="section-title"><Play size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Continue Watching</h3>
            <div className={styles.posterScroll}>
              {continue_watching.map((item, i) => (
                <div key={i} className={styles.posterCard}>
                  <div className={styles.posterWrap}>
                    {item.poster ? (
                      <img src={item.poster} alt={item.name} className={styles.posterImg} loading="lazy" />
                    ) : (
                      <div className={styles.posterEmpty}><Film size={24} /></div>
                    )}
                    <div className={styles.posterProgress}>
                      <div className={styles.posterProgressFill} style={{ width: `${item.progress}%` }} />
                    </div>
                  </div>
                  <span className={styles.posterTitle}>{item.name}</span>
                  <span className={styles.posterMeta}>{item.progress}% · {item.runtime_min}m</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Next Up */}
        {next_up.length > 0 && (
          <div className="section">
            <h3 className="section-title"><ChevronRight size={16} style={{ marginRight: 6, verticalAlign: -3 }} /> Next Up</h3>
            <div className={styles.posterScroll}>
              {next_up.map((item, i) => (
                <div key={i} className={styles.posterCard}>
                  <div className={styles.posterWrap}>
                    {item.poster ? (
                      <img src={item.poster} alt={item.name} className={styles.posterImg} loading="lazy" />
                    ) : (
                      <div className={styles.posterEmpty}><Tv size={24} /></div>
                    )}
                  </div>
                  <span className={styles.posterTitle}>{item.series_name}</span>
                  <span className={styles.posterMeta}>S{item.season}E{item.episode} · {item.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recently Added */}
        {recently_added.length > 0 && (
          <div className="section">
            <h3 className="section-title">Recently Added</h3>
            <div className={styles.libraryGrid}>
              {recently_added.map((item, i) => {
                const isMovie = item.type === 'Movie'
                const href = isMovie
                  ? `/discover/movie/${item.id}`
                  : `/discover/tv/${item.id}`
                return (
                  <div key={i} className={styles.libCard}>
                    <div className={styles.libPosterWrap}>
                      {item.poster ? (
                        <img src={item.poster} alt={item.name} className={styles.libPoster} loading="lazy" />
                      ) : (
                        <div className={styles.libPosterEmpty}>{isMovie ? <Film size={24} /> : <Tv size={24} />}</div>
                      )}
                      {item.played && (
                        <div className={styles.libWatched}><CheckCircle size={16} /></div>
                      )}
                      {item.rating && (
                        <div className={styles.libRating}><Star size={10} /> {item.rating.toFixed(1)}</div>
                      )}
                    </div>
                    <span className={styles.libTitle}>{item.name}</span>
                    <div className={styles.libMeta}>
                      {item.year && <span className="badge gray">{item.year}</span>}
                      <span className={`badge ${isMovie ? 'blue' : 'green'}`}>
                        {isMovie ? 'Movie' : `${item.season_count || '?'} Seasons`}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Genre Breakdown */}
        {topGenres.length > 0 && (
          <div className="section">
            <h3 className="section-title">Library by Genre</h3>
            <div className={styles.genreChart}>
              {topGenres.map(g => (
                <div key={g.name} className={styles.genreRow}>
                  <span className={styles.genreName}>{g.name}</span>
                  <div className={styles.genreBarWrap}>
                    <div
                      className={styles.genreBar}
                      style={{ width: `${(g.count / maxGenreCount) * 100}%` }}
                    />
                  </div>
                  <span className={styles.genreCount}>{g.count}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  )
}
