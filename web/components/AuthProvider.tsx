"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import type { AuthContext, AADUser, AuthMode } from "../types/evidence";

const AuthContext = createContext<AuthContext | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<AADUser | null>(null);
  const [mode, setMode] = useState<AuthMode>({ mode: 'demo', enabled: true });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();
  const router = useRouter();

  useEffect(() => {
    initializeAuth();
  }, []);

  async function initializeAuth() {
    try {
      setIsLoading(true);
      setError(undefined);

      // Optimize: Use Promise.all for parallel API calls and add timeouts
      const authModePromise = fetch('/api/auth/mode', { 
        signal: AbortSignal.timeout(5000) // 5 second timeout
      });
      
      const authModeResponse = await authModePromise;
      if (authModeResponse.ok) {
        const authModeData = await authModeResponse.json();
        setMode(authModeData);

        if (authModeData.mode === 'aad' && authModeData.enabled) {
          // Try to get current AAD session with timeout
          const sessionResponse = await fetch('/api/auth/session', { 
            signal: AbortSignal.timeout(5000) // 5 second timeout
          });
          if (sessionResponse.ok) {
            const sessionData = await sessionResponse.json();
            if (sessionData.user) {
              setUser({
                id: sessionData.user.id,
                email: sessionData.user.email,
                name: sessionData.user.name,
                roles: sessionData.user.roles,
                tenant_id: sessionData.user.tenant_id,
              });
            }
          }
        } else {
          // Demo mode - check localStorage (non-blocking)
          const email = localStorage.getItem('email');
          if (email) {
            setUser({
              id: email,
              email: email,
              name: email.split('@')[0],
            });
          }
        }
      } else {
        // Fast fallback if auth mode API fails
        const email = localStorage.getItem('email');
        if (email) {
          setMode({ mode: 'demo', enabled: true });
          setUser({
            id: email,
            email: email,
            name: email.split('@')[0],
          });
        }
      }
    } catch (err) {
      console.warn('Auth initialization timed out, falling back to demo mode:', err);
      
      // Fast fallback to demo mode - don't let auth issues block the page
      setMode({ mode: 'demo', enabled: true });
      const email = localStorage.getItem('email');
      if (email) {
        setUser({
          id: email,
          email: email,
          name: email.split('@')[0],
        });
      }
    } finally {
      setIsLoading(false);
    }
  }

  async function signIn() {
    if (mode.mode === 'aad') {
      // Redirect to AAD sign-in
      window.location.href = '/api/auth/signin';
    } else {
      // Redirect to demo sign-in page
      router.push('/signin');
    }
  }

  async function signOut() {
    try {
      if (mode.mode === 'aad') {
        // Use NextAuth signOut function for proper AAD logout
        const { signOut: nextAuthSignOut } = await import('next-auth/react');
        await nextAuthSignOut({ callbackUrl: '/signin' });
        setUser(null);
      } else {
        // Demo mode sign out
        localStorage.removeItem('email');
        localStorage.removeItem('engagementId');
        setUser(null);
        router.push('/signin');
      }
    } catch (err) {
      console.error('Sign out failed:', err);
      setError(err instanceof Error ? err.message : 'Sign out failed');
    }
  }

  const isAuthenticated = !!user;

  const contextValue: AuthContext = {
    user,
    mode,
    isAuthenticated,
    isLoading,
    error,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Auth utilities
export function useRequireAuth() {
  const auth = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!auth.isLoading && !auth.isAuthenticated) {
      if (auth.mode.mode === 'aad') {
        window.location.href = '/api/auth/signin';
      } else {
        router.push('/signin');
      }
    }
  }, [auth.isLoading, auth.isAuthenticated, auth.mode.mode, router]);

  return auth;
}

export function getAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  
  const headers: Record<string, string> = {};
  
  // Always try to get email from localStorage first (works for both modes)
  const email = localStorage.getItem('email');
  if (email) {
    headers['X-User-Email'] = email;
  }
  
  const engagementId = localStorage.getItem('engagementId');
  if (engagementId) {
    headers['X-Engagement-ID'] = engagementId;
  }
  
  return headers;
}