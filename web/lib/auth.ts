import { type AuthOptions } from "next-auth";
import AzureADProvider from "next-auth/providers/azure-ad";
import CredentialsProvider from "next-auth/providers/credentials";

// Dynamic provider configuration - evaluated at runtime
function getProviders() {
  const aadEnabled = process.env.AUTH_MODE === "aad"
    && !!process.env.AZURE_AD_CLIENT_ID
    && !!process.env.AZURE_AD_TENANT_ID
    && !!process.env.AZURE_AD_CLIENT_SECRET;

  const demoEnabled = process.env.DEMO_E2E === "1";

  const providers = [];
  if (aadEnabled) {
    providers.push(AzureADProvider({
      clientId: process.env.AZURE_AD_CLIENT_ID!,
      clientSecret: process.env.AZURE_AD_CLIENT_SECRET!,
      tenantId: process.env.AZURE_AD_TENANT_ID!,
    }));
  }
  if (demoEnabled || providers.length === 0) {
    // Always include demo provider as fallback to prevent 405 errors
    providers.push(CredentialsProvider({
      name: "Demo",
      credentials: { email: { label: "Email", type: "text" } },
      async authorize(creds) { 
        return { 
          id: "demo-user", 
          email: creds?.email || "demo@example.com", 
          name: "Demo User",
          role: "admin", 
          groups: ["admin"] 
        }; 
      }
    }));
  }
  return providers;
}

export const authOptions: AuthOptions = {
  providers: getProviders(),
  session: { strategy: "jwt", maxAge: 30 * 24 * 60 * 60 },
  callbacks: {
    async jwt({ token, account, profile }) {
      // Surface AAD groups/roles when available
      if (account && profile) {
        token.groups = (profile as any).groups || token.groups;
        token.role = (profile as any).role || token.role;
        token.tenant_id = (profile as any).tid || token.tenant_id;
      }
      return token;
    },
    async session({ session, token }) {
      (session as any).groups = (token as any).groups || [];
      (session as any).role = (token as any).role;
      (session as any).tenant_id = (token as any).tenant_id;
      // Map to expected user format
      if (session.user) {
        (session as any).user = {
          id: session.user.email,
          email: session.user.email,
          name: session.user.name,
          roles: (token as any).groups || ['Member'],
          tenant_id: (token as any).tenant_id
        };
      }
      return session;
    }
  },
  pages: {
    signIn: "/signin",
  }
};

// Client-side utility functions
export function isAdmin(): boolean {
  if (typeof window === 'undefined') return false;
  
  // Check localStorage for admin role (demo mode)
  const email = localStorage.getItem('email');
  const adminEmails = ['admin@example.com', 'va.sysoiev@audit3a.com'];
  
  return email ? adminEmails.includes(email.toLowerCase()) : false;
}

export function getEmail(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('email');
}

export function getEngagementId(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('engagementId');
}

export function setEngagementId(id: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('engagementId', id);
}

export function requireEmail(): string {
  const email = getEmail();
  if (!email) {
    throw new Error('Email is required');
  }
  return email;
}