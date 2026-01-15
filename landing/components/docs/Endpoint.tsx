import clsx from 'clsx'

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

type EndpointProps = {
  method: HttpMethod
  path: string
  description: string
}

const methodColors: Record<HttpMethod, string> = {
  GET: 'bg-green-100 text-green-700',
  POST: 'bg-blue-100 text-blue-700',
  PUT: 'bg-yellow-100 text-yellow-700',
  PATCH: 'bg-orange-100 text-orange-700',
  DELETE: 'bg-red-100 text-red-700',
}

export function Endpoint({ method, path, description }: EndpointProps) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-gray-100 last:border-0">
      <span
        className={clsx(
          'inline-flex items-center px-2 py-1 rounded text-xs font-mono font-semibold',
          methodColors[method]
        )}
      >
        {method}
      </span>
      <div>
        <code className="text-sm font-mono text-gray-900">{path}</code>
        <p className="mt-1 text-sm text-gray-600">{description}</p>
      </div>
    </div>
  )
}
