import { NextResponse } from "next/server";
export const runtime = "edge";

export async function POST(request: Request) {
  if (process.env.DEMO_E2E !== "1") {
    return new Response("Demo login disabled", { status: 404 });
  }
  
  // This endpoint helps CI programmatically trigger login
  // The actual auth happens via NextAuth
  return NextResponse.json({ 
    ok: true,
    message: "Demo login enabled - use NextAuth signin"
  });
}
