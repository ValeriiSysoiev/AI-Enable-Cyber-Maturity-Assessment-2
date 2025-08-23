export const dynamic = "force-static";
export default function AdminIndex(){
  const showAdmin = process.env.NEXT_PUBLIC_ADMIN_E2E === "1";
  if (!showAdmin) return null;
  return (
    <main>
      <h1 data-testid="admin-home">Admin</h1>
      <div data-testid="auth-diagnostics">Auth Diagnostics</div>
      <div data-testid="gdpr-admin">GDPR Administration</div>
      <div data-testid="performance-dashboard">System Performance</div>
      <div data-testid="jobs-dashboard">Background Jobs</div>
      <div data-testid="health-dashboard">System Health</div>
    </main>
  );
}
