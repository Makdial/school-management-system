import { Navigate, useParams } from 'react-router-dom'
import { ResourceView } from '@/components/ResourceView'
import { resourceByKey } from '@/config/resources'

export function ResourcePage() {
  const { key } = useParams<{ key: string }>()
  const resource = key ? resourceByKey(key) : undefined
  if (!resource) return <Navigate to="/dashboard" replace />
  return <ResourceView key={resource.key} config={resource} />
}
