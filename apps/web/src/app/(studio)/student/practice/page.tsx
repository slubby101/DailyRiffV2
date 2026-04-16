"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

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

function useStudentRecordings(search: string) {
  return useQuery<RecordingItem[]>({
    queryKey: ["student", "recordings", search],
    queryFn: () => apiFetch("/student/recordings"),
  });
}

export default function StudentPracticeSessionsPage() {
  const [search, setSearch] = useState("");
  const recordings = useStudentRecordings(search);
  const queryClient = useQueryClient();

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-6">
        <h1 className="font-display text-[40px] leading-[48px] font-semibold tracking-tight">
          Practice Sessions
        </h1>
        <p className="text-muted-foreground mt-2">
          Manage and review your practice sessions.
        </p>
      </div>

      <div className="mb-4">
        <Input
          placeholder="Search recordings..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search recordings"
        />
      </div>

      {recordings.isLoading && (
        <p className="text-muted-foreground">Loading practice sessions...</p>
      )}

      {recordings.error && (
        <p className="text-destructive" role="alert">
          Failed to load practice sessions.
        </p>
      )}

      {recordings.data && recordings.data.length === 0 && (
        <p className="text-muted-foreground">
          No practice sessions yet.
        </p>
      )}

      {recordings.data && recordings.data.length > 0 && (
        <ul className="space-y-3">
          {recordings.data.map((r) => (
            <li key={r.id}>
              <Card>
                <CardContent className="flex items-center justify-between py-4">
                  <div>
                    <p className="font-medium">
                      {formatMinutes(r.duration_seconds)} session
                    </p>
                    {r.uploaded_at && (
                      <p className="text-muted-foreground text-sm">
                        {new Date(r.uploaded_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {r.assignment_id ? (
                      <span className="text-muted-foreground rounded-md border px-2 py-1 text-xs">
                        Assignment
                      </span>
                    ) : (
                      <span className="text-muted-foreground rounded-md border px-2 py-1 text-xs">
                        Free
                      </span>
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
