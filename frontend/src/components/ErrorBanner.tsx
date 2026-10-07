// components/ErrorBanner.tsx : a red message box for errors (role="alert" so screen readers announce it).
// Used by: every view and form. Renders nothing when there is no message.
export function ErrorBanner({ message }: { message: string | null | undefined }) {
  if (!message) return null;
  return <div className="banner banner--error" role="alert">{message}</div>;
}
