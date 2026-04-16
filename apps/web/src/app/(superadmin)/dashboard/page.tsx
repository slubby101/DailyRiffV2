"use client";

import { useQuery } from "@tanstack/react-query";
import type {
  StudioResponse,
  EmployeeResponse,
  SettingResponse,
} from "@dailyriff/api-client";
import { apiFetch } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Building2, UserCog, Settings, ClipboardCheck } from "lucide-react";

function useAdminStudios() {
  return useQuery<StudioResponse[]>({
    queryKey: ["admin", "studios"],
    queryFn: () => apiFetch("/admin/studios"),
  });
}

function useEmployees() {
  return useQuery<EmployeeResponse[]>({
    queryKey: ["employees"],
    queryFn: () => apiFetch("/employees"),
  });
}

function useSettings() {
  return useQuery<SettingResponse[]>({
    queryKey: ["settings"],
    queryFn: () => apiFetch("/settings"),
  });
}

function usePendingStudios() {
  return useQuery<StudioResponse[]>({
    queryKey: ["admin", "verification-queue"],
    queryFn: () => apiFetch("/admin/verification-queue"),
  });
}

export default function SuperadminDashboard() {
  const studios = useAdminStudios();
  const employees = useEmployees();
  const settings = useSettings();
  const pending = usePendingStudios();

  const cards = [
    {
      title: "Studios",
      icon: Building2,
      value: studios.data?.length ?? "...",
      description: "Total registered studios",
      href: "/studios",
    },
    {
      title: "Pending Verification",
      icon: ClipboardCheck,
      value: pending.data?.length ?? "...",
      description: "Studios awaiting review",
      href: "/verification-queue",
    },
    {
      title: "Employees",
      icon: UserCog,
      value: employees.data?.length ?? "...",
      description: "DailyRiff team members",
      href: "/employees",
    },
    {
      title: "Settings",
      icon: Settings,
      value: settings.data?.length ?? "...",
      description: "Platform settings configured",
      href: "/settings",
    },
  ];

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Dashboard
        </h1>
        <p className="text-muted-foreground mt-2">
          Platform overview and quick actions.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => (
          <a key={card.title} href={card.href}>
            <Card className="transition-colors hover:border-primary/30">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardDescription>{card.title}</CardDescription>
                <card.icon
                  className="h-4 w-4 text-muted-foreground"
                  aria-hidden="true"
                />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{card.value}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {card.description}
                </p>
              </CardContent>
            </Card>
          </a>
        ))}
      </div>

      {/* Recent activity */}
      <div className="mt-8">
        <h2 className="font-display text-xl font-semibold mb-4">
          Recent Studios
        </h2>
        {studios.isLoading ? (
          <p className="text-muted-foreground text-sm">Loading...</p>
        ) : studios.data && studios.data.length > 0 ? (
          <div className="space-y-2">
            {studios.data.slice(0, 5).map((studio) => (
              <div
                key={studio.id}
                className="flex items-center justify-between rounded-md border border-border p-3"
              >
                <div>
                  <p className="text-sm font-medium">
                    {studio.display_name || studio.name}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {studio.timezone}
                  </p>
                </div>
                <Badge
                  variant={
                    studio.state === "active"
                      ? "default"
                      : studio.state === "suspended"
                        ? "destructive"
                        : "secondary"
                  }
                >
                  {studio.state}
                </Badge>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-muted-foreground text-sm">No studios yet.</p>
        )}
      </div>
    </div>
  );
}
