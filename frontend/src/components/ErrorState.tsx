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
    <div className="break-words whitespace-pre-wrap rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-error" role="alert">
      <div>{message}</div>
      {fields?.length ? <ul className="mt-2 list-disc space-y-1 pl-5">{fields.map((field, index) => <li key={`${field.field}-${index}`}>{field.message}</li>)}</ul> : null}
      {code || requestId ? <details className="mt-3 text-sm text-red-800"><summary className="cursor-pointer font-semibold">Details for support</summary><div className="mt-2">{code ? <div>Code: {code}</div> : null}{requestId ? <div>Reference: {requestId}</div> : null}</div></details> : null}
    </div>
  );
}
