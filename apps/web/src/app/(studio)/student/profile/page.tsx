"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

export default function StudentProfilePage() {
  const [notifyAssignments, setNotifyAssignments] = useState(true);
  const [notifyMessages, setNotifyMessages] = useState(true);
  const [notifyStreaks, setNotifyStreaks] = useState(true);

  return (
    <div className="mx-auto max-w-2xl p-6">
      <div className="mb-8">
        <h1 className="font-display text-[40px] leading-[48px] font-semibold tracking-tight">
          Profile
        </h1>
        <p className="text-muted-foreground mt-2">
          Manage your account settings and preferences.
        </p>
      </div>

      {/* Change Password */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg">Change Password</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label htmlFor="current-password" className="text-sm font-medium">
              Current Password
            </label>
            <Input
              id="current-password"
              type="password"
              autoComplete="current-password"
              className="mt-1"
            />
          </div>
          <div>
            <label htmlFor="new-password" className="text-sm font-medium">
              New Password
            </label>
            <Input
              id="new-password"
              type="password"
              autoComplete="new-password"
              className="mt-1"
            />
          </div>
          <button
            type="button"
            className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg px-4 py-2 text-sm font-medium"
          >
            Update Password
          </button>
        </CardContent>
      </Card>

      {/* Notification Preferences */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg">Notification Preferences</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex items-center justify-between" htmlFor="notify-assignments">
            <span className="text-sm">New assignments</span>
            <input
              id="notify-assignments"
              type="checkbox"
              checked={notifyAssignments}
              onChange={(e) => setNotifyAssignments(e.target.checked)}
              className="h-4 w-4 rounded"
            />
          </label>
          <Separator />
          <label className="flex items-center justify-between" htmlFor="notify-messages">
            <span className="text-sm">Messages from teacher</span>
            <input
              id="notify-messages"
              type="checkbox"
              checked={notifyMessages}
              onChange={(e) => setNotifyMessages(e.target.checked)}
              className="h-4 w-4 rounded"
            />
          </label>
          <Separator />
          <label className="flex items-center justify-between" htmlFor="notify-streaks">
            <span className="text-sm">Streak milestones</span>
            <input
              id="notify-streaks"
              type="checkbox"
              checked={notifyStreaks}
              onChange={(e) => setNotifyStreaks(e.target.checked)}
              className="h-4 w-4 rounded"
            />
          </label>
        </CardContent>
      </Card>

      {/* Delete Account */}
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="text-destructive text-lg">
            Delete Account
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground mb-4 text-sm">
            This will schedule your account for deletion. You have a 15-day
            grace period during which you can cancel. After that, all data will
            be permanently removed.
          </p>
          <button
            type="button"
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90 rounded-lg px-4 py-2 text-sm font-medium"
          >
            Request Account Deletion
          </button>
        </CardContent>
      </Card>
    </div>
  );
}
