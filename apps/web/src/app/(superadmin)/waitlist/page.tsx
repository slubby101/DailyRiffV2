"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface WaitlistEntry {
  id: string;
  email: string;
  name: string;
  studio_name: string | null;
  status: "pending" | "approved" | "rejected" | "invited";
  ip_address: string | null;
  bypass_token: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  studio_id: string | null;
  created_at: string;
  updated_at: string;
}

interface WaitlistMessage {
  id: string;
  waitlist_entry_id: string;
  sender_id: string;
  body: string;
  created_at: string;
}

const STATUS_COLORS: Record<WaitlistEntry["status"], "default" | "secondary" | "destructive" | "outline"> = {
  pending: "secondary",
  approved: "default",
  rejected: "destructive",
  invited: "outline",
};

function useWaitlist(statusFilter: string | null) {
  const params = statusFilter && statusFilter !== "all" ? `?status=${statusFilter}` : "";
  return useQuery<WaitlistEntry[]>({
    queryKey: ["admin", "waitlist", statusFilter],
    queryFn: () => apiFetch(`/admin/waitlist${params}`),
  });
}

export default function WaitlistPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedEntry, setSelectedEntry] = useState<WaitlistEntry | null>(null);
  const [messageBody, setMessageBody] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const [showBypassDialog, setShowBypassDialog] = useState(false);
  const [bypassForm, setBypassForm] = useState({ email: "", name: "", studio_name: "" });

  const queryClient = useQueryClient();
  const waitlist = useWaitlist(statusFilter);

  const approveMutation = useMutation({
    mutationFn: (entryId: string) =>
      apiFetch(`/admin/waitlist/${entryId}/approve`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "waitlist"] });
      setSelectedEntry(null);
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ entryId, reason }: { entryId: string; reason: string | null }) =>
      apiFetch(`/admin/waitlist/${entryId}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "waitlist"] });
      setSelectedEntry(null);
      setRejectReason("");
    },
  });

  const messageMutation = useMutation({
    mutationFn: ({ entryId, body }: { entryId: string; body: string }) =>
      apiFetch(`/admin/waitlist/${entryId}/messages`, {
        method: "POST",
        body: JSON.stringify({ body }),
      }),
    onSuccess: () => {
      setMessageBody("");
      queryClient.invalidateQueries({ queryKey: ["admin", "waitlist", "messages"] });
    },
  });

  const bypassMutation = useMutation({
    mutationFn: (data: { email: string; name: string; studio_name?: string }) =>
      apiFetch<WaitlistEntry>("/admin/waitlist/bypass", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "waitlist"] });
      setShowBypassDialog(false);
      setBypassForm({ email: "", name: "", studio_name: "" });
    },
  });

  const messages = useQuery<WaitlistMessage[]>({
    queryKey: ["admin", "waitlist", "messages", selectedEntry?.id],
    queryFn: () => apiFetch(`/admin/waitlist/${selectedEntry!.id}/messages`),
    enabled: !!selectedEntry,
  });

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-3xl font-semibold tracking-tight">
            Waitlist
          </h1>
          <p className="text-muted-foreground mt-2">
            Manage studio interest submissions and send direct invites.
          </p>
        </div>
        <Button onClick={() => setShowBypassDialog(true)}>
          Direct Invite
        </Button>
      </div>

      {/* Filter */}
      <div className="mb-4">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="rejected">Rejected</SelectItem>
            <SelectItem value="invited">Invited</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* List */}
      {waitlist.isLoading ? (
        <p className="text-muted-foreground text-sm" role="status">Loading waitlist...</p>
      ) : (waitlist.data ?? []).length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No waitlist entries found.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {(waitlist.data ?? []).map((entry) => (
            <Card key={entry.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-base">{entry.name}</CardTitle>
                    <CardDescription>
                      {entry.email}
                      {entry.studio_name && <> &middot; {entry.studio_name}</>}
                      {" "}&middot;{" "}
                      {new Date(entry.created_at).toLocaleDateString()}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={STATUS_COLORS[entry.status]}>{entry.status}</Badge>
                    {entry.bypass_token && (
                      <Badge variant="outline">bypass</Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex gap-2">
                  {entry.status === "pending" && (
                    <>
                      <Button
                        size="sm"
                        onClick={() => approveMutation.mutate(entry.id)}
                        disabled={approveMutation.isPending}
                      >
                        Approve
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => {
                          setSelectedEntry(entry);
                          setRejectReason("");
                        }}
                      >
                        Reject
                      </Button>
                    </>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedEntry(entry)}
                  >
                    Details
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Entry detail + messaging dialog */}
      <Dialog
        open={!!selectedEntry}
        onOpenChange={(open) => { if (!open) setSelectedEntry(null); }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{selectedEntry?.name}</DialogTitle>
          </DialogHeader>
          {selectedEntry && (
            <div className="space-y-4">
              <dl className="grid grid-cols-2 gap-2 text-sm">
                <dt className="text-muted-foreground">Email</dt>
                <dd>{selectedEntry.email}</dd>
                <dt className="text-muted-foreground">Studio</dt>
                <dd>{selectedEntry.studio_name || "—"}</dd>
                <dt className="text-muted-foreground">Status</dt>
                <dd><Badge variant={STATUS_COLORS[selectedEntry.status]}>{selectedEntry.status}</Badge></dd>
                <dt className="text-muted-foreground">Applied</dt>
                <dd>{new Date(selectedEntry.created_at).toLocaleString()}</dd>
                {selectedEntry.rejection_reason && (
                  <>
                    <dt className="text-muted-foreground">Rejection reason</dt>
                    <dd>{selectedEntry.rejection_reason}</dd>
                  </>
                )}
              </dl>

              {/* Reject with reason */}
              {selectedEntry.status === "pending" && (
                <div className="space-y-2 border-t pt-4">
                  <label htmlFor="reject-reason" className="text-sm font-medium">
                    Rejection reason (optional)
                  </label>
                  <Input
                    id="reject-reason"
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Reason for rejection..."
                  />
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={() => approveMutation.mutate(selectedEntry.id)}
                      disabled={approveMutation.isPending}
                    >
                      Approve
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() =>
                        rejectMutation.mutate({
                          entryId: selectedEntry.id,
                          reason: rejectReason || null,
                        })
                      }
                      disabled={rejectMutation.isPending}
                    >
                      Reject
                    </Button>
                  </div>
                </div>
              )}

              {/* Messages */}
              <div className="border-t pt-4">
                <h3 className="text-sm font-medium mb-2">Messages</h3>
                {messages.isLoading ? (
                  <p className="text-sm text-muted-foreground">Loading...</p>
                ) : (messages.data ?? []).length === 0 ? (
                  <p className="text-sm text-muted-foreground">No messages yet.</p>
                ) : (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {(messages.data ?? []).map((msg) => (
                      <div key={msg.id} className="rounded bg-muted p-2 text-sm">
                        <p>{msg.body}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {new Date(msg.created_at).toLocaleString()}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
                <div className="mt-2 flex gap-2">
                  <Textarea
                    value={messageBody}
                    onChange={(e) => setMessageBody(e.target.value)}
                    placeholder="Type a message..."
                    rows={2}
                  />
                  <Button
                    size="sm"
                    className="self-end"
                    disabled={!messageBody.trim() || messageMutation.isPending}
                    onClick={() =>
                      messageMutation.mutate({
                        entryId: selectedEntry.id,
                        body: messageBody.trim(),
                      })
                    }
                  >
                    Send
                  </Button>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Bypass invite dialog */}
      <Dialog open={showBypassDialog} onOpenChange={setShowBypassDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Direct Invite (Bypass Waitlist)</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label htmlFor="bypass-email" className="text-sm font-medium">Email</label>
              <Input
                id="bypass-email"
                type="email"
                value={bypassForm.email}
                onChange={(e) => setBypassForm((f) => ({ ...f, email: e.target.value }))}
              />
            </div>
            <div>
              <label htmlFor="bypass-name" className="text-sm font-medium">Name</label>
              <Input
                id="bypass-name"
                value={bypassForm.name}
                onChange={(e) => setBypassForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div>
              <label htmlFor="bypass-studio" className="text-sm font-medium">Studio name (optional)</label>
              <Input
                id="bypass-studio"
                value={bypassForm.studio_name}
                onChange={(e) => setBypassForm((f) => ({ ...f, studio_name: e.target.value }))}
              />
            </div>
            <Button
              onClick={() => {
                const data: { email: string; name: string; studio_name?: string } = {
                  email: bypassForm.email,
                  name: bypassForm.name,
                };
                if (bypassForm.studio_name) data.studio_name = bypassForm.studio_name;
                bypassMutation.mutate(data);
              }}
              disabled={!bypassForm.email || !bypassForm.name || bypassMutation.isPending}
            >
              {bypassMutation.isPending ? "Creating..." : "Create Bypass Invite"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
