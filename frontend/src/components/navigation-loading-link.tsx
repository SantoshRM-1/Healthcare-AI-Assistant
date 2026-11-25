"use client";

import { MouseEvent, ReactNode, useTransition } from "react";
import { useRouter } from "next/navigation";

export function NavigationLoadingLink({
  href,
  className,
  children,
  pendingLabel = "Opening…",
}: {
  href: string;
  className: string;
  children: ReactNode;
  pendingLabel?: string;
}) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  function navigate(event: MouseEvent<HTMLAnchorElement>) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (pending) return;
    startTransition(() => router.push(href));
  }

  return (
    <a href={href} className={className} onClick={navigate} aria-busy={pending}>
      {pending ? (
        <span className="inline-flex items-center justify-center gap-2" role="status">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent" aria-hidden="true" />
          {pendingLabel}
        </span>
      ) : children}
    </a>
  );
}
