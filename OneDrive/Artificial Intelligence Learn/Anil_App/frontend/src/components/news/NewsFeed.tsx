import { Newspaper } from 'lucide-react';
import { Card } from '../common/Card';
import { NewsCard } from './NewsCard';
import type { NewsItem } from '../../types/analysis';

interface NewsFeedProps {
  items: NewsItem[];
}

export function NewsFeed({ items }: NewsFeedProps) {
  return (
    <Card>
      <div className="flex items-center gap-2 mb-3">
        <Newspaper size={16} className="text-stone-500" />
        <h4 className="text-sm font-medium text-stone-500">Latest News</h4>
        <span className="text-xs text-stone-400 ml-auto">{items.length} articles</span>
      </div>
      <div className="divide-y divide-stone-100">
        {items.length === 0 ? (
          <p className="text-sm text-stone-400 text-center py-4">No recent news found</p>
        ) : (
          items.map((item, i) => <NewsCard key={i} item={item} />)
        )}
      </div>
    </Card>
  );
}
