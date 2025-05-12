export interface ValidationMessage {
  message: string;
  type: 'success' | 'warning' | 'error';
}

export interface Lead {
  id: string;
  name: string;
  title: string;
  agency: string;
  email: string;
  phone: string;
  office: string;
  dateAdded: string;
  validationMessages: ValidationMessage[];
}

export interface LeadsResponse {
  leads: Lead[];
  total: number;
}

export interface EmailRequest {
  email: string;
  subject: string;
  body: string;
}

export type SortField = 'title' | 'agency' | 'email' | 'dateAdded';
export type SortDirection = 'asc' | 'desc';
export type ExportFormat = 'csv' | 'xlsx';

export interface DateRange {
  from: string;
  to: string;
}

export interface Filters {
  validationStatus: string[];
  dateRange: DateRange;
  emailDomains: string[];
}
