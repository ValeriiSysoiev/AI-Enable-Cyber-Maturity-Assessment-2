import { NextResponse } from 'next/server';
import { readFileSync } from 'fs';
import path from 'path';

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  const { id } = params;

  try {
    // Try to read the preset file from the app/config/presets directory
    const presetPath = path.join(process.cwd(), '..', 'app', 'config', 'presets', `${id}.json`);
    
    try {
      const presetData = readFileSync(presetPath, 'utf8');
      const preset = JSON.parse(presetData);
      return NextResponse.json(preset);
    } catch (fileError) {
      // If cyber-for-ai.json doesn't exist, try the alternative filename
      if (id === 'cscm-v3') {
        try {
          const altPath = path.join(process.cwd(), '..', 'app', 'config', 'presets', 'preset_cscm_v3.json');
          const presetData = readFileSync(altPath, 'utf8');
          const preset = JSON.parse(presetData);
          return NextResponse.json(preset);
        } catch (altError) {
          // Fall through to fallback data
        }
      }
    }

    // Fallback preset data when files are not available
    const fallbackPresets: { [key: string]: any } = {
      'cyber-for-ai': {
        "schema_version": "0.1.0",
        "id": "cyber-for-ai",
        "name": "Cyber for AI (Secure the AI)",
        "description": "Preset focused on securing models, data, pipelines, prompts and agents. Maps to NIST AI RMF, ISO/IEC 42001, and OWASP LLM Top 10.",
        "default_target_level": 4,
        "maturity_levels": {
          "1": "Ad hoc",
          "2": "Emerging controls",
          "3": "Defined & repeatable",
          "4": "Managed & risk-based",
          "5": "Optimized & continuous"
        },
        "pillars": [
          { "id": "governance", "name": "Governance & Responsible AI", "weight": 0.20, "examples": ["AI policy, intake workflow, risk acceptance, RACI"] },
          { "id": "model_security", "name": "Model & Prompt Security", "weight": 0.20, "examples": ["prompt injection defenses, output filters, key handling"] },
          { "id": "data_security", "name": "Data Security & Privacy", "weight": 0.20, "examples": ["training/inference data protection, DLP, retention"] },
          { "id": "supply_chain", "name": "AI Supply Chain & Ops Security", "weight": 0.15, "examples": ["artifact signing/verification, CI/CD hardening"] },
          { "id": "evals_monitoring", "name": "Evaluations, Guardrails & Monitoring", "weight": 0.15, "examples": ["eval suites, jailbreak testing, drift & safety monitoring"] },
          { "id": "platform_access", "name": "Platform & Access Controls", "weight": 0.10, "examples": ["platform baseline, network controls, IAM/JIT/JEA"] }
        ],
        "scoring": {
          "method": "weighted_average",
          "gates": [
            { "pillar": "governance", "min_level": 2, "reason": "Minimum governance required to exceed overall level 3" }
          ]
        },
        "mappings": {
          "nist_ai_rmf": { "functions": ["Govern", "Map", "Measure", "Manage"] },
          "iso_42001": { "clauses": ["Context", "Leadership", "Planning", "Support", "Operation", "Performance evaluation", "Improvement"] },
          "nist_csf_2_0": { "functions": ["Identify", "Protect", "Detect", "Respond", "Recover", "Govern"] },
          "owasp_llm_top10_2023": [
            "LLM01: Prompt Injection",
            "LLM02: Data Leakage",
            "LLM03: Supply Chain",
            "LLM04: Model Theft",
            "LLM05: Insecure Output Handling"
          ]
        },
        "questions": {
          "governance": [
            {
              "id": "gov-01",
              "text": "Is there an approved AI policy with roles, intake workflow, and risk approvals?",
              "evidence": ["AI policy doc", "intake process", "approval records"],
              "level_hints": { "3": "Policy approved; roles & intake defined", "4": "Risk-based approvals with periodic review and metrics" }
            },
            {
              "id": "gov-02",
              "text": "Are AI risk assessments performed per use case and tracked in a risk register?",
              "evidence": ["methodology", "risk register entries"],
              "level_hints": { "3": "Standard method applied", "4": "Thresholds drive controls and go/no-go decisions" }
            }
          ],
          "model_security": [
            {
              "id": "mod-01",
              "text": "Are prompt-injection and data-exfiltration tests executed per release with documented mitigations?",
              "evidence": ["test plans", "results", "mitigation PRs"],
              "level_hints": { "3": "Basic tests exist", "4": "Automated gates with thresholds and regression history" }
            }
          ],
          "data_security": [
            {
              "id": "data-01",
              "text": "Is training/inference data classified, access-controlled, and protected by preventive DLP where appropriate?",
              "evidence": ["data map", "classification standard", "DLP policy/config"],
              "level_hints": { "3": "Classification defined & applied", "4": "Preventive enforcement + periodic audits" }
            }
          ],
          "supply_chain": [
            {
              "id": "sc-01",
              "text": "Are model artifacts and dependencies signed and verified in CI/CD with provenance records?",
              "evidence": ["sigstore/cosign logs", "pipeline config"],
              "level_hints": { "3": "Signing present", "4": "Verification enforced; failure blocks release" }
            }
          ],
          "evals_monitoring": [
            {
              "id": "eval-01",
              "text": "Are evals for safety, security, bias, and drift run and reviewed with alerts on regressions?",
              "evidence": ["eval reports", "alert config", "review minutes"],
              "level_hints": { "3": "Periodic manual evals", "4": "Automated eval suite with SLOs & alerting" }
            }
          ],
          "platform_access": [
            {
              "id": "plat-01",
              "text": "Is least-privilege enforced for models, prompts, data, and keys with JIT/JEA and recertification?",
              "evidence": ["IAM policy", "PIM/JIT config", "access review logs"],
              "level_hints": { "3": "RBAC defined", "4": "JIT/JEA + periodic recertification + anomaly detection" }
            }
          ]
        },
        "evidence": { "allowed_types": ["pdf", "docx", "xlsx", "csv", "md", "png", "jpg"], "storage_container": "docs" }
      },
      'cscm-v3': {
        "id": "cscm-v3",
        "name": "Cyber Security Capability Model v3",
        "version": "3.0",
        "generated_at": "2025-08-14T21:20:40Z",
        "source_file": "Cyber+Security+Capability+Model+v3.xlsx",
        "description": "Comprehensive cybersecurity capability maturity model covering governance, identification, protection, detection, response, and recovery functions.",
        "columns_mapping": {
          "pillar": "Function",
          "capability": "Category",
          "question": "Control Statement",
          "weight": "Weight"
        },
        "stats": {
          "pillars": 6,
          "capabilities": 22,
          "questions": 448
        },
        "maturity_levels": {
          "0": "Not Implemented",
          "1": "Initial",
          "2": "Developing",
          "3": "Defined",
          "4": "Managed",
          "5": "Optimized"
        },
        "pillars": [
          {
            "id": "govern",
            "name": "Govern",
            "weight": 0.20,
            "description": "Establish, communicate, and monitor organizational cybersecurity policy, procedures, and processes"
          },
          {
            "id": "identify",
            "name": "Identify", 
            "weight": 0.20,
            "description": "Understanding cybersecurity risks to systems, people, assets, data, and capabilities"
          },
          {
            "id": "protect",
            "name": "Protect",
            "weight": 0.20,
            "description": "Implement safeguards to ensure delivery of critical infrastructure services"
          },
          {
            "id": "detect",
            "name": "Detect",
            "weight": 0.15,
            "description": "Develop and implement activities to identify occurrence of cybersecurity events"
          },
          {
            "id": "respond",
            "name": "Respond",
            "weight": 0.15,
            "description": "Develop and implement activities to take action regarding detected cybersecurity incidents"
          },
          {
            "id": "recover",
            "name": "Recover",
            "weight": 0.10,
            "description": "Develop and implement activities to maintain resilience and restore capabilities impaired by cybersecurity incidents"
          }
        ],
        "scoring": {
          "method": "weighted_average"
        },
        "evidence": { "allowed_types": ["pdf", "docx", "xlsx", "csv", "md", "png", "jpg"], "storage_container": "docs" }
      }
    };

    const preset = fallbackPresets[id];
    if (!preset) {
      return NextResponse.json(
        { error: 'Preset not found', available_presets: Object.keys(fallbackPresets) },
        { status: 404 }
      );
    }

    return NextResponse.json(preset);
  } catch (error) {
    console.error('Error fetching preset:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}