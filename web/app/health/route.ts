import { NextResponse } from 'next/server';

export async function GET() {
  const timestamp = new Date().toISOString();
  const status = "healthy";
  
  return NextResponse.json({ 
    status,
    timestamp,
    version: "0.1.0"
  }, {
    status: 200,
    headers: { "content-type": "application/json" }
  });
}
