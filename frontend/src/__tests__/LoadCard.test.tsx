import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LoadCard } from '../components/loads/LoadCard';
import { Load } from '../types';

const mockLoad: Load = {
  id: 'test-id-1',
  load_id: '202883',
  shipper_id: 'shipper-1',
  origin: 'Lincolnshire, IL',
  destination: 'Ashville, OH',
  pickup_datetime: '2026-04-15T10:00:00',
  delivery_datetime: '2026-04-16T14:00:00',
  equipment_type: 'Flatbed',
  loadboard_rate: 2.0,
  weight: 44000,
  commodity_type: 'Coils',
  num_of_pieces: 1,
  miles: 410,
  total_rate: 820,
  per_mile_rate: 2.0,
  status: 'available',
  created_at: '2026-04-12T00:00:00',
  updated_at: '2026-04-12T00:00:00',
};

describe('LoadCard', () => {
  it('renders load ID and route', () => {
    render(<LoadCard load={mockLoad} isSelected={false} onClick={() => {}} />);
    expect(screen.getByText('202883')).toBeInTheDocument();
    expect(screen.getByText('Lincolnshire, IL')).toBeInTheDocument();
    expect(screen.getByText('Ashville, OH')).toBeInTheDocument();
  });

  it('shows selected state with visual indicator', () => {
    const { container } = render(
      <LoadCard load={mockLoad} isSelected={true} onClick={() => {}} />
    );
    const btn = container.querySelector('button');
    expect(btn?.className).toContain('border-l-white');
  });

  it('calls onClick when clicked', async () => {
    const onClick = jest.fn();
    render(<LoadCard load={mockLoad} isSelected={false} onClick={onClick} />);
    await userEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
