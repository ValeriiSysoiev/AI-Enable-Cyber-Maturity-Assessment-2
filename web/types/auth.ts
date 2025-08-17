// Auth diagnostics types for admin interface

export interface AuthDiagnostics {
  mode: 'demo' | 'aad';
  tenant?: {
    id: string;
    name: string;
  };
  groups?: AuthGroup[];
  roles?: AuthRole[];
  configuration: {
    status: 'ok' | 'warning' | 'error';
    issues?: string[];
  };
  user?: {
    email: string;
    groups?: string[];
    roles?: string[];
  };
}

export interface AuthGroup {
  id: string;
  name: string;
  mapped_role?: string;
}

export interface AuthRole {
  name: string;
  description?: string;
  permissions?: string[];
}

export interface AuthDiagnosticsResponse {
  diagnostics: AuthDiagnostics;
  timestamp: string;
}