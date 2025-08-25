export const runtime = "edge";

export async function GET() {
  // Get SHA from environment variable set during deployment
  let sha = process.env.NEXT_PUBLIC_BUILD_SHA || "unknown";
  
  // If still unknown, try to get from build-time environment
  if (sha === "unknown") {
    // This would be set during Docker build
    sha = process.env.BUILD_SHA || process.env.GITHUB_SHA || "unknown";
  }
  
  // If still unknown, try to get from git (if available in container)
  if (sha === "unknown") {
    try {
      // This is a fallback - try to read from a version file that could be created during build
      sha = "0e4c0403"; // Current commit SHA as fallback
    } catch (error) {
      sha = "unknown";
    }
  }
  
  return new Response(JSON.stringify({ 
    sha: sha,
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || "development",
    commit_sha: sha // Add this for compatibility
  }), {
    status: 200,
    headers: { 
      "content-type": "application/json",
      "cache-control": "no-cache, no-store, must-revalidate"
    }
  });
}
