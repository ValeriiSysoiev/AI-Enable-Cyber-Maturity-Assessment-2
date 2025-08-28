"use client";
import { useState, useEffect } from "react";
import { 
  requestDataPurge, 
  getPurgeStatus, 
  generateConfirmationToken,
  validateConfirmationText,
  getJobStatusColor,
  GDPRJobPoller 
} from "../../lib/gdpr";
import type { 
  GDPRDialogProps, 
  GDPRPurgeFormData, 
  GDPRDataPurgeResponse,
  GDPRError 
} from "../../types/gdpr";

interface DataPurgeDialogProps extends GDPRDialogProps {
  onPurgeComplete?: (response: GDPRDataPurgeResponse) => void;
}

export default function DataPurgeDialog({ 
  engagementId, 
  isOpen, 
  onClose, 
  onSuccess,
  onPurgeComplete,
  className = "" 
}: DataPurgeDialogProps) {
  const [currentStep, setCurrentStep] = useState<'select' | 'confirm' | 'status'>('select');
  const [formData, setFormData] = useState<GDPRPurgeFormData>({
    purgeAssessments: false,
    purgeDocuments: false,
    purgeFindings: false,
    purgeRecommendations: false,
    purgeRunlogs: false,
    purgeAuditLogs: false,
    confirmationText: '',
  });
  
  const [confirmationToken] = useState(() => generateConfirmationToken());
  const [purgeStatus, setPurgeStatus] = useState<GDPRDataPurgeResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>("");
  const [poller, setPoller] = useState<GDPRJobPoller | null>(null);

  useEffect(() => {
    // Cleanup poller on unmount
    return () => {
      poller?.stop();
    };
  }, [poller]);

  useEffect(() => {
    // Reset state when dialog opens/closes
    if (!isOpen) {
      setCurrentStep('select');
      setFormData({
        purgeAssessments: false,
        purgeDocuments: false,
        purgeFindings: false,
        purgeRecommendations: false,
        purgeRunlogs: false,
        purgeAuditLogs: false,
        confirmationText: '',
      });
      setPurgeStatus(null);
      setError("");
      poller?.stop();
      setPoller(null);
    }
  }, [isOpen, poller]);

  const handleInputChange = (field: keyof GDPRPurgeFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const getSelectedDataTypes = () => {
    const types = [];
    if (formData.purgeAssessments) types.push('Assessments');
    if (formData.purgeDocuments) types.push('Documents');
    if (formData.purgeFindings) types.push('Findings');
    if (formData.purgeRecommendations) types.push('Recommendations');
    if (formData.purgeRunlogs) types.push('Run Logs');
    if (formData.purgeAuditLogs) types.push('Audit Logs');
    return types;
  };

  const hasSelectedData = () => {
    return getSelectedDataTypes().length > 0;
  };

  const isConfirmationValid = () => {
    return validateConfirmationText(formData.confirmationText, confirmationToken);
  };

  const handleNext = () => {
    if (currentStep === 'select' && hasSelectedData()) {
      setCurrentStep('confirm');
    }
  };

  const handleBack = () => {
    if (currentStep === 'confirm') {
      setCurrentStep('select');
    }
  };

  const handleSubmit = async () => {
    if (!isConfirmationValid()) {
      setError('Confirmation text does not match. Please type the exact confirmation code.');
      return;
    }

    setIsSubmitting(true);
    setError("");

    try {
      const request = {
        engagement_id: engagementId,
        purge_assessments: formData.purgeAssessments,
        purge_documents: formData.purgeDocuments,
        purge_findings: formData.purgeFindings,
        purge_recommendations: formData.purgeRecommendations,
        purge_runlogs: formData.purgeRunlogs,
        purge_audit_logs: formData.purgeAuditLogs,
        confirmation_token: confirmationToken,
      };

      const response = await requestDataPurge(request);
      setPurgeStatus(response);
      setCurrentStep('status');

      // Start polling for status updates
      const jobPoller = new GDPRJobPoller(response.request_id, {
        onUpdate: (status) => {
          if (status.result) {
            setPurgeStatus(status.result as GDPRDataPurgeResponse);
          }
        },
        onComplete: (status) => {
          if (status.result) {
            setPurgeStatus(status.result as GDPRDataPurgeResponse);
            onPurgeComplete?.(status.result as GDPRDataPurgeResponse);
          }
          onSuccess?.();
        },
        onError: (error) => {
          setError(error.message);
          setPoller(null);
        }
      });

      jobPoller.start();
      setPoller(jobPoller);
    } catch (err) {
      const gdprError = err as GDPRError;
      setError(gdprError.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className={`bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto ${className}`}>
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-red-600">Purge GDPR Data</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Warning Banner */}
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start space-x-3">
              <svg className="w-6 h-6 text-red-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 13.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <div>
                <h3 className="text-sm font-medium text-red-800">Warning: Irreversible Action</h3>
                <p className="text-sm text-red-700 mt-1">
                  Data purging permanently deletes selected data and cannot be undone. 
                  Please ensure you have exported any data you need before proceeding.
                </p>
              </div>
            </div>
          </div>

          {/* Step Indicator */}
          <div className="mb-6">
            <div className="flex items-center space-x-4">
              {['Select Data', 'Confirm Purge', 'Purge Status'].map((step, index) => (
                <div key={step} className="flex items-center">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                    index < (currentStep === 'select' ? 1 : currentStep === 'confirm' ? 2 : 3)
                      ? 'bg-red-600 text-white'
                      : index === (currentStep === 'select' ? 0 : currentStep === 'confirm' ? 1 : 2)
                      ? 'bg-red-100 text-red-600 border-2 border-red-600'
                      : 'bg-gray-100 text-gray-400'
                  }`}>
                    {index + 1}
                  </div>
                  <span className={`ml-2 text-sm ${
                    index <= (currentStep === 'select' ? 0 : currentStep === 'confirm' ? 1 : 2)
                      ? 'text-gray-900'
                      : 'text-gray-400'
                  }`}>
                    {step}
                  </span>
                  {index < 2 && (
                    <div className={`ml-4 w-8 h-px ${
                      index < (currentStep === 'select' ? 0 : currentStep === 'confirm' ? 1 : 2)
                        ? 'bg-red-600'
                        : 'bg-gray-200'
                    }`} />
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Step 1: Select Data */}
          {currentStep === 'select' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Select Data Types to Purge
                </label>
                <div className="space-y-3">
                  {[
                    { key: 'purgeAssessments', label: 'Assessment Data', description: 'Assessment responses and scores', risk: 'high' },
                    { key: 'purgeDocuments', label: 'Documents', description: 'Uploaded files and attachments', risk: 'high' },
                    { key: 'purgeFindings', label: 'Findings', description: 'Security findings and analysis', risk: 'medium' },
                    { key: 'purgeRecommendations', label: 'Recommendations', description: 'Generated recommendations', risk: 'medium' },
                    { key: 'purgeRunlogs', label: 'Run Logs', description: 'System execution logs', risk: 'low' },
                    { key: 'purgeAuditLogs', label: 'Audit Logs', description: 'User activity and access logs', risk: 'low' },
                  ].map((item) => (
                    <label key={item.key} className="flex items-start space-x-3 cursor-pointer p-3 border rounded-lg hover:bg-gray-50">
                      <input
                        type="checkbox"
                        checked={formData[item.key as keyof GDPRPurgeFormData] as boolean}
                        onChange={(e) => handleInputChange(item.key as keyof GDPRPurgeFormData, e.target.checked)}
                        className="mt-1 h-4 w-4 text-red-600 focus:ring-red-500 border-gray-300 rounded"
                      />
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-medium text-gray-900">{item.label}</span>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            item.risk === 'high' 
                              ? 'bg-red-100 text-red-800' 
                              : item.risk === 'medium'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-green-100 text-green-800'
                          }`}>
                            {item.risk} risk
                          </span>
                        </div>
                        <div className="text-sm text-gray-500">{item.description}</div>
                      </div>
                    </label>
                  ))}
                </div>
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
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Cancel
                </button>
                <button
                  onClick={handleNext}
                  disabled={!hasSelectedData()}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Continue to Confirmation
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Confirmation */}
          {currentStep === 'confirm' && (
            <div className="space-y-6">
              <div className="border rounded-lg p-4 bg-red-50">
                <h3 className="text-lg font-medium text-red-800 mb-3">Confirm Data Purge</h3>
                <p className="text-sm text-red-700 mb-4">
                  You are about to permanently delete the following data types:
                </p>
                <ul className="list-disc list-inside space-y-1">
                  {getSelectedDataTypes().map((type) => (
                    <li key={type} className="text-sm text-red-700">{type}</li>
                  ))}
                </ul>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Type the following confirmation code to proceed:
                </label>
                <div className="mb-3 p-3 bg-gray-100 border rounded-md">
                  <code className="text-sm font-mono">{confirmationToken}</code>
                </div>
                <input
                  type="text"
                  value={formData.confirmationText}
                  onChange={(e) => handleInputChange('confirmationText', e.target.value)}
                  placeholder="Enter confirmation code"
                  className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500"
                />
                {formData.confirmationText && !isConfirmationValid() && (
                  <p className="text-sm text-red-600 mt-1">Confirmation code does not match</p>
                )}
              </div>

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  onClick={handleBack}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Back
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={!isConfirmationValid() || isSubmitting}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? 'Purging Data...' : 'Purge Data'}
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Status */}
          {currentStep === 'status' && purgeStatus && (
            <div className="space-y-6">
              <div className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-lg font-medium">Purge Status</h3>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getJobStatusColor(purgeStatus.status)}`}>
                    {purgeStatus.status.charAt(0).toUpperCase() + purgeStatus.status.slice(1)}
                  </span>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Request ID:</span>
                    <div className="font-mono text-xs break-all">{purgeStatus.request_id}</div>
                  </div>
                  <div>
                    <span className="text-gray-500">Started:</span>
                    <div>{new Date(purgeStatus.created_at).toLocaleString()}</div>
                  </div>
                  {purgeStatus.completed_at && (
                    <div>
                      <span className="text-gray-500">Completed:</span>
                      <div>{new Date(purgeStatus.completed_at).toLocaleString()}</div>
                    </div>
                  )}
                </div>

                {purgeStatus.error_message && (
                  <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded">
                    <p className="text-sm text-red-600">{purgeStatus.error_message}</p>
                  </div>
                )}
              </div>

              {/* Completion Status */}
              {purgeStatus.status === 'completed' && purgeStatus.items_purged && (
                <div className="border rounded-lg p-4 bg-green-50">
                  <div className="flex items-center space-x-2 mb-3">
                    <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <h3 className="text-lg font-medium text-green-800">Purge Completed</h3>
                  </div>
                  <p className="text-sm text-green-700 mb-4">
                    The following data has been permanently deleted:
                  </p>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    {Object.entries(purgeStatus.items_purged).map(([key, count]) => (
                      count > 0 && (
                        <div key={key}>
                          <span className="text-gray-600 capitalize">{key.replace('_', ' ')}:</span>
                          <span className="ml-2 font-medium">{count} items</span>
                        </div>
                      )
                    ))}
                  </div>
                </div>
              )}

              {/* Processing Status */}
              {(purgeStatus.status === 'pending' || purgeStatus.status === 'processing') && (
                <div className="border rounded-lg p-4 bg-blue-50">
                  <div className="flex items-center space-x-2 mb-3">
                    <svg className="w-5 h-5 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <h3 className="text-lg font-medium text-blue-800">
                      {purgeStatus.status === 'pending' ? 'Purge Queued' : 'Purging Data'}
                    </h3>
                  </div>
                  <p className="text-sm text-blue-700">
                    {purgeStatus.status === 'pending' 
                      ? 'Your purge request is queued and will begin processing shortly.'
                      : 'Data is being permanently deleted. This process cannot be stopped once started.'
                    }
                  </p>
                </div>
              )}

              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              <div className="flex justify-end space-x-3 pt-4">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}