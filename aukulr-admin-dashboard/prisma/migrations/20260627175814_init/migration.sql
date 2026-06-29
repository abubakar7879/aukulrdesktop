-- CreateTable
CREATE TABLE "Client" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'enabled',
    "expiryDate" TEXT NOT NULL,
    "createdAt" TEXT NOT NULL,
    "lastUpdated" TEXT NOT NULL,
    "notes" TEXT
);

-- CreateTable
CREATE TABLE "AuditEntry" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "clientId" TEXT NOT NULL,
    "timestamp" TEXT NOT NULL,
    "actor" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "before" TEXT,
    "after" TEXT,
    CONSTRAINT "AuditEntry_clientId_fkey" FOREIGN KEY ("clientId") REFERENCES "Client" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "RegistrationRequest" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "cpuId" TEXT NOT NULL,
    "clinicName" TEXT NOT NULL,
    "contact" TEXT NOT NULL,
    "machineName" TEXT NOT NULL,
    "windowsUser" TEXT NOT NULL,
    "requestedAt" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'pending'
);

-- CreateIndex
CREATE UNIQUE INDEX "Client_userId_key" ON "Client"("userId");

-- CreateIndex
CREATE UNIQUE INDEX "RegistrationRequest_cpuId_key" ON "RegistrationRequest"("cpuId");
