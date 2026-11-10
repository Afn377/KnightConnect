
"use client";

import { useState, type ReactNode } from "react";

type MatchingContext = {
  skills: string[];
  roles: string[];
  tracks: string[];
  hackathons: string[];
  availability: string;
};

type ContactDetails = {
  email: string;
  discord: string;
  portfolio: string;
};

const initialMatching: MatchingContext = {
  skills: ["Node.js", "PostgreSQL", "API Design", "Figma", "React"],
  roles: ["Backend Developer", "Project Manager"],
  tracks: ["AI", "Fintech", "Web3", "EdTech"],
  hackathons: ["HackRU Spring", "HackPrinceton Spring"],
  availability: "Available Full Event",
};

const initialContact: ContactDetails = {
  email: "alex.chen@scarletmail.rutgers.edu",
  discord: "alexchen.dev",
  portfolio: "linkedin.com/in/alexchen",
};

function Tags({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span
          key={item}
          className="rounded-full bg-[#FCE7EC] px-3 py-1 text-xs font-medium text-[#A00028]"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function InfoBox({
  title,
  items,
}: {
  title: string;
  items: string[];
}) {
  return (
    <div className="rounded-lg bg-gray-50 p-4">
      <h3 className="mb-3 text-sm font-semibold">{title}</h3>
      <Tags items={items} />
    </div>
  );
}

function EditButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded-md bg-[#CC0033] px-5 py-2 text-sm font-medium text-white transition hover:bg-[#A00028]"
    >
      Edit
    </button>
  );
}

function TextField({
  label,
  value,
  onChange,
  required = false,
  type = "text",
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  type?: string;
  placeholder?: string;
}) {
  return (
    <label className="block text-sm font-semibold">
      {label}
      <input
        type={type}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        placeholder={placeholder}
        className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 font-normal outline-none focus:border-[#CC0033]"
      />
    </label>
  );
}

function Modal({
  title,
  onClose,
  onSave,
  children,
}: {
  title: string;
  onClose: () => void;
  onSave: () => void;
  children: ReactNode;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-6 shadow-xl"
      >
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-xl font-bold">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="text-2xl text-gray-500 hover:text-black"
          >
            ×
          </button>
        </div>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            onSave();
          }}
          className="space-y-4"
        >
          {children}

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm"
            >
              Cancel
            </button>

            <button
              type="submit"
              className="rounded-md bg-[#CC0033] px-5 py-2 text-sm font-medium text-white hover:bg-[#A00028]"
            >
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function parseList(value: string): string[] {
  return [
    ...new Set(
      value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean)
    ),
  ];
}

export default function ProfilePage() {
  // Student information
  const [name, setName] = useState("Alex Chen");
  const [major, setMajor] = useState("Computer Science");
  const [year, setYear] = useState("Senior");

  const [draftName, setDraftName] = useState(name);
  const [draftMajor, setDraftMajor] = useState(major);
  const [draftYear, setDraftYear] = useState(year);

  // Matching information
  const [matching, setMatching] = useState(initialMatching);

  const [draftMatching, setDraftMatching] = useState({
    skills: "",
    roles: "",
    tracks: "",
    hackathons: "",
    availability: "Available Full Event",
  });

  // Contact information
  const [contact, setContact] = useState(initialContact);
  const [draftContact, setDraftContact] = useState(initialContact);
  const [contactError, setContactError] = useState("");

  // Which popup is open?
  const [activeModal, setActiveModal] = useState<
    "profile" | "matching" | "contact" | null
  >(null);

  function openProfileEditor() {
    setDraftName(name);
    setDraftMajor(major);
    setDraftYear(year);
    setActiveModal("profile");
  }

  function saveProfile() {
    if (!draftName.trim() || !draftMajor.trim()) return;

    setName(draftName.trim());
    setMajor(draftMajor.trim());
    setYear(draftYear);
    setActiveModal(null);
  }

  function openMatchingEditor() {
    setDraftMatching({
      skills: matching.skills.join(", "),
      roles: matching.roles.join(", "),
      tracks: matching.tracks.join(", "),
      hackathons: matching.hackathons.join(", "),
      availability: matching.availability,
    });

    setActiveModal("matching");
  }

  function saveMatching() {
    setMatching({
      skills: parseList(draftMatching.skills),
      roles: parseList(draftMatching.roles),
      tracks: parseList(draftMatching.tracks),
      hackathons: parseList(draftMatching.hackathons),
      availability: draftMatching.availability,
    });

    setActiveModal(null);
  }

  function openContactEditor() {
    setDraftContact({ ...contact });
    setContactError("");
    setActiveModal("contact");
  }

  function saveContact() {
    const email = draftContact.email.trim();

    if (
      !/^[^\s@]+@(scarletmail\.rutgers\.edu|rutgers\.edu)$/i.test(email)
    ) {
      setContactError(
        "Please enter a valid Rutgers email address."
      );
      return;
    }

    setContact({
      email,
      discord: draftContact.discord.trim(),
      portfolio: draftContact.portfolio.trim(),
    });

    setContactError("");
    setActiveModal(null);
  }

  const initials = name
    .trim()
    .split(/\s+/)
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <main className="min-h-screen bg-[#FAFAFA] text-gray-900">
      <div className="h-1 bg-[#CC0033]" />

      <div className="mx-auto max-w-5xl px-5 py-8 sm:px-8">
        {/* Navigation */}
        <nav className="mb-10 flex flex-wrap items-center justify-between gap-5 border-b border-gray-200 pb-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#CC0033] text-lg font-bold text-white">
              K
            </div>

            <h1 className="text-xl font-bold">
              Knight
              <span className="text-[#CC0033]">Connect</span>
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-6 text-sm font-medium text-gray-600">
            <span>Opportunity</span>
            <span>Post</span>
            <span>Requests</span>
            <span className="border-b-2 border-[#CC0033] pb-1 font-semibold text-[#CC0033]">
              Profile
            </span>
          </div>
        </nav>

        {/* Page Heading */}
        <div className="mb-7">
          <h2 className="text-3xl font-bold">
            Your Profile
          </h2>

          <p className="mt-2 text-sm text-gray-500">
            Review the information KnightConnect uses to
            match you with hackathon teammates.
          </p>
        </div>

        {/* Student Information */}
        <section className="mb-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#FCE7EC] text-xl font-bold text-[#CC0033]">
                {initials}
              </div>

              <div>
                <h3 className="text-lg font-bold">{name}</h3>
                <p className="mt-1 text-sm text-gray-500">
                  {major} · {year}
                </p>
                <span className="mt-2 inline-block rounded-full bg-green-50 px-3 py-1 text-xs font-medium text-green-700">
                  ✓ Verified Student
                </span>
              </div>
            </div>

            <EditButton onClick={openProfileEditor} />
          </div>
        </section>

        {/* Matching Context */}
        <section className="mb-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-bold">
            Matching Context
          </h3>

          <p className="mb-6 mt-1 text-sm text-gray-500">
            This information is visible to potential
            teammates and helps them understand how
            you can contribute to a hackathon.
          </p>

          <div className="grid gap-4 md:grid-cols-2">
            <InfoBox title="Skills" items={matching.skills} />

            <InfoBox
              title="Roles I Can Contribute To"
              items={matching.roles}
            />

            <InfoBox
              title="Interested Tracks"
              items={matching.tracks}
            />

            <InfoBox
              title="Interested Hackathons"
              items={matching.hackathons}
            />

            <div className="rounded-lg bg-gray-50 p-4">
              <h3 className="mb-3 text-sm font-semibold">
                Event Availability
              </h3>

              <p className="text-sm font-medium">
                <span className="mr-2 text-[#CC0033]">●</span>
                {matching.availability}
              </p>

              <p className="mt-2 text-xs text-gray-500">
                Your availability is shown to teammates
                considering you for this event.
              </p>
            </div>
          </div>

          <div className="mt-6 flex justify-end">
            <EditButton onClick={openMatchingEditor} />
          </div>
        </section>

        {/* Contact Details */}
        <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-bold">
            Contact Details
          </h3>

          <p className="mb-6 mt-1 text-sm text-gray-500">
            These details stay private until a connection
            request is accepted.
          </p>

          <div className="grid gap-4 md:grid-cols-3">
            {[
              ["Rutgers Email", contact.email],
              ["Discord", contact.discord || "Not provided"],
              [
                "LinkedIn / Portfolio",
                contact.portfolio || "Not provided",
              ],
            ].map(([label, value]) => (
              <div
                key={label}
                className="rounded-lg bg-gray-50 p-4"
              >
                <p className="mb-2 text-xs text-gray-500">
                  {label}
                </p>
                <p className="break-all text-sm font-semibold">
                  {value}
                </p>
              </div>
            ))}
          </div>

          {/* Privacy Notice */}
          <div className="mt-5 rounded-lg border border-[#F4C6D1] bg-[#FFF5F7] p-4">
            <p className="text-sm font-semibold text-[#A00028]">
              🔒 Your contact information is private
            </p>

            <p className="mt-1 text-xs text-gray-600">
              Only you can see these details. They are shared
              with another student only after a connection
              request is accepted.
            </p>
          </div>

          <div className="mt-6 flex justify-end">
            <EditButton onClick={openContactEditor} />
          </div>
        </section>

        {/* Footer */}
        <footer className="mt-10 border-t border-gray-200 pt-5 text-center text-xs text-gray-400">
          KnightConnect · Connecting Rutgers Students
        </footer>
      </div>

      {/* Edit Student Profile Popup */}
      {activeModal === "profile" && (
        <Modal
          title="Edit Your Profile"
          onClose={() => setActiveModal(null)}
          onSave={saveProfile}
        >
          <TextField
            label="Name"
            value={draftName}
            onChange={setDraftName}
            required
          />

          <TextField
            label="Major"
            value={draftMajor}
            onChange={setDraftMajor}
            required
          />

          <label className="block text-sm font-semibold">
            Year
            <select
              value={draftYear}
              onChange={(event) =>
                setDraftYear(event.target.value)
              }
              className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 font-normal"
            >
              {[
                "Freshman",
                "Sophomore",
                "Junior",
                "Senior",
                "Graduate",
              ].map((option) => (
                <option key={option}>{option}</option>
              ))}
            </select>
          </label>
        </Modal>
      )}

      {/* Edit Matching Context Popup */}
      {activeModal === "matching" && (
        <Modal
          title="Edit Matching Context"
          onClose={() => setActiveModal(null)}
          onSave={saveMatching}
        >
          <p className="text-sm text-gray-500">
            Separate multiple items with commas.
            For example: React, Python, Figma
          </p>

          <TextField
            label="Skills"
            value={draftMatching.skills}
            onChange={(value) =>
              setDraftMatching((prev) => ({
                ...prev,
                skills: value,
              }))
            }
          />

          <TextField
            label="Preferred Roles"
            value={draftMatching.roles}
            onChange={(value) =>
              setDraftMatching((prev) => ({
                ...prev,
                roles: value,
              }))
            }
          />

          <TextField
            label="Interested Tracks"
            value={draftMatching.tracks}
            onChange={(value) =>
              setDraftMatching((prev) => ({
                ...prev,
                tracks: value,
              }))
            }
          />

          <TextField
            label="Interested Hackathons"
            value={draftMatching.hackathons}
            onChange={(value) =>
              setDraftMatching((prev) => ({
                ...prev,
                hackathons: value,
              }))
            }
          />

          <label className="block text-sm font-semibold">
            Event Availability
            <select
              value={draftMatching.availability}
              onChange={(event) =>
                setDraftMatching((prev) => ({
                  ...prev,
                  availability: event.target.value,
                }))
              }
              className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 font-normal"
            >
              <option>Available Full Event</option>
              <option>Available Part of Event</option>
              <option>Not Available</option>
              <option>Flexible</option>
            </select>
          </label>
        </Modal>
      )}

      {/* Edit Contact Details Popup */}
      {activeModal === "contact" && (
        <Modal
          title="Edit Contact Information"
          onClose={() => setActiveModal(null)}
          onSave={saveContact}
        >
          <p className="text-sm text-gray-500">
            Your contact details are used to help approved
            teammates connect with you.
          </p>

          <TextField
            label="Rutgers Email *"
            type="email"
            value={draftContact.email}
            onChange={(value) => {
              setDraftContact((prev) => ({
                ...prev,
                email: value,
              }));
              setContactError("");
            }}
            placeholder="name@scarletmail.rutgers.edu"
            required
          />

          <TextField
            label="Discord Username (Optional)"
            value={draftContact.discord}
            onChange={(value) =>
              setDraftContact((prev) => ({
                ...prev,
                discord: value,
              }))
            }
            placeholder="yourusername"
          />

          <TextField
            label="LinkedIn / Portfolio URL (Optional)"
            value={draftContact.portfolio}
            onChange={(value) =>
              setDraftContact((prev) => ({
                ...prev,
                portfolio: value,
              }))
            }
            placeholder="linkedin.com/in/yourname"
          />

          {contactError && (
            <p role="alert" className="text-sm font-medium text-red-600">
              {contactError}
            </p>
          )}

          <div className="rounded-lg bg-[#FFF5F7] p-4">
            <p className="text-sm font-semibold text-[#A00028]">
              🔒 Privacy Reminder
            </p>
            <p className="mt-1 text-xs text-gray-600">
              Contact details should only be shared with
              another student after a connection is approved.
            </p>
          </div>
        </Modal>
      )}
    </main>
  );
}
