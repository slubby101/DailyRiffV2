"use client";

import { useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { AccountConversionDialog } from "@/components/account-conversion-dialog";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface ParentChildPermissions {
  id: string;
  parent_id: string;
  parent_user_id: string;
  child_user_id: string;
  is_primary_contact: boolean;
  can_manage_payments: boolean;
  can_view_progress: boolean;
  can_communicate_with_teacher: boolean;
  created_at: string;
}

interface ParentInfo {
  parent_id: string;
  user_id: string;
  children: ParentChildPermissions[];
}

interface LoanResponse {
  id: string;
  studio_id: string;
  student_user_id: string;
  item_name: string;
  description: string | null;
  loaned_at: string;
  returned_at: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

interface StudentDetail {
  user_id: string;
  email: string | null;
  role: string;
  joined_at: string;
  parents: ParentInfo[];
  loans: LoanResponse[];
}

function useStudentDetail(studioId: string, userId: string) {
  return useQuery<StudentDetail>({
    queryKey: ["teacher", "student", studioId, userId],
    queryFn: () => apiFetch(`/studios/${studioId}/students/${userId}`),
    enabled: !!studioId && !!userId,
  });
}

function PermissionToggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-border"
        aria-label={label}
      />
      <span className="text-sm">{label}</span>
    </label>
  );
}

