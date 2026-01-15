type JsonLdProps = {
  data: Record<string, unknown>
}

/**
 * Component for rendering JSON-LD structured data.
 * The data is statically generated at build time from trusted source code,
 * not from user input, making it safe to render.
 */
export function JsonLd({ data }: JsonLdProps) {
  const jsonString = JSON.stringify(data)

  return (
    <script
      type="application/ld+json"
      suppressHydrationWarning
      dangerouslySetInnerHTML={{ __html: jsonString }}
    />
  )
}
