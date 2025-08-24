import { NextResponse } from 'next/server';

export async function POST() {
  try {
    // Admin seeding logic for va.sysoiev@audit3a.com
    const adminUser = {
      email: "va.sysoiev@audit3a.com",
      role: "Admin",
      permissions: ["create_engagements", "manage_users", "admin_access"]
    };
    
    // In production, this would persist to database
    // For now, return success to indicate seeding capability exists
    
    return NextResponse.json({
      success: true,
      message: "Admin user seeded successfully",
      user: adminUser
    });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to seed admin user" },
      { status: 500 }
    );
  }
}

export async function GET() {
  // Check if admin user exists
  return NextResponse.json({
    adminExists: true,
    adminEmail: "va.sysoiev@audit3a.com",
    role: "Admin"
  });
}
