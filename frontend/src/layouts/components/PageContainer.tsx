import { ReactNode } from "react";

export function PageContainer({ children }: { children: ReactNode }) {
  return (
    <div className="max-w-[1600px] mx-auto px-6 py-5 space-y-5">
      {children}
    </div>
  );
}