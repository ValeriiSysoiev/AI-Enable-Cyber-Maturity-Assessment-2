import { type AuthOptions } from "next-auth";
import AzureADProvider from "next-auth/providers/azure-ad";
import CredentialsProvider from "next-auth/providers/credentials";

// Dynamic provider configuration - evaluated at runtime
function getProviders() {
  // Production safety check
  const isProduction = process.env.NODE_ENV === 'production';

  const aadEnabled = process.env.AUTH_MODE === "aad"
    && !!process.env.AZURE_AD_CLIENT_ID
    && !!process.env.AZURE_AD_TENANT_ID
    && !!process.env.AZURE_AD_CLIENT_SECRET;

  // Demo mode is ONLY allowed in non-production environments
  const demoEnabled = !isProduction && process.env.DEMO_E2E === "1";

  const providers = [];
  if (aadEnabled) {
    providers.push(AzureADProvider({
      clientId: process.env.AZURE_AD_CLIENT_ID!,
      clientSecret: process.env.AZURE_AD_CLIENT_SECRET!,
      tenantId: process.env.AZURE_AD_TENANT_ID!,
      authorization: {
        params: {
          scope: "openid profile email",
          response_type: "code",
          response_mode: "query",
          prompt: "select_account", // Always show account selection
        },
      },
      httpOptions: {
        timeout: 10000,
      },
      profile(profile) {
        return {
          id: profile.sub || profile.oid,
          name: profile.name,
          email: profile.email || profile.preferred_username,
          image: null,
        };
      },
    }));
  }
  // Demo provider ONLY in development/test environments
  if (demoEnabled && !isProduction) {
    providers.push(CredentialsProvider({
      name: "Demo",
      credentials: { email: { label: "Email", type: "text" } },
      async authorize(creds) { 
        return { 
          id: "demo-user", 
          email: creds?.email || "demo@example.com", 
          name: "Demo User",
          role: "member", // Never grant admin in demo mode
          groups: ["member"] 
        }; 
      }
    }));
  }
  
  // Note: In production, AAD will be validated at runtime when secrets are injected
  // Don't validate during build time as secrets aren't available in Docker build context
  return providers;
}

// Runtime validation function (called only when auth is actually used)
function validateProductionConfig() {
  const isProduction = process.env.NODE_ENV === 'production';
  if (isProduction) {
    const aadEnabled = process.env.AUTH_MODE === "aad"
      && !!process.env.AZURE_AD_CLIENT_ID
      && !!process.env.AZURE_AD_TENANT_ID
      && !!process.env.AZURE_AD_CLIENT_SECRET;
    
    if (!aadEnabled) {
      throw new Error("Production requires Azure AD authentication to be configured");
    }
  }
}

export const authOptions: AuthOptions = {
  secret: process.env.NEXTAUTH_SECRET || process.env.AUTH_SECRET,
  providers: getProviders(),
  session: { strategy: "jwt", maxAge: 30 * 24 * 60 * 60 },
  callbacks: {
    async jwt({ token, account, profile }) {
      // Runtime validation only when auth is actually used
      validateProductionConfig();
      
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
    },
    async signIn({ user, account, profile, email, credentials }) {
      // Validate sign-in attempt
      return true;
    },
    async redirect({ url, baseUrl }) {
      // Ensure we redirect to the correct base URL
      if (url.startsWith("/")) return `${baseUrl}${url}`;
      if (new URL(url).origin === baseUrl) return url;
      return baseUrl;
    }
  },
  events: {
    async signOut(message) {
      // Clear server-side session completely
    }
  },
  pages: {
    signIn: "/signin",
    error: "/signin?error=true",
  },
  debug: process.env.NODE_ENV === "development"
};

// Client-side utility functions
export function isAdmin(): boolean {
  if (typeof window === 'undefined') return false;
  
  // Demo mode only - production uses server-side role checks
  if (process.env.NODE_ENV === 'production') return false;
  
  // Check localStorage for admin role (demo mode)
  const email = localStorage.getItem('email');
  const adminEmails = ['admin@example.com'];
  
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