function confidenceStyle(confidence) {
  if (confidence >= 0.8) {
    return {
      label: "High confidence",
      bar: "bg-emerald-500",
      text: "text-emerald-700",
      bg: "bg-emerald-50 ring-emerald-100",
    };
  }
  if (confidence >= 0.55) {
    return {
      label: "Medium confidence",
      bar: "bg-amber-500",
      text: "text-amber-700",
      bg: "bg-amber-50 ring-amber-100",
    };
  }
  return {
    label: "Low confidence",
    bar: "bg-rose-500",
    text: "text-rose-700",
    bg: "bg-rose-50 ring-rose-100",
  };
}

export default function ConfidenceBadge({ confidence }) {
  if (typeof confidence !== "number") return null;

  const percent = Math.round(confidence * 100);
  const style = confidenceStyle(confidence);

  return (
    <div className={`rounded-xl px-3 py-2 ring-1 ${style.bg}`}>
      <div className="flex items-center justify-between gap-3">
        <span className={`text-xs font-semibold ${style.text}`}>{style.label}</span>
        <span className={`text-sm font-bold ${style.text}`}>{percent}%</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/70">
        <div
          className={`h-full rounded-full transition-all ${style.bar}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
