/**
 * 403 Forbidden Page
 * Displayed when users don't have sufficient permissions to access a resource
 */
"use client";

import { useRouter } from "next/navigation";

export default function ForbiddenPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="text-center">
          <svg
            className="mx-auto h-16 w-16 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">
            403 - Access Forbidden
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            You don't have permission to access this resource.
          </p>
          <p className="mt-1 text-sm text-gray-600">
            Contact your administrator to request access.
          </p>
        </div>

        <div className="mt-8 bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <div className="space-y-4">
            <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg
                    className="h-5 w-5 text-yellow-400"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-yellow-800">
                    Insufficient Permissions
                  </h3>
                  <div className="mt-2 text-sm text-yellow-700">
                    <p>You need one of the following roles to access this page:</p>
                    <ul className="list-disc list-inside mt-1">
                      <li>Member</li>
                      <li>LEM (Lead Engagement Manager)</li>
                      <li>Admin</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex space-x-4">
              <button
                onClick={() => router.back()}
                className="flex-1 bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
              >
                Go Back
              </button>
              <button
                onClick={() => router.push('/signin')}
                className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 px-4 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              >
                Sign In
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}