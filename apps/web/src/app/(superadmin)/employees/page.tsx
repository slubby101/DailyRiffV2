"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type {
  EmployeeResponse,
  EmployeeCreateRequest,
} from "@dailyriff/api-client";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

function useEmployees() {
  return useQuery<EmployeeResponse[]>({
    queryKey: ["employees"],
    queryFn: () => apiFetch("/employees"),
  });
}

export default function EmployeesPage() {
  const employees = useEmployees();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newUserId, setNewUserId] = useState("");
  const [newRole, setNewRole] = useState<"owner" | "support" | "verifier">(
    "support",
  );
  const [newNotes, setNewNotes] = useState("");

  const createMutation = useMutation({
    mutationFn: (body: EmployeeCreateRequest) =>
      apiFetch("/employees", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      setDialogOpen(false);
      setNewUserId("");
      setNewNotes("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/employees/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">
            Employees
          </h1>
          <p className="text-muted-foreground mt-2">
            Manage DailyRiff team members (owner, support, verifier).
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>Add Employee</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Employee</DialogTitle>
              <DialogDescription>
                Add a new DailyRiff team member. They must already have a
                Supabase Auth account.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div>
                <label
                  htmlFor="user-id"
                  className="text-sm font-medium mb-1.5 block"
                >
                  User ID (UUID)
                </label>
                <Input
                  id="user-id"
                  value={newUserId}
                  onChange={(e) => setNewUserId(e.target.value)}
                  placeholder="00000000-0000-0000-0000-000000000000"
                />
              </div>
              <div>
                <label
                  htmlFor="role"
                  className="text-sm font-medium mb-1.5 block"
                >
                  Role
                </label>
                <Select
                  value={newRole}
                  onValueChange={(v) =>
                    setNewRole(v as "owner" | "support" | "verifier")
                  }
                >
                  <SelectTrigger id="role">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="owner">Owner</SelectItem>
                    <SelectItem value="support">Support</SelectItem>
                    <SelectItem value="verifier">Verifier</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label
                  htmlFor="notes"
                  className="text-sm font-medium mb-1.5 block"
                >
                  Notes (optional)
                </label>
                <Textarea
                  id="notes"
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  placeholder="Optional notes about this employee"
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={() =>
                  createMutation.mutate({
                    user_id: newUserId,
                    role: newRole,
                    notes: newNotes || null,
                  })
                }
                disabled={!newUserId || createMutation.isPending}
              >
                {createMutation.isPending ? "Adding..." : "Add Employee"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {employees.isLoading ? (
        <p className="text-muted-foreground text-sm" role="status">
          Loading employees...
        </p>
      ) : (
        <div className="rounded-md border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User ID</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Notes</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(employees.data ?? []).length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={5}
                    className="text-center text-muted-foreground py-8"
                  >
                    No employees yet.
                  </TableCell>
                </TableRow>
              ) : (
                (employees.data ?? []).map((emp) => (
                  <TableRow key={emp.id}>
                    <TableCell>
                      <code className="font-mono text-xs">{emp.user_id}</code>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary">{emp.role}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {emp.notes ?? "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {new Date(emp.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteMutation.mutate(emp.id)}
                        disabled={deleteMutation.isPending}
                        className="text-destructive hover:text-destructive"
                      >
                        Remove
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
