import { type AuthOptions } from "next-auth";
import AzureADProvider from "next-auth/providers/azure-ad";
import CredentialsProvider from "next-auth/providers/credentials";

// Dynamic provider configuration - evaluated at runtime
function getProviders() {
  // Debug environment variables
  console.log("Auth config debug:", {
    AUTH_MODE: process.env.AUTH_MODE,
    AZURE_AD_CLIENT_ID: !!process.env.AZURE_AD_CLIENT_ID ? "SET" : "MISSING",
    AZURE_AD_TENANT_ID: !!process.env.AZURE_AD_TENANT_ID ? "SET" : "MISSING", 
    AZURE_AD_CLIENT_SECRET: !!process.env.AZURE_AD_CLIENT_SECRET ? "SET" : "MISSING",
    DEMO_E2E: process.env.DEMO_E2E,
  });

  const aadEnabled = process.env.AUTH_MODE === "aad"
    && !!process.env.AZURE_AD_CLIENT_ID
    && !!process.env.AZURE_AD_TENANT_ID
    && !!process.env.AZURE_AD_CLIENT_SECRET;

  const demoEnabled = process.env.DEMO_E2E === "1";
  
  console.log("Provider config:", { aadEnabled, demoEnabled });

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
  secret: process.env.NEXTAUTH_SECRET || process.env.AUTH_SECRET,
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
    },
    async signIn({ user, account, profile, email, credentials }) {
      console.log('NextAuth signIn callback:', { user: user?.email, account: account?.provider });
      return true;
    },
    async redirect({ url, baseUrl }) {
      console.log('NextAuth redirect callback:', { url, baseUrl });
      // Ensure we redirect to the correct base URL
      if (url.startsWith("/")) return `${baseUrl}${url}`;
      if (new URL(url).origin === baseUrl) return url;
      return baseUrl;
    }
  },
  pages: {
    signIn: "/signin",
    signOut: "/signout",
    error: "/signin?error=true",
  },
  debug: process.env.NODE_ENV === "development",
  logger: {
    error(code, metadata) {
      console.error('NextAuth error:', code, metadata);
    },
    warn(code) {
      console.warn('NextAuth warning:', code);
    },
    debug(code, metadata) {
      console.log('NextAuth debug:', code, metadata);
    }
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