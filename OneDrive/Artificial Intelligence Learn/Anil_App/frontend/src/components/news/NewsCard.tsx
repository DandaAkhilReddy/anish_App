import type { NewsItem } from '../../types/analysis';

interface NewsCardProps {
  item: NewsItem;
}

const dotColor: Record<string, string> = {
  positive: 'bg-emerald-500',
  negative: 'bg-red-500',
  neutral: 'bg-stone-300',
};

export function NewsCard({ item }: NewsCardProps) {
  const dot = item.sentiment !== null ? (dotColor[item.sentiment] ?? 'bg-stone-300') : 'bg-stone-300';

  return (
    <div className="flex items-start gap-2.5 py-2.5 px-1">
      <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${dot}`} />
      <div className="min-w-0">
        <p className="text-sm text-stone-700 leading-snug">{item.title}</p>
        {item.source !== null && (
          <span className="text-xs text-stone-400">{item.source}</span>
        )}
      </div>
    </div>
  );
}
