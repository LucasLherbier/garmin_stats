interface ChartNoteProps {
  /** Short clauses shown inline, separated by a muted middle dot. */
  parts: string[];
}

export function ChartNote({ parts }: ChartNoteProps) {
  if (!parts.length) return null;

  return (
    <p className="chart-note" role="note">
      {parts.map((part, index) => (
        <span key={part} className="chart-note-part">
          {index > 0 ? <span className="chart-note-sep" aria-hidden="true">·</span> : null}
          {part}
        </span>
      ))}
    </p>
  );
}
