"use client";
import { useState, useEffect } from "react";
import type { RAGConfiguration } from "@/types/evidence";

interface RAGToggleProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  disabled?: boolean;
  className?: string;
  showStatus?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export default function RAGToggle({ 
  enabled, 
  onToggle, 
  disabled = false, 
  className = "",
  showStatus = true,
  size = 'md'
}: RAGToggleProps) {
  const [ragConfig, setRagConfig] = useState<RAGConfiguration | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRAGConfiguration();
  }, []);

  async function loadRAGConfiguration() {
    try {
      const response = await fetch("/api/proxy/system/rag-config");
      if (response.ok) {
        const config: RAGConfiguration = await response.json();
        setRagConfig(config);
      } else {
        // Default to disabled if config unavailable
        setRagConfig({
          mode: 'none',
          enabled: false,
          status: 'offline',
        });
      }
    } catch (error) {
      console.warn("Failed to load RAG configuration:", error);
      setRagConfig({
        mode: 'none',
        enabled: false,
        status: 'offline',
      });
    } finally {
      setLoading(false);
    }
  }

  function getStatusIcon() {
    if (!ragConfig) return "❓";
    switch (ragConfig.status) {
      case 'healthy': return "🟢";
      case 'degraded': return "🟡";
      case 'offline': return "🔴";
      default: return "❓";
    }
  }

  function getStatusText() {
    if (!ragConfig) return "Unknown";
    switch (ragConfig.status) {
      case 'healthy': return "Healthy";
      case 'degraded': return "Degraded";
      case 'offline': return "Offline";
      default: return "Unknown";
    }
  }

  function getSizeClasses() {
    switch (size) {
      case 'sm': return {
        container: 'text-sm',
        toggle: 'w-9 h-5',
        thumb: 'w-4 h-4',
        thumbTranslate: 'translate-x-4',
        label: 'text-xs',
        status: 'text-xs'
      };
      case 'lg': return {
        container: 'text-lg',
        toggle: 'w-14 h-8',
        thumb: 'w-7 h-7',
        thumbTranslate: 'translate-x-6',
        label: 'text-base',
        status: 'text-sm'
      };
      default: return {
        container: 'text-base',
        toggle: 'w-11 h-6',
        thumb: 'w-5 h-5',
        thumbTranslate: 'translate-x-5',
        label: 'text-sm',
        status: 'text-xs'
      };
    }
  }

  const sizeClasses = getSizeClasses();
  const isRAGAvailable = ragConfig?.enabled && ragConfig?.mode !== 'none';
  const isDisabled = disabled || loading || !isRAGAvailable;

  if (loading) {
    return (
      <div className={`flex items-center gap-2 ${sizeClasses.container} ${className}`}>
        <div className="animate-pulse">
          <div className={`${sizeClasses.toggle} bg-gray-200 rounded-full`}></div>
        </div>
        <span className="text-gray-500">Loading RAG status...</span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 ${sizeClasses.container} ${className}`}>
      <div className="flex items-center gap-3">
        {/* Toggle Switch */}
        <button
          type="button"
          onClick={() => !isDisabled && onToggle(!enabled)}
          disabled={isDisabled}
          className={`
            relative inline-flex ${sizeClasses.toggle} rounded-full border-2 border-transparent 
            transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 
            focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed
            ${enabled && isRAGAvailable 
              ? 'bg-blue-600' 
              : 'bg-gray-200'
            }
          `}
          role="switch"
          aria-checked={enabled && isRAGAvailable}
          aria-label="Toggle Grounded Analysis (RAG)"
        >
          <span
            className={`
              ${sizeClasses.thumb} inline-block transform rounded-full bg-white shadow-lg 
              ring-0 transition duration-200 ease-in-out
              ${enabled && isRAGAvailable 
                ? sizeClasses.thumbTranslate 
                : 'translate-x-0'
              }
            `}
          />
        </button>

        {/* Label */}
        <div className="flex flex-col">
          <label 
            className={`${sizeClasses.label} font-medium text-gray-900 cursor-pointer`}
            onClick={() => !isDisabled && onToggle(!enabled)}
          >
            Grounded Analysis (RAG)
          </label>
          
          {showStatus && (
            <div className={`${sizeClasses.status} text-gray-500 flex items-center gap-1`}>
              <span>{getStatusIcon()}</span>
              <span>{getStatusText()}</span>
              {ragConfig?.mode && ragConfig.mode !== 'none' && (
                <span className="text-blue-600">• {ragConfig.mode}</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Availability Warning */}
      {!isRAGAvailable && (
        <div className="flex items-center gap-1 text-amber-600 bg-amber-50 px-2 py-1 rounded text-xs">
          <span>⚠️</span>
          <span>RAG Unavailable</span>
        </div>
      )}

      {/* Enhanced Status Tooltip */}
      {enabled && ragConfig && (
        <div className="relative group">
          <button 
            type="button"
            className="text-gray-400 hover:text-gray-600 text-xs"
            title="RAG Configuration Details"
          >
            ℹ️
          </button>
          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:block z-10">
            <div className="bg-gray-900 text-white text-xs rounded py-2 px-3 whitespace-nowrap">
              <div>Mode: {ragConfig.mode}</div>
              <div>Status: {getStatusText()}</div>
              {ragConfig.model && <div>Model: {ragConfig.model}</div>}
              {ragConfig.last_check && (
                <div>Last Check: {new Date(ragConfig.last_check).toLocaleTimeString()}</div>
              )}
              <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Utility hook for RAG availability
export function useRAGAvailability() {
  const [config, setConfig] = useState<RAGConfiguration | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadConfig() {
      try {
        const response = await fetch("/api/proxy/system/rag-config");
        if (response.ok) {
          const data = await response.json();
          setConfig(data);
        }
      } catch (error) {
        console.warn("Failed to load RAG config:", error);
      } finally {
        setLoading(false);
      }
    }
    loadConfig();
  }, []);

  return {
    isAvailable: config?.enabled && config?.mode !== 'none',
    config,
    loading,
    status: config?.status || 'offline'
  };
}