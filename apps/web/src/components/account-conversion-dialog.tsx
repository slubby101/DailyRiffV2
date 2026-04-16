"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface ConversionOption {
  target: "minor" | "teen" | "adult";
  requires_parent_consent: boolean;
  requires_new_credentials: boolean;
  message: string;
}

interface EligibilityResponse {
  current: "minor" | "teen" | "adult";
  conversions: ConversionOption[];
}

interface ConvertResponse {
  child_user_id: string;
  studio_id: string;
  previous_age_class: string;
  new_age_class: string;
  parent_access_removed: boolean;
  message: string;
}

const AGE_CLASS_LABELS: Record<string, string> = {
  minor: "Minor (under 13)",
  teen: "Teen (13–17)",
  adult: "Adult (18+)",
};

export function AccountConversionDialog({
  studioId,
  childUserId,
}: {
  studioId: string;
  childUserId: string;
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);
  const [parentConsentGiven, setParentConsentGiven] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [error, setError] = useState<string | null>(null);

  const eligibility = useQuery<EligibilityResponse>({
    queryKey: ["conversion-eligibility", studioId, childUserId],
    queryFn: () =>
      apiFetch(
        `/studios/${studioId}/students/${childUserId}/conversion-eligibility`
      ),
    enabled: open,
  });

  const convert = useMutation({
    mutationFn: (data: {
      target_age_class: string;
      parent_consent_given: boolean;
      new_email?: string;
    }) =>
      apiFetch<ConvertResponse>(
        `/studios/${studioId}/students/${childUserId}/convert`,
        {
          method: "POST",
          body: JSON.stringify(data),
        }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["teacher", "student", studioId, childUserId],
      });
      queryClient.invalidateQueries({
        queryKey: ["conversion-eligibility", studioId, childUserId],
      });
      setOpen(false);
      resetForm();
    },
    onError: (err: Error) => {
      setError(err.message || "Conversion failed");
    },
  });

  function resetForm() {
    setSelectedTarget(null);
    setParentConsentGiven(false);
    setNewEmail("");
    setError(null);
  }

  const selectedConversion = eligibility.data?.conversions.find(
    (c) => c.target === selectedTarget
  );

  function handleSubmit() {
    if (!selectedTarget || !selectedConversion) return;
    setError(null);

    if (selectedConversion.requires_parent_consent && !parentConsentGiven) {
      setError("Parent consent is required for this conversion.");
      return;
    }
    if (selectedConversion.requires_new_credentials && !newEmail.trim()) {
      setError("An email address is required for this conversion.");
      return;
    }

    convert.mutate({
      target_age_class: selectedTarget,
      parent_consent_given: parentConsentGiven,
      new_email: newEmail.trim() || undefined,
    });
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        if (!v) resetForm();
      }}
    >
      <DialogTrigger asChild>
        <button className="text-sm px-3 py-1.5 rounded-md border border-border bg-background hover:bg-accent transition-colors">
          Convert Account
        </button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Account Conversion</DialogTitle>
        </DialogHeader>

        {eligibility.isLoading && (
          <p className="text-sm text-muted-foreground">
            Checking eligibility...
          </p>
        )}

        {eligibility.error && (
          <p className="text-sm text-destructive" role="alert">
            Failed to check eligibility.
          </p>
        )}

        {eligibility.data && eligibility.data.conversions.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No conversions available for this student. Current class:{" "}
            {AGE_CLASS_LABELS[eligibility.data.current] ??
              eligibility.data.current}
          </p>
        )}

        {eligibility.data && eligibility.data.conversions.length > 0 && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Current:{" "}
              {AGE_CLASS_LABELS[eligibility.data.current] ??
                eligibility.data.current}
            </p>

            <fieldset>
              <legend className="text-sm font-medium mb-2">Convert to:</legend>
              <div className="space-y-2">
                {eligibility.data.conversions.map((opt) => (
                  <label
                    key={opt.target}
                    className="flex items-start gap-3 p-3 border rounded-lg cursor-pointer hover:bg-accent/50 transition-colors"
                  >
                    <input
                      type="radio"
                      name="target_age_class"
                      value={opt.target}
                      checked={selectedTarget === opt.target}
                      onChange={() => setSelectedTarget(opt.target)}
                      className="mt-0.5"
                      aria-label={`Convert to ${AGE_CLASS_LABELS[opt.target]}`}
                    />
                    <div>
                      <span className="text-sm font-medium">
                        {AGE_CLASS_LABELS[opt.target]}
                      </span>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {opt.message}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
            </fieldset>

            {selectedConversion?.requires_parent_consent && (
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={parentConsentGiven}
                  onChange={(e) => setParentConsentGiven(e.target.checked)}
                  className="h-4 w-4 rounded border-border"
                  aria-label="Parent consent given"
                />
                <span className="text-sm">
                  Parent or guardian has given consent
                </span>
              </label>
            )}

            {selectedConversion?.requires_new_credentials && (
              <div>
                <label
                  htmlFor="new-email"
                  className="block text-sm font-medium mb-1"
                >
                  Student email address
                </label>
                <input
                  id="new-email"
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="student@example.com"
                  className="w-full px-3 py-2 border rounded-md text-sm bg-background"
                  aria-label="Student email address"
                />
              </div>
            )}

            {error && (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            )}

            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="text-sm px-4 py-2 rounded-md border border-border hover:bg-accent transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={!selectedTarget || convert.isPending}
                className="text-sm px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
                aria-label="Confirm conversion"
              >
                {convert.isPending ? "Converting..." : "Convert"}
              </button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
