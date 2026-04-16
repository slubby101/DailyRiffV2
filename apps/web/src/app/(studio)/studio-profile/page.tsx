"use client";

import { useState, useRef } from "react";
import Image from "next/image";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import { STUDIO_PALETTE, getStudioThemeStyle } from "@/lib/studio-theme";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

interface StudioResponse {
  id: string;
  name: string;
  display_name: string | null;
  logo_url: string | null;
  primary_color: string | null;
  timezone: string;
  state: string;
}

/**
 * Studio profile page — logo upload (R2 presigned URL flow),
 * primary color picker (12-swatch palette), display name edit.
 */
export default function StudioProfilePage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadStatus, setUploadStatus] = useState<"idle" | "uploading" | "success" | "error">("idle");

  // Fetch the user's studios (first one for now)
  const studios = useQuery<StudioResponse[]>({
    queryKey: ["studios"],
    queryFn: () => apiFetch("/studios"),
  });

  const studio = studios.data?.[0];

  const updateStudio = useMutation({
    mutationFn: (data: { display_name?: string; primary_color?: string; logo_url?: string }) =>
      apiFetch(`/studios/${studio!.id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["studios"] });
    },
  });

  const [displayName, setDisplayName] = useState("");
  const [selectedColor, setSelectedColor] = useState<string | null>(null);

  // Initialize form state when studio loads
  const studioLoaded = studio && !selectedColor;
  if (studioLoaded) {
    setDisplayName(studio.display_name || "");
    setSelectedColor(studio.primary_color || "Amber");
  }

  const handleLogoUpload = async (file: File) => {
    if (!studio) return;

    setUploadStatus("uploading");
    try {
      // Request presigned upload URL from API
      const { upload_url, public_url } = await apiFetch<{
        upload_url: string;
        public_url: string;
      }>(`/studios/${studio.id}/logo-upload-url`, {
        method: "POST",
        body: JSON.stringify({
          content_type: file.type,
          file_name: file.name,
        }),
      });

      // Upload directly to R2 via presigned URL
      await fetch(upload_url, {
        method: "PUT",
        body: file,
        headers: { "Content-Type": file.type },
      });

      // Update studio with the public URL
      await updateStudio.mutateAsync({ logo_url: public_url });
      setUploadStatus("success");
    } catch {
      setUploadStatus("error");
    }
  };

  const handleColorChange = async (colorName: string) => {
    setSelectedColor(colorName);
    if (studio) {
      await updateStudio.mutateAsync({ primary_color: colorName });
    }
  };

  const handleDisplayNameSave = async () => {
    if (studio && displayName.trim()) {
      await updateStudio.mutateAsync({ display_name: displayName.trim() });
    }
  };

  if (studios.isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground" role="status">Loading studio...</p>
      </div>
    );
  }

  if (!studio) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">
              No studio found. Complete onboarding first.
            </p>
            <Button className="mt-4" onClick={() => window.location.href = "/onboarding"}>
              Go to Onboarding
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Apply live studio theme
  const themeStyle = getStudioThemeStyle(
    STUDIO_PALETTE.find((s) => s.name === selectedColor)?.hsl ?? ""
  );

  return (
    <div className="min-h-screen bg-background" style={{ "--primary": STUDIO_PALETTE.find((s) => s.name === selectedColor)?.hsl } as React.CSSProperties}>
      <div className="mx-auto max-w-2xl px-4 py-8">
        <h1 className="font-display text-3xl font-semibold tracking-tight mb-2">
          Studio Profile
        </h1>
        <p className="text-muted-foreground mb-8">
          Manage your studio&apos;s appearance and branding.
        </p>

        {/* Display name */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Display Name</CardTitle>
            <CardDescription>
              How students and parents see your studio.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Studio display name"
              />
              <Button
                onClick={handleDisplayNameSave}
                disabled={updateStudio.isPending}
              >
                Save
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Logo upload */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Logo</CardTitle>
            <CardDescription>
              Upload your studio logo. Recommended: square image, at least 256x256px.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              {studio.logo_url ? (
                <Image
                  src={studio.logo_url}
                  alt={`${studio.display_name || studio.name} logo`}
                  width={64}
                  height={64}
                  className="h-16 w-16 rounded-lg object-cover border"
                />
              ) : (
                <div className="h-16 w-16 rounded-lg border-2 border-dashed border-muted-foreground/25 flex items-center justify-center">
                  <span className="text-muted-foreground text-xs">No logo</span>
                </div>
              )}
              <div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/svg+xml"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleLogoUpload(file);
                  }}
                />
                <Button
                  variant="outline"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadStatus === "uploading"}
                >
                  {uploadStatus === "uploading" ? "Uploading..." : "Upload Logo"}
                </Button>
                {uploadStatus === "success" && (
                  <p className="text-sm text-green-600 mt-1">Logo uploaded successfully!</p>
                )}
                {uploadStatus === "error" && (
                  <p className="text-sm text-destructive mt-1" role="alert">
                    Upload failed. The presigned URL endpoint may not be available yet.
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <Separator className="my-6" />

        {/* Primary color picker */}
        <Card>
          <CardHeader>
            <CardTitle>Studio Color</CardTitle>
            <CardDescription>
              Pick a primary color for your studio. This themes the entire
              experience for your students and parents.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              className="grid grid-cols-4 sm:grid-cols-6 gap-3"
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
                    onClick={() => handleColorChange(swatch.name)}
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
              <p className="text-sm text-muted-foreground mb-2">Live preview</p>
              <div className="flex gap-3 items-center">
                <div
                  className="rounded-md px-4 py-2 text-white text-sm font-medium"
                  style={{
                    backgroundColor: `hsl(${
                      STUDIO_PALETTE.find((s) => s.name === selectedColor)?.hsl ?? "30 85% 48%"
                    })`,
                  }}
                >
                  Primary Button
                </div>
                <div
                  className="rounded-md px-4 py-2 text-sm font-medium border"
                  style={{
                    borderColor: `hsl(${
                      STUDIO_PALETTE.find((s) => s.name === selectedColor)?.hsl ?? "30 85% 48%"
                    })`,
                    color: `hsl(${
                      STUDIO_PALETTE.find((s) => s.name === selectedColor)?.hsl ?? "30 85% 48%"
                    })`,
                  }}
                >
                  Outline Button
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
