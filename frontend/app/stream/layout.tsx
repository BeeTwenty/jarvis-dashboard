import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Stream — Jarvis',
}

export default function StreamLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 1000, background: '#000' }}>
      {children}
    </div>
  )
}
