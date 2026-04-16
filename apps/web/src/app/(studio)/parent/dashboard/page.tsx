"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";

interface ChildPermissions {
  is_primary_contact: boolean;
  can_manage_payments: boolean;
  can_view_progress: boolean;
  can_communicate_with_teacher: boolean;
}

interface ChildSummary {
  child_user_id: string;
  email: string | null;
  studio_id: string;
  studio_name: string;
  parent_child_id: string;
  permissions: ChildPermissions;
  next_lesson_date: string | null;
  latest_assignment_title: string | null;
  current_streak: number;
}

interface ParentDashboardData {
  children: ChildSummary[];
}

function useParentDashboard() {
  return useQuery<ParentDashboardData>({
    queryKey: ["parent", "children"],
    queryFn: () => apiFetch("/parent/children"),
  });
}

export default function ParentDashboardPage() {
  const dashboard = useParentDashboard();

  if (dashboard.isLoading) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-muted-foreground">Loading dashboard...</p>
      </div>
    );
  }

  if (dashboard.error) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-destructive" role="alert">
          Failed to load dashboard.
        </p>
      </div>
    );
  }

  const data = dashboard.data!;

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-8">
        <h1 className="font-display text-[40px] leading-[48px] font-semibold tracking-tight">
          My Children
        </h1>
        <p className="text-muted-foreground mt-2">
          Overview of your children&apos;s music progress.
        </p>
      </div>

      {data.children.length === 0 ? (
        <p className="text-muted-foreground">
          No children linked to your account yet.
        </p>
      ) : (
        <ul className="space-y-4" role="list">
          {data.children.map((child) => (
            <li key={child.parent_child_id}>
              <Card>
                <CardContent className="py-6">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-lg font-semibold">
                        {child.email ?? "Student"}
                      </p>
                      <p className="text-muted-foreground text-sm">
                        {child.studio_name}
                      </p>
                    </div>
                    {child.permissions.can_view_progress && child.current_streak > 0 && (
                      <span
                        className="font-display text-2xl font-bold tabular-nums"
                        aria-label={`${child.current_streak} day streak`}
                      >
                        {child.current_streak} day streak
                      </span>
                    )}
                  </div>

                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    {child.next_lesson_date && (
                      <div className="rounded-md border p-3">
                        <p className="text-muted-foreground text-xs font-medium uppercase tracking-wider">
                          Next Lesson
                        </p>
                        <p className="mt-1 font-medium">
                          {new Date(child.next_lesson_date).toLocaleDateString()}
                        </p>
                      </div>
                    )}
                    {child.latest_assignment_title && (
                      <div className="rounded-md border p-3">
                        <p className="text-muted-foreground text-xs font-medium uppercase tracking-wider">
                          Latest Assignment
                        </p>
                        <p className="mt-1 font-medium">
                          {child.latest_assignment_title}
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <Link
                      href={`/parent/schedule?child=${child.child_user_id}`}
                      className="text-primary text-sm underline"
                    >
                      Schedule
                    </Link>
                    {child.permissions.can_view_progress && (
                      <Link
                        href={`/parent/progress?child=${child.child_user_id}`}
                        className="text-primary text-sm underline"
                      >
                        Progress
                      </Link>
                    )}
                    {child.permissions.can_manage_payments && (
                      <Link
                        href={`/parent/payments?child=${child.child_user_id}`}
                        className="text-primary text-sm underline"
                      >
                        Payments
                      </Link>
                    )}
                    {child.permissions.can_communicate_with_teacher && (
                      <Link
                        href="/parent/messages"
                        className="text-primary text-sm underline"
                      >
                        Messages
                      </Link>
                    )}
                  </div>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
