"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";

interface RecordingItem {
  id: string;
  assignment_id: string | null;
  duration_seconds: number;
  uploaded_at: string | null;
  created_at: string;
}

interface ProgressData {
  child_user_id: string;
  current_streak: number;
  longest_streak: number;
  is_active: boolean;
  total_practice_days: number;
  weekly_minutes: number;
  total_assignments: number;
  completed_assignments: number;
  recent_recordings: RecordingItem[];
}

function useChildProgress(childId: string) {
  return useQuery<ProgressData>({
    queryKey: ["parent", "children", childId, "progress"],
    queryFn: () => apiFetch(`/parent/children/${childId}/progress`),
    enabled: !!childId,
  });
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}

export default function ParentProgressPage() {
  return (
    <Suspense fallback={<div className="p-6 text-muted-foreground">Loading...</div>}>
      <ParentProgressContent />
    </Suspense>
  );
}

function ParentProgressContent() {
  const searchParams = useSearchParams();
  const childId = searchParams.get("child") ?? "";

  const progress = useChildProgress(childId);

  if (!childId) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-muted-foreground">
          Select a child from the dashboard to view their progress.
        </p>
      </div>
    );
  }

  if (progress.isLoading) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-muted-foreground">Loading progress...</p>
      </div>
    );
  }

  if (progress.error) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-destructive" role="alert">
          Failed to load progress. You may not have permission to view this child&apos;s progress.
        </p>
      </div>
    );
  }

  const data = progress.data!;
  const completionRate =
    data.total_assignments > 0
      ? Math.round((data.completed_assignments / data.total_assignments) * 100)
      : 0;

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-8">
        <h1 className="font-display text-[40px] leading-[48px] font-semibold tracking-tight">
          Practice Progress
        </h1>
        <p className="text-muted-foreground mt-2">
          Track your child&apos;s practice streaks, assignment completion, and recordings.
        </p>
      </div>

      {/* Streak + Stats */}
      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-8">
            <span
              className="font-display text-[48px] leading-[56px] font-bold tracking-tight tabular-nums"
              aria-label={`Current streak: ${data.current_streak} days`}
            >
              {data.current_streak}
            </span>
            <span className="text-muted-foreground mt-1 text-sm font-medium uppercase tracking-wider">
              Day Streak {data.is_active ? "🔥" : ""}
            </span>
            <span className="text-muted-foreground mt-2 text-xs">
              Longest: {data.longest_streak} days
            </span>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex flex-col items-center justify-center py-8">
            <span
              className="font-display text-[48px] leading-[56px] font-bold tracking-tight tabular-nums"
              aria-label={`${data.weekly_minutes} minutes this week`}
            >
              {data.weekly_minutes}
            </span>
            <span className="text-muted-foreground mt-1 text-sm font-medium uppercase tracking-wider">
              Minutes This Week
            </span>
            <span className="text-muted-foreground mt-2 text-xs">
              {data.total_practice_days} total practice days
            </span>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex flex-col items-center justify-center py-8">
            <span
              className="font-display text-[48px] leading-[56px] font-bold tracking-tight tabular-nums"
              aria-label={`${completionRate}% assignment completion rate`}
            >
              {completionRate}%
            </span>
            <span className="text-muted-foreground mt-1 text-sm font-medium uppercase tracking-wider">
              Completion Rate
            </span>
            <span className="text-muted-foreground mt-2 text-xs">
              {data.completed_assignments} of {data.total_assignments} assignments
            </span>
          </CardContent>
        </Card>
      </div>

      {/* Recent Recordings */}
      <section aria-labelledby="recordings-heading">
        <h2 id="recordings-heading" className="mb-4 text-xl font-semibold">
          Recent Recordings
        </h2>

        {data.recent_recordings.length === 0 ? (
          <p className="text-muted-foreground">No recordings yet.</p>
        ) : (
          <ul className="space-y-3">
            {data.recent_recordings.map((r) => (
              <li key={r.id}>
                <Card>
                  <CardContent className="flex items-center justify-between py-4">
                    <div>
                      <p className="font-medium">
                        {formatDuration(r.duration_seconds)} practice
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
