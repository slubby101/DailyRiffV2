"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

interface StudentListItem {
  user_id: string;
  email: string | null;
  role: string;
  joined_at: string;
}

function useStudents(studioId: string, search: string) {
  const params = new URLSearchParams();
  if (search) params.set("search", search);
  const qs = params.toString();
  return useQuery<StudentListItem[]>({
    queryKey: ["teacher", "students", studioId, search],
    queryFn: () =>
      apiFetch(`/studios/${studioId}/students${qs ? `?${qs}` : ""}`),
    enabled: !!studioId,
  });
}

export default function TeacherStudentsPage() {
  const [search, setSearch] = useState("");
  // Studio ID would come from auth context/session in production.
  // For now, use a query param or default.
  const studioId =
    typeof window !== "undefined"
      ? new URLSearchParams(window.location.search).get("studio_id") ?? ""
      : "";

  const students = useStudents(studioId, search);

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-6">
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Students
        </h1>
        <p className="text-muted-foreground mt-2">
          View and manage your studio&apos;s students.
        </p>
      </div>

      <div className="mb-4">
        <Input
          placeholder="Search by email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search students"
        />
      </div>

      {students.isLoading && (
        <p className="text-muted-foreground">Loading students...</p>
      )}

      {students.error && (
        <p className="text-destructive" role="alert">
          Failed to load students.
        </p>
      )}

      {students.data && students.data.length === 0 && (
        <p className="text-muted-foreground">No students found.</p>
      )}

      {students.data && students.data.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Email</TableHead>
              <TableHead>Joined</TableHead>
              <TableHead>
                <span className="sr-only">Actions</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {students.data.map((s) => (
              <TableRow key={s.user_id}>
                <TableCell>{s.email ?? "—"}</TableCell>
                <TableCell>
                  {new Date(s.joined_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <Link
                    href={`/teacher/students/${s.user_id}?studio_id=${studioId}`}
                    className="text-primary underline"
                  >
                    View
                  </Link>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
