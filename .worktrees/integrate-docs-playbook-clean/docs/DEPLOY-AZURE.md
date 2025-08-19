# Deploy to Azure (Outline)

> This is a **starter**. You will need to plug identities, ACR images, and auth.

## 1) Prereqs
- Azure CLI (`az`), Azure Developer CLI (`azd`)
- GitHub repo with OIDC to Azure (or a Service Principal secret)
- ACR (Azure Container Registry) or use `azd` to create one

## 2) Infra
```bash
azd init
azd up
```
This will create Log Analytics, App Insights, Key Vault, Cosmos DB, Service Bus, and a Container Apps Environment.

## 3) Build & Push Images
Use GitHub Actions (see `.github/workflows/deploy.yml`) or local:
```bash
# example local build
az acr build --registry <acrName> --image api:latest services/api
# repeat for each service...
```

## 4) Container Apps
Define Container Apps for each service to pull from ACR and set env vars:
- API: `ORCHESTRATOR_URL`
- ORCH: URLs for each agent
- Shared: `DATA_DIR` (for persistent storage mount or switch to Cosmos DB)

## 5) Identity / Auth
- Register Azure AD app for API (audience) and for SPA (frontend).
- Validate JWT in API (add FastAPI dependency to verify `Authorization: Bearer`).
- Frontend uses MSAL to sign in and call API.

## 6) Data
- Replace local file persistence with Cosmos DB containers:
  - `projects`, `evidence`, `gaps`, `initiatives`, `roadmap`, `reports`
- Use Managed Identity for API/Orchestrator to access Cosmos and Key Vault.

## 7) Azure OpenAI
- Add endpoint and key in Key Vault; agents call `gpt-4o`/`o4-mini` for analysis.
- Keep a strict prompt template with **explanations** for transparency.

## 8) Monitoring
- Container Apps → Log Analytics (already wired via environment).
- Sentinel rules for error spikes or auth failures.
