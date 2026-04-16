"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { STUDIO_PALETTE } from "@/lib/studio-theme";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface StudioResponse {
  id: string;
  name: string;
  display_name: string | null;
  logo_url: string | null;
  primary_color: string | null;
  timezone: string;
}

/**
 * Studio onboarding page — post-signup walkthrough.
 *
 * After waitlist approval and signup, the studio owner completes
 * this walkthrough to set up their studio profile. Not a blocking
 * modal — lands on dashboard when done.
 */
export default function StudioOnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [studioName, setStudioName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [timezone, setTimezone] = useState("America/New_York");
  const [selectedColor, setSelectedColor] = useState("Amber");

  const createStudio = useMutation({
    mutationFn: (data: { name: string; display_name?: string; timezone: string }) =>
      apiFetch<StudioResponse>("/studios", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  });

  const updateStudio = useMutation({
    mutationFn: ({ id, ...data }: { id: string; primary_color?: string; display_name?: string }) =>
      apiFetch<StudioResponse>(`/studios/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  });

  const handleCreateStudio = async () => {
    const studio = await createStudio.mutateAsync({
      name: studioName.toLowerCase().replace(/\s+/g, "-"),
      display_name: displayName || studioName,
      timezone,
    });
    // Move to color picker step
    setStep(1);
    return studio;
  };

  const handleFinish = async () => {
    if (createStudio.data) {
      await updateStudio.mutateAsync({
        id: createStudio.data.id,
        primary_color: selectedColor,
      });
    }
    // Land on dashboard
    router.push("/dashboard");
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Step indicator */}
        <div className="flex justify-center gap-2 mb-8" role="group" aria-label="Onboarding progress">
          {[0, 1].map((s) => (
            <div
              key={s}
              className={`h-2 w-16 rounded-full transition-colors ${
                s <= step ? "bg-primary" : "bg-muted"
              }`}
              aria-label={`Step ${s + 1}${s <= step ? " (completed)" : ""}`}
            />
          ))}
        </div>

        {step === 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="font-display text-2xl">
                Welcome to DailyRiff
              </CardTitle>
              <CardDescription>
                Let&apos;s set up your studio. This only takes a minute.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label htmlFor="studio-name" className="text-sm font-medium block mb-1.5">
                  Studio name
                </label>
                <Input
                  id="studio-name"
                  value={studioName}
                  onChange={(e) => setStudioName(e.target.value)}
                  placeholder="e.g. Mitchell Music Studio"
                  autoFocus
                />
              </div>
              <div>
                <label htmlFor="display-name" className="text-sm font-medium block mb-1.5">
                  Display name (optional)
                </label>
                <Input
                  id="display-name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="How students see your studio"
                />
              </div>
              <div>
                <label htmlFor="timezone" className="text-sm font-medium block mb-1.5">
                  Timezone
                </label>
                <select
                  id="timezone"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="America/New_York">Eastern (America/New_York)</option>
                  <option value="America/Chicago">Central (America/Chicago)</option>
                  <option value="America/Denver">Mountain (America/Denver)</option>
                  <option value="America/Los_Angeles">Pacific (America/Los_Angeles)</option>
                  <option value="America/Phoenix">Arizona (America/Phoenix)</option>
                  <option value="Pacific/Honolulu">Hawaii (Pacific/Honolulu)</option>
                  <option value="America/Anchorage">Alaska (America/Anchorage)</option>
                  <option value="Europe/London">London (Europe/London)</option>
                  <option value="Europe/Berlin">Berlin (Europe/Berlin)</option>
                  <option value="Asia/Tokyo">Tokyo (Asia/Tokyo)</option>
                </select>
              </div>
              <Button
                className="w-full"
                disabled={!studioName.trim() || createStudio.isPending}
                onClick={handleCreateStudio}
              >
                {createStudio.isPending ? "Creating..." : "Continue"}
              </Button>
              {createStudio.isError && (
                <p className="text-sm text-destructive" role="alert">
                  {createStudio.error.message}
                </p>
              )}
            </CardContent>
          </Card>
        )}

        {step === 1 && (
          <Card>
            <CardHeader>
              <CardTitle className="font-display text-2xl">
                Pick your studio color
              </CardTitle>
              <CardDescription>
                This color themes your entire studio surface — students, parents,
                and teachers will see it everywhere.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div
                className="grid grid-cols-4 gap-3"
                role="radiogroup"
                aria-label="Studio color palette"
              >
                {STUDIO_PALETTE.map((swatch) => {
                  const isSelected = selectedColor === swatch.name;
                  return (
                    <button
                      key={swatch.name}
                      type="button"
                      role="radio"
                      aria-checked={isSelected}
                      aria-label={swatch.name}
                      className={`flex flex-col items-center gap-1.5 rounded-lg p-3 transition-all ${
                        isSelected
                          ? "ring-2 ring-ring ring-offset-2 ring-offset-background"
                          : "hover:bg-muted"
                      }`}
                      onClick={() => setSelectedColor(swatch.name)}
                    >
                      <div
                        className="h-10 w-10 rounded-full border border-border"
                        style={{ backgroundColor: `hsl(${swatch.hsl})` }}
                      />
                      <span className="text-xs text-muted-foreground">{swatch.name}</span>
                    </button>
                  );
                })}
              </div>

              {/* Live preview */}
              <div className="rounded-lg border p-4 mt-4">
                <p className="text-sm text-muted-foreground mb-2">Preview</p>
                <div
                  className="rounded-md px-4 py-2 text-white text-sm font-medium inline-block"
                  style={{
                    backgroundColor: `hsl(${
                      STUDIO_PALETTE.find((s) => s.name === selectedColor)?.hsl ?? "30 85% 48%"
                    })`,
                  }}
                >
                  {createStudio.data?.display_name || studioName}
                </div>
              </div>

              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setStep(0)}>
                  Back
                </Button>
                <Button
                  className="flex-1"
                  disabled={updateStudio.isPending}
                  onClick={handleFinish}
                >
                  {updateStudio.isPending ? "Saving..." : "Finish setup"}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
