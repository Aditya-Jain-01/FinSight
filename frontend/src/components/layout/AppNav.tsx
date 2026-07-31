"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function AppNav() {
  const pathname = usePathname();
  
  const tabs = [
    { label: "Chat", href: "/chat" },
    { label: "Compare", href: "/compare" },
  ];

  return (
    <div className="border-b border-border bg-panel px-6 py-0 shadow-sm relative z-10">
      <div className="flex items-center gap-6 text-sm font-medium">
        {tabs.map((tab) => {
          const isActive = pathname === tab.href || pathname.startsWith(`${tab.href}/`);
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`py-3 border-b-2 transition-colors ${
                isActive
                  ? "border-accent text-accent"
                  : "border-transparent text-text-secondary hover:text-text-primary hover:border-border-strong"
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
