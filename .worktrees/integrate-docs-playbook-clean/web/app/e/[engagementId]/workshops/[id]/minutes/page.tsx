'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { 
  getMinutes, 
  updateMinutes, 
  publishMinutes, 
  createNewVersion, 
  MinutesConflictError 
} from '../../../../../../lib/minutes';
import { Minutes, MinutesSection } from '../../../../../../types/minutes';

export default function MinutesEditorPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  
  const workshopId = params.id as string;
  const engagementId = params.engagementId as string;
  const minutesId = searchParams.get('id');

  const [minutes, setMinutes] = useState<Minutes | null>(null);
  const [sections, setSections] = useState<MinutesSection>({
    attendees: [],
    decisions: [],
    actions: [],
    questions: []
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (minutesId) {
      loadMinutes();
    }
  }, [minutesId]);

  const loadMinutes = async () => {
    try {
      setLoading(true);
      const minutesData = await getMinutes(minutesId!);
      setMinutes(minutesData);
      setSections(minutesData.sections);
      setError('');
    } catch (err) {
      console.error('Failed to load minutes:', err);
      setError('Failed to load minutes');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!minutes) return;
    
    try {
      setSaving(true);
      setError('');
      const updated = await updateMinutes(minutes.id, { sections });
      setMinutes(updated);
    } catch (err) {
      if (err instanceof MinutesConflictError) {
        setError(err.message);
      } else {
        setError('Failed to save minutes');
      }
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!minutes) return;
    
    try {
      setPublishing(true);
      setError('');
      const published = await publishMinutes(minutes.id);
      setMinutes(published);
    } catch (err) {
      if (err instanceof MinutesConflictError) {
        setError(err.message);
      } else {
        setError('Failed to publish minutes');
      }
    } finally {
      setPublishing(false);
    }
  };

  const handleCreateNewVersion = async () => {
    if (!minutes) return;
    
    try {
      setError('');
      const newVersion = await createNewVersion(minutes.id);
      router.push(`/e/${engagementId}/workshops/${workshopId}/minutes?id=${newVersion.id}`);
    } catch (err) {
      setError('Failed to create new version');
    }
  };

  const updateListField = (field: keyof MinutesSection, index: number, value: string) => {
    setSections(prev => ({
      ...prev,
      [field]: prev[field].map((item, i) => i === index ? value : item)
    }));
  };

  const addListItem = (field: keyof MinutesSection) => {
    setSections(prev => ({
      ...prev,
      [field]: [...prev[field], '']
    }));
  };

  const removeListItem = (field: keyof MinutesSection, index: number) => {
    setSections(prev => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index)
    }));
  };

  const renderEditableList = (
    title: string, 
    field: keyof MinutesSection, 
    placeholder: string
  ) => {
    const isReadonly = minutes?.status === 'published';
    
    return (
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-medium text-gray-900">{title}</h3>
          {!isReadonly && (
            <button
              onClick={() => addListItem(field)}
              className="text-blue-600 hover:text-blue-800 text-sm"
            >
              + Add
            </button>
          )}
        </div>
        <div className="space-y-2">
          {sections[field].map((item, index) => (
            <div key={index} className="flex gap-2">
              <input
                type="text"
                value={item}
                onChange={(e) => updateListField(field, index, e.target.value)}
                placeholder={placeholder}
                readOnly={isReadonly}
                className={`flex-1 px-3 py-2 border rounded-md ${
                  isReadonly 
                    ? 'bg-gray-50 border-gray-200 text-gray-600' 
                    : 'border-gray-300 focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                }`}
              />
              {!isReadonly && (
                <button
                  onClick={() => removeListItem(field, index)}
                  className="text-red-600 hover:text-red-800 px-2"
                >
                  ×
                </button>
              )}
            </div>
          ))}
          {sections[field].length === 0 && (
            <p className="text-gray-500 text-sm italic">No {field} recorded</p>
          )}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="space-y-4">
            <div className="h-32 bg-gray-200 rounded"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!minutes) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="text-center">
          <p className="text-gray-600">Minutes not found</p>
          <button
            onClick={() => router.push(`/e/${engagementId}/workshops/${workshopId}`)}
            className="mt-4 text-blue-600 hover:text-blue-800"
          >
            ← Back to Workshop
          </button>
        </div>
      </div>
    );
  }

  const isPublished = minutes.status === 'published';

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <header className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Minutes Editor</h1>
          <div className="flex items-center gap-4 mt-2 text-sm text-gray-600">
            <span className={`px-2 py-1 rounded-full ${
              isPublished ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
            }`}>
              {isPublished ? 'Published' : 'Draft'}
            </span>
            {minutes.published_at && (
              <span>Published: {new Date(minutes.published_at).toLocaleString()}</span>
            )}
          </div>
        </div>
        <button
          onClick={() => router.push(`/e/${engagementId}/workshops/${workshopId}`)}
          className="text-blue-600 hover:text-blue-800"
        >
          ← Back to Workshop
        </button>
      </header>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {isPublished && (
        <div className="bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded">
          <div className="flex justify-between items-start">
            <div>
              <p className="font-medium">Minutes are immutable after publishing</p>
              {minutes.content_hash && (
                <p className="text-sm font-mono mt-1">Hash: {minutes.content_hash}</p>
              )}
            </div>
            <button
              onClick={handleCreateNewVersion}
              className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
            >
              Create New Version
            </button>
          </div>
        </div>
      )}

      <div className="bg-white shadow rounded-lg p-6 space-y-8">
        {renderEditableList('Attendees', 'attendees', 'Enter attendee name')}
        {renderEditableList('Decisions', 'decisions', 'Enter decision made')}
        {renderEditableList('Actions', 'actions', 'Enter action item')}
        {renderEditableList('Questions', 'questions', 'Enter question or concern')}
      </div>

      {!isPublished && (
        <div className="flex justify-end gap-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 disabled:bg-gray-400"
          >
            {saving ? 'Saving...' : 'Save Draft'}
          </button>
          <button
            onClick={handlePublish}
            disabled={publishing}
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:bg-green-400"
          >
            {publishing ? 'Publishing...' : 'Publish Minutes'}
          </button>
        </div>
      )}
    </div>
  );
}