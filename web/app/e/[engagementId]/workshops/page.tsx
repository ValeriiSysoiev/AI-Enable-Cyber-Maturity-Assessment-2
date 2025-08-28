"use client";
import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { listWorkshops, getConsentStatus, hasAllConsent } from "../../../../lib/workshops";
import type { Workshop } from "../../../../types/workshops";

interface NewWorkshopModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  engagementId: string;
}

function NewWorkshopModal({ isOpen, onClose, onSuccess, engagementId }: NewWorkshopModalProps) {
  const [formData, setFormData] = useState({
    title: "",
    attendees: [{ user_id: "", email: "", role: "Member" }]
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError("");

    try {
      const { createWorkshop } = await import("../../../../lib/workshops");
      await createWorkshop(engagementId, formData);
      onSuccess();
      onClose();
      // Reset form
      setFormData({
        title: "",
        attendees: [{ user_id: "", email: "", role: "Member" }]
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create workshop");
    } finally {
      setIsSubmitting(false);
    }
  };

  const addAttendee = () => {
    setFormData(prev => ({
      ...prev,
      attendees: [...prev.attendees, { user_id: "", email: "", role: "Member" }]
    }));
  };

  const removeAttendee = (index: number) => {
    setFormData(prev => ({
      ...prev,
      attendees: prev.attendees.filter((_, i) => i !== index)
    }));
  };

  const updateAttendee = (index: number, field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      attendees: prev.attendees.map((att, i) => 
        i === index ? { ...att, [field]: value } : att
      )
    }));
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold">New Workshop</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Workshop Title
              </label>
              <input
                type="text"
                value={formData.title}
                onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-3">
                <label className="block text-sm font-medium text-gray-700">
                  Attendees
                </label>
                <button
                  type="button"
                  onClick={addAttendee}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  + Add Attendee
                </button>
              </div>
              
              {formData.attendees.map((attendee, index) => (
                <div key={index} className="grid grid-cols-12 gap-3 mb-3">
                  <div className="col-span-4">
                    <input
                      type="email"
                      placeholder="Email"
                      value={attendee.email}
                      onChange={(e) => updateAttendee(index, "email", e.target.value)}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div className="col-span-3">
                    <input
                      type="text"
                      placeholder="User ID"
                      value={attendee.user_id}
                      onChange={(e) => updateAttendee(index, "user_id", e.target.value)}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div className="col-span-3">
                    <select
                      value={attendee.role}
                      onChange={(e) => updateAttendee(index, "role", e.target.value)}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="Member">Member</option>
                      <option value="Lead">Lead</option>
                      <option value="Observer">Observer</option>
                    </select>
                  </div>
                  <div className="col-span-2">
                    {formData.attendees.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeAttendee(index)}
                        className="w-full h-full text-red-600 hover:text-red-700 flex items-center justify-center"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <div className="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {isSubmitting ? "Creating..." : "Create Workshop"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

function WorkshopCard({ workshop }: { workshop: Workshop }) {
  const consentStatus = getConsentStatus(workshop);
  const allConsented = hasAllConsent(workshop);

  return (
    <div className="bg-white shadow rounded-lg p-6 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <Link href={`/e/${workshop.engagement_id}/workshops/${workshop.id}`} className="block group">
            <h3 className="text-lg font-medium text-gray-900 group-hover:text-indigo-600">
              {workshop.title}
            </h3>
          </Link>
          
          <div className="mt-2 flex items-center space-x-4 text-sm text-gray-500">
            <div className="flex items-center">
              <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
              {workshop.attendees.length} attendees
            </div>
            <div className="flex items-center">
              <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {consentStatus.consented}/{consentStatus.total} consented ({consentStatus.percentage}%)
            </div>
            <div className="flex items-center">
              <svg className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Created {new Date(workshop.created_at).toLocaleDateString()}
            </div>
          </div>
        </div>
        
        <div className="ml-4 flex flex-col items-end space-y-2">
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
            workshop.started 
              ? 'bg-green-100 text-green-800'
              : allConsented
              ? 'bg-blue-100 text-blue-800' 
              : 'bg-yellow-100 text-yellow-800'
          }`}>
            {workshop.started ? 'Started' : allConsented ? 'Ready' : 'Pending Consent'}
          </span>
        </div>
      </div>
      
      <div className="mt-4 flex justify-between items-center">
        <Link 
          href={`/e/${workshop.engagement_id}/workshops/${workshop.id}`}
          className="text-sm font-medium text-indigo-600 hover:text-indigo-500"
        >
          View Details →
        </Link>
        <button
          className={`px-3 py-1 text-sm font-medium rounded-md ${
            allConsented && !workshop.started
              ? 'text-white bg-green-600 hover:bg-green-700'
              : 'text-gray-500 bg-gray-100 cursor-not-allowed'
          }`}
          disabled={!allConsented || workshop.started}
        >
          {workshop.started ? 'Started' : 'Start Workshop'}
        </button>
      </div>
    </div>
  );
}

export default function WorkshopsPage() {
  const params = useParams();
  const engagementId = params.engagementId as string;
  
  const [workshops, setWorkshops] = useState<Workshop[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showNewModal, setShowNewModal] = useState(false);

  const loadWorkshops = async () => {
    try {
      setLoading(true);
      const response = await listWorkshops(engagementId);
      setWorkshops(response.workshops);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workshops");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (engagementId) {
      loadWorkshops();
    }
  }, [engagementId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-64 mb-6"></div>
            <div className="space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="bg-white shadow rounded-lg p-6">
                  <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/2"></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white shadow-sm rounded-lg px-6 py-4 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Workshops</h1>
              <p className="mt-1 text-sm text-gray-500">
                Manage workshop consent and participation
              </p>
            </div>
            <button
              onClick={() => setShowNewModal(true)}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
            >
              New Workshop
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {workshops.length === 0 ? (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-gray-900">No workshops</h3>
            <p className="mt-1 text-sm text-gray-500">Get started by creating a new workshop.</p>
            <div className="mt-6">
              <button
                onClick={() => setShowNewModal(true)}
                className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                New Workshop
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {workshops.map(workshop => (
              <WorkshopCard key={workshop.id} workshop={workshop} />
            ))}
          </div>
        )}

        <NewWorkshopModal
          isOpen={showNewModal}
          onClose={() => setShowNewModal(false)}
          onSuccess={() => {
            loadWorkshops();
            setShowNewModal(false);
          }}
          engagementId={engagementId}
        />
      </div>
    </div>
  );
}