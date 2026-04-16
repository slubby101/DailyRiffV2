"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

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

function useChildren() {
  return useQuery<ParentDashboardData>({
    queryKey: ["parent", "children"],
    queryFn: () => apiFetch("/parent/children"),
  });
}

function PermissionBadge({ label, enabled }: { label: string; enabled: boolean }) {
  return (
    <Badge variant={enabled ? "default" : "secondary"}>
      {label}: {enabled ? "Yes" : "No"}
    </Badge>
  );
}

function CoppaDeletionDialog({ childId, studioId }: { childId: string; studioId: string }) {
  const queryClient = useQueryClient();
  const [confirmText, setConfirmText] = useState("");
  const [open, setOpen] = useState(false);

  const initiateDeletion = useMutation({
    mutationFn: () =>
      apiFetch("/coppa/deletion/initiate", {
        method: "POST",
        body: JSON.stringify({ child_id: childId, studio_id: studioId }),
      }),
    onSuccess: () => {
      setOpen(false);
      setConfirmText("");
      queryClient.invalidateQueries({ queryKey: ["parent", "children"] });
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="destructive" size="sm">
          Request Data Deletion
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Request Child Data Deletion</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <p className="text-muted-foreground text-sm">
            This will initiate a 15-day deletion grace period. You can cancel
            at any time before the deletion is finalized. All of your child&apos;s
            data including recordings, assignments, and messages will be
            permanently deleted.
          </p>
          <div>
            <label htmlFor="delete-confirm" className="text-sm font-medium">
              Type DELETE to confirm
            </label>
            <Input
              id="delete-confirm"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="DELETE"
              className="mt-1"
            />
          </div>
          <Button
            variant="destructive"
            disabled={confirmText !== "DELETE" || initiateDeletion.isPending}
            onClick={() => initiateDeletion.mutate()}
            className="w-full"
          >
            {initiateDeletion.isPending ? "Requesting..." : "Confirm Deletion Request"}
          </Button>
          {initiateDeletion.error && (
            <p className="text-destructive text-sm" role="alert">
              Failed to initiate deletion. Please try again.
            </p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function ParentChildrenPage() {
  const children = useChildren();

  if (children.isLoading) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-muted-foreground">Loading children...</p>
      </div>
    );
  }

  if (children.error) {
    return (
      <div className="mx-auto max-w-4xl p-6">
        <p className="text-destructive" role="alert">
          Failed to load children.
        </p>
      </div>
    );
  }

  const data = children.data!;

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-8">
        <h1 className="font-display text-[40px] leading-[48px] font-semibold tracking-tight">
          My Children
        </h1>
        <p className="text-muted-foreground mt-2">
          Manage your children and view their permission settings.
        </p>
      </div>

      {data.children.length === 0 ? (
        <p className="text-muted-foreground">
          No children linked to your account yet.
        </p>
      ) : (
        <ul className="space-y-4">
          {data.children.map((child) => (
            <li key={child.parent_child_id}>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>{child.email ?? "Student"}</span>
                    <span className="text-muted-foreground text-sm font-normal">
                      {child.studio_name}
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div>
                      <p className="text-muted-foreground mb-2 text-sm font-medium">
                        Permissions
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <PermissionBadge
                          label="Primary Contact"
                          enabled={child.permissions.is_primary_contact}
                        />
                        <PermissionBadge
                          label="View Progress"
                          enabled={child.permissions.can_view_progress}
                        />
                        <PermissionBadge
                          label="Manage Payments"
                          enabled={child.permissions.can_manage_payments}
                        />
                        <PermissionBadge
                          label="Message Teacher"
                          enabled={child.permissions.can_communicate_with_teacher}
                        />
                      </div>
                    </div>
                    <p className="text-muted-foreground text-xs">
                      Permission changes are managed by your studio teacher.
                    </p>
                    <div className="border-destructive/50 mt-3 border-t pt-3">
                      <CoppaDeletionDialog
                        childId={child.child_user_id}
                        studioId={child.studio_id}
                      />
                    </div>
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
