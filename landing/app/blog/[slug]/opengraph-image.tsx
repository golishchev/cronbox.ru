import { ImageResponse } from 'next/og'
import { getPostBySlug } from '@/lib/blog'

export const runtime = 'nodejs'
export const alt = 'CronBox Blog'
export const size = {
  width: 1200,
  height: 630,
}
export const contentType = 'image/png'

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params
  const post = getPostBySlug(slug)

  const title = post?.title || 'CronBox Blog'

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
            / Блог
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
              fontSize: title.length > 50 ? '48px' : '56px',
              fontWeight: 700,
              color: 'white',
              lineHeight: 1.3,
              maxWidth: '1000px',
            }}
          >
            {title}
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
            cronbox.ru/blog
          </span>
          <div
            style={{
              display: 'flex',
              gap: '24px',
            }}
          >
            {['Heartbeat', 'SSL', 'Cron', 'Автоматизация'].map((tag) => (
              <span
                key={tag}
                style={{
                  fontSize: '16px',
                  color: '#9ca3af',
                  backgroundColor: '#1f2937',
                  padding: '8px 16px',
                  borderRadius: '6px',
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    ),
    {
      ...size,
    }
  )
}
