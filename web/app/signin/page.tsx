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
  const [authError, setAuthError] = useState<string | null>(null);
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
        .then(res => {
          if (!res.ok && res.status === 500) {
            // Handle production AAD configuration error
            return res.json().then(data => {
              throw new Error(data.error || 'Authentication configuration error');
            });
          }
          return res.json();
        })
        .then(data => {
          // In production, only AAD is allowed
          if (data.mode === 'aad') {
            setIsAAD(true);
          } else if (data.mode === 'error') {
            setAuthError(data.error || 'Authentication not properly configured');
            setIsAAD(true); // Show AAD UI even if misconfigured
          } else {
            // Demo mode - only in non-production
            setIsAAD(false);
          }
          setIsLoading(false);
        })
        .catch((error) => {
          console.error('Auth mode check failed:', error);
          setAuthError(error.message || 'Failed to determine authentication mode');
          // Default to AAD in case of error (safer for production)
          setIsAAD(true);
          setIsLoading(false);
        });
    } else {
      // During build/SSG, default to AAD mode for production safety
      setIsAAD(true);
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
          const errorData = await response.json().catch(() => ({}));
          const errorMessage = errorData.error || `Sign in failed (${response.status})`;
          console.error('Failed to sign in:', errorMessage);
          
          // Show user-friendly error message
          if (response.status === 403) {
            alert('Demo sign-in is not available in production. Please use Azure Active Directory.');
          } else {
            alert(`Sign in failed: ${errorMessage}`);
          }
        }
      } catch (error) {
        console.error('Sign in error:', error);
        alert('An error occurred during sign in. Please try again.');
      }
    }
  };

  const handleAADSignIn = async () => {
    try {
      // Force a fresh authentication by adding prompt=login
      // This ensures Azure AD doesn't use cached credentials
      await signIn('azure-ad', { 
        callbackUrl: '/engagements',
        redirect: true,
        prompt: 'login' // Force re-authentication
      });
    } catch (error) {
      console.error('AAD sign in error:', error);
      // Fallback to direct redirect if NextAuth signIn fails
      if (typeof window !== 'undefined') {
        window.location.href = '/api/auth/signin/azure-ad?callbackUrl=' + encodeURIComponent('/engagements') + '&prompt=login';
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
          
          {authError && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">
                    Authentication Configuration Error
                  </h3>
                  <div className="mt-2 text-sm text-red-700">
                    <p>{authError}</p>
                    <p className="mt-1">Please contact your system administrator.</p>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <div className="mt-8">
            <button
              onClick={handleAADSignIn}
              disabled={!!authError}
              className={`group relative flex w-full justify-center rounded-md border border-transparent py-2 px-4 text-sm font-medium text-white focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                authError 
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : 'bg-indigo-600 hover:bg-indigo-700 focus:ring-indigo-500'
              }`}
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