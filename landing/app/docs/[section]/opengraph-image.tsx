import { ImageResponse } from 'next/og'
import { getSectionById } from '@/lib/docs'

export const runtime = 'edge'
export const alt = 'CronBox Documentation'
export const size = {
  width: 1200,
  height: 630,
}
export const contentType = 'image/png'

export default async function Image({ params }: { params: Promise<{ section: string }> }) {
  const { section } = await params
  const sectionData = getSectionById(section)

  const title = sectionData?.name || 'Документация'

  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#111827',
          padding: '60px 80px',
          fontFamily: 'Inter, sans-serif',
        }}
      >
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              width: '48px',
              height: '48px',
              backgroundColor: '#2563eb',
              borderRadius: '10px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <span style={{ fontSize: '28px', fontWeight: 700, color: 'white' }}>
            CronBox
          </span>
          <span style={{ fontSize: '20px', color: '#6b7280', marginLeft: '8px' }}>
            / Документация
          </span>
        </div>

        {/* Title */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            marginTop: '80px',
            flex: 1,
          }}
        >
          <span
            style={{
              fontSize: '56px',
              fontWeight: 700,
              color: 'white',
              lineHeight: 1.3,
            }}
          >
            {title}
          </span>
          <span
            style={{
              fontSize: '24px',
              color: '#9ca3af',
              marginTop: '16px',
            }}
          >
            API Reference & Guides
          </span>
        </div>

        {/* Footer */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginTop: 'auto',
          }}
        >
          <span style={{ fontSize: '20px', color: '#6b7280' }}>
            cronbox.ru/docs
          </span>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              backgroundColor: '#1f2937',
              padding: '12px 20px',
              borderRadius: '8px',
            }}
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#9ca3af"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            <span style={{ fontSize: '18px', color: '#9ca3af' }}>
              REST API
            </span>
          </div>
        </div>
      </div>
    ),
    {
      ...size,
    }
  )
}
