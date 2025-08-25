import { NextResponse } from 'next/server';
import { readFileSync } from 'fs';
import path from 'path';

export async function GET() {
  // Try to read preset information from actual files first
  const presetSummaries = [];
  
  try {
    // Try to read cyber-for-ai preset
    const cyberAiPath = path.join(process.cwd(), '..', 'app', 'config', 'presets', 'cyber-for-ai.json');
    try {
      const cyberAiData = JSON.parse(readFileSync(cyberAiPath, 'utf8'));
      const pillarCount = cyberAiData.pillars?.length || 0;
      let questionCount = 0;
      if (cyberAiData.questions) {
        questionCount = Object.values(cyberAiData.questions).reduce((sum: number, questions: any) => sum + (Array.isArray(questions) ? questions.length : 0), 0);
      }
      
      presetSummaries.push({
        id: cyberAiData.id || "cyber-for-ai",
        name: cyberAiData.name || "Cyber for AI",
        description: cyberAiData.description || "Preset focused on securing AI models, data, pipelines, prompts and agents",
        version: "1.0",
        source: "NIST AI RMF, ISO/IEC 42001, OWASP LLM Top 10",
        counts: {
          pillars: pillarCount,
          capabilities: pillarCount, // Each pillar is roughly a capability in this preset
          questions: questionCount
        }
      });
    } catch (error) {
      // File not found or parse error, use fallback data
      presetSummaries.push({
        id: "cyber-for-ai",
        name: "Cyber for AI (Secure the AI)",
        description: "Preset focused on securing AI models, data, pipelines, prompts and agents. Maps to NIST AI RMF, ISO/IEC 42001, and OWASP LLM Top 10.",
        version: "1.0",
        source: "NIST AI RMF, ISO/IEC 42001, OWASP LLM Top 10",
        counts: {
          pillars: 6,
          capabilities: 6,
          questions: 6
        }
      });
    }

    // Try to read cscm-v3 preset
    const cscmPath = path.join(process.cwd(), '..', 'app', 'config', 'presets', 'preset_cscm_v3.json');
    try {
      const cscmData = JSON.parse(readFileSync(cscmPath, 'utf8'));
      presetSummaries.push({
        id: cscmData.id || "cscm-v3",
        name: cscmData.name || "Cyber Security Capability Model v3",
        description: "Comprehensive cybersecurity capability maturity model covering governance, identification, protection, detection, response, and recovery functions.",
        version: cscmData.version || "3.0",
        source: "CISA",
        counts: {
          pillars: cscmData.stats?.pillars || 6,
          capabilities: cscmData.stats?.capabilities || 22,
          questions: cscmData.stats?.questions || 448
        }
      });
    } catch (error) {
      // File not found or parse error, use fallback data
      presetSummaries.push({
        id: "cscm-v3",
        name: "Cyber Security Capability Model v3",
        description: "Comprehensive cybersecurity capability maturity model covering governance, identification, protection, detection, response, and recovery functions.",
        version: "3.0",
        source: "CISA",
        counts: {
          pillars: 6,
          capabilities: 22,
          questions: 448
        }
      });
    }
  } catch (error) {
    console.error('Error reading preset files:', error);
    // Complete fallback if everything fails
    presetSummaries.push(
      {
        id: "cyber-for-ai",
        name: "Cyber for AI (Secure the AI)",
        description: "Preset focused on securing AI models, data, pipelines, prompts and agents",
        version: "1.0",
        source: "NIST AI RMF, ISO/IEC 42001, OWASP LLM Top 10",
        counts: {
          pillars: 6,
          capabilities: 6,
          questions: 6
        }
      },
      {
        id: "cscm-v3",
        name: "Cyber Security Capability Model v3", 
        description: "Comprehensive cybersecurity capability maturity model",
        version: "3.0",
        source: "CISA",
        counts: {
          pillars: 6,
          capabilities: 22,
          questions: 448
        }
      }
    );
  }
  
  return NextResponse.json(presetSummaries);
}
