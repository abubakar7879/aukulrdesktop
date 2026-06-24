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
  timestamp: string   // ISO
  actor: string
  action: AuditAction
  before?: string
  after?: string
}

const log: AuditEntry[] = []
let nextId = 1

export function addAuditEntry(entry: Omit<AuditEntry, 'id' | 'timestamp'>): void {
  log.push({
    id: String(nextId++),
    timestamp: new Date().toISOString(),
    ...entry,
  })
}

export function getClientAuditLog(clientId: string): AuditEntry[] {
  return log
    .filter((e) => e.clientId === clientId)
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
}
