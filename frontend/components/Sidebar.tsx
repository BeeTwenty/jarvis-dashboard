'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { memo, useEffect, useState } from 'react'
import { LayoutGrid, Cpu, Container, ArrowDownUp, Film, FolderOpen, Sparkles, Clock, CloudSun, Server } from 'lucide-react'
import ThemeToggle from '@/components/ThemeToggle'

const navItems = [
  { href: '/', label: 'Overview', Icon: LayoutGrid },
  { href: '/system', label: 'System', Icon: Cpu },
  { href: '/docker', label: 'Docker', Icon: Container },
  { href: '/torrents', label: 'Torrents', Icon: ArrowDownUp },
  { href: '/media', label: 'Media', Icon: Film },
  { href: '/discover', label: 'Discover', Icon: Sparkles },
  { href: '/files', label: 'Files', Icon: FolderOpen },
]

export default memo(function Sidebar() {
  const pathname = usePathname()
  const [clock, setClock] = useState('')
  const [meta, setMeta] = useState({ uptime: '', weather: '' })

  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString('en-GB', { hour12: false }))
    tick()
    const t = setInterval(tick, 1000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    async function load() {
      try {
        const [s, w] = await Promise.all([
          fetch('/api/system').then(r => r.json()),
          fetch('/api/weather').then(r => r.json()),
        ])
        setMeta({
          uptime: s?.uptime_human || '',
          weather: w?.temp_c ? `${w.temp_c}° ${w.condition || ''}` : '',
        })
      } catch {}
    }
    load()
    const t = setInterval(load, 60000)
    return () => clearInterval(t)
  }, [])

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="sidebar-logo">J</div>
          <div>
            <div className="sidebar-title">Jarvis</div>
            <div className="sidebar-subtitle">Mission Control</div>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(({ href, label, Icon }) => (
          <Link
            key={href}
            href={href}
            prefetch={true}
            className={`nav-item ${pathname === href || (href !== '/' && pathname.startsWith(href + '/')) ? 'active' : ''}`}
          >
            <span className="nav-icon"><Icon size={18} strokeWidth={1.8} /></span>
            {label}
          </Link>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-footer-row">
          <div className="sidebar-meta"><Clock size={12} /> {clock}</div>
          <ThemeToggle size={16} />
        </div>
        {meta.uptime && <div className="sidebar-meta"><Server size={12} /> Up {meta.uptime}</div>}
        {meta.weather && <div className="sidebar-meta"><CloudSun size={12} /> {meta.weather}</div>}
      </div>
    </aside>
  )
})
