
"use client";

import Link from "next/link";
import { useState } from "react";

type Tab = "received" | "sent" | "history";
type RequestStatus =
  | "new"
  | "pending"
  | "approved"
  | "declined"
  | "withdrawn";

type ConnectionRequest = {
  id: number;
  direction: "received" | "sent";
  name: string;
  major: string;
  year: string;
  opportunity: string;
  event: string;
  notes: string;
  matchReason: string;
  status: RequestStatus;
  email: string;
  discord: string;
  portfolio: string;
};

const initialRequests: ConnectionRequest[] = [
  {
    id: 1,
    direction: "received",
    name: "Alex Chen",
    major: "Computer Science",
    year: "Senior",
    opportunity: "HackRU Spring Teammates Needed",
    event: "HackRU Spring",
    notes:
      "I have built Node and PostgreSQL projects before and would love to contribute to the backend for the team.",
    matchReason:
      "Available for the full event. Backend experience matches an open role.",
    status: "new",
    email: "alex.chen@scarletmail.rutgers.edu",
    discord: "alexchen.dev",
    portfolio: "linkedin.com/in/alexchen",
  },
  {
    id: 2,
    direction: "received",
    name: "Maya Patel",
    major: "Information Technology",
    year: "Junior",
    opportunity: "HackRU Spring Teammates Needed",
    event: "HackRU Spring",
    notes:
      "I enjoy designing user interfaces and would love to help build the frontend for this project.",
    matchReason:
      "React and Figma skills match your team's frontend needs.",
    status: "new",
    email: "maya.patel@scarletmail.rutgers.edu",
    discord: "mayadesigns",
    portfolio: "linkedin.com/in/mayapatel",
  },
  {
    id: 3,
    direction: "sent",
    name: "Jordan Lee",
    major: "Computer Science",
    year: "Junior",
    opportunity: "AI Hackathon Project Team",
    event: "HackPrinceton Spring",
    notes:
      "I am interested in AI and would love to contribute my React and API development experience.",
    matchReason:
      "Your frontend skills match the team's open role.",
    status: "pending",
    email: "jordan.lee@scarletmail.rutgers.edu",
    discord: "jordanbuilds",
    portfolio: "linkedin.com/in/jordanlee",
  },
  {
    id: 4,
    direction: "sent",
    name: "Taylor Kim",
    major: "Data Science",
    year: "Senior",
    opportunity: "Fintech Innovation Team",
    event: "HackRU Spring",
    notes:
      "I'd love to collaborate on the fintech project and help with the application.",
    matchReason:
      "Your interests align with the project's fintech track.",
    status: "approved",
    email: "taylor.kim@scarletmail.rutgers.edu",
    discord: "taylorkim",
    portfolio: "linkedin.com/in/taylorkim",
  },
];

function getInitials(name: string) {
  return name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}

