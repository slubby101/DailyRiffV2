"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface StreakData {
  current_streak: number;
  longest_streak: number;
  is_active: boolean;
  total_practice_days: number;
  weekly_minutes: number;
}

interface AssignmentSummary {
  id: string;
  title: string;
  due_date: string | null;
  status: string;
  created_at: string;
}

interface RecordingItem {
  id: string;
  assignment_id: string | null;
  duration_seconds: number;
  uploaded_at: string | null;
  created_at: string;
}

interface DashboardData {
  streak: StreakData;
  upcoming_assignments: AssignmentSummary[];
  recent_recordings: RecordingItem[];
}

function formatMinutes(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}

function useDashboard() {
  return useQuery<DashboardData>({
    queryKey: ["student", "dashboard"],
    queryFn: () => apiFetch("/student/dashboard"),
  });
}

export default function StudentDashboardPage() {
  const dashboard = useDashboard();

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
          My Practice
        </h1>
        <p className="text-muted-foreground mt-2">
          Track your progress and keep your streak alive.
        </p>
      </div>

      {/* Streak + Weekly Minutes Hero */}
      <div className="mb-8 grid gap-4 sm:grid-cols-2">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-8">
            <span
              className="font-display text-[64px] leading-[72px] font-bold tracking-tight tabular-nums"
              aria-label={`Current streak: ${data.streak.current_streak} days`}
            >
              {data.streak.current_streak}
            </span>
            <span className="text-muted-foreground mt-1 text-sm font-medium uppercase tracking-wider">
              Day Streak {data.streak.is_active ? "🔥" : ""}
            </span>
            <span className="text-muted-foreground mt-2 text-xs">
              Longest: {data.streak.longest_streak} days
            </span>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex flex-col items-center justify-center py-8">
            <span
              className="font-display text-[48px] leading-[56px] font-bold tracking-tight tabular-nums"
              aria-label={`${data.streak.weekly_minutes} minutes this week`}
            >
              {data.streak.weekly_minutes}
            </span>
            <span className="text-muted-foreground mt-1 text-sm font-medium uppercase tracking-wider">
              Minutes This Week
            </span>
            <span className="text-muted-foreground mt-2 text-xs">
              {data.streak.total_practice_days} total practice days
            </span>
          </CardContent>
        </Card>
      </div>

      {/* Upcoming Assignments */}
      <section className="mb-8" aria-labelledby="assignments-heading">
        <div className="mb-4 flex items-center justify-between">
          <h2
            id="assignments-heading"
            className="text-xl font-semibold"
          >
            Upcoming Assignments
          </h2>
          <Link
            href="/student/assignments"
            className="text-primary text-sm underline"
          >
            View all
          </Link>
        </div>

        {data.upcoming_assignments.length === 0 ? (
          <p className="text-muted-foreground">No upcoming assignments.</p>
        ) : (
          <ul className="space-y-3" role="list">
            {data.upcoming_assignments.map((a) => (
              <li key={a.id}>
                <Card>
                  <CardContent className="flex items-center justify-between py-4">
                    <div>
                      <p className="font-medium">{a.title}</p>
                      {a.due_date && (
                        <p className="text-muted-foreground text-sm">
                          Due {new Date(a.due_date).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                    <span className="text-muted-foreground rounded-md border px-2 py-1 text-xs capitalize">
                      {a.status}
                    </span>
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Recent Recordings */}
      <section aria-labelledby="recordings-heading">
        <div className="mb-4 flex items-center justify-between">
          <h2
            id="recordings-heading"
            className="text-xl font-semibold"
          >
            Recent Recordings
          </h2>
          <Link
            href="/student/recordings"
            className="text-primary text-sm underline"
          >
            View all
          </Link>
        </div>

        {data.recent_recordings.length === 0 ? (
          <p className="text-muted-foreground">No recordings yet.</p>
        ) : (
          <ul className="space-y-3" role="list">
            {data.recent_recordings.map((r) => (
              <li key={r.id}>
                <Card>
                  <CardContent className="flex items-center justify-between py-4">
                    <div>
                      <p className="font-medium">
                        {formatMinutes(r.duration_seconds)} practice
                      </p>
                      {r.uploaded_at && (
                        <p className="text-muted-foreground text-sm">
                          {new Date(r.uploaded_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                    {r.assignment_id && (
                      <span className="text-muted-foreground text-xs">
                        Assignment linked
                      </span>
                    )}
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
