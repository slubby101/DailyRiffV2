"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface NotificationPref {
  id: string;
  category: string;
  channel: string;
  enabled: boolean;
}

function useNotificationPrefs() {
  return useQuery<NotificationPref[]>({
    queryKey: ["parent", "notification-prefs"],
    queryFn: () => apiFetch("/preferences/notification-categories"),
  });
}

export default function ParentNotificationsPage() {
  const queryClient = useQueryClient();
  const prefs = useNotificationPrefs();

  const togglePref = useMutation({
    mutationFn: (pref: NotificationPref) =>
      apiFetch(`/preferences/notification-categories/${pref.id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !pref.enabled }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["parent", "notification-prefs"],
      });
    },
  });

  if (prefs.isLoading) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <p className="text-muted-foreground">Loading notification preferences...</p>
      </div>
    );
  }

  if (prefs.error) {
    return (
      <div className="mx-auto max-w-2xl p-6">
        <p className="text-destructive" role="alert">
          Failed to load notification preferences.
        </p>
      </div>
    );
  }

  const data = prefs.data ?? [];

  // Group by category
  const grouped = data.reduce<Record<string, NotificationPref[]>>((acc, p) => {
    if (!acc[p.category]) acc[p.category] = [];
    acc[p.category].push(p);
    return acc;
  }, {});

  return (
    <div className="mx-auto max-w-2xl p-6">
      <div className="mb-8">
        <h1 className="font-display text-[40px] leading-[48px] font-semibold tracking-tight">
          Notification Preferences
        </h1>
        <p className="text-muted-foreground mt-2">
          Manage how and when you receive notifications.
        </p>
      </div>

      {Object.keys(grouped).length === 0 ? (
        <p className="text-muted-foreground">
          No notification preferences available.
        </p>
      ) : (
        <div className="space-y-4">
          {Object.entries(grouped).map(([category, categoryPrefs]) => (
            <Card key={category}>
              <CardHeader>
                <CardTitle className="text-base capitalize">
                  {category.replace(/_/g, " ")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {categoryPrefs.map((pref) => (
                    <label
                      key={pref.id}
                      className="flex items-center justify-between"
                    >
                      <span className="text-sm capitalize">
                        {pref.channel.replace(/_/g, " ")}
                      </span>
                      <input
                        type="checkbox"
                        checked={pref.enabled}
                        onChange={() => togglePref.mutate(pref)}
                        disabled={togglePref.isPending}
                        className="h-4 w-4 rounded border-gray-300"
                        aria-label={`${pref.channel} notifications for ${category}`}
                      />
                    </label>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
