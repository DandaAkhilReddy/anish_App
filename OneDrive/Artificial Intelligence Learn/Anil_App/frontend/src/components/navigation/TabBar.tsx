import { motion } from 'framer-motion';
import { LineChart, Newspaper, BarChart3, Info, TrendingUp } from 'lucide-react';
import type { AnalysisTab } from '../../types/analysis';

interface TabConfig {
  id: AnalysisTab;
  label: string;
  icon: typeof LineChart;
}

const tabs: TabConfig[] = [
  { id: 'chart', label: 'Chart', icon: LineChart },
  { id: 'news', label: 'News', icon: Newspaper },
  { id: 'financials', label: 'Financials', icon: BarChart3 },
  { id: 'about', label: 'About', icon: Info },
  { id: 'invest', label: 'Invest', icon: TrendingUp },
];

interface TabBarProps {
  activeTab: AnalysisTab;
  onTabChange: (tab: AnalysisTab) => void;
}

export function TabBar({ activeTab, onTabChange }: TabBarProps) {
  return (
    <div className="flex border-b border-stone-200">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`relative flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors ${
              isActive
                ? 'text-stone-900'
                : 'text-stone-400 hover:text-stone-600'
            }`}
          >
            <Icon size={16} />
            {tab.label}

            {isActive && (
              <motion.div
                layoutId="tab-underline"
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-600"
                transition={{ type: 'spring', stiffness: 500, damping: 35 }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
