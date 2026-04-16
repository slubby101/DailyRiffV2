import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy | DailyRiff",
  description: "DailyRiff Privacy Policy — how we collect, use, and protect your data.",
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

export default function PrivacyPolicyPage() {
  return (
    <div className="mx-auto max-w-prose px-4 py-16 sm:px-6 lg:px-8">
      <h1 className="font-display text-4xl font-bold tracking-tight">
        Privacy Policy
      </h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Last updated: April 2026
      </p>

      <div className="mt-6">
        <DraftBanner />
      </div>

      <div className="mt-8 space-y-6 text-base leading-relaxed text-muted-foreground">
        <h2 className="font-display text-2xl font-semibold text-foreground">
          1. Information we collect
        </h2>
        <p>
          We collect information you provide directly: name, email address,
          studio affiliation, and practice recordings. For children under 13, we
          collect information only with verified parental consent (see COPPA
          section below).
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          2. How we use your information
        </h2>
        <p>
          We use your information to provide the DailyRiff service: managing
          studio memberships, facilitating practice assignments, delivering
          notifications, and enabling communication between teachers, students,
          and parents.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          3. Data sharing
        </h2>
        <p>
          We do not sell your personal information. We share data only with
          service providers necessary to operate DailyRiff (hosting, email
          delivery, payment processing) and as required by law.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          4. Children&apos;s privacy (COPPA)
        </h2>
        <p>
          DailyRiff complies with the Children&apos;s Online Privacy Protection
          Act (COPPA). We do not knowingly collect personal information from
          children under 13 without verifiable parental consent. Parents may
          review, delete, or refuse further collection of their child&apos;s
          information at any time by contacting us.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          5. California privacy rights (CCPA/CPRA)
        </h2>
        <p>
          California residents have additional rights including the right to
          know, delete, and opt out of the sale of personal information. We
          honor the Global Privacy Control (GPC) signal automatically. To
          exercise your rights, contact us at the address below.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          6. Data retention &amp; deletion
        </h2>
        <p>
          We retain your data for as long as your account is active or as needed
          to provide services. Account deletion requests are processed within 15
          days, with a grace period during which you can cancel the deletion.
          Practice recordings are soft-deleted immediately and hard-deleted after
          the grace period.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          7. Security
        </h2>
        <p>
          We implement industry-standard security measures including encryption
          in transit, row-level security for data isolation between studios, and
          regular security reviews.
        </p>

        <h2 className="font-display text-2xl font-semibold text-foreground">
          8. Contact us
        </h2>
        <p>
          For privacy questions or data requests, contact us at{" "}
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
