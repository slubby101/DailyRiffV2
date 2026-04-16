import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service | DailyRiff",
  description: "DailyRiff Terms of Service.",
};

function DraftBanner() {
  return (
    <div
      role="alert"
      className="rounded-lg border border-primary/30 bg-primary/5 px-4 py-3 text-sm"
    >
      <p className="font-semibold">DRAFT &mdash; legal review pending</p>
      <p className="mt-1 text-muted-foreground">
        This document is a working draft and has not yet been reviewed by legal
        counsel. Final copy will replace this before public launch.
      </p>
    </div>
  );
}

export default function TermsOfServicePage() {
  return (
    <div className="mx-auto max-w-prose px-4 py-16 sm:px-6 lg:px-8">
      <h1 className="font-display text-4xl font-bold tracking-tight">
        Terms of Service
      </h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Last updated: April 2026
      </p>

      <div className="mt-6">
        <DraftBanner />
      </div>

      <div className="mt-8 space-y-6 text-base leading-relaxed text-muted-foreground">
        <h2 className="font-display text-2xl font-semibold text-foreground">
          1. Acceptance of terms
        </h2>
        <p>
          By accessing or using DailyRiff, you agree to be bound by these Terms
          of Service. If you do not agree, do not use the service.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          2. Description of service
        </h2>
        <p>
          DailyRiff is a practice-management platform that connects music
          teachers, students, and parents. Teachers can create assignments,
          students can record practice sessions, and all parties can communicate
          and track progress.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          3. User accounts
        </h2>
        <p>
          You are responsible for maintaining the confidentiality of your account
          credentials and for all activities under your account. You must provide
          accurate information when creating an account. Children under 13 may
          only use DailyRiff with verified parental consent.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          4. Acceptable use
        </h2>
        <p>
          You agree to use DailyRiff only for its intended purpose of music
          education and practice management. You may not use the service to
          transmit harmful, illegal, or inappropriate content.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          5. Content ownership
        </h2>
        <p>
          You retain ownership of all content you upload, including practice
          recordings. By using DailyRiff, you grant us a limited license to
          store, process, and deliver your content as part of the service.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          6. Studio operators
        </h2>
        <p>
          Studio owners and teachers are responsible for the appropriate use of
          DailyRiff within their studios, including ensuring that student data is
          handled in accordance with applicable laws and these terms.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          7. Termination
        </h2>
        <p>
          We may suspend or terminate your access to DailyRiff at any time for
          violation of these terms. You may delete your account at any time
          through your account settings.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          8. Limitation of liability
        </h2>
        <p>
          DailyRiff is provided &ldquo;as is&rdquo; without warranties of any
          kind. We are not liable for any indirect, incidental, or consequential
          damages arising from your use of the service.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          9. Changes to terms
        </h2>
        <p>
          We may update these terms from time to time. We will notify you of
          material changes via email or through the service. Continued use after
          changes constitutes acceptance.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          10. Contact
        </h2>
        <p>
          Questions about these terms? Contact us at{" "}
          <a
            href="mailto:privacy@dailyriff.com"
            className="text-primary underline underline-offset-2 hover:text-primary/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            privacy@dailyriff.com
          </a>
        </p>
      </div>
    </div>
  );
}
