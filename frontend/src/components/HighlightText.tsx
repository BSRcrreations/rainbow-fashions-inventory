interface HighlightTextProps {
  text?: string | null;
  query: string;
}

export default function HighlightText({ text, query }: HighlightTextProps) {
  const value = text ?? "";
  const needle = query.trim();
  if (!needle) return <>{value}</>;
  const index = value.toLowerCase().indexOf(needle.toLowerCase());
  if (index === -1) return <>{value}</>;
  return (
    <>
      {value.slice(0, index)}
      <mark className="rounded bg-amber-100 px-0.5 text-amber-900">{value.slice(index, index + needle.length)}</mark>
      {value.slice(index + needle.length)}
    </>
  );
}
