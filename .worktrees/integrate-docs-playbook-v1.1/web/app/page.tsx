"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";

export default function HomePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, mode } = useAuth();

  useEffect(() => {
    if (!isLoading) {
      if (!isAuthenticated) {
        // Not authenticated - redirect to signin
        router.replace("/signin");
      } else {
        // Authenticated - redirect to engagements
        router.replace("/engagements");
      }
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // This should not be visible as we redirect above
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">
          AI-Enabled Cyber Maturity Assessment
        </h1>
        <p className="text-gray-600 mb-8">
          Redirecting...
        </p>
      </div>
    </div>
  );
}