export default function ErrorState({ message }: { message: string }) {
  return (
    <div className="break-words whitespace-pre-wrap rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-error" role="alert">
      {message}
    </div>
  );
}
