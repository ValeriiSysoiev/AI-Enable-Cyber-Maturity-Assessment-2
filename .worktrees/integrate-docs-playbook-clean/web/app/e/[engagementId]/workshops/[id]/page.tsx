"use client";
import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { listWorkshops, giveConsent, startWorkshop, hasAllConsent } from "@/lib/workshops";
import type { Workshop, WorkshopAttendee } from "@/types/workshops";

function ConsentStatus({ attendee, currentUserEmail }: { 
  attendee: WorkshopAttendee; 
  currentUserEmail: string;
}) {
  if (attendee.consent) {
    return (
      <div className="flex items-center space-x-2 text-green-600">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span className="text-sm font-medium">Consented</span>
        <span className="text-xs text-gray-500">
          at {new Date(attendee.consent.timestamp).toLocaleString()}
        </span>
      </div>
    );
  }

  if (attendee.email === currentUserEmail) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
        Your consent required
      </span>
    );
  }

  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
      Consent pending
    </span>
  );
}

function AttendeeRow({ 
  attendee, 
  workshopId, 
  engagementId, 
  currentUserEmail, 
  onConsentGiven 
}: {
  attendee: WorkshopAttendee;
  workshopId: string;
  engagementId: string;
  currentUserEmail: string;
  onConsentGiven: () => void;
}) {
  const [isGivingConsent, setIsGivingConsent] = useState(false);
  const [error, setError] = useState("");

  const handleGiveConsent = async () => {
    setIsGivingConsent(true);
    setError("");

    try {
      await giveConsent(engagementId, workshopId, {
        attendee_id: attendee.id,
        consent: true,
      });
      onConsentGiven();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to give consent");
    } finally {
      setIsGivingConsent(false);
    }
  };

  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center space-x-3">
            <div>
              <h4 className="text-sm font-medium text-gray-900">{attendee.email}</h4>
              <p className="text-xs text-gray-500">
                {attendee.role} • ID: {attendee.user_id}
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <ConsentStatus attendee={attendee} currentUserEmail={currentUserEmail} />
          
          {!attendee.consent && attendee.email === currentUserEmail && (
            <div>
              <button
                onClick={handleGiveConsent}
                disabled={isGivingConsent}
                className="px-3 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 disabled:opacity-50"
              >
                {isGivingConsent ? "Giving Consent..." : "I Consent to Participate"}
              </button>
              {error && (
                <p className="mt-1 text-xs text-red-600">{error}</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function WorkshopDetailPage() {
  const params = useParams();
  const router = useRouter();
  const engagementId = params.engagementId as string;
  const workshopId = params.id as string;
  
  const [workshop, setWorkshop] = useState<Workshop | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isStarting, setIsStarting] = useState(false);
  
  // Mock current user - in real app would come from auth context
  const currentUserEmail = typeof window !== 'undefined' ? localStorage.getItem('email') || '' : '';

  const loadWorkshop = async () => {
    try {
      setLoading(true);
      // Get workshop by ID - we'll find it in the list for now
      const response = await listWorkshops(engagementId);
      const foundWorkshop = response.workshops.find(w => w.id === workshopId);
      
      if (!foundWorkshop) {
        setError("Workshop not found");
        return;
      }
      
      setWorkshop(foundWorkshop);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workshop");
    } finally {
      setLoading(false);
    }
  };

  const handleStartWorkshop = async () => {
    if (!workshop) return;
    
    setIsStarting(true);
    try {
      const response = await startWorkshop(engagementId, workshopId);
      setWorkshop(response.workshop);
      // Could show success message here
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start workshop");
    } finally {
      setIsStarting(false);
    }
  };

  useEffect(() => {
    if (engagementId && workshopId) {
      loadWorkshop();
    }
  }, [engagementId, workshopId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-64 mb-6"></div>
            <div className="bg-white shadow rounded-lg p-6">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
              <div className="space-y-3">
                {[1, 2, 3].map(i => (
                  <div key={i} className="h-12 bg-gray-200 rounded"></div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!workshop) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center py-12">
            <h3 className="mt-2 text-lg font-medium text-gray-900">Workshop not found</h3>
            <p className="mt-1 text-sm text-gray-500">{error || "The requested workshop could not be found."}</p>
            <div className="mt-6">
              <Link
                href={`/e/${engagementId}/workshops`}
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                ← Back to Workshops
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const allConsented = hasAllConsent(workshop);
  const consentedCount = workshop.attendees.filter(a => a.consent).length;
  const totalCount = workshop.attendees.length;
  const consentPercentage = Math.round((consentedCount / totalCount) * 100);

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-6">
          <nav className="flex" aria-label="Breadcrumb">
            <ol className="flex items-center space-x-4">
              <li>
                <Link href={`/e/${engagementId}/workshops`} className="text-gray-500 hover:text-gray-700">
                  <span>Workshops</span>
                </Link>
              </li>
              <li>
                <div className="flex items-center">
                  <svg className="flex-shrink-0 h-4 w-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                  </svg>
                  <span className="ml-4 text-sm font-medium text-gray-900">{workshop.title}</span>
                </div>
              </li>
            </ol>
          </nav>
        </div>

        {/* Workshop Info */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{workshop.title}</h1>
              <div className="mt-2 flex items-center space-x-4 text-sm text-gray-500">
                <span>Created by {workshop.created_by}</span>
                <span>•</span>
                <span>{new Date(workshop.created_at).toLocaleString()}</span>
                {workshop.start_ts && (
                  <>
                    <span>•</span>
                    <span>Scheduled for {new Date(workshop.start_ts).toLocaleString()}</span>
                  </>
                )}
              </div>
            </div>
            
            <div className="text-right">
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                workshop.started 
                  ? 'bg-green-100 text-green-800'
                  : allConsented
                  ? 'bg-blue-100 text-blue-800' 
                  : 'bg-yellow-100 text-yellow-800'
              }`}>
                {workshop.started ? 'Started' : allConsented ? 'Ready to Start' : 'Awaiting Consent'}
              </span>
              {workshop.started && workshop.started_at && (
                <div className="mt-1 text-xs text-gray-500">
                  Started at {new Date(workshop.started_at).toLocaleString()}
                </div>
              )}
            </div>
          </div>

          {/* Consent Progress */}
          <div className="mt-6">
            <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
              <span>Consent Progress</span>
              <span>{consentedCount}/{totalCount} ({consentPercentage}%)</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-green-600 h-2 rounded-full transition-all duration-300" 
                style={{ width: `${consentPercentage}%` }}
              />
            </div>
          </div>

          {/* Start Workshop Button */}
          {!workshop.started && (
            <div className="mt-6 flex justify-end">
              <button
                onClick={handleStartWorkshop}
                disabled={!allConsented || isStarting}
                className={`px-4 py-2 text-sm font-medium rounded-md ${
                  allConsented && !isStarting
                    ? 'text-white bg-green-600 hover:bg-green-700'
                    : 'text-gray-500 bg-gray-100 cursor-not-allowed'
                }`}
              >
                {isStarting ? 'Starting Workshop...' : 'Start Workshop'}
              </button>
              {!allConsented && (
                <p className="ml-3 text-xs text-gray-500 self-center">
                  All attendees must consent before workshop can start
                </p>
              )}
            </div>
          )}
        </div>

        {/* Attendees List */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-lg font-medium text-gray-900 mb-4">
            Attendees ({workshop.attendees.length})
          </h2>
          
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <div className="space-y-3">
            {workshop.attendees.map((attendee) => (
              <AttendeeRow
                key={attendee.id}
                attendee={attendee}
                workshopId={workshopId}
                engagementId={engagementId}
                currentUserEmail={currentUserEmail}
                onConsentGiven={loadWorkshop}
              />
            ))}
          </div>
        </div>

        {/* Workshop Started Message */}
        {workshop.started && (
          <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center space-x-2">
              <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h3 className="text-sm font-medium text-green-800">Workshop Started</h3>
            </div>
            <p className="mt-2 text-sm text-green-700">
              This workshop has been started and is now in progress. All attendees have successfully given their consent to participate.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}