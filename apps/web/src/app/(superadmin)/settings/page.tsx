"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type {
  SettingResponse,
  ActivityLogResponse,
} from "@dailyriff/api-client";
import { apiFetch } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

function useSettings() {
  return useQuery<SettingResponse[]>({
    queryKey: ["settings"],
    queryFn: () => apiFetch("/settings"),
  });
}

function useActivityLogs() {
  return useQuery<ActivityLogResponse[]>({
    queryKey: ["activity-logs"],
    queryFn: () => apiFetch("/settings/activity-logs/"),
  });
}

const CATEGORIES = [
  "rate_limits",
  "business_rule_caps",
  "notification_delays",
  "coppa_grace_windows",
] as const;

function categoryLabel(cat: string): string {
  return cat
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export default function SettingsPage() {
  const settings = useSettings();
  const activityLogs = useActivityLogs();
  const queryClient = useQueryClient();
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const updateMutation = useMutation({
    mutationFn: ({ key, value }: { key: string; value: unknown }) =>
      apiFetch(`/settings/${key}`, {
        method: "PUT",
        body: JSON.stringify({ value_json: value }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      queryClient.invalidateQueries({ queryKey: ["activity-logs"] });
      setEditingKey(null);
    },
  });

  function startEdit(setting: SettingResponse) {
    setEditingKey(setting.key);
    setEditValue(JSON.stringify(setting.value_json, null, 2));
  }

  function saveEdit() {
    if (!editingKey) return;
    try {
      const parsed = JSON.parse(editValue);
      updateMutation.mutate({ key: editingKey, value: parsed });
    } catch {
      // invalid JSON — don't submit
    }
  }

  const grouped: Record<string, SettingResponse[]> = {};
  for (const cat of CATEGORIES) {
    grouped[cat] = (settings.data ?? []).filter((s) => s.category === cat);
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="font-display text-3xl font-semibold tracking-tight">
          Platform Settings
        </h1>
        <p className="text-muted-foreground mt-2">
          Category-grouped platform configuration with audit trail.
        </p>
      </div>

      <Tabs defaultValue="settings">
        <TabsList>
          <TabsTrigger value="settings">Settings</TabsTrigger>
          <TabsTrigger value="audit">Audit Log</TabsTrigger>
        </TabsList>

        <TabsContent value="settings" className="mt-4">
          {settings.isLoading ? (
            <p className="text-muted-foreground text-sm" role="status">
              Loading settings...
            </p>
          ) : (
            <div className="space-y-6">
              {CATEGORIES.map((cat) => (
                <Card key={cat}>
                  <CardHeader>
                    <CardTitle>{categoryLabel(cat)}</CardTitle>
                    <CardDescription>
                      {grouped[cat]?.length ?? 0} setting(s) configured.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {(grouped[cat] ?? []).length === 0 ? (
                      <p className="text-muted-foreground text-sm">
                        No settings in this category.
                      </p>
                    ) : (
                      <div className="space-y-3">
                        {(grouped[cat] ?? []).map((s) => (
                          <div
                            key={s.key}
                            className="flex items-start justify-between rounded-md border border-border p-3"
                          >
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-medium">{s.key}</p>
                              {s.description && (
                                <p className="text-xs text-muted-foreground mt-0.5">
                                  {s.description}
                                </p>
                              )}
                              <pre className="text-xs font-mono bg-muted px-2 py-1 rounded mt-1 overflow-x-auto">
                                {JSON.stringify(s.value_json)}
                              </pre>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => startEdit(s)}
                              className="ml-2 shrink-0"
                            >
                              Edit
                            </Button>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Edit dialog */}
          <Dialog
            open={editingKey !== null}
            onOpenChange={(open) => !open && setEditingKey(null)}
          >
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Edit Setting</DialogTitle>
                <DialogDescription>
                  Editing <code className="font-mono">{editingKey}</code>.
                  Value must be valid JSON.
                </DialogDescription>
              </DialogHeader>
              <div className="py-4">
                <textarea
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono min-h-[120px] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  aria-label="Setting value (JSON)"
                />
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setEditingKey(null)}
                >
                  Cancel
                </Button>
                <Button
                  onClick={saveEdit}
                  disabled={updateMutation.isPending}
                >
                  {updateMutation.isPending ? "Saving..." : "Save"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </TabsContent>

        <TabsContent value="audit" className="mt-4">
          {activityLogs.isLoading ? (
            <p className="text-muted-foreground text-sm" role="status">
              Loading activity logs...
            </p>
          ) : (
            <div className="rounded-md border border-border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Action</TableHead>
                    <TableHead>Entity</TableHead>
                    <TableHead>Details</TableHead>
                    <TableHead>User</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(activityLogs.data ?? []).length === 0 ? (
                    <TableRow>
                      <TableCell
                        colSpan={5}
                        className="text-center text-muted-foreground py-8"
                      >
                        No activity logs yet.
                      </TableCell>
                    </TableRow>
                  ) : (
                    (activityLogs.data ?? []).map((log) => (
                      <TableRow key={log.id}>
                        <TableCell className="text-muted-foreground text-xs whitespace-nowrap">
                          {new Date(log.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{log.action}</Badge>
                        </TableCell>
                        <TableCell className="text-sm">
                          {log.entity_type}
                          {log.entity_id && (
                            <>
                              {" "}
                              <code className="font-mono text-xs">
                                {log.entity_id}
                              </code>
                            </>
                          )}
                        </TableCell>
                        <TableCell className="text-xs font-mono max-w-xs truncate">
                          {log.details ? JSON.stringify(log.details) : "—"}
                        </TableCell>
                        <TableCell>
                          <code className="font-mono text-xs">
                            {log.user_id.slice(0, 8)}...
                          </code>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
