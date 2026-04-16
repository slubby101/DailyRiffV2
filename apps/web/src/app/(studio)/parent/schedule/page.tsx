"use client";

import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";

interface ScheduleItem {
  lesson_id: string;
  occurrence_id: string | null;
  start_date: string;
  start_time: string | null;
  end_time: string | null;
  duration_minutes: number | null;
  teacher_email: string | null;
  status: string | null;
}

function useChildSchedule(childId: string) {
  return useQuery<ScheduleItem[]>({
    queryKey: ["parent", "children", childId, "schedule"],
    queryFn: () => apiFetch(`/parent/children/${childId}/schedule`),
    enabled: !!childId,
  });
}

export default function ParentSchedulePage() {
  const searchParams = useSearchParams();
  const childId = searchParams.get("child") ?? "";

  const schedule = useChildSchedule(childId);

  if (!childId) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-muted-foreground">
          Select a child from the dashboard to view their schedule.
        </p>
      </div>
    );
  }

  if (schedule.isLoading) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-muted-foreground">Loading schedule...</p>
      </div>
    );
  }

  if (schedule.error) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-destructive" role="alert">
          Failed to load schedule.
        </p>
      </div>
    );
  }

  const data = schedule.data!;

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-8">
        <h1 className="font-display text-[40px] leading-[48px] font-semibold tracking-tight">
          Lesson Schedule
        </h1>
        <p className="text-muted-foreground mt-2">
          Upcoming lessons for your child.
        </p>
      </div>

      {data.length === 0 ? (
        <p className="text-muted-foreground">No upcoming lessons scheduled.</p>
      ) : (
        <ul className="space-y-3" role="list">
          {data.map((item) => (
            <li key={item.occurrence_id ?? item.lesson_id}>
              <Card>
                <CardContent className="flex items-center justify-between py-4">
                  <div>
                    <p className="font-medium">
                      {new Date(item.start_date).toLocaleDateString(undefined, {
                        weekday: "long",
                        year: "numeric",
                        month: "long",
                        day: "numeric",
                      })}
                    </p>
                    <p className="text-muted-foreground text-sm">
                      {item.start_time && item.end_time
                        ? `${item.start_time} – ${item.end_time}`
                        : item.duration_minutes
                          ? `${item.duration_minutes} minutes`
                          : ""}
                      {item.teacher_email && ` · ${item.teacher_email}`}
                    </p>
                  </div>
                  {item.status && (
                    <span className="text-muted-foreground rounded-md border px-2 py-1 text-xs capitalize">
                      {item.status}
                    </span>
                  )}
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
