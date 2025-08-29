"use client";

import { signOut } from "next-auth/react";
import { useEffect, useState } from "react";

export default function SignOut() {
  const [status, setStatus] = useState("Signing out...");

  useEffect(() => {
    const performSignOut = async () => {
      try {
        // First, try to sign out with NextAuth
        setStatus("Clearing session...");
        await signOut({ 
          redirect: false // Don't redirect yet
        });
        
        // Then force clear all cookies via our API route
        setStatus("Finalizing sign out...");
        window.location.href = '/api/force-signout';
      } catch (error) {
        console.error('Sign out error:', error);
        // If anything fails, still force redirect to clear cookies
        window.location.href = '/api/force-signout';
      }
    };
    
    performSignOut();
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="text-center">
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">{status}</h2>
        <p className="text-gray-600">You will be redirected shortly.</p>
      </div>
    </div>
  );
}