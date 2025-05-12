import React, { Fragment } from 'react';
import { Menu, Transition } from '@headlessui/react';
import { ArrowDownTrayIcon } from '@heroicons/react/20/solid';
import { ExportFormat } from '../utils/export';

interface ExportMenuProps {
  onExport: (format: ExportFormat) => void;
  selectedCount: number;
}

const exportOptions: { format: ExportFormat; label: string }[] = [
  { format: 'xlsx', label: 'Excel (.xlsx)' },
  { format: 'csv', label: 'CSV (.csv)' },
  { format: 'pdf', label: 'PDF (.pdf)' },
];

const ExportMenu: React.FC<ExportMenuProps> = ({ onExport, selectedCount }) => {
  return (
    <Menu as="div" className="relative inline-block text-left">
      <Menu.Button className="btn-secondary inline-flex items-center">
        <ArrowDownTrayIcon className="-ml-0.5 mr-2 h-4 w-4" />
        Export {selectedCount > 0 ? `Selected (${selectedCount})` : 'All'}
      </Menu.Button>

      <Transition
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <Menu.Items className="absolute right-0 z-10 mt-2 w-48 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
          <div className="py-1">
            {exportOptions.map(({ format, label }) => (
              <Menu.Item key={format}>
                {({ active }) => (
                  <button
                    onClick={() => onExport(format)}
                    className={`${
                      active ? 'bg-gray-100 text-gray-900' : 'text-gray-700'
                    } block w-full px-4 py-2 text-left text-sm`}
                  >
                    {label}
                  </button>
                )}
              </Menu.Item>
            ))}
          </div>
        </Menu.Items>
      </Transition>
    </Menu>
  );
};

export default ExportMenu;
