type CodeBlockProps = {
  code: string
  language?: string
}

export function CodeBlock({ code, language = 'bash' }: CodeBlockProps) {
  return (
    <pre
      className={`language-${language} rounded-lg bg-gray-900 p-4 overflow-x-auto text-sm`}
    >
      <code className="text-gray-300">{code}</code>
    </pre>
  )
}
