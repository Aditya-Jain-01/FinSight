import { Newspaper } from "lucide-react";
import type { NewsListProps } from "./schemas";

export function NewsList({ ticker, news }: NewsListProps) {
  if (!news || news.length === 0) return null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2 mb-2">
        <Newspaper className="w-5 h-5 text-gray-400" />
        <h3 className="font-semibold text-lg tracking-tight text-gray-900 dark:text-gray-100">
          Latest News {ticker && <span className="text-gray-500 font-normal">for {ticker}</span>}
        </h3>
      </div>
      <div className="flex flex-col gap-4">
        {news.map((item, idx) => (
          <a
            key={idx}
            href={item.link}
            target="_blank"
            rel="noreferrer"
            className="group flex flex-col gap-1 p-3 -mx-3 rounded-lg hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
          >
            <h4 className="font-medium text-gray-900 dark:text-gray-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors line-clamp-2">
              {item.title}
            </h4>
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              <span className="font-medium">{item.publisher}</span>
              {item.timestamp && (
                <>
                  <span>•</span>
                  <span>
                    {new Date(item.timestamp * 1000).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                </>
              )}
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
