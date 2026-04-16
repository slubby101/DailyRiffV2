"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

export default function BetaLandingPage() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-2xl px-4 py-16 text-center text-muted-foreground">Loading...</div>}>
      <BetaLandingContent />
    </Suspense>
  );
}

function BetaLandingContent() {
  const searchParams = useSearchParams();
  const tokenParam = searchParams.get("token");

  const [isValidating, setIsValidating] = useState(false);
  const [isValid, setIsValid] = useState<boolean | null>(null);
  const [tokenInput, setTokenInput] = useState(tokenParam ?? "");

  async function handleValidate(e: React.FormEvent) {
    e.preventDefault();
    if (!tokenInput.trim()) return;

    setIsValidating(true);
    try {
      const result = await apiFetch<{ valid: boolean }>("/beta/validate-token", {
        method: "POST",
        body: JSON.stringify({ token: tokenInput.trim() }),
      });
      setIsValid(result.valid);
    } catch {
      setIsValid(false);
    } finally {
      setIsValidating(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-16 sm:px-6 lg:px-8">
      <div className="text-center">
        <p className="text-sm font-medium uppercase tracking-widest text-primary">
          Private Beta
        </p>
        <h1 className="mt-4 font-display text-4xl font-bold tracking-tight sm:text-5xl">
          Welcome to the DailyRiff Beta
        </h1>
        <p className="mt-4 text-lg text-muted-foreground">
          You have been invited to help shape the future of music practice.
          Enter your access token below to get started.
        </p>
      </div>

      {isValid === true ? (
        <div
          className="mt-12 rounded-lg border border-green-200 bg-green-50 p-8 text-center dark:border-green-800 dark:bg-green-950"
          role="status"
        >
          <h2 className="font-display text-2xl font-semibold text-green-900 dark:text-green-100">
            Access Confirmed
          </h2>
          <p className="mt-2 text-green-800 dark:text-green-200">
            Your beta access token is valid. Welcome aboard!
          </p>
          <p className="mt-4 text-sm text-green-700 dark:text-green-300">
            Check your email for onboarding instructions and next steps.
          </p>
          <Link
            href="/contact"
            className="mt-6 inline-block rounded-md bg-primary px-6 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            Contact Us
          </Link>
        </div>
      ) : (
        <form onSubmit={handleValidate} className="mt-12">
          <label
            htmlFor="beta-token"
            className="block text-sm font-medium text-foreground"
          >
            Beta Access Token
          </label>
          <div className="mt-2 flex gap-3">
            <input
              id="beta-token"
              type="text"
              value={tokenInput}
              onChange={(e) => {
                setTokenInput(e.target.value);
                setIsValid(null);
              }}
              placeholder="Enter your access token"
              className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              required
              autoComplete="off"
            />
            <button
              type="submit"
              disabled={isValidating || !tokenInput.trim()}
              className="rounded-md bg-primary px-6 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
            >
              {isValidating ? "Validating..." : "Verify"}
            </button>
          </div>

          {isValid === false && (
            <p className="mt-2 text-sm text-destructive" role="alert">
              Invalid or expired token. Please check your invitation email and try again.
            </p>
          )}
        </form>
      )}

      <div className="mt-16 border-t border-border pt-8 text-center">
        <p className="text-sm text-muted-foreground">
          Not part of the beta?{" "}
          <Link href="/" className="text-primary underline underline-offset-2 hover:text-primary/80">
            Join the waitlist
          </Link>{" "}
          to be notified when DailyRiff launches.
        </p>
      </div>
    </div>
  );
}
