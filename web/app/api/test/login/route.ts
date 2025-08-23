// CI-only login helper (guarded by DEMO_E2E=1). Sets a stable demo session.
import { NextResponse } from "next/server";
export const runtime = "edge";
export async function POST() {
  if (process.env.DEMO_E2E !== "1") return new Response("disabled", { status: 404 });
  // Minimal cookie; your NextAuth will create a real one — this endpoint just hints e2e path exists.
  return NextResponse.json({ ok: true });
}
