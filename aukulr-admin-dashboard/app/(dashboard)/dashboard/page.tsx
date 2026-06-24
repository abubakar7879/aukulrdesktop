import { getClients } from '@/lib/clients'
import ClientsView from './components/ClientsView'

export default async function DashboardPage() {
  const clients = await getClients()
  return <ClientsView clients={clients} />
}
