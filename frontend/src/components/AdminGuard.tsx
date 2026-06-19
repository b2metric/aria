"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState, ReactNode } from "react";

export function AdminGuard({ children }: { children: ReactNode }) {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [isAuthorized, setIsAuthorized] = useState(false);

  useEffect(() => {
    if (status === "loading") return;

    const anySession = session as any;
    const roles = anySession?.user?.roles || [];

    if (!session || !roles.includes("admin")) {
      router.replace("/");
    } else {
      void (async () => { setIsAuthorized(true); })();
    }
  }, [session, status, router]);

  if (status === "loading" || !isAuthorized) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return <>{children}</>;
}
