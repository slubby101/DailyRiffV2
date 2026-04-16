"use client";

import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";

interface AssignmentSummary {
  id: string;
  title: string;
  due_date: string | null;
  status: string;
  created_at: string;
}

function useStudentAssignments() {
  return useQuery<AssignmentSummary[]>({
    queryKey: ["student", "assignments"],
    queryFn: () => apiFetch("/student/assignments"),
  });
}

export default function StudentAssignmentsPage() {
  const assignments = useStudentAssignments();

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-6">
        <h1 className="font-display text-[40px] leading-[48px] font-semibold tracking-tight">
          My Assignments
        </h1>
        <p className="text-muted-foreground mt-2">
          View and track your assigned practice.
        </p>
      </div>

      {assignments.isLoading && (
        <p className="text-muted-foreground">Loading assignments...</p>
      )}

      {assignments.error && (
        <p className="text-destructive" role="alert">
          Failed to load assignments.
        </p>
      )}

      {assignments.data && assignments.data.length === 0 && (
        <p className="text-muted-foreground">
          No assignments yet. Your teacher will assign practice soon.
        </p>
      )}

      {assignments.data && assignments.data.length > 0 && (
        <ul className="space-y-3">
          {assignments.data.map((a) => (
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
                    <p className="text-muted-foreground text-xs">
                      Assigned{" "}
                      {new Date(a.created_at).toLocaleDateString()}
                    </p>
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
    </div>
  );
}
