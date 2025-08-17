import "./globals.css";
import type { Metadata } from "next";
import TopNav from "@/components/TopNav";
import { AuthProvider } from "@/components/AuthProvider";

export const metadata: Metadata = { title: "AI Maturity Tool", description: "Assess and plan AI security maturity" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900">
        <AuthProvider>
          <TopNav />
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}
