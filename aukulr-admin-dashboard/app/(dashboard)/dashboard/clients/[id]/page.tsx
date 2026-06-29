import { getClient } from '@/lib/clients'
import { getClientAuditLog } from '@/lib/audit'
import EditClientForm from './EditClientForm'
import { notFound } from 'next/navigation'

export default async function EditClientPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const client = await getClient(id)
  if (!client) notFound()

  const auditLog = await getClientAuditLog(id)
  return <EditClientForm client={client} auditLog={auditLog} />
}
