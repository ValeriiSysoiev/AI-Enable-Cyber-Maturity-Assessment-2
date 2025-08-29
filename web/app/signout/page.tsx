"use client";

import { signOut } from "next-auth/react";
import { useEffect } from "react";

export default function SignOut() {
  useEffect(() => {
    // Automatically sign out when this page loads
    signOut({ 
      callbackUrl: '/signin',
      redirect: true 
    });
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="text-center">
        <h2 className="text-2xl font-semibold text-gray-900 mb-2">Signing out...</h2>
        <p className="text-gray-600">You will be redirected shortly.</p>
      </div>
    </div>
  );
}