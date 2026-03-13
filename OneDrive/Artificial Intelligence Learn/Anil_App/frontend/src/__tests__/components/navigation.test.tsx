/**
 * Tests for TabBar component.
 *
 * Globals (describe, it, expect, vi) are injected by vitest's `globals: true` config.
 * jest-dom matchers are available via the setup file (src/test/setup.ts).
 *
 * framer-motion is mocked so that <motion.div> renders as a plain <div>;
 * this avoids animation / layout-measurement side effects in jsdom.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { TabBar } from '../../components/navigation/TabBar';
import type { AnalysisTab } from '../../types/analysis';

// ---------------------------------------------------------------------------
// Module mocks — must be declared before any imports that pull framer-motion
// ---------------------------------------------------------------------------

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, layoutId, transition, className, ...rest }: React.HTMLAttributes<HTMLDivElement> & { layoutId?: string; transition?: unknown }) => (
      <div className={className} data-testid={layoutId ?? 'motion-div'} {...rest}>
        {children}
      </div>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useMotionValue: () => ({ set: vi.fn() }),
  useSpring: (v: unknown) => v,
  useTransform: () => 0,
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function renderTabBar(activeTab: AnalysisTab = 'chart', onTabChange = vi.fn()) {
  return { onTabChange, ...render(<TabBar activeTab={activeTab} onTabChange={onTabChange} />) };
}

// ---------------------------------------------------------------------------
// TabBar
// ---------------------------------------------------------------------------

describe('TabBar', () => {
  // --- Rendering ------------------------------------------------------------

  it('renders exactly 5 tab buttons', () => {
    renderTabBar();
    expect(screen.getAllByRole('button')).toHaveLength(5);
  });

  it('renders a "Chart" tab button', () => {
    renderTabBar();
    expect(screen.getByRole('button', { name: /chart/i })).toBeInTheDocument();
  });

  it('renders a "News" tab button', () => {
    renderTabBar();
    expect(screen.getByRole('button', { name: /news/i })).toBeInTheDocument();
  });

  it('renders a "Financials" tab button', () => {
    renderTabBar();
    expect(screen.getByRole('button', { name: /financials/i })).toBeInTheDocument();
  });

  it('renders an "About" tab button', () => {
    renderTabBar();
    expect(screen.getByRole('button', { name: /about/i })).toBeInTheDocument();
  });

  it('renders an "Invest" tab button', () => {
    renderTabBar();
    expect(screen.getByRole('button', { name: /invest/i })).toBeInTheDocument();
  });

  // --- Active tab styling ---------------------------------------------------

  it('applies text-stone-900 class to the active tab button', () => {
    renderTabBar('chart');
    const activeButton = screen.getByRole('button', { name: /chart/i });
    expect(activeButton).toHaveClass('text-stone-900');
  });

  it('does not apply text-stone-900 to inactive tab buttons', () => {
    renderTabBar('chart');
    expect(screen.getByRole('button', { name: /news/i })).not.toHaveClass('text-stone-900');
    expect(screen.getByRole('button', { name: /financials/i })).not.toHaveClass('text-stone-900');
    expect(screen.getByRole('button', { name: /about/i })).not.toHaveClass('text-stone-900');
    expect(screen.getByRole('button', { name: /invest/i })).not.toHaveClass('text-stone-900');
  });

  it('applies text-stone-400 to inactive tab buttons', () => {
    renderTabBar('chart');
    expect(screen.getByRole('button', { name: /news/i })).toHaveClass('text-stone-400');
    expect(screen.getByRole('button', { name: /financials/i })).toHaveClass('text-stone-400');
    expect(screen.getByRole('button', { name: /about/i })).toHaveClass('text-stone-400');
    expect(screen.getByRole('button', { name: /invest/i })).toHaveClass('text-stone-400');
  });

  it('marks "news" button as active when activeTab is "news"', () => {
    renderTabBar('news');
    expect(screen.getByRole('button', { name: /news/i })).toHaveClass('text-stone-900');
    expect(screen.getByRole('button', { name: /chart/i })).toHaveClass('text-stone-400');
    expect(screen.getByRole('button', { name: /financials/i })).toHaveClass('text-stone-400');
    expect(screen.getByRole('button', { name: /about/i })).toHaveClass('text-stone-400');
    expect(screen.getByRole('button', { name: /invest/i })).toHaveClass('text-stone-400');
  });

  it('marks "financials" button as active when activeTab is "financials"', () => {
    renderTabBar('financials');
    expect(screen.getByRole('button', { name: /financials/i })).toHaveClass('text-stone-900');
    expect(screen.getByRole('button', { name: /chart/i })).toHaveClass('text-stone-400');
    expect(screen.getByRole('button', { name: /news/i })).toHaveClass('text-stone-400');
    expect(screen.getByRole('button', { name: /about/i })).toHaveClass('text-stone-400');
    expect(screen.getByRole('button', { name: /invest/i })).toHaveClass('text-stone-400');
  });

  it('marks "about" button as active when activeTab is "about"', () => {
    renderTabBar('about');
    expect(screen.getByRole('button', { name: /about/i })).toHaveClass('text-stone-900');
    expect(screen.getByRole('button', { name: /chart/i })).toHaveClass('text-stone-400');
    expect(screen.getByRole('button', { name: /news/i })).toHaveClass('text-stone-400');
    expect(screen.getByRole('button', { name: /financials/i })).toHaveClass('text-stone-400');
    expect(screen.getByRole('button', { name: /invest/i })).toHaveClass('text-stone-400');
  });

  it('marks "invest" button as active when activeTab is "invest"', () => {
    renderTabBar('invest');
    expect(screen.getByRole('button', { name: /invest/i })).toHaveClass('text-stone-900');
    expect(screen.getByRole('button', { name: /chart/i })).toHaveClass('text-stone-400');
    expect(screen.getByRole('button', { name: /news/i })).toHaveClass('text-stone-400');
    expect(screen.getByRole('button', { name: /financials/i })).toHaveClass('text-stone-400');
    expect(screen.getByRole('button', { name: /about/i })).toHaveClass('text-stone-400');
  });

  // --- Underline indicator --------------------------------------------------

  it('renders the animated underline only for the active tab', () => {
    renderTabBar('chart');
    const underlines = screen.getAllByTestId('tab-underline');
    expect(underlines).toHaveLength(1);
  });

  it('places the underline inside the active tab button', () => {
    renderTabBar('financials');
    const [underline] = screen.getAllByTestId('tab-underline');
    expect(screen.getByRole('button', { name: /financials/i })).toContainElement(underline);
  });

  it('underline has bg-indigo-600 class', () => {
    renderTabBar('chart');
    const [underline] = screen.getAllByTestId('tab-underline');
    expect(underline).toHaveClass('bg-indigo-600');
  });

  // --- Click callbacks ------------------------------------------------------

  it('calls onTabChange with "chart" when the Chart button is clicked', () => {
    const { onTabChange } = renderTabBar('news');
    fireEvent.click(screen.getByRole('button', { name: /chart/i }));
    expect(onTabChange).toHaveBeenCalledTimes(1);
    expect(onTabChange).toHaveBeenCalledWith('chart');
  });

  it('calls onTabChange with "news" when the News button is clicked', () => {
    const { onTabChange } = renderTabBar('chart');
    fireEvent.click(screen.getByRole('button', { name: /news/i }));
    expect(onTabChange).toHaveBeenCalledTimes(1);
    expect(onTabChange).toHaveBeenCalledWith('news');
  });

  it('calls onTabChange with "financials" when the Financials button is clicked', () => {
    const { onTabChange } = renderTabBar('chart');
    fireEvent.click(screen.getByRole('button', { name: /financials/i }));
    expect(onTabChange).toHaveBeenCalledTimes(1);
    expect(onTabChange).toHaveBeenCalledWith('financials');
  });

  it('calls onTabChange with "about" when the About button is clicked', () => {
    const { onTabChange } = renderTabBar('chart');
    fireEvent.click(screen.getByRole('button', { name: /about/i }));
    expect(onTabChange).toHaveBeenCalledTimes(1);
    expect(onTabChange).toHaveBeenCalledWith('about');
  });

  it('calls onTabChange with "invest" when the Invest button is clicked', () => {
    const { onTabChange } = renderTabBar('chart');
    fireEvent.click(screen.getByRole('button', { name: /invest/i }));
    expect(onTabChange).toHaveBeenCalledTimes(1);
    expect(onTabChange).toHaveBeenCalledWith('invest');
  });

  it('calls onTabChange even when the already-active tab is clicked', () => {
    const { onTabChange } = renderTabBar('chart');
    fireEvent.click(screen.getByRole('button', { name: /chart/i }));
    expect(onTabChange).toHaveBeenCalledWith('chart');
  });

  it('does not call onTabChange when no button is clicked', () => {
    const { onTabChange } = renderTabBar();
    expect(onTabChange).not.toHaveBeenCalled();
  });

  // --- Tab order ------------------------------------------------------------

  it('renders tabs in the order: Chart, News, Financials, About, Invest', () => {
    renderTabBar();
    const buttons = screen.getAllByRole('button');
    expect(buttons[0]).toHaveAccessibleName(/chart/i);
    expect(buttons[1]).toHaveAccessibleName(/news/i);
    expect(buttons[2]).toHaveAccessibleName(/financials/i);
    expect(buttons[3]).toHaveAccessibleName(/about/i);
    expect(buttons[4]).toHaveAccessibleName(/invest/i);
  });

  // --- Container structure --------------------------------------------------

  it('wraps all buttons in a flex container with a bottom border', () => {
    const { container } = renderTabBar();
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.tagName).toBe('DIV');
    expect(wrapper).toHaveClass('flex');
    expect(wrapper).toHaveClass('border-b');
  });

  it('uses border-stone-200 on the container', () => {
    const { container } = renderTabBar();
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper).toHaveClass('border-stone-200');
  });
});
