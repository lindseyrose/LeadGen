import { Lead } from '../types';
import { ExportFormat } from '../utils/export';
import { EmailRequest } from '../types';
import { API_BASE_URL } from '../config';

export const exportLeads = async (leads: Lead[], format: ExportFormat): Promise<void> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/export`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ leads, format }),
    });

    if (!response.ok) {
      throw new Error('Failed to export leads');
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `leads.${format}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  } catch (error) {
    console.error('Error exporting leads:', error);
    throw error;
  }
};

export const sendEmail = async (request: EmailRequest): Promise<void> => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/send-email`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error('Failed to send email');
    }
  } catch (error) {
    console.error('Error sending email:', error);
    throw error;
  }
};
