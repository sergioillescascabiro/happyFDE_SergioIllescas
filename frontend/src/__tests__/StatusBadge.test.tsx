import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../components/ui/StatusBadge';

describe('StatusBadge', () => {
  it('renders available status', () => {
    render(<StatusBadge status="available" />);
    expect(screen.getByText('Available')).toBeInTheDocument();
  });

  it('renders covered status with blue style', () => {
    render(<StatusBadge status="covered" />);
    expect(screen.getByText('Covered')).toBeInTheDocument();
  });

  it('renders unknown status gracefully', () => {
    render(<StatusBadge status="unknown_status" />);
    expect(screen.getByText('unknown_status')).toBeInTheDocument();
  });
});
