import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

interface Lead {
  name: string;
  email: string;
  title: string;
  office: string;
  phone: string;
  dateAdded: string;
  validationMessages: {
    type: 'success' | 'warning' | 'error';
    message: string;
  }[];
}

export type ExportFormat = 'xlsx' | 'csv' | 'pdf';

interface FormattedLeadData {
  Name: string;
  Title: string;
  Office: string;
  Email: string;
  Phone: string;
  'Date Added': string;
  'Validation Status': string;
}

const formatLeadsData = (leads: Lead[]): FormattedLeadData[] => {
  return leads.map(lead => ({
    Name: lead.name,
    Title: lead.title,
    Office: lead.office,
    Email: lead.email,
    Phone: lead.phone,
    'Date Added': lead.dateAdded,
    'Validation Status': lead.validationMessages
      .map(msg => `${msg.type.toUpperCase()}: ${msg.message}`)
      .join('\n')
  }));
};

const exportToExcel = (leads: Lead[], fileName: string) => {
  const data = formatLeadsData(leads);
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.json_to_sheet(data);

  // Set column widths
  ws['!cols'] = [
    { wch: 20 }, // Name
    { wch: 25 }, // Title
    { wch: 25 }, // Office
    { wch: 30 }, // Email
    { wch: 15 }, // Phone
    { wch: 12 }, // Date Added
    { wch: 40 }, // Validation Status
  ];

  XLSX.utils.book_append_sheet(wb, ws, 'Leads');
  XLSX.writeFile(wb, `${fileName}.xlsx`);
};

const exportToCsv = (leads: Lead[], fileName: string) => {
  const data = formatLeadsData(leads);
  const ws = XLSX.utils.json_to_sheet(data);
  const csv = XLSX.utils.sheet_to_csv(ws);
  
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${fileName}.csv`;
  link.click();
};

const exportToPdf = (leads: Lead[], fileName: string) => {
  const data = formatLeadsData(leads);
  const doc = new jsPDF();

  autoTable(doc, {
    head: [Object.keys(data[0])],
    body: data.map(Object.values),
    styles: { fontSize: 8 },
    columnStyles: {
      0: { cellWidth: 25 }, // Name
      1: { cellWidth: 25 }, // Title
      2: { cellWidth: 25 }, // Office
      3: { cellWidth: 35 }, // Email
      4: { cellWidth: 20 }, // Phone
      5: { cellWidth: 20 }, // Date Added
      6: { cellWidth: 40 }, // Validation Status
    },
    didDrawPage: () => {
      doc.setFontSize(15);
      doc.text('Government AI Leads', 14, 15);
      doc.setFontSize(10);
      doc.text(`Generated on ${new Date().toLocaleDateString()}`, 14, 22);
    },
  });

  doc.save(`${fileName}.pdf`);
};

export const exportLeads = (leads: Lead[], format: ExportFormat = 'xlsx') => {
  const fileName = `gov-ai-leads-${new Date().toISOString().split('T')[0]}`;

  switch (format) {
    case 'xlsx':
      exportToExcel(leads, fileName);
      break;
    case 'csv':
      exportToCsv(leads, fileName);
      break;
    case 'pdf':
      exportToPdf(leads, fileName);
      break;
    default:
      console.error('Unsupported export format');
  }
};
