import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { 
  Button, 
  Checkbox, 
  Chip, 
  Paper, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TablePagination, 
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  SelectChangeEvent,
  CircularProgress,
  Alert,
  Pagination
} from '@mui/material';
import { useSnackbar } from 'notistack';
import { Lead, ValidationMessage, LeadsResponse } from '../types';
import { API_BASE_URL } from '../config';
import { Filters } from './FilterMenu';
import { SortField, SortDirection } from './SortMenu';
import { ExportFormat } from '../utils/export';
import { exportLeads, sendEmail } from '../api';
import ConfirmDialog from './ConfirmDialog';
import ExportMenu from './ExportMenu';
import FilterMenu from './FilterMenu';
import SortMenu from './SortMenu';

export type ValidationStatus = 'error' | 'warning' | 'success';

interface FilterState {
  validationStatus: ValidationStatus[];
  dateRange: { from: string; to: string };
  emailDomains: string[];
}

interface LeadsListProps {}

const LeadsList: React.FC<LeadsListProps> = () => {
  // Hooks
  const { enqueueSnackbar } = useSnackbar();

  // Constants
  const pageSizeOptions = [5, 10, 25, 50, 100];

  // State declarations
  const [leads, setLeads] = useState<Lead[]>([]);
  const [response, setResponse] = useState<LeadsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalLeads, setTotalLeads] = useState(0);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [selectedLeads, setSelectedLeads] = useState<Set<string>>(new Set());
  const [selectedEmail, setSelectedEmail] = useState<string>('');
  const [emailDialogOpen, setEmailDialogOpen] = useState<boolean>(false);
  const [showClearDialog, setShowClearDialog] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState<FilterState>({
    validationStatus: [],
    dateRange: { from: '', to: '' },
    emailDomains: [],
  });
  const [sortField, setSortField] = useState<SortField>('title');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  // Effects
  useEffect(() => {
    void fetchLeads();
  }, [currentPage, itemsPerPage, sortField, sortDirection, filters]);

  // Event handlers
  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>): void => {
    setSearchTerm(e.target.value);
  }, []);

  const handleSort = useCallback((field: SortField): void => {
    if (field === sortField) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  }, [sortField, sortDirection]);

  const handlePageChange = useCallback((page: number): void => {
    setCurrentPage(page);
  }, []);

  const handlePageSizeChange = useCallback((event: SelectChangeEvent<number>): void => {
    const size = Number(event.target.value);
    setItemsPerPage(size);
    setCurrentPage(1);
  }, []);

  const handleExport = useCallback((format: ExportFormat): void => {
    const selectedData = leads.filter(lead => selectedLeads.has(lead.id));
    void exportLeads(selectedData, format).catch(error => {
      setError(error instanceof Error ? error.message : 'Failed to export leads');
    });
  }, [leads, selectedLeads]);

  const handleEmailSelected = useCallback((): void => {
    const selectedLeadsList = leads.filter(lead => selectedLeads.has(lead.id));
    void Promise.all(
      selectedLeadsList.map(lead => {
        if (lead.email) {
          return sendEmail({ email: lead.email, subject: 'Email Subject', body: 'Email Content' });
        }
        return Promise.resolve();
      })
    ).then(() => {
      enqueueSnackbar('Emails sent successfully', { variant: 'success' });
    }).catch(() => {
      enqueueSnackbar('Failed to send emails', { variant: 'error' });
    });
  }, [leads, selectedLeads, enqueueSnackbar]);

  const handleSendBulkEmails = useCallback(async () => {
    const selectedEmails = Array.from(selectedLeads)
      .map(id => leads.find(lead => lead.id === id))
      .filter((lead): lead is Lead => lead !== undefined)
      .map(lead => lead.email)
      .filter(Boolean);

    if (selectedEmails.length === 0) {
      enqueueSnackbar('No valid emails selected', { variant: 'warning' });
      return;
    }

    try {
      await Promise.all(
        selectedEmails.map(email => {
          if (!email) {
            return Promise.resolve();
          }
          return sendEmail({
            email,
            subject: 'Bulk Email Subject',
            body: 'Bulk Email Content'
          });
        })
      );
      setSelectedLeads(new Set());
      enqueueSnackbar('Bulk emails sent successfully', { variant: 'success' });
    } catch (error) {
      enqueueSnackbar('Failed to send bulk emails', { variant: 'error' });
    }
  }, [leads, selectedLeads, enqueueSnackbar]);

  const handleClearSelected = useCallback((): void => {
    setSelectedLeads(new Set());
    setShowClearDialog(false);
  }, []);

  const handleFilterChange = useCallback((newFilters: FilterState): void => {
    setFilters(newFilters);
    setCurrentPage(1);
  }, []);

  const handleSortChange = useCallback((field: SortField, direction: SortDirection) => {
    setSortField(field);
    setSortDirection(direction);
    setCurrentPage(1);
  }, []);

  const handleSelectAll = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      const newSelected = new Set(leads.map(lead => lead.id));
      setSelectedLeads(newSelected);
    } else {
      setSelectedLeads(new Set());
    }
  }, [leads]);

  const handleSelect = useCallback((id: string) => {
    setSelectedLeads(prev => {
      const newSelected = new Set(prev);
      if (prev.has(id)) {
        newSelected.delete(id);
      } else {
        newSelected.add(id);
      }
      return newSelected;
    });
  }, []);

  const handleEmailClick = useCallback((email: string) => {
    setSelectedEmail(email);
    setEmailDialogOpen(true);
  }, []);

  const handleSendEmail = useCallback(async (subject: string, body: string) => {
    try {
      await sendEmail({ email: selectedEmail, subject, body });
      setEmailDialogOpen(false);
      enqueueSnackbar('Email sent successfully', { variant: 'success' });
    } catch (error) {
      enqueueSnackbar('Failed to send email', { variant: 'error' });
    }
  }, [selectedEmail, enqueueSnackbar]);

  const getEmailDomain = (email: string) => {
    if (!email) return '';
    const parts = email.split('@');
    return parts.length === 2 ? parts[1] : '';
  };

  const getValidationColor = useCallback((messages: ValidationMessage[]) => {
    if (messages.some(m => m.type === 'error')) return 'error';
    if (messages.some(m => m.type === 'warning')) return 'warning';
    if (messages.some(m => m.type === 'success')) return 'success';
    return 'default';
  }, []);

  // Memoized values
  const availableEmailDomains = useMemo(() => {
    const domains = new Set<string>();
    leads.forEach(lead => {
      if (lead.email) {
        const domain = getEmailDomain(lead.email);
        if (domain) domains.add(domain);
      }
    });
    return Array.from(domains);
  }, [leads]);

  const filteredLeads = useMemo(() => {
    return leads.filter(lead => {
      // Apply search filter
      if (searchTerm && !(
        lead.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        lead.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        lead.agency.toLowerCase().includes(searchTerm.toLowerCase()) ||
        lead.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        lead.phone.toLowerCase().includes(searchTerm.toLowerCase()) ||
        lead.office.toLowerCase().includes(searchTerm.toLowerCase())
      )) {
        return false;
      }

      // Apply validation status filter
      if (filters.validationStatus.length > 0) {
        const leadStatus = lead.validationMessages[0]?.type || 'success';
        if (!filters.validationStatus.includes(leadStatus)) {
          return false;
        }
      }

      // Apply email domain filter
      if (filters.emailDomains.length > 0 && lead.email) {
        const domain = getEmailDomain(lead.email);
        if (!filters.emailDomains.includes(domain)) {
          return false;
        }
      }

      return true;
    });
  }, [leads, searchTerm, filters, getEmailDomain]);

  // Fetch leads
  const fetchLeads = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams({
        page: currentPage.toString(),
        per_page: itemsPerPage.toString(),
        sort_field: sortField,
        sort_direction: sortDirection,
      });

      if (searchTerm) {
        params.append('search', searchTerm);
      }

      if (filters.validationStatus.length > 0) {
        params.append('validation_status', filters.validationStatus.join(','));
      }

      if (filters.dateRange.from) {
        params.append('date_from', filters.dateRange.from);
      }

      if (filters.dateRange.to) {
        params.append('date_to', filters.dateRange.to);
      }

      if (filters.emailDomains.length > 0) {
        params.append('email_domains', filters.emailDomains.join(','));
      }

      const response = await fetch(`${API_BASE_URL}/api/leads?${params.toString()}`);
      if (!response.ok) {
        throw new Error('Failed to fetch leads');
      }

      const data: LeadsResponse = await response.json();
      setLeads(data.leads);
      setTotalLeads(data.total);
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setLeads([]);
      setTotalLeads(0);
    } finally {
      setLoading(false);
    }
  }, [currentPage, itemsPerPage, sortField, sortDirection, filters, searchTerm]);

  return (
    <div className="min-h-full">
      <div className="py-6">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="min-w-0 flex-1">
              <TextField
                label="Search"
                variant="outlined"
                size="small"
                value={searchTerm}
                onChange={handleSearchChange}
                className="w-64"
              />
            </div>
            <div className="flex items-center space-x-3 ml-4">
              <FilterMenu
                filters={filters}
                onFiltersChange={handleFilterChange}
                availableEmailDomains={availableEmailDomains}
              />
              <SortMenu
                sortField={sortField}
                sortDirection={sortDirection}
                onSortChange={handleSort}
                onDirectionChange={direction => setSortDirection(direction)}
              />
              <ExportMenu
                onExport={handleExport}
                selectedCount={selectedLeads.size}
              />
              <Button
                variant="contained"
                color="primary"
                onClick={handleEmailSelected}
                disabled={selectedLeads.size === 0}
              >
                Email Selected
              </Button>
              <Button
                variant="outlined"
                color="secondary"
                onClick={() => setShowClearDialog(true)}
                disabled={selectedLeads.size === 0}
              >
                Clear Selected
              </Button>
            </div>
          </div>
        </div>

        <div className="mt-8">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            {error && (
              <Alert severity="error" className="mb-4">
                {error}
              </Alert>
            )}

            {loading ? (
              <div className="flex justify-center">
                <CircularProgress />
              </div>
            ) : leads.length === 0 ? (
              <p className="text-center text-gray-500">No leads found</p>
            ) : (
              <div className="flex flex-col">
                <div className="-mx-4 -my-2 overflow-x-auto sm:-mx-6 lg:-mx-8">
                  <div className="inline-block min-w-full py-2 align-middle">
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell padding="checkbox">
                            <Checkbox
                              indeterminate={selectedLeads.size > 0 && selectedLeads.size < leads.length}
                              checked={selectedLeads.size === leads.length}
                              onChange={handleSelectAll}
                            />
                          </TableCell>
                          <TableCell>Name</TableCell>
                          <TableCell>Title</TableCell>
                          <TableCell>Agency</TableCell>
                          <TableCell>Email</TableCell>
                          <TableCell>Phone</TableCell>
                          <TableCell>Office</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {leads.map((lead) => (
                          <TableRow
                            key={lead.id}
                            selected={selectedLeads.has(lead.id)}
                          >
                            <TableCell padding="checkbox">
                              <Checkbox
                                checked={selectedLeads.has(lead.id)}
                                onChange={() => handleSelect(lead.id)}
                              />
                            </TableCell>
                            <TableCell>{lead.name}</TableCell>
                            <TableCell>{lead.title}</TableCell>
                            <TableCell>{lead.agency}</TableCell>
                            <TableCell>
                              <Button
                                onClick={() => handleEmailClick(lead.email)}
                                disabled={!lead.email}
                              >
                                {lead.email}
                              </Button>
                            </TableCell>
                            <TableCell>{lead.phone}</TableCell>
                            <TableCell>{lead.office}</TableCell>
                            <TableCell>
                              <Chip
                                label={lead.validationMessages[0]?.type || 'success'}
                                color={getValidationColor(lead.validationMessages)}
                              />
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between px-4 sm:px-6 lg:px-8">
                  <div className="flex items-center gap-4">
                    <Select
                      value={itemsPerPage}
                      onChange={handlePageSizeChange}
                      size="small"
                    >
                      {pageSizeOptions.map((size) => (
                        <MenuItem key={size} value={size}>
                          {size} per page
                        </MenuItem>
                      ))}
                    </Select>
                    <div className="text-sm text-gray-700">
                      Showing {(currentPage - 1) * itemsPerPage + 1} to{' '}
                      {Math.min(currentPage * itemsPerPage, totalLeads)} of {totalLeads} results
                    </div>
                  </div>

                  <Pagination
                    count={Math.ceil(totalLeads / itemsPerPage)}
                    page={currentPage}
                    onChange={(_, page) => handlePageChange(page)}
                    color="primary"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <ConfirmDialog
        isOpen={showClearDialog}
        title="Clear Selected Leads"
        message="Are you sure you want to clear all selected leads?"
        onConfirm={handleClearSelected}
        onClose={() => setShowClearDialog(false)}
      />
    </div>
  );
};

export default LeadsList;
