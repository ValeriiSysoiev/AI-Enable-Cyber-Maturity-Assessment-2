import NextAuth from "next-auth";
import AzureADProvider from "next-auth/providers/azure-ad";
import CredentialsProvider from "next-auth/providers/credentials";

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
if (demoEnabled) {
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

const handler = NextAuth({
  providers,
  session: { strategy: "jwt", maxAge: 30 * 24 * 60 * 60 },
  callbacks: {
    async jwt({ token, account, profile }) {
      // Surface AAD groups/roles when available
      if (account && profile) {
        token.groups = (profile as any).groups || token.groups;
        token.role = (profile as any).role || token.role;
      }
      return token;
    },
    async session({ session, token }) {
      (session as any).groups = (token as any).groups || [];
      (session as any).role = (token as any).role;
      return session;
    }
  },
  pages: {
    signIn: "/signin",
  }
});

export { handler as GET, handler as POST };
