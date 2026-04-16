"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import type { EmployeeResponse } from "@dailyriff/api-client";
import { apiFetch } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { DashboardAlertBanner } from "@/components/dashboard-alert-banner";

function useEmployees() {
  return useQuery<EmployeeResponse[]>({
    queryKey: ["employees"],
    queryFn: () => apiFetch("/employees"),
  });
}

export default function UsersPage() {
  const employees = useEmployees();
  const [search, setSearch] = useState("");

  const filtered = (employees.data ?? []).filter((e) => {
    if (!search) return true;
    return (
      e.user_id.toLowerCase().includes(search.toLowerCase()) ||
      e.role.toLowerCase().includes(search.toLowerCase())
    );
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Users
        </h1>
        <p className="text-muted-foreground mt-2">
          View platform users.
        </p>
      </div>

      <DashboardAlertBanner variant="info" className="mb-6">
        Full user management requires Supabase Admin API integration (coming in a
        future slice). Currently showing DailyRiff employees as known users.
      </DashboardAlertBanner>

      <div className="mb-4">
        <Input
          placeholder="Search by user ID or role..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
          aria-label="Search users"
        />
      </div>

      {employees.isLoading ? (
        <p className="text-muted-foreground text-sm" role="status">Loading users...</p>
      ) : filtered.length === 0 ? (
        <p className="text-muted-foreground text-sm">No users found.</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((emp) => (
            <Link key={emp.id} href={`/users/${emp.user_id}`}>
              <Card className="transition-colors hover:border-primary/30">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">
                    <code className="font-mono text-xs">{emp.user_id}</code>
                  </CardTitle>
                  <CardDescription>
                    {emp.notes || "No notes"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Badge variant="secondary">{emp.role}</Badge>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
