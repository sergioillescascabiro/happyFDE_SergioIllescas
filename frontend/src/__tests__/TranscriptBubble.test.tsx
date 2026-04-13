import { render, screen } from '@testing-library/react';
import { TranscriptBubble } from '../components/communications/TranscriptBubble';

describe('TranscriptBubble', () => {
  it('renders assistant message', () => {
    render(
      <TranscriptBubble
        message={{ role: 'assistant', message: 'Hello carrier!', timestamp: '00:00:05' }}
      />
    );
    expect(screen.getByText('Hello carrier!')).toBeInTheDocument();
  });

  it('renders caller message', () => {
    render(
      <TranscriptBubble
        message={{ role: 'caller', message: 'MC 98765', timestamp: '00:00:10' }}
      />
    );
    expect(screen.getByText('MC 98765')).toBeInTheDocument();
  });

  it('renders tool_call as collapsible row', () => {
    render(
      <TranscriptBubble
        message={{ role: 'tool_call', message: 'verify_carrier(mc="98765")', timestamp: '00:00:11' }}
      />
    );
    expect(screen.getByText('Tool call')).toBeInTheDocument();
  });
});
