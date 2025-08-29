"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useSession, signOut } from "next-auth/react";
import { 
  getSessionConfig, 
  getRemainingSessionTime, 
  shouldShowExpiryWarning,
  isUserIdle,
  formatDuration 
} from "../lib/session-config";

interface SessionMonitorProps {
  onIdleLogout?: () => void;
  onSessionExpiring?: (remainingSeconds: number) => void;
  showWarnings?: boolean;
}

/**
 * Session Monitor Component
 * 
 * Monitors user session for:
 * - Idle timeout
 * - Session expiry
 * - Shows warnings before logout
 */
export default function SessionMonitor({ 
  onIdleLogout,
  onSessionExpiring,
  showWarnings = true 
}: SessionMonitorProps) {
  const { data: session, status } = useSession();
  const [showWarning, setShowWarning] = useState(false);
  const [remainingTime, setRemainingTime] = useState<number | null>(null);
  const lastActivityRef = useRef<Date>(new Date());
  const warningShownRef = useRef(false);
  const config = getSessionConfig();

  // Update last activity on user interaction
  const updateActivity = useCallback(() => {
    lastActivityRef.current = new Date();
    
    // Hide warning if user becomes active again
    if (showWarning) {
      setShowWarning(false);
      warningShownRef.current = false;
    }
  }, [showWarning]);

  // Handle session expiry
  const handleSessionExpiry = useCallback(async () => {
    console.log("Session expired - logging out");
    await signOut({ redirect: true, callbackUrl: "/signin?reason=expired" });
  }, []);

  // Handle idle timeout
  const handleIdleTimeout = useCallback(async () => {
    console.log("User idle timeout - logging out");
    if (onIdleLogout) {
      onIdleLogout();
    }
    await signOut({ redirect: true, callbackUrl: "/signin?reason=idle" });
  }, [onIdleLogout]);

  // Check session and idle status
  useEffect(() => {
    if (status !== "authenticated" || !session) {
      return;
    }

    const checkInterval = setInterval(() => {
      // Get session start time (from JWT iat claim if available)
      const sessionStart = session.expires ? 
        new Date(new Date(session.expires).getTime() - config.maxAge * 1000) : 
        new Date();

      // Check remaining session time
      const remaining = getRemainingSessionTime(sessionStart, config.maxAge);
      setRemainingTime(remaining);

      // Check if session expired
      if (remaining <= 0) {
        handleSessionExpiry();
        return;
      }

      // Check if should show expiry warning
      if (shouldShowExpiryWarning(sessionStart, config.maxAge) && !warningShownRef.current) {
        setShowWarning(true);
        warningShownRef.current = true;
        if (onSessionExpiring) {
          onSessionExpiring(remaining);
        }
      }

      // Check idle timeout
      if (isUserIdle(lastActivityRef.current, config.idleTimeout)) {
        handleIdleTimeout();
        return;
      }
    }, 10000); // Check every 10 seconds

    return () => clearInterval(checkInterval);
  }, [session, status, config, handleSessionExpiry, handleIdleTimeout, onSessionExpiring]);

  // Add activity listeners
  useEffect(() => {
    const events = ["mousedown", "keydown", "scroll", "touchstart", "click"];
    
    events.forEach(event => {
      document.addEventListener(event, updateActivity);
    });

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, updateActivity);
      });
    };
  }, [updateActivity]);

  // Extend session when warning is shown and user is active
  const extendSession = useCallback(async () => {
    try {
      // Trigger session update by calling an API endpoint
      const response = await fetch("/api/auth/session", {
        method: "GET",
      });
      
      if (response.ok) {
        setShowWarning(false);
        warningShownRef.current = false;
        console.log("Session extended");
      }
    } catch (error) {
      console.error("Failed to extend session:", error);
    }
  }, []);

  if (!showWarnings || !showWarning || status !== "authenticated") {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 max-w-sm bg-yellow-50 border border-yellow-200 rounded-lg shadow-lg p-4 z-50">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg className="h-6 w-6 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" 
            />
          </svg>
        </div>
        <div className="ml-3">
          <h3 className="text-sm font-medium text-yellow-800">
            Session Expiring Soon
          </h3>
          <div className="mt-2 text-sm text-yellow-700">
            <p>
              Your session will expire in {remainingTime ? formatDuration(remainingTime) : "a few moments"}.
            </p>
          </div>
          <div className="mt-4 flex space-x-3">
            <button
              onClick={extendSession}
              className="text-sm bg-yellow-100 hover:bg-yellow-200 text-yellow-800 font-medium py-1 px-3 rounded"
            >
              Stay Signed In
            </button>
            <button
              onClick={() => signOut({ callbackUrl: "/signin" })}
              className="text-sm text-yellow-600 hover:text-yellow-800 font-medium"
            >
              Sign Out
            </button>
          </div>
        </div>
        <button
          onClick={() => setShowWarning(false)}
          className="ml-auto flex-shrink-0 text-yellow-400 hover:text-yellow-500"
        >
          <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" 
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" 
              clipRule="evenodd" 
            />
          </svg>
        </button>
      </div>
    </div>
  );
}