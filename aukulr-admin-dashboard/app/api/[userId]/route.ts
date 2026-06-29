import { NextRequest, NextResponse } from 'next/server'
import { getClientByUserId } from '@/lib/db'

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ userId: string }> },
) {
  const { userId } = await params
  const today = new Date().toISOString().slice(0, 10)
  const client = await getClientByUserId(userId.trim().toLowerCase())

  if (!client) {
    return NextResponse.json(
      { enabled: false, currentDate: today, expiryDate: null },
      { status: 404 },
    )
  }

  return NextResponse.json({
    currentDate: today,
    expiryDate: client.expiryDate,
    enabled: client.status === 'enabled',
  })
}
