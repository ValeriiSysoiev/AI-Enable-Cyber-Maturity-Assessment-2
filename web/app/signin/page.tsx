"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { signIn, useSession } from "next-auth/react";

// Force dynamic rendering to prevent static generation issues with API calls
export const dynamic = 'force-dynamic';

export default function SignIn() {
  const [email, setEmail] = useState("");
  const [isAAD, setIsAAD] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const { data: session, status } = useSession();

  // Redirect if already authenticated
  useEffect(() => {
    if (status === "authenticated" && session?.user) {
      router.push("/engagements");
    }
  }, [status, session, router]);

  useEffect(() => {
    // Only fetch auth mode in browser environment to prevent SSG build errors
    if (typeof window !== 'undefined') {
      // Check auth mode endpoint to determine if AAD is properly configured
      fetch('/api/auth/mode')
        .then(res => res.json())
        .then(data => {
          setIsAAD(data.mode === 'aad' && data.enabled && data.aadEnabled);
          setIsLoading(false);
        })
        .catch(() => {
          setIsAAD(false);
          setIsLoading(false);
        });
    } else {
      // During build/SSG, default to demo mode to prevent errors
      setIsAAD(false);
      setIsLoading(false);
    }
  }, []);

  const handleDemoSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (email.trim()) {
      try {
        // Call demo API route to set authentication cookie
        const response = await fetch('/api/demo/signin', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email: email.trim() }),
        });
        
        if (response.ok) {
          // Also set localStorage for client-side state
          localStorage.setItem('email', email.trim());
          router.push("/engagements");
        } else {
          console.error('Failed to sign in');
        }
      } catch (error) {
        console.error('Sign in error:', error);
      }
    }
  };

  const handleAADSignIn = async () => {
    try {
      // Use NextAuth signIn function for proper CSRF handling
      await signIn('azure-ad', { 
        callbackUrl: '/engagements',
        redirect: true 
      });
    } catch (error) {
      console.error('AAD sign in error:', error);
      // Fallback to direct redirect if NextAuth signIn fails
      if (typeof window !== 'undefined') {
        window.location.href = '/api/auth/signin/azure-ad?callbackUrl=' + encodeURIComponent('/engagements');
      }
    }
  };

  // Show loading while checking session or auth mode
  if (status === "loading" || isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div>Loading...</div>
      </div>
    );
  }

  if (isAAD) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="w-full max-w-md space-y-8">
          <div>
            <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
              Sign in to AI Maturity Assessment
            </h2>
            <p className="mt-2 text-center text-sm text-gray-600">
              Use your organizational account to continue
            </p>
          </div>
          <div className="mt-8">
            <button
              onClick={handleAADSignIn}
              className="group relative flex w-full justify-center rounded-md border border-transparent bg-indigo-600 py-2 px-4 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              Sign in with Azure Active Directory
            </button>
          </div>
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
            Enter your email to continue (demo)
          </p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleDemoSubmit}>
          <div className="-space-y-px rounded-md shadow-sm">
            <div>
              <label htmlFor="email" className="sr-only">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                className="relative block w-full appearance-none rounded-md border border-gray-300 px-3 py-2 text-gray-900 placeholder-gray-500 focus:z-10 focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              className="group relative flex w-full justify-center rounded-md border border-transparent bg-indigo-600 py-2 px-4 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
            >
              Sign in
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}