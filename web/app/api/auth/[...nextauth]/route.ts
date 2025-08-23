import NextAuth from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

const demoEnabled = process.env.DEMO_E2E === "1";

const handler = NextAuth({
  providers: demoEnabled ? [
    CredentialsProvider({
      name: "Demo",
      credentials: { 
        email: { label: "Email", type: "text" } 
      },
      async authorize(credentials) {
        if (!demoEnabled) return null;
        const email = credentials?.email || "demo@example.com";
        return { 
          id: "demo-user", 
          email, 
          name: "Demo User", 
          role: "admin", 
          groups: ["admin"] 
        };
      }
    })
  ] : [],
  session: { 
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.role = user.role;
        token.groups = user.groups;
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.role = token.role;
        session.user.groups = token.groups;
      }
      return session;
    }
  },
  pages: {
    signIn: '/signin',
  }
});

export { handler as GET, handler as POST };
