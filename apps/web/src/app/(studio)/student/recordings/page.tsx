"use client";

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

function formatMinutes(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}

function useStudentRecordings() {
  return useQuery<RecordingItem[]>({
    queryKey: ["student", "recordings"],
    queryFn: () => apiFetch("/student/recordings"),
  });
}

export default function StudentRecordingHistoryPage() {
  const recordings = useStudentRecordings();

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-6">
        <h1 className="font-display text-[40px] leading-[48px] font-semibold tracking-tight">
          Recording History
        </h1>
        <p className="text-muted-foreground mt-2">
          Your practice recordings, most recent first.
        </p>
      </div>

      {recordings.isLoading && (
        <p className="text-muted-foreground">Loading recordings...</p>
      )}

      {recordings.error && (
        <p className="text-destructive" role="alert">
          Failed to load recordings.
        </p>
      )}

      {recordings.data && recordings.data.length === 0 && (
        <p className="text-muted-foreground">
          No recordings yet. Start practicing to see your history here.
        </p>
      )}

      {recordings.data && recordings.data.length > 0 && (
        <ul className="space-y-3" role="list">
          {recordings.data.map((r) => (
            <li key={r.id}>
              <Card>
                <CardContent className="flex items-center justify-between py-4">
                  <div>
                    <p className="font-medium">
                      {formatMinutes(r.duration_seconds)} practice session
                    </p>
                    {r.uploaded_at && (
                      <p className="text-muted-foreground text-sm">
                        {new Date(r.uploaded_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                  {r.assignment_id ? (
                    <span className="text-muted-foreground rounded-md border px-2 py-1 text-xs">
                      Assignment linked
                    </span>
                  ) : (
                    <span className="text-muted-foreground rounded-md border px-2 py-1 text-xs">
                      Free practice
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
