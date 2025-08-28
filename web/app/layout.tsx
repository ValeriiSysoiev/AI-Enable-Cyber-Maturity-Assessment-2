import "./globals.css";
import type { Metadata } from "next";
import TopNav from "../components/TopNav";
import { Providers } from "../components/Providers";
import ErrorBoundary from "../components/ErrorBoundary";

export const metadata: Metadata = { 
  title: "AI Maturity Tool", 
  description: "Assess and plan AI security maturity",
  keywords: ["AI", "cybersecurity", "maturity", "assessment", "NIST"],
  robots: "index, follow"
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
};

// Enable static optimization for layout
export const runtime = 'nodejs';
export const preferredRegion = 'auto';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900">
        <ErrorBoundary>
          <Providers>
            <TopNav />
            {children}
          </Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}
