interface LoadMoreButtonProps {
  hasMore: boolean;
  loading: boolean;
  onClick: () => void;
}

export function LoadMoreButton({ hasMore, loading, onClick }: LoadMoreButtonProps) {
  if (!hasMore) return null;

  return (
    <div className="load-more-wrap">
      <button type="button" className="load-more-btn" disabled={loading} onClick={onClick}>
        {loading ? 'Loading…' : 'Load more'}
      </button>
    </div>
  );
}
