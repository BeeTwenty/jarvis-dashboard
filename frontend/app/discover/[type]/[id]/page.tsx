'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { api, fmtBytes } from '@/lib/api'
import { toast } from '@/lib/toast'
import {
  ArrowLeft, Star, Clock, Film, Tv, Plus, X, ArrowUp, ArrowDown, Loader2, Search
} from 'lucide-react'
import styles from './page.module.scss'

interface CastMember {
  name: string
  character: string
  photo: string
}

interface SimilarMovie {
  title: string
  year: string
  tmdb_id: string
  poster: string
  rating: number
  type: string
}

interface KBMovie {
  title: string
  year: string
  type: string
  tmdb_id?: string
  torrent_query: string
  poster?: string
  rating?: number
}

interface MovieDetail {
  title: string
  year: string
  overview: string
  poster: string
  backdrop: string
  genres: string[]
  runtime: number
  rating: number
  vote_count: number
  cast: CastMember[]
  director: string
  tagline: string
  status: string
  tmdb_id: string
  type: string
  torrent_query: string
  similar_tmdb: SimilarMovie[]
  similar_kb: KBMovie[]
  error?: string
}

function TorrentSearchModal({ query, onClose }: { query: string; onClose: () => void }) {
  const [results, setResults] = useState<any[] | null>(null)
  const [searching, setSearching] = useState(true)

  useEffect(() => {
    async function search() {
      setSearching(true)
      const r = await api(`/api/torrent-search?q=${encodeURIComponent(query)}`)
      setSearching(false)
      if (r.error || !Array.isArray(r.data)) {
        setResults([])
      } else {
        setResults(r.data)
      }
    }
    search()
  }, [query])

  async function addTorrent(hash: string, name: string) {
    const magnet = `magnet:?xt=urn:btih:${hash}&dn=${encodeURIComponent(name)}`
    const r = await api('/api/torrent-add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ magnet }),
    })
    toast(r.error ? r.error : `Added: ${name.substring(0, 50)}`, r.error ? 'error' : 'success')
    onClose()
  }

  return (
    <div className={styles.modalOverlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <div className={styles.modalHeader}>
          <h3>Torrents for: {query}</h3>
          <button className="btn btn-ghost btn-sm" onClick={onClose}><X size={16} /></button>
        </div>
        <div className={styles.modalBody}>
          {searching ? (
            <div className={styles.loadingState}><Loader2 size={20} className={styles.spinner} /> Searching...</div>
          ) : results && results.length === 0 ? (
            <div className="empty-state" style={{ padding: 16 }}>No torrents found</div>
          ) : results && (
            <div className="stagger-children">
              {results.map((r, i) => (
                <div key={i} className={styles.torrentResult}>
                  <span className={styles.torrentName} title={r.name}>{r.name}</span>
                  <span className={styles.torrentMeta}>{fmtBytes(r.size)}</span>
                  <span className={styles.torrentSeeds}><ArrowUp size={10} />{r.seeders}</span>
                  <span className={styles.torrentMeta}><ArrowDown size={10} />{r.leechers}</span>
                  <button className={`btn btn-sm ${styles.addBtn}`} onClick={() => addTorrent(r.info_hash, r.name)}>
                    <Plus size={12} /> Add
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function MovieDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [detail, setDetail] = useState<MovieDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [torrentQuery, setTorrentQuery] = useState<string | null>(null)

  const type = params.type as string
  const id = params.id as string

  useEffect(() => {
    async function load() {
      setLoading(true)
      const r = await api<MovieDetail>(`/api/recommendations/detail?tmdb_id=${id}&type=${type}`)
      setLoading(false)
      if (r.data && !r.data.error) {
        setDetail(r.data)
      } else {
        toast(r.error || r.data?.error || 'Failed to load details', 'error')
      }
    }
    if (id && type) load()
  }, [id, type])

  function formatRuntime(min: number): string {
    if (!min) return ''
    const h = Math.floor(min / 60)
    const m = min % 60
    return h > 0 ? `${h}h ${m}m` : `${m}m`
  }

  if (loading) {
    return (
      <>
        <header className="page-header">
          <button className="btn btn-ghost btn-sm" onClick={() => router.push('/discover')}>
            <ArrowLeft size={16} /> Discover
          </button>
        </header>
        <div className="page-body">
          <div className={styles.loadingState}><Loader2 size={24} className={styles.spinner} /> Loading details...</div>
        </div>
      </>
    )
  }

  if (!detail) {
    return (
      <>
        <header className="page-header">
          <button className="btn btn-ghost btn-sm" onClick={() => router.push('/discover')}>
            <ArrowLeft size={16} /> Discover
          </button>
        </header>
        <div className="page-body">
          <div className="empty-state">Could not load movie details</div>
        </div>
      </>
    )
  }

  // Combine similar movies from TMDB and KB, deduplicating
  const allSimilar: SimilarMovie[] = [...detail.similar_tmdb]
  const seenIds = new Set(detail.similar_tmdb.map(s => s.tmdb_id))
  for (const kb of detail.similar_kb) {
    if (kb.tmdb_id && !seenIds.has(kb.tmdb_id)) {
      seenIds.add(kb.tmdb_id)
      allSimilar.push({
        title: kb.title,
        year: kb.year,
        tmdb_id: kb.tmdb_id,
        poster: kb.poster || '',
        rating: kb.rating || 0,
        type: kb.type === 'series' ? 'tv' : kb.type,
      })
    }
  }

  return (
    <>
      <header className="page-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="btn btn-ghost btn-sm" onClick={() => router.push('/discover')}>
            <ArrowLeft size={16} /> Discover
          </button>
          <h1 className="page-title">{detail.title}</h1>
        </div>
        <div className="page-meta">
          <span className={`badge ${detail.type === 'tv' ? 'purple' : 'blue'}`}>
            {detail.type === 'tv' ? <><Tv size={10} /> Series</> : <><Film size={10} /> Movie</>}
          </span>
        </div>
      </header>

      <div className={styles.detailPage}>
        {/* Hero section */}
        <div className={styles.hero} style={detail.backdrop ? { backgroundImage: `url(${detail.backdrop})` } : undefined}>
          <div className={styles.heroOverlay}>
            <div className={styles.heroContent}>
              {detail.poster && (
                <img src={detail.poster} alt={detail.title} className={styles.heroPoster} />
              )}
              <div className={styles.heroInfo}>
                <h2 className={styles.heroTitle}>{detail.title}</h2>
                {detail.tagline && <p className={styles.heroTagline}>{detail.tagline}</p>}
                <div className={styles.heroMeta}>
                  {detail.year && <span className="badge gray">{detail.year}</span>}
                  {detail.runtime > 0 && (
                    <span className={styles.metaItem}><Clock size={12} /> {formatRuntime(detail.runtime)}</span>
                  )}
                  {detail.rating > 0 && (
                    <span className={styles.metaItem}><Star size={12} /> {detail.rating}/10 ({detail.vote_count.toLocaleString()} votes)</span>
                  )}
                  {detail.status && detail.status !== 'Released' && (
                    <span className="badge orange">{detail.status}</span>
                  )}
                </div>
                <div className={styles.heroGenres}>
                  {detail.genres.map(g => (
                    <span key={g} className="badge blue">{g}</span>
                  ))}
                </div>
                {detail.director && (
                  <div className={styles.heroDirector}>Directed by <strong>{detail.director}</strong></div>
                )}
                <div className={styles.heroActions}>
                  <button
                    className={`btn btn-primary`}
                    onClick={() => setTorrentQuery(detail.torrent_query)}
                  >
                    <Search size={14} /> Find Torrent
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Synopsis */}
        {detail.overview && (
          <div className={styles.section}>
            <h3 className="section-title">Synopsis</h3>
            <p className={styles.overview}>{detail.overview}</p>
          </div>
        )}

        {/* Cast */}
        {detail.cast.length > 0 && (
          <div className={styles.section}>
            <h3 className="section-title">Cast</h3>
            <div className={styles.castGrid}>
              {detail.cast.map((member, i) => (
                <div key={i} className={styles.castCard}>
                  {member.photo ? (
                    <img src={member.photo} alt={member.name} className={styles.castPhoto} />
                  ) : (
                    <div className={styles.castPhotoPlaceholder}>
                      <Film size={20} />
                    </div>
                  )}
                  <div className={styles.castName}>{member.name}</div>
                  <div className={styles.castCharacter}>{member.character}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Similar Movies */}
        {allSimilar.length > 0 && (
          <div className={styles.section}>
            <h3 className="section-title">Similar Titles</h3>
            <div className={styles.similarGrid}>
              {allSimilar.map((s, i) => {
                const sType = s.type === 'series' ? 'tv' : s.type === 'tv' ? 'tv' : 'movie'
                return s.tmdb_id ? (
                  <Link
                    key={i}
                    href={`/discover/${sType}/${s.tmdb_id}`}
                    className={styles.similarCard}
                  >
                    {s.poster ? (
                      <img src={s.poster} alt={s.title} className={styles.similarPoster} />
                    ) : (
                      <div className={styles.similarPosterPlaceholder}>
                        <Film size={24} />
                      </div>
                    )}
                    <div className={styles.similarInfo}>
                      <div className={styles.similarTitle}>{s.title}</div>
                      <div className={styles.similarMeta}>
                        {s.year && <span>{s.year}</span>}
                        {s.rating > 0 && <span><Star size={10} /> {s.rating}</span>}
                      </div>
                    </div>
                  </Link>
                ) : (
                  <div key={i} className={styles.similarCard}>
                    <div className={styles.similarPosterPlaceholder}>
                      <Film size={24} />
                    </div>
                    <div className={styles.similarInfo}>
                      <div className={styles.similarTitle}>{s.title}</div>
                      <div className={styles.similarMeta}>
                        {s.year && <span>{s.year}</span>}
                        {s.rating > 0 && <span><Star size={10} /> {s.rating}</span>}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* Torrent search modal */}
      {torrentQuery && (
        <TorrentSearchModal query={torrentQuery} onClose={() => setTorrentQuery(null)} />
      )}
    </>
  )
}
