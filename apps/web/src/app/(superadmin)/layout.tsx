"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Building2,
  Users,
  UserCog,
  Settings,
  ClipboardCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/studios", label: "Studios", icon: Building2 },
  { href: "/users", label: "Users", icon: Users },
  { href: "/employees", label: "Employees", icon: UserCog },
  { href: "/settings", label: "Settings", icon: Settings },
  {
    href: "/verification-queue",
    label: "Verification Queue",
    icon: ClipboardCheck,
  },
] as const;

export default function SuperadminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border bg-sidebar flex flex-col">
        <div className="p-6">
          <h1 className="font-display text-xl font-semibold text-sidebar-foreground">
            DailyRiff
          </h1>
          <p className="text-xs text-sidebar-foreground/60 mt-1">
            Superadmin
          </p>
        </div>
        <Separator />
        <nav aria-label="Superadmin navigation" className="flex-1 p-3">
          <ul className="space-y-1">
            {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
              const active = pathname === href || pathname.startsWith(href + "/");
              return (
                <li key={href}>
                  <Link
                    href={href}
                    className={cn(
                      "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                      "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                      active
                        ? "bg-sidebar-accent text-sidebar-accent-foreground"
                        : "text-sidebar-foreground/70 hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
                    )}
                    aria-current={active ? "page" : undefined}
                  >
                    <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-6xl px-6 py-8">
          {children}
        </div>
      </main>
    </div>
  );
}
