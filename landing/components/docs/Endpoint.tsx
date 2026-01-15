import clsx from 'clsx'

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

type EndpointProps = {
  method: HttpMethod
  path: string
  description: string
}

const methodColors: Record<HttpMethod, string> = {
  GET: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-400',
  POST: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-400',
  PUT: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-400',
  PATCH: 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-400',
  DELETE: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-400',
}

export function Endpoint({ method, path, description }: EndpointProps) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-gray-100 dark:border-gray-700 last:border-0">
      <span
        className={clsx(
          'inline-flex items-center px-2 py-1 rounded text-xs font-mono font-semibold',
          methodColors[method]
        )}
      >
        {method}
      </span>
      <div>
        <code className="text-sm font-mono text-gray-900 dark:text-white">{path}</code>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">{description}</p>
      </div>
    </div>
  )
}
