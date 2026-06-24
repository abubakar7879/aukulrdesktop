export type Client = {
  id: string
  name: string
  userId: string
  status: 'enabled' | 'disabled'
  expiryDate: string
  createdAt: string
}

function makeUserId(): string {
  return Array.from(crypto.getRandomValues(new Uint8Array(16)))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
}

const store: Client[] = [
  {
    id: '1',
    name: 'Al-Noor Clinic',
    userId: 'a3f8c2d1e4b5f6a7b8c9d0e1f2a3b4c5',
    status: 'enabled',
    expiryDate: '2026-12-31',
    createdAt: '2026-01-10',
  },
  {
    id: '2',
    name: 'Crescent Medical Centre',
    userId: 'b7e9d2c4f1a6b3c8d5e0f7a2b9c4d1e6',
    status: 'enabled',
    expiryDate: '2026-06-28',
    createdAt: '2026-02-14',
  },
  {
    id: '3',
    name: 'Hilal Diagnostics',
    userId: 'c1d4e7f0a3b6c9d2e5f8a1b4c7d0e3f6',
    status: 'disabled',
    expiryDate: '2026-09-15',
    createdAt: '2026-03-01',
  },
  {
    id: '4',
    name: 'Rehman Healthcare',
    userId: 'd5e8f1a4b7c0d3e6f9a2b5c8d1e4f7a0',
    status: 'enabled',
    expiryDate: '2026-05-01',
    createdAt: '2025-11-20',
  },
  {
    id: '5',
    name: 'Saeed Poly Clinic',
    userId: 'e2f5a8b1c4d7e0f3a6b9c2d5e8f1a4b7',
    status: 'disabled',
    expiryDate: '2026-03-31',
    createdAt: '2025-12-05',
  },
]

let nextId = store.length + 1

export async function getClients(): Promise<Client[]> {
  return [...store]
}

export async function getClient(id: string): Promise<Client | null> {
  return store.find((c) => c.id === id) ?? null
}

export async function addClient(input: {
  name: string
  expiryDate: string
}): Promise<Client> {
  const client: Client = {
    id: String(nextId++),
    name: input.name,
    userId: makeUserId(),
    status: 'enabled',
    expiryDate: input.expiryDate,
    createdAt: new Date().toISOString().slice(0, 10),
  }
  store.push(client)
  return client
}

export async function updateClient(
  id: string,
  input: Partial<Pick<Client, 'name' | 'expiryDate'>>,
): Promise<Client> {
  const idx = store.findIndex((c) => c.id === id)
  if (idx === -1) throw new Error(`Client ${id} not found`)
  store[idx] = { ...store[idx], ...input }
  return store[idx]
}

export async function setClientStatus(
  id: string,
  enabled: boolean,
): Promise<Client> {
  const idx = store.findIndex((c) => c.id === id)
  if (idx === -1) throw new Error(`Client ${id} not found`)
  store[idx] = { ...store[idx], status: enabled ? 'enabled' : 'disabled' }
  return store[idx]
}

export async function deleteClient(id: string): Promise<void> {
  const idx = store.findIndex((c) => c.id === id)
  if (idx === -1) throw new Error(`Client ${id} not found`)
  store.splice(idx, 1)
}
