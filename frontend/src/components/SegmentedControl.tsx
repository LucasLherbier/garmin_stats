export type SegmentedVariant = 'default' | 'orange' | 'purple';

interface SegmentedControlProps<T extends string> {
  options: Array<{ value: T; label: string }>;
  value: T;
  onChange: (value: T) => void;
  variant?: SegmentedVariant;
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  variant = 'default',
}: SegmentedControlProps<T>) {
  const variantClass =
    variant === 'orange' ? 'segmented--orange' : variant === 'purple' ? 'segmented--purple' : '';

  return (
    <div className={`segmented${variantClass ? ` ${variantClass}` : ''}`} role="tablist">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          role="tab"
          aria-selected={value === opt.value}
          className={value === opt.value ? 'active' : undefined}
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
