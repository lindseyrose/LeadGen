import { Lead, ExportFormat } from '../types';

export const exportLeads = async (leads: Lead[], format: ExportFormat): Promise<void> => {
  try {
    const response = await fetch('http://localhost:8000/api/leads/export', {
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

export const sendEmail = async (leads: Lead[]): Promise<void> => {
  try {
    const response = await fetch('http://localhost:8000/api/leads/email', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ leads }),
    });

    if (!response.ok) {
      throw new Error('Failed to send email');
    }
  } catch (error) {
    console.error('Error sending email:', error);
    throw error;
  }
};
