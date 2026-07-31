import { AppHeader } from "@/components/layout/AppHeader";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-screen flex flex-col bg-page">
      <AppHeader />
      <div className="flex-1 overflow-hidden relative">
        {children}
      </div>
    </div>
  );
}
