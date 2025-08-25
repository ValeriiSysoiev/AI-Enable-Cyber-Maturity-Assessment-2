import { NextResponse } from 'next/server';

// Fallback admin users when backend is unavailable
const adminUsers = [
  {
    email: "va.sysoiev@audit3a.com",
    name: "Valentyn Sysoiev", 
    roles: ["Admin"],
    status: "active",
    created_at: "2025-08-24T00:00:00Z"
  }
];

export async function GET(request: Request) {
  try {
    return NextResponse.json(adminUsers);
  } catch (error) {
    console.error("Admin users API error:", error);
    return NextResponse.json({ error: "Failed to fetch admin users" }, { status: 500 });
  }
}
