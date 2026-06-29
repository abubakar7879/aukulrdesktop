import { PrismaClient } from '@prisma/client'

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient }

export const prisma =
  globalForPrisma.prisma ?? new PrismaClient()

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma

// ─── Types ───────────────────────────────────────────────────────────────────

export type Client = {
  id: string
  name: string
  userId: string
  status: 'enabled' | 'disabled'
  expiryDate: string
  createdAt: string
  lastUpdated: string
  notes?: string
}

export type AuditAction =
  | 'created'
  | 'enabled'
  | 'disabled'
  | 'expiry_changed'
  | 'userid_changed'
  | 'notes_updated'
  | 'removed'

export type AuditEntry = {
  id: string
  clientId: string
  timestamp: string
  actor: string
  action: AuditAction
  before?: string
  after?: string
}

export type RegistrationRequest = {
  id: string
  cpuId: string
  clinicName: string
  contact: string
  machineName: string
  windowsUser: string
  requestedAt: string
  status: 'pending' | 'approved' | 'rejected'
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function today(): string {
  return new Date().toISOString().slice(0, 10)
}

function toClient(raw: {
  id: string
  name: string
  userId: string
  status: string
  expiryDate: string
  createdAt: string
  lastUpdated: string
  notes: string | null
}): Client {
  return {
    ...raw,
    status: raw.status as 'enabled' | 'disabled',
    notes: raw.notes ?? undefined,
  }
}

function toAuditEntry(raw: {
  id: string
  clientId: string
  timestamp: string
  actor: string
  action: string
  before: string | null
  after: string | null
}): AuditEntry {
  return {
    ...raw,
    action: raw.action as AuditAction,
    before: raw.before ?? undefined,
    after: raw.after ?? undefined,
  }
}

// ─── Client Queries ───────────────────────────────────────────────────────────

export async function getClients(): Promise<Client[]> {
  const rows = await prisma.client.findMany({ orderBy: { createdAt: 'desc' } })
  return rows.map(toClient)
}

export async function getClient(id: string): Promise<Client | null> {
  const row = await prisma.client.findUnique({ where: { id } })
  return row ? toClient(row) : null
}

export async function getClientByUserId(userId: string): Promise<Client | null> {
  const row = await prisma.client.findUnique({ where: { userId } })
  return row ? toClient(row) : null
}

export async function checkUserIdExists(userId: string, excludeId?: string): Promise<boolean> {
  const count = await prisma.client.count({
    where: { userId, ...(excludeId ? { NOT: { id: excludeId } } : {}) },
  })
  return count > 0
}

export async function addClient(input: {
  name: string
  userId: string
  expiryDate: string
  notes?: string
}): Promise<Client> {
  const t = today()
  const row = await prisma.client.create({
    data: {
      name: input.name,
      userId: input.userId,
      status: 'enabled',
      expiryDate: input.expiryDate,
      createdAt: t,
      lastUpdated: t,
      notes: input.notes ?? null,
    },
  })
  return toClient(row)
}

export async function updateClient(
  id: string,
  input: Partial<Pick<Client, 'name' | 'userId' | 'expiryDate' | 'notes'>>,
): Promise<Client> {
  const row = await prisma.client.update({
    where: { id },
    data: { ...input, notes: input.notes ?? null, lastUpdated: today() },
  })
  return toClient(row)
}

export async function setClientStatus(id: string, enabled: boolean): Promise<Client> {
  const row = await prisma.client.update({
    where: { id },
    data: { status: enabled ? 'enabled' : 'disabled', lastUpdated: today() },
  })
  return toClient(row)
}

export async function deleteClient(id: string): Promise<void> {
  await prisma.client.delete({ where: { id } })
}

// ─── Audit Queries ────────────────────────────────────────────────────────────

export async function addAuditEntry(
  entry: Omit<AuditEntry, 'id' | 'timestamp'>,
): Promise<void> {
  await prisma.auditEntry.create({
    data: {
      clientId: entry.clientId,
      timestamp: new Date().toISOString(),
      actor: entry.actor,
      action: entry.action,
      before: entry.before ?? null,
      after: entry.after ?? null,
    },
  })
}

export async function getClientAuditLog(clientId: string): Promise<AuditEntry[]> {
  const rows = await prisma.auditEntry.findMany({
    where: { clientId },
    orderBy: { timestamp: 'desc' },
  })
  return rows.map(toAuditEntry)
}

// ─── Registration Requests ────────────────────────────────────────────────────

export async function createRegistrationRequest(input: {
  cpuId: string
  clinicName: string
  contact: string
  machineName: string
  windowsUser: string
}): Promise<RegistrationRequest> {
  const row = await prisma.registrationRequest.upsert({
    where: { cpuId: input.cpuId },
    update: {
      clinicName: input.clinicName,
      contact: input.contact,
      machineName: input.machineName,
      windowsUser: input.windowsUser,
      requestedAt: new Date().toISOString(),
      status: 'pending',
    },
    create: {
      cpuId: input.cpuId,
      clinicName: input.clinicName,
      contact: input.contact,
      machineName: input.machineName,
      windowsUser: input.windowsUser,
      requestedAt: new Date().toISOString(),
      status: 'pending',
    },
  })
  return row as RegistrationRequest
}

export async function getRegistrationRequests(): Promise<RegistrationRequest[]> {
  const rows = await prisma.registrationRequest.findMany({
    orderBy: { requestedAt: 'desc' },
  })
  return rows as RegistrationRequest[]
}

export async function updateRegistrationStatus(
  id: string,
  status: 'approved' | 'rejected',
): Promise<void> {
  await prisma.registrationRequest.update({ where: { id }, data: { status } })
}