function StatusBadge({ status }: { status: RequestStatus }) {
  const styles: Record<RequestStatus, string> = {
    new: "bg-green-50 text-green-700",
    pending: "bg-amber-50 text-amber-700",
    approved: "bg-green-50 text-green-700",
    declined: "bg-red-50 text-red-700",
    withdrawn: "bg-gray-100 text-gray-600",
  };

  const labels: Record<RequestStatus, string> = {
    new: "New",
    pending: "Pending",
    approved: "Approved",
    declined: "Declined",
    withdrawn: "Withdrawn",
  };

  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-medium ${styles[status]}`}
    >
      {labels[status]}
    </span>
  );
}

function ActionButton({
  children,
  onClick,
  secondary = false,
}: {
  children: React.ReactNode;
  onClick: () => void;
  secondary?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        secondary
          ? "flex-1 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          : "flex-1 rounded-md bg-[#CC0033] px-4 py-2 text-sm font-medium text-white hover:bg-[#A00028]"
      }
    >
      {children}
    </button>
  );
}

function RequestCard({
  request,
  onAccept,
  onDecline,
  onWithdraw,
  onContact,
}: {
  request: ConnectionRequest;
  onAccept: (id: number) => void;
  onDecline: (id: number) => void;
  onWithdraw: (id: number) => void;
  onContact: (request: ConnectionRequest) => void;
}) {
  const isHistory =
    request.status === "declined" ||
    request.status === "withdrawn";

  return (
    <article className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#FCE7EC] text-sm font-bold text-[#CC0033]">
          {getInitials(request.name)}
        </div>

        <div className="min-w-0 flex-1">
          <h3 className="font-bold">{request.name}</h3>
          <p className="text-xs text-gray-500">
            {request.major} · {request.year}
          </p>
        </div>

        <StatusBadge status={request.status} />
      </div>

      <div className="mb-4 rounded-lg bg-gray-100 p-3">
        <p className="text-sm font-semibold">
          {request.opportunity}
        </p>
        <p className="mt-1 text-xs text-gray-500">
          {request.event}
        </p>
      </div>

      <div className="mb-4">
        <h4 className="mb-2 text-xs font-semibold text-gray-600">
          Notes from {request.direction === "received" ? request.name : "You"}
        </h4>
        <p className="rounded-lg bg-gray-50 p-3 text-sm leading-6 text-gray-700">
          {request.notes}
        </p>
      </div>

      <div className="mb-5 rounded-lg border border-[#F4C6D1] bg-[#FFF5F7] p-3">
        <p className="text-sm font-semibold text-[#A00028]">
          ✨ Why you may be a fit
        </p>
        <p className="mt-1 text-xs leading-5 text-gray-600">
          {request.matchReason}
        </p>
      </div>

      {isHistory ? (
        <div className="rounded-md bg-gray-100 px-4 py-2 text-center text-sm text-gray-500">
          Request {request.status}
        </div>
      ) : request.status === "approved" ? (
        <ActionButton onClick={() => onContact(request)}>
          View Contact Details
        </ActionButton>
      ) : request.direction === "received" ? (
        <div className="flex gap-3">
          <ActionButton
            secondary
            onClick={() => onDecline(request.id)}
          >
            Decline
          </ActionButton>

          <ActionButton onClick={() => onAccept(request.id)}>
            Accept
          </ActionButton>
        </div>
      ) : (
        <div className="flex gap-3">
          <ActionButton
            secondary
            onClick={() => onWithdraw(request.id)}
          >
            Withdraw Request
          </ActionButton>
        </div>
      )}
    </article>
  );
}

export default function RequestsPage() {
  const [requests, setRequests] = useState(initialRequests);
  const [activeTab, setActiveTab] = useState<Tab>("received");
  const [selectedContact, setSelectedContact] =
    useState<ConnectionRequest | null>(null);

  function updateStatus(id: number, status: RequestStatus) {
    setRequests((previous) =>
      previous.map((request) =>
        request.id === id ? { ...request, status } : request
      )
    );
  }

  const received = requests.filter(
    (request) =>
      request.direction === "received" &&
      request.status !== "declined" &&
      request.status !== "withdrawn"
  );

  const sent = requests.filter(
    (request) =>
      request.direction === "sent" &&
      request.status !== "declined" &&
      request.status !== "withdrawn"
  );

  const history = requests.filter(
    (request) =>
      request.status === "declined" ||
      request.status === "withdrawn"
  );

  const visibleRequests =
    activeTab === "received"
      ? received
      : activeTab === "sent"
      ? sent
      : history;

  async function copyText(value: string) {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      alert("Could not copy automatically. Please copy the text manually.");
    }
  }

  return (
    <main className="min-h-screen bg-[#FAFAFA] text-gray-900">
      <div className="h-1 bg-[#CC0033]" />

      <div className="mx-auto max-w-5xl px-5 py-8 sm:px-8">
        {/* Navigation */}
        <nav className="mb-10 flex flex-wrap items-center justify-between gap-5 border-b border-gray-200 pb-5">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#CC0033] text-lg font-bold text-white">
              K
            </div>

            <h1 className="text-xl font-bold">
              Knight
              <span className="text-[#CC0033]">Connect</span>
            </h1>
          </Link>

          <div className="flex flex-wrap items-center gap-6 text-sm font-medium text-gray-600">
            <span>Opportunity</span>
            <span>Post</span>

            <Link
              href="/requests"
              className="border-b-2 border-[#CC0033] pb-1 font-semibold text-[#CC0033]"
            >
              Requests
            </Link>

            <Link
              href="/profile"
              className="hover:text-[#CC0033]"
            >
              Profile
            </Link>
          </div>
        </nav>

        {/* Heading */}
        <div className="mb-7">
          <h2 className="text-3xl font-bold">
            Your Connection Requests
          </h2>
          <p className="mt-2 text-sm text-gray-500">
            Manage your teammate connection requests here.
          </p>
        </div>

        {/* Tabs */}
        <div
          role="tablist"
          aria-label="Request categories"
          className="mb-7 flex flex-wrap gap-2 border-b border-gray-200 pb-5"
        >
          {([
            ["sent", `Sent (${sent.length})`],
            ["received", `Received (${received.length})`],
            ["history", `History (${history.length})`],
          ] as const).map(([tab, label]) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={activeTab === tab}
              onClick={() => setActiveTab(tab)}
              className={`rounded-md px-5 py-2 text-sm font-medium transition ${
                activeTab === tab
                  ? "bg-[#CC0033] text-white"
                  : "border border-gray-200 bg-white text-gray-600 hover:bg-gray-100"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Request List */}
        <section>
          <h3 className="mb-1 text-lg font-bold">
            {activeTab === "received"
              ? "Received"
              : activeTab === "sent"
              ? "Sent"
              : "History"}
          </h3>

          <p className="mb-5 text-sm text-gray-500">
            {activeTab === "received"
              ? "Requests from students who want to join your team."
              : activeTab === "sent"
              ? "Requests you've sent to other teams."
              : "Requests that were declined or withdrawn."}
          </p>

          {visibleRequests.length > 0 ? (
            <div className="grid gap-5 md:grid-cols-2">
              {visibleRequests.map((request) => (
                <RequestCard
                  key={request.id}
                  request={request}
                  onAccept={(id) => updateStatus(id, "approved")}
                  onDecline={(id) => updateStatus(id, "declined")}
                  onWithdraw={(id) => updateStatus(id, "withdrawn")}
                  onContact={setSelectedContact}
                />
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-gray-300 bg-white px-6 py-20 text-center">
              <div className="mb-4 text-4xl">📭</div>
              <h3 className="text-lg font-bold">
                No requests yet
              </h3>
              <p className="mt-2 text-sm text-gray-500">
                There are no requests in this category.
              </p>
            </div>
          )}
        </section>

        <footer className="mt-12 border-t border-gray-200 pt-5 text-center text-xs text-gray-400">
          KnightConnect · Connecting Rutgers Students
        </footer>
      </div>

      {/* Accepted Connection Modal */}
      {selectedContact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Accepted connection details"
            className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-xl font-bold">
                  You've connected with {selectedContact.name}!
                </h2>
                <p className="mt-1 text-sm text-gray-500">
                  Contact information is now shared.
                </p>
              </div>

              <button
                type="button"
                aria-label="Close"
                onClick={() => setSelectedContact(null)}
                className="text-2xl text-gray-500 hover:text-black"
              >
                ×
              </button>
            </div>

            <div className="my-5 flex items-center gap-3 rounded-lg bg-gray-50 p-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-[#FCE7EC] font-bold text-[#CC0033]">
                {getInitials(selectedContact.name)}
              </div>

              <div>
                <p className="font-semibold">
                  {selectedContact.name}
                </p>
                <p className="text-xs text-gray-500">
                  {selectedContact.major} · {selectedContact.year}
                </p>
              </div>
            </div>

            <h3 className="mb-3 font-semibold">
              Contact Details
            </h3>

            <div className="space-y-3">
              {[
                ["Discord", selectedContact.discord],
                ["Rutgers Email", selectedContact.email],
                ["LinkedIn / Portfolio", selectedContact.portfolio],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="flex items-center justify-between gap-3 rounded-lg bg-gray-50 p-3"
                >
                  <div className="min-w-0">
                    <p className="text-xs text-gray-500">
                      {label}
                    </p>
                    <p className="break-all text-sm font-medium">
                      {value || "Not provided"}
                    </p>
                  </div>

                  {value && (
                    <button
                      type="button"
                      onClick={() => copyText(value)}
                      className="shrink-0 rounded-md bg-[#CC0033] px-3 py-2 text-xs font-medium text-white hover:bg-[#A00028]"
                    >
                      Copy
                    </button>
                  )}
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={() => setSelectedContact(null)}
              className="mt-6 w-full rounded-md border border-gray-300 px-4 py-2 text-sm font-medium hover:bg-gray-50"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
