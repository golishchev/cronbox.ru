import { ImageResponse } from 'next/og'

export const runtime = 'edge'

export const alt = 'CronBox — Платформа мониторинга и автоматизации'
export const size = {
  width: 1200,
  height: 630,
}
export const contentType = 'image/png'

export default async function Image() {
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
              width: '56px',
              height: '56px',
              backgroundColor: '#2563eb',
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg
              width="32"
              height="32"
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
          <span style={{ fontSize: '32px', fontWeight: 700, color: 'white' }}>
            CronBox
          </span>
        </div>

        {/* Main title */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            marginTop: '60px',
            gap: '8px',
          }}
        >
          <span
            style={{
              fontSize: '64px',
              fontWeight: 700,
              color: 'white',
              lineHeight: 1.2,
            }}
          >
            Узнайте первым, когда
          </span>
          <span
            style={{
              fontSize: '64px',
              fontWeight: 700,
              color: '#3b82f6',
              lineHeight: 1.2,
            }}
          >
            что-то пойдёт не так
          </span>
        </div>

        {/* Features */}
        <div
          style={{
            display: 'flex',
            gap: '32px',
            marginTop: '48px',
          }}
        >
          {[
            { icon: '💓', label: 'Heartbeat', color: '#22c55e' },
            { icon: '🛡️', label: 'SSL', color: '#a855f7' },
            { icon: '⏰', label: 'Cron', color: '#3b82f6' },
            { icon: '🔗', label: 'Цепочки', color: '#f97316' },
          ].map((feature) => (
            <div
              key={feature.label}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                backgroundColor: '#1f2937',
                padding: '12px 20px',
                borderRadius: '8px',
              }}
            >
              <span style={{ fontSize: '24px' }}>{feature.icon}</span>
              <span style={{ fontSize: '20px', color: '#9ca3af' }}>
                {feature.label}
              </span>
            </div>
          ))}
        </div>

        {/* Status examples */}
        <div
          style={{
            display: 'flex',
            gap: '24px',
            marginTop: 'auto',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <div
              style={{
                width: '12px',
                height: '12px',
                backgroundColor: '#22c55e',
                borderRadius: '50%',
              }}
            />
            <span style={{ fontSize: '18px', color: '#22c55e' }}>Работает</span>
          </div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <div
              style={{
                width: '12px',
                height: '12px',
                backgroundColor: '#eab308',
                borderRadius: '50%',
              }}
            />
            <span style={{ fontSize: '18px', color: '#eab308' }}>Истекает</span>
          </div>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <div
              style={{
                width: '12px',
                height: '12px',
                backgroundColor: '#ef4444',
                borderRadius: '50%',
              }}
            />
            <span style={{ fontSize: '18px', color: '#ef4444' }}>
              Не отвечает
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
