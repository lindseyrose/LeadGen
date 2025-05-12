import React, { Fragment, useState } from 'react';
import { Popover, Transition } from '@headlessui/react';
import { FunnelIcon } from '@heroicons/react/20/solid';

export interface Filters {
  validationStatus: ('success' | 'warning' | 'error')[];
  dateRange: {
    from: string;
    to: string;
  };
  emailDomains: string[];
}

interface FilterMenuProps {
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
  availableEmailDomains: string[];
}

const FilterMenu: React.FC<FilterMenuProps> = ({
  filters,
  onFiltersChange,
  availableEmailDomains,
}) => {
  const [localFilters, setLocalFilters] = useState(filters);

  const handleValidationChange = (status: 'success' | 'warning' | 'error') => {
    const newStatuses = localFilters.validationStatus.includes(status)
      ? localFilters.validationStatus.filter(s => s !== status)
      : [...localFilters.validationStatus, status];
    
    const newFilters = {
      ...localFilters,
      validationStatus: newStatuses,
    };
    setLocalFilters(newFilters);
    onFiltersChange(newFilters);
  };

  const handleDateChange = (field: 'from' | 'to', value: string) => {
    const newFilters = {
      ...localFilters,
      dateRange: {
        ...localFilters.dateRange,
        [field]: value,
      },
    };
    setLocalFilters(newFilters);
    onFiltersChange(newFilters);
  };

  const handleDomainChange = (domain: string) => {
    const newDomains = localFilters.emailDomains.includes(domain)
      ? localFilters.emailDomains.filter(d => d !== domain)
      : [...localFilters.emailDomains, domain];
    
    const newFilters = {
      ...localFilters,
      emailDomains: newDomains,
    };
    setLocalFilters(newFilters);
    onFiltersChange(newFilters);
  };

  const activeFilterCount = 
    localFilters.validationStatus.length +
    (localFilters.dateRange.from || localFilters.dateRange.to ? 1 : 0) +
    localFilters.emailDomains.length;

  return (
    <Popover className="relative">
      <Popover.Button
        className={`
          ${activeFilterCount > 0 ? 'bg-blue-50 text-blue-600' : 'bg-white text-gray-900'}
          inline-flex items-center rounded-md px-3 py-2 text-sm font-semibold shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50
        `}
      >
        <FunnelIcon className="-ml-0.5 mr-1.5 h-5 w-5" aria-hidden="true" />
        Filters
        {activeFilterCount > 0 && (
          <span className="ml-2 inline-flex items-center rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700">
            {activeFilterCount}
          </span>
        )}
      </Popover.Button>

      <Transition
        as={Fragment}
        enter="transition ease-out duration-200"
        enterFrom="opacity-0 translate-y-1"
        enterTo="opacity-100 translate-y-0"
        leave="transition ease-in duration-150"
        leaveFrom="opacity-100 translate-y-0"
        leaveTo="opacity-0 translate-y-1"
      >
        <Popover.Panel className="absolute right-0 z-10 mt-2 w-80 origin-top-right rounded-md bg-white p-4 shadow-2xl ring-1 ring-black ring-opacity-5 focus:outline-none">
          <div className="space-y-6">
            {/* Validation Status Filters */}
            <div>
              <h3 className="text-sm font-medium text-gray-900">Validation Status</h3>
              <div className="mt-2 space-y-2">
                {(['success', 'warning', 'error'] as const).map((status) => (
                  <label key={status} className="inline-flex items-center mr-4">
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      checked={localFilters.validationStatus.includes(status)}
                      onChange={() => handleValidationChange(status)}
                    />
                    <span className="ml-2 text-sm text-gray-600 capitalize">{status}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Date Range Filters */}
            <div>
              <h3 className="text-sm font-medium text-gray-900">Date Added</h3>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs text-gray-500">From</label>
                  <input
                    type="date"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    value={localFilters.dateRange.from}
                    onChange={(e) => handleDateChange('from', e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500">To</label>
                  <input
                    type="date"
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                    value={localFilters.dateRange.to}
                    onChange={(e) => handleDateChange('to', e.target.value)}
                  />
                </div>
              </div>
            </div>

            {/* Email Domain Filters */}
            <div>
              <h3 className="text-sm font-medium text-gray-900">Email Domain</h3>
              <div className="mt-2 max-h-32 overflow-y-auto space-y-2">
                {availableEmailDomains.map((domain) => (
                  <label key={domain} className="flex items-center">
                    <input
                      type="checkbox"
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      checked={localFilters.emailDomains.includes(domain)}
                      onChange={() => handleDomainChange(domain)}
                    />
                    <span className="ml-2 text-sm text-gray-600">{domain}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        </Popover.Panel>
      </Transition>
    </Popover>
  );
};

export default FilterMenu;
