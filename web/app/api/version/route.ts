export const runtime = "edge";

export async function GET() {
  // Priority order for getting the SHA:
  // 1. Runtime environment variable (set by Azure App Service)
  // 2. Build-time environment variables (set during Docker build)
  // 3. Fallback to unknown
  
  let sha = process.env.NEXT_PUBLIC_BUILD_SHA || 
            process.env.BUILD_SHA || 
            process.env.GITHUB_SHA || 
            "unknown";
  
  // Remove any hardcoded fallbacks that could mask issues
  if (sha === "unknown") {
    console.warn("⚠️  No version information found in environment variables");
  }
  
  return new Response(JSON.stringify({ 
    sha: sha,
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || "development",
    commit_sha: sha,
    // Add debug info to help troubleshoot in the future
    debug: {
      next_public_build_sha: process.env.NEXT_PUBLIC_BUILD_SHA ? "set" : "not set",
      build_sha: process.env.BUILD_SHA ? "set" : "not set", 
      github_sha: process.env.GITHUB_SHA ? "set" : "not set"
    }
  }), {
    status: 200,
    headers: { 
      "content-type": "application/json",
      "cache-control": "no-cache, no-store, must-revalidate"
    }
  });
}
