import React, { Fragment } from 'react';
import { Menu, Transition } from '@headlessui/react';
import { ChevronDownIcon } from '@heroicons/react/20/solid';

export type SortField = 'name' | 'title' | 'office' | 'email' | 'validationStatus' | 'dateAdded';
export type SortDirection = 'asc' | 'desc';

interface SortOption {
  field: SortField;
  label: string;
}

const sortOptions: SortOption[] = [
  { field: 'name', label: 'Name' },
  { field: 'title', label: 'Title' },
  { field: 'office', label: 'Office' },
  { field: 'email', label: 'Email Domain' },
  { field: 'validationStatus', label: 'Validation Status' },
  { field: 'dateAdded', label: 'Date Added' },
];

interface SortMenuProps {
  sortField: SortField;
  sortDirection: SortDirection;
  onSortChange: (field: SortField) => void;
  onDirectionChange: (direction: SortDirection) => void;
}

const SortMenu: React.FC<SortMenuProps> = ({
  sortField,
  sortDirection,
  onSortChange,
  onDirectionChange,
}) => {
  return (
    <Menu as="div" className="relative inline-block text-left">
      <div className="flex items-center space-x-2">
        <Menu.Button className="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50">
          Sort by: {sortOptions.find(opt => opt.field === sortField)?.label}
          <ChevronDownIcon className="-mr-1 ml-1.5 h-5 w-5" aria-hidden="true" />
        </Menu.Button>
        <button
          onClick={() => onDirectionChange(sortDirection === 'asc' ? 'desc' : 'asc')}
          className="p-2 text-gray-400 hover:text-gray-600"
        >
          {sortDirection === 'asc' ? '↑' : '↓'}
        </button>
      </div>

      <Transition
        as={Fragment}
        enter="transition ease-out duration-100"
        enterFrom="transform opacity-0 scale-95"
        enterTo="transform opacity-100 scale-100"
        leave="transition ease-in duration-75"
        leaveFrom="transform opacity-100 scale-100"
        leaveTo="transform opacity-0 scale-95"
      >
        <Menu.Items className="absolute right-0 z-10 mt-2 w-40 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
          <div className="py-1">
            {sortOptions.map((option) => (
              <Menu.Item key={option.field}>
                {({ active }) => (
                  <button
                    onClick={() => onSortChange(option.field)}
                    className={`${
                      active ? 'bg-gray-100 text-gray-900' : 'text-gray-700'
                    } ${
                      sortField === option.field ? 'bg-gray-50' : ''
                    } block w-full px-4 py-2 text-left text-sm`}
                  >
                    {option.label}
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

export default SortMenu;
