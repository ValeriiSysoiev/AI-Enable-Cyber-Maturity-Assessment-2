import { NextResponse } from 'next/server';

export async function GET() {
  // Fallback presets when API is not available
  const fallbackPresets = [
    {
      id: "cyber-for-ai",
      name: "Cyber for AI",
      version: "1.0",
      source: "NIST",
      counts: {
        pillars: 4,
        capabilities: 12,
        questions: 45
      }
    },
    {
      id: "cscm-v3",
      name: "Cybersecurity Capability Maturity Model",
      version: "3.0", 
      source: "CISA",
      counts: {
        pillars: 5,
        capabilities: 15,
        questions: 60
      }
    }
  ];
  
  return NextResponse.json(fallbackPresets);
}
