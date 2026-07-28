interface ErrorField {
  field: string;
  message: string;
}

interface ErrorStateProps {
  message: string;
  code?: string;
  requestId?: string;
  fields?: ErrorField[];
}

export default function ErrorState({ message, code, requestId, fields }: ErrorStateProps) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-error" role="alert">
      <div>{message}</div>
      {fields?.length ? <ul className="mt-2 list-disc space-y-1 pl-5">{fields.map((field, index) => <li key={`${field.field}-${index}`}>{field.message}</li>)}</ul> : null}
      {code || requestId ? <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-red-700">{code ? <span>Code: {code}</span> : null}{requestId ? <span>Reference: {requestId}</span> : null}</div> : null}
    </div>
  );
}
