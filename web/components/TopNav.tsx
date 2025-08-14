"use client";
import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";

// Dynamic import to avoid SSR issues with localStorage
const EngagementSwitcher = dynamic(() => import("./EngagementSwitcher"), {
  ssr: false,
});

export default function TopNav() {
  const pathname = usePathname();
  const [engagementId, setEngagementId] = useState<string | null>(null);

  useEffect(() => {
    // Extract engagement ID from pathname if we're in an engagement route
    const match = pathname.match(/^\/e\/([^\/]+)/);
    if (match) {
      setEngagementId(match[1]);
    } else {
      setEngagementId(null);
    }
  }, [pathname]);

  return (
    <nav className="bg-white border-b px-8 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-8">
          <h1 className="text-lg font-semibold">AI Maturity Tool</h1>
          <div className="flex space-x-6">
            <a href="/" className="text-sm hover:text-blue-600">Home</a>
            <a href="/new" className="text-sm hover:text-blue-600">New Assessment</a>
            <a href="/engagements" className="text-sm hover:text-blue-600">Engagements</a>
            {engagementId && (
              <>
                <Link href={`/e/${engagementId}/dashboard`} className="text-sm hover:text-blue-600">Dashboard</Link>
                <Link href={`/e/${engagementId}/demo`} className="text-sm hover:text-blue-600">Demo</Link>
              </>
            )}
          </div>
        </div>
        <EngagementSwitcher />
      </div>
    </nav>
  );
}
