"use client";

import React from 'react';

// Performance monitoring utilities
export class PerformanceTracker {
  private static instance: PerformanceTracker;
  private timers: Map<string, number> = new Map();

  static getInstance(): PerformanceTracker {
    if (!PerformanceTracker.instance) {
      PerformanceTracker.instance = new PerformanceTracker();
    }
    return PerformanceTracker.instance;
  }

  startTimer(label: string): void {
    this.timers.set(label, performance.now());
  }

  endTimer(label: string): number {
    const startTime = this.timers.get(label);
    if (!startTime) {
      console.warn(`Timer "${label}" was never started`);
      return 0;
    }

    const duration = performance.now() - startTime;
    this.timers.delete(label);
    
    if (process.env.NODE_ENV === 'development') {
      console.log(`⏱️ ${label}: ${duration.toFixed(2)}ms`);
    }

    // Track slow operations
    if (duration > 5000) { // 5+ seconds
      console.warn(`🐌 Slow operation detected: ${label} took ${duration.toFixed(2)}ms`);
    }

    return duration;
  }

  measureAsync<T>(label: string, fn: () => Promise<T>): Promise<T> {
    this.startTimer(label);
    return fn().finally(() => {
      this.endTimer(label);
    });
  }

  // Basic performance tracking using native APIs
  trackWebVitals(): void {
    if (typeof window !== 'undefined' && 'performance' in window) {
      // Track basic performance metrics using native APIs
      const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
          if (process.env.NODE_ENV === 'development') {
            console.log(`📊 ${entry.name}: ${entry.duration?.toFixed(2)}ms`);
          }
        }
      });

      try {
        observer.observe({ entryTypes: ['navigation', 'measure'] });
      } catch (error) {
        // PerformanceObserver not supported
        if (process.env.NODE_ENV === 'development') {
          console.log('PerformanceObserver not supported');
        }
      }

      // Track page load time
      window.addEventListener('load', () => {
        const loadTime = performance.now();
        if (process.env.NODE_ENV === 'development') {
          console.log(`🚀 Page loaded in: ${loadTime.toFixed(2)}ms`);
        }
      });
    }
  }

  // Check if page load is taking too long
  monitorPageLoad(): void {
    if (typeof window === 'undefined') return;

    const startTime = performance.now();
    
    const checkPageLoad = () => {
      const currentTime = performance.now();
      const loadTime = currentTime - startTime;
      
      if (loadTime > 10000) { // 10+ seconds
        console.warn(`🚨 Page load taking too long: ${loadTime.toFixed(2)}ms`);
        // Could send analytics or show user feedback here
      }
    };

    // Check after 10 seconds
    setTimeout(checkPageLoad, 10000);
  }
}

// Hook for React components
export function usePerformanceTracker() {
  return PerformanceTracker.getInstance();
}

// Utility for measuring component render time
export function withPerformanceTracking<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  componentName: string
) {
  return function PerformanceTrackedComponent(props: P) {
    const tracker = usePerformanceTracker();
    
    React.useEffect(() => {
      tracker.startTimer(`${componentName}_mount`);
      return () => {
        tracker.endTimer(`${componentName}_mount`);
      };
    }, [tracker]);

    return React.createElement(WrappedComponent, props);
  };
}

// Performance-aware fetch wrapper
export async function performanceFetch(
  input: RequestInfo | URL, 
  init?: RequestInit,
  label?: string
): Promise<Response> {
  const tracker = PerformanceTracker.getInstance();
  const timerLabel = label || `fetch_${typeof input === 'string' ? input : input.toString()}`;
  
  return tracker.measureAsync(timerLabel, () => fetch(input, init));
}

export default PerformanceTracker;