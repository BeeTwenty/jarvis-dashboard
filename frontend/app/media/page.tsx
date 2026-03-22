'use client'

import { memo } from 'react'
import { useData } from '@/lib/DataContext'
import { timeAgo } from '@/lib/api'
import { Film, Tv, Clapperboard, MonitorPlay } from 'lucide-react'
import styles from './page.module.scss'

const MediaItem = memo(function MediaItem({ item }: { item: any }) {
  const t = item.Type || '?'
  const cls = t === 'Movie' ? 'blue' : t === 'Series' ? 'green' : 'purple'
  return (
    <div className={styles.mediaItem}>
      <span className={styles.mediaName} title={item.Name}>{item.Name || '?'}</span>
      <span className={`badge ${cls}`}>{t}</span>
      <span className={styles.mediaTime}>{timeAgo(item.DateCreated)}</span>
    </div>
  )
})

export default function MediaPage() {
  const { data } = useData()
  const { counts, latest, sessions } = data
  const playing = Array.isArray(sessions) ? sessions.filter((s: any) => s.NowPlayingItem) : []

  return (
    <>
      <header className="page-header">
        <h1 className="page-title">Media</h1>
        {playing.length > 0 && (
          <div className="page-meta"><span className="badge green"><MonitorPlay size={12} /> {playing.length} now playing</span></div>
        )}
      </header>

      <div className="page-body">
        {counts && !counts.error && (
          <div className="section">
            <div className={`${styles.statsGrid} stagger-children`}>
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
        )}

        {playing.length > 0 && (
          <div className="section">
            <div className="section-title">Now Playing</div>
            <div className={`${styles.playingList} stagger-children`}>
              {playing.map((s: any, i: number) => (
                <div key={i} className={styles.playingItem}>
                  <div className={styles.npDot} />
                  <div>
                    <div><span className={styles.npUser}>{s.UserName || '?'}</span> watching <span className={styles.npTitle}>{s.NowPlayingItem?.Name || '?'}</span></div>
                    <div className={styles.npDevice}>{s.DeviceName || ''} {s.Client || ''}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {Array.isArray(latest) && latest.length > 0 && (
          <div className="section">
            <div className="section-title">Recently Added</div>
            <div className="card">
              <div className="card-body" style={{ padding: 0 }}>
                {latest.map((item: any, i: number) => <MediaItem key={i} item={item} />)}
              </div>
            </div>
          </div>
        )}

        {!counts && !latest?.length && <div className="empty-state">Jellyfin unavailable</div>}
      </div>
    </>
  )
}