function GuardianDetailDialog({
  parent,
  studioId,
}: {
  parent: ParentInfo;
  studioId: string;
}) {
  const queryClient = useQueryClient();

  const updatePermissions = useMutation({
    mutationFn: (args: {
      pcId: string;
      data: Partial<ParentChildPermissions>;
    }) =>
      apiFetch(`/studios/${studioId}/parent-children/${args.pcId}`, {
        method: "PATCH",
        body: JSON.stringify(args.data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teacher", "student"] });
    },
  });

  return (
    <Dialog>
      <DialogTrigger asChild>
        <button
          className="text-primary underline text-sm"
          type="button"
          aria-label={`View guardian ${parent.user_id}`}
        >
          View Guardian
        </button>
      </DialogTrigger>
      <DialogContent aria-describedby={undefined}>
        <DialogHeader>
          <DialogTitle>Guardian Details</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            User ID: {parent.user_id}
          </p>

          {parent.children.map((pc) => (
            <div key={pc.id} className="border rounded-lg p-4 space-y-2">
              <p className="text-sm font-medium">
                Child: {pc.child_user_id}
              </p>
              <div className="space-y-1">
                <PermissionToggle
                  label="Primary contact"
                  checked={pc.is_primary_contact}
                  onChange={(v) =>
                    updatePermissions.mutate({
                      pcId: pc.id,
                      data: { is_primary_contact: v },
                    })
                  }
                />
                <PermissionToggle
                  label="Can manage payments"
                  checked={pc.can_manage_payments}
                  onChange={(v) =>
                    updatePermissions.mutate({
                      pcId: pc.id,
                      data: { can_manage_payments: v },
                    })
                  }
                />
                <PermissionToggle
                  label="Can view progress"
                  checked={pc.can_view_progress}
                  onChange={(v) =>
                    updatePermissions.mutate({
                      pcId: pc.id,
                      data: { can_view_progress: v },
                    })
                  }
                />
                <PermissionToggle
                  label="Can communicate with teacher"
                  checked={pc.can_communicate_with_teacher}
                  onChange={(v) =>
                    updatePermissions.mutate({
                      pcId: pc.id,
                      data: { can_communicate_with_teacher: v },
                    })
                  }
                />
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function LoanWidget({
  loans,
  studioId,
  studentUserId,
}: {
  loans: LoanResponse[];
  studioId: string;
  studentUserId: string;
}) {
  const queryClient = useQueryClient();
  const [newItem, setNewItem] = useState("");
  const [newDesc, setNewDesc] = useState("");

  const createLoan = useMutation({
    mutationFn: (data: {
      studio_id: string;
      student_user_id: string;
      item_name: string;
      description?: string;
    }) =>
      apiFetch(`/studios/${studioId}/loans`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teacher", "student"] });
      setNewItem("");
      setNewDesc("");
    },
  });

  const markReturned = useMutation({
    mutationFn: (loanId: string) =>
      apiFetch(`/studios/${studioId}/loans/${loanId}`, {
        method: "PATCH",
        body: JSON.stringify({ returned_at: new Date().toISOString() }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teacher", "student"] });
    },
  });

  const deleteLoan = useMutation({
    mutationFn: (loanId: string) =>
      apiFetch(`/studios/${studioId}/loans/${loanId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["teacher", "student"] });
    },
  });

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Loans</h3>

      {loans.length === 0 && (
        <p className="text-muted-foreground text-sm">No active loans.</p>
      )}

      {loans.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Item</TableHead>
              <TableHead>Loaned</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>
                <span className="sr-only">Actions</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loans.map((loan) => (
              <TableRow key={loan.id}>
                <TableCell>
                  <div>
                    <span className="font-medium">{loan.item_name}</span>
                    {loan.description && (
                      <p className="text-muted-foreground text-xs">
                        {loan.description}
                      </p>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  {new Date(loan.loaned_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  {loan.returned_at ? (
                    <Badge variant="secondary">Returned</Badge>
                  ) : (
                    <Badge>Active</Badge>
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex gap-2">
                    {!loan.returned_at && (
                      <button
                        type="button"
                        className="text-primary underline text-sm"
                        onClick={() => markReturned.mutate(loan.id)}
                      >
                        Mark Returned
                      </button>
                    )}
                    <button
                      type="button"
                      className="text-destructive underline text-sm"
                      onClick={() => deleteLoan.mutate(loan.id)}
                    >
                      Delete
                    </button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <div className="border rounded-lg p-4 space-y-3">
        <h4 className="text-sm font-medium">Add Loan</h4>
        <Input
          placeholder="Item name (e.g. Violin #3)"
          value={newItem}
          onChange={(e) => setNewItem(e.target.value)}
          aria-label="Loan item name"
        />
        <Input
          placeholder="Description (optional)"
          value={newDesc}
          onChange={(e) => setNewDesc(e.target.value)}
          aria-label="Loan description"
        />
        <button
          type="button"
          className="bg-primary text-primary-foreground px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50"
          disabled={!newItem.trim() || createLoan.isPending}
          onClick={() =>
            createLoan.mutate({
              studio_id: studioId,
              student_user_id: studentUserId,
              item_name: newItem.trim(),
              description: newDesc.trim() || undefined,
            })
          }
        >
          {createLoan.isPending ? "Adding..." : "Add Loan"}
        </button>
      </div>
    </div>
  );
}

export default function TeacherStudentDetailPage() {
  const params = useParams<{ userId: string }>();
  const searchParams = useSearchParams();
  const studioId = searchParams.get("studio_id") ?? "";
  const userId = params.userId;

  const detail = useStudentDetail(studioId, userId);

  if (detail.isLoading) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-muted-foreground">Loading student details...</p>
      </div>
    );
  }

  if (detail.error) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-destructive" role="alert">
          Failed to load student details.
        </p>
      </div>
    );
  }

  if (!detail.data) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-muted-foreground">Student not found.</p>
      </div>
    );
  }

  const student = detail.data;

  return (
    <div className="mx-auto max-w-4xl p-6 space-y-8">
      <div>
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Student Detail
        </h1>
        <p className="text-muted-foreground mt-1">
          {student.email ?? "No email"}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="border rounded-lg p-4">
          <p className="text-sm text-muted-foreground">Email</p>
          <p className="font-medium">{student.email ?? "—"}</p>
        </div>
        <div className="border rounded-lg p-4">
          <p className="text-sm text-muted-foreground">Joined</p>
          <p className="font-medium">
            {new Date(student.joined_at).toLocaleDateString()}
          </p>
        </div>
      </div>

      {/* Account Conversion */}
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-semibold">Account Type</h2>
        <AccountConversionDialog
          studioId={studioId}
          childUserId={student.user_id}
        />
      </div>

      {/* Parents / Guardians */}
      <div>
        <h2 className="text-xl font-semibold mb-3">Parents / Guardians</h2>
        {student.parents.length === 0 && (
          <p className="text-muted-foreground text-sm">
            No parents linked to this student.
          </p>
        )}
        <div className="space-y-2">
          {student.parents.map((parent) => (
            <div
              key={parent.parent_id}
              className="border rounded-lg p-4 flex items-center justify-between"
            >
              <p className="text-sm">Parent: {parent.user_id}</p>
              <GuardianDetailDialog parent={parent} studioId={studioId} />
            </div>
          ))}
        </div>
      </div>

      {/* Loans */}
      <LoanWidget
        loans={student.loans}
        studioId={studioId}
        studentUserId={student.user_id}
      />
    </div>
  );
}
