import { NextRequest, NextResponse } from 'next/server'
import { createRegistrationRequest } from '@/lib/db'

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { cpuId, clinicName, contact, machineName, windowsUser } = body

    if (!cpuId || !clinicName || !contact) {
      return NextResponse.json(
        { success: false, message: 'cpuId, clinicName, and contact are required.' },
        { status: 400 },
      )
    }

    await createRegistrationRequest({
      cpuId: cpuId.trim().toLowerCase(),
      clinicName: clinicName.trim(),
      contact: contact.trim(),
      machineName: (machineName ?? '').trim(),
      windowsUser: (windowsUser ?? '').trim(),
    })

    return NextResponse.json({ success: true, message: 'Registration request submitted.' })
  } catch {
    return NextResponse.json(
      { success: false, message: 'Server error. Please try again.' },
      { status: 500 },
    )
  }
}
