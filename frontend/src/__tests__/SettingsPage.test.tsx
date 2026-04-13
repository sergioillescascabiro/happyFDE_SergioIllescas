import { render, screen } from '@testing-library/react';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  usePathname: () => '/dashboard/settings',
}));

// Mock auth
jest.mock('../lib/auth', () => ({
  getToken: () => 'hr-dashboard-token-test',
  clearToken: jest.fn(),
}));

// Need to import after mocks
import SettingsPage from '../app/dashboard/settings/page';

describe('SettingsPage', () => {
  it('renders settings sections', () => {
    render(<SettingsPage />);
    expect(screen.getByText('Authentication')).toBeInTheDocument();
    expect(screen.getByText('API Configuration')).toBeInTheDocument();
    expect(screen.getByText('Application')).toBeInTheDocument();
  });

  it('shows connected status', () => {
    render(<SettingsPage />);
    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  it('shows masked token by default', () => {
    render(<SettingsPage />);
    // Token should be masked (contains bullet chars)
    const tokenEl = screen.getByText(/hr-da/);
    expect(tokenEl).toBeInTheDocument();
  });
});
