// API Fallback Handler for 503 Service Unavailable
// This module provides graceful degradation when the API is down

export class APIFallback {
  private static isAPIDown = false;
  private static lastCheckTime = 0;
  private static CHECK_INTERVAL = 60000; // Check every minute

  static async checkAPIHealth(apiUrl: string): Promise<boolean> {
    const now = Date.now();
    
    // Rate limit health checks
    if (now - this.lastCheckTime < this.CHECK_INTERVAL && this.isAPIDown) {
      return false;
    }

    try {
      const response = await fetch(`${apiUrl}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000) // 5 second timeout
      });
      
      this.lastCheckTime = now;
      this.isAPIDown = !response.ok;
      return response.ok;
    } catch (error) {
      this.lastCheckTime = now;
      this.isAPIDown = true;
      return false;
    }
  }

  static async wrapAPICall<T>(
    apiCall: () => Promise<T>,
    fallbackData?: T,
    options?: { 
      showMaintenanceMessage?: boolean;
      cacheKey?: string;
    }
  ): Promise<T> {
    try {
      const result = await apiCall();
      
      // Cache successful responses
      if (options?.cacheKey) {
        localStorage.setItem(options.cacheKey, JSON.stringify({
          data: result,
          timestamp: Date.now()
        }));
      }
      
      return result;
    } catch (error: any) {
      // Check if it's a 503 error
      if (error.status === 503 || error.message?.includes('503')) {
        this.isAPIDown = true;
        
        // Try to return cached data if available
        if (options?.cacheKey) {
          const cached = localStorage.getItem(options.cacheKey);
          if (cached) {
            const { data, timestamp } = JSON.parse(cached);
            // Use cache if less than 1 hour old
            if (Date.now() - timestamp < 3600000) {
              console.warn('API down, using cached data');
              return data;
            }
          }
        }
        
        // Return fallback data if provided
        if (fallbackData !== undefined) {
          console.warn('API down, using fallback data');
          return fallbackData;
        }
        
        // Show maintenance message if requested
        if (options?.showMaintenanceMessage) {
          throw new Error('The API is currently undergoing maintenance. Please try again later.');
        }
      }
      
      // Re-throw other errors
      throw error;
    }
  }

  static getMaintenanceMessage(): string {
    return `
      <div class="maintenance-notice">
        <h3>System Maintenance</h3>
        <p>We're currently performing maintenance on our API services.</p>
        <p>Some features may be temporarily unavailable.</p>
        <p>We expect to be back online shortly. Thank you for your patience.</p>
      </div>
    `;
  }

  static getMockEngagements() {
    return [
      {
        id: 'demo-001',
        name: 'Demo Engagement (Offline Mode)',
        description: 'This is cached/demo data shown while the API is unavailable',
        status: 'demo',
        created: new Date().toISOString(),
        owner: 'Demo User'
      }
    ];
  }

  static getMockAssessment() {
    return {
      id: 'demo-assessment-001',
      engagementId: 'demo-001',
      name: 'Demo Assessment',
      framework: 'NIST CSF 2.0',
      status: 'demo',
      completionPercentage: 0,
      sections: []
    };
  }
}

export default APIFallback;