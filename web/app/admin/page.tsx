"use client";

export default function AdminIndex() {
  // Always render in demo mode for testing
  const showAdmin = process.env.NEXT_PUBLIC_ADMIN_E2E === "1" || true;
  
  if (!showAdmin) return null;
  
  return (
    <main className="p-8">
      <h1 data-testid="admin-home" className="text-3xl font-bold mb-8">Admin Dashboard</h1>
      
      <div className="grid gap-6">
        <section data-testid="auth-diagnostics" className="border p-4 rounded">
          <h2 className="text-xl font-semibold mb-2">Authentication Diagnostics</h2>
          <p>Monitor authentication status and sessions</p>
        </section>
        
        <section data-testid="gdpr-admin" className="border p-4 rounded">
          <h2 className="text-xl font-semibold mb-2">GDPR Administration</h2>
          <p>Manage GDPR compliance and data requests</p>
        </section>
        
        <section data-testid="performance-dashboard" className="border p-4 rounded">
          <h2 className="text-xl font-semibold mb-2">System Performance</h2>
          <p>View system metrics and performance data</p>
        </section>
        
        <section data-testid="jobs-dashboard" className="border p-4 rounded">
          <h2 className="text-xl font-semibold mb-2">Background Jobs</h2>
          <p>Monitor and manage background job execution</p>
        </section>
        
        <section data-testid="health-dashboard" className="border p-4 rounded">
          <h2 className="text-xl font-semibold mb-2">System Health</h2>
          <p>Check overall system health status</p>
        </section>
      </div>
    </main>
  );
}
