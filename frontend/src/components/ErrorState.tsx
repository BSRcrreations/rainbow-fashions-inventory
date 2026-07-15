export default function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
      {message}
    </div>
  );
}
