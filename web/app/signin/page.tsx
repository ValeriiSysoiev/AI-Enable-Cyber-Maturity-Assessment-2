"use client";

import { useEffect, useState } from "react";
import { signIn, getProviders } from "next-auth/react";

export default function SignIn() {
  const [providers, setProviders] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadProviders = async () => {
      const res = await getProviders();
      setProviders(res);
      setLoading(false);
    };
    loadProviders();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600">Loading authentication...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            Sign in to AI Maturity Assessment
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Sign in with your organizational account
          </p>
        </div>
        
        <div className="mt-8 space-y-4">
          {providers && Object.values(providers).map((provider: any) => (
            <div key={provider.name}>
              <button
                onClick={() => signIn(provider.id, { callbackUrl: "/engagements" })}
                className="group relative flex w-full justify-center rounded-md border border-transparent bg-indigo-600 py-3 px-4 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              >
                Sign in with {provider.name}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
