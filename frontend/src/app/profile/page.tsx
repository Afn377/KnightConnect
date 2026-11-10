
"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type ReactNode } from "react";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const YEAR_OPTIONS = [
  { value: "freshman", label: "Freshman" },
  { value: "sophomore", label: "Sophomore" },
  { value: "junior", label: "Junior" },
  { value: "senior", label: "Senior" },
  { value: "grad", label: "Graduate Student" },
];

type CatalogValue =
  | string
  | {
      slug?: string;
      name?: string;
      label?: string;
    };

type Skill = {
  skill: CatalogValue;
  proficiency: string;
};

type Profile = {
  id: string;
  email: string;
  display_name: string;
  major: string | null;
  year: string | null;
  bio: string;
  availability: string[];
  preferred_roles: CatalogValue[];
  interests: CatalogValue[];
  interested_events: CatalogValue[];
  skills: Skill[];
};

type ContactMethod = {
  id: number;
  kind: string;
  value: string;
  is_preferred: boolean;
};

type CatalogItem = {
  slug: string;
  name: string;
};

type CatalogResponse =
  | CatalogItem[]
  | { results: CatalogItem[] };

type Catalog = {
  skills: CatalogItem[];
  roles: CatalogItem[];
  interests: CatalogItem[];
  events: CatalogItem[];
};

type ModalType = "profile" | "matching" | "contact" | null;

function getCookie(name: string): string {
  const item = document.cookie
    .split("; ")
    .find((cookie) => cookie.startsWith(`${name}=`));

  return item
    ? decodeURIComponent(item.split("=").slice(1).join("="))
    : "";
}

function errorMessage(data: unknown): string {
  if (typeof data === "string") return data;

  if (data && typeof data === "object") {
    const obj = data as Record<string, unknown>;

    if (typeof obj.detail === "string") {
      return obj.detail;
    }

    for (const [key, value] of Object.entries(obj)) {
      if (Array.isArray(value) && value.length) {
        return `${key}: ${String(value[0])}`;
      }

      if (typeof value === "string") {
        return `${key}: ${value}`;
      }
    }
  }

  return "Something went wrong. Please try again.";
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers);

  if (method !== "GET" && method !== "HEAD") {
    const csrfResponse = await fetch(
      `${API_URL}/api/auth/csrf/`,
      { credentials: "include" }
    );

    if (!csrfResponse.ok) {
      throw new Error("Could not get the security token.");
    }

    const csrfData = await csrfResponse.json();

    headers.set(
      "X-CSRFToken",
      csrfData.csrf_token || getCookie("csrftoken")
    );
  }

  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error(errorMessage(data));
  }

  return data as T;
}

function catalogItems(data: CatalogResponse): CatalogItem[] {
  if (Array.isArray(data)) return data;

  return Array.isArray(data.results) ? data.results : [];
}

function getSlug(value: CatalogValue | null | undefined): string {
  if (typeof value === "string") {
    return value;
  }

  if (value && typeof value === "object") {
    return value.slug || value.name || value.label || "";
  }

  return "";
}

function displayYear(value: string | null): string {
  if (!value) return "Year not added";

  return (
    YEAR_OPTIONS.find((option) => option.value === value)
      ?.label || value
  );
}

function displaySlug(
  value: CatalogValue,
  options: CatalogItem[]
): string {
  const slug = getSlug(value);

  const matchingOption = options.find(
    (option) => option.slug === slug
  );

  if (matchingOption) {
    return matchingOption.name;
  }

  if (typeof value === "object" && value !== null) {
    return (
      value.name ||
      value.label ||
      slug.replace(/-/g, " ") ||
      "Unknown"
    );
  }

  return slug.replace(/-/g, " ") || "Unknown";
}

function Tags({ items }: { items: string[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.length === 0 ? (
        <span className="text-sm text-gray-400">
          Not added yet
        </span>
      ) : (
        items.map((item, index) => (
          <span
            key={`${item}-${index}`}
            className="rounded-full bg-[#FCE7EC] px-3 py-1 text-xs font-medium text-[#A00028]"
          >
            {item}
          </span>
        ))
      )}
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
      <h3 className="mb-3 text-sm font-semibold">
        {title}
      </h3>
      <Tags items={items} />
    </div>
  );
}

function EditButton({
  onClick,
}: {
  onClick: () => void;
}) {
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
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
}) {
  return (
    <label className="block text-sm font-semibold">
      {label}
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 font-normal outline-none focus:border-[#CC0033]"
      />
    </label>
  );
}

function ChoiceGroup({
  title,
  options,
  selected,
  onChange,
}: {
  title: string;
  options: CatalogItem[];
  selected: string[];
  onChange: (values: string[]) => void;
}) {
  function toggle(slug: string) {
    if (selected.includes(slug)) {
      onChange(selected.filter((item) => item !== slug));
    } else {
      onChange([...selected, slug]);
    }
  }

  return (
    <div>
      <h3 className="mb-3 text-sm font-semibold">
        {title}
      </h3>

      {options.length === 0 ? (
        <p className="rounded-lg bg-gray-50 p-3 text-sm text-gray-500">
          No options available yet. The catalog may need
          to be populated in Django.
        </p>
      ) : (
        <div className="grid max-h-40 grid-cols-2 gap-2 overflow-y-auto rounded-lg border border-gray-200 p-3">
          {options.map((option) => (
            <label
              key={option.slug}
              className="flex cursor-pointer items-center gap-2 text-sm"
            >
              <input
                type="checkbox"
                checked={selected.includes(option.slug)}
                onChange={() => toggle(option.slug)}
                className="accent-[#CC0033]"
              />
              <span>{option.name}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

function Modal({
  title,
  onClose,
  onSave,
  saving,
  error,
  children,
}: {
  title: string;
  onClose: () => void;
  onSave: () => Promise<void>;
  saving: boolean;
  error: string;
  children: ReactNode;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onMouseDown={(event) => {
        if (
          event.target === event.currentTarget &&
          !saving
        ) {
          onClose();
        }
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
            disabled={saving}
            aria-label="Close"
            className="text-2xl text-gray-500"
          >
            ×
          </button>
        </div>

        <form
          onSubmit={(event) => {
            event.preventDefault();
            void onSave();
          }}
          className="space-y-5"
        >
          {children}

          {error && (
            <p
              role="alert"
              className="text-sm font-medium text-red-600"
            >
              {error}
            </p>
          )}

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm"
            >
              Cancel
            </button>

            <button
              type="submit"
              disabled={saving}
              className="rounded-md bg-[#CC0033] px-5 py-2 text-sm font-medium text-white disabled:opacity-60"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);

  const [contacts, setContacts] = useState<ContactMethod[]>([]);

  const [catalog, setCatalog] = useState<Catalog>({
    skills: [],
    roles: [],
    interests: [],
    events: [],
  });

  const [loading, setLoading] = useState(true);
  const [pageError, setPageError] = useState("");
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);

  const [activeModal, setActiveModal] =
    useState<ModalType>(null);

  const [draftProfile, setDraftProfile] = useState({
    display_name: "",
    major: "",
    year: "",
    bio: "",
  });

  const [draftMatching, setDraftMatching] = useState({
    skills: [] as string[],
    roles: [] as string[],
    tracks: [] as string[],
    hackathons: [] as string[],
  });

  const [draftContacts, setDraftContacts] =
    useState<Record<string, string>>({});

  const loadProfile = useCallback(async () => {
    setLoading(true);
    setPageError("");

    try {
      const me = await apiRequest<Profile>("/api/me/");
      setProfile(me);

      const [
        skillsResult,
        rolesResult,
        interestsResult,
        eventsResult,
        contactsResult,
      ] = await Promise.allSettled([
        apiRequest<CatalogResponse>("/api/skills/"),
        apiRequest<CatalogResponse>("/api/roles/"),
        apiRequest<CatalogResponse>("/api/interests/"),
        apiRequest<CatalogResponse>("/api/events/"),
        apiRequest<ContactMethod[]>("/api/me/contact-methods/"),
      ]);

      setCatalog({
        skills:
          skillsResult.status === "fulfilled"
            ? catalogItems(skillsResult.value)
            : [],
        roles:
          rolesResult.status === "fulfilled"
            ? catalogItems(rolesResult.value)
            : [],
        interests:
          interestsResult.status === "fulfilled"
            ? catalogItems(interestsResult.value)
            : [],
        events:
          eventsResult.status === "fulfilled"
            ? catalogItems(eventsResult.value)
            : [],
      });

      setContacts(
        contactsResult.status === "fulfilled"
          ? contactsResult.value
          : []
      );
    } catch (error) {
      setPageError(
        error instanceof Error
          ? error.message
          : "Could not load profile."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProfile();
  }, [loadProfile]);

  function openProfileEditor() {
    if (!profile) return;

    setDraftProfile({
      display_name: profile.display_name || "",
      major: profile.major || "",
      year: profile.year || "",
      bio: profile.bio || "",
    });

    setSaveError("");
    setActiveModal("profile");
  }

  function openMatchingEditor() {
    if (!profile) return;

    setDraftMatching({
      skills: profile.skills.map((item) =>
        getSlug(item.skill)
      ),
      roles: profile.preferred_roles.map(getSlug),
      tracks: profile.interests.map(getSlug),
      hackathons: profile.interested_events.map(getSlug),
    });

    setSaveError("");
    setActiveModal("matching");
  }

  function openContactEditor() {
    const drafts: Record<string, string> = {};

    contacts.forEach((method) => {
      drafts[String(method.id)] = method.value;
    });

    setDraftContacts(drafts);
    setSaveError("");
    setActiveModal("contact");
  }

  async function saveProfile() {
    setSaving(true);
    setSaveError("");

    try {
      const updated = await apiRequest<Profile>(
        "/api/me/",
        {
          method: "PATCH",
          body: JSON.stringify({
            display_name: draftProfile.display_name.trim(),
            major: draftProfile.major.trim(),
            year: draftProfile.year,
            bio: draftProfile.bio.trim(),
          }),
        }
      );

      setProfile(updated);
      setActiveModal(null);
    } catch (error) {
      setSaveError(
        error instanceof Error
          ? error.message
          : "Could not save profile."
      );
    } finally {
      setSaving(false);
    }
  }

  async function saveMatching() {
    if (!profile) return;

    setSaving(true);
    setSaveError("");

    try {
      const existing = new Map(
        profile.skills.map((item) => [
          getSlug(item.skill),
          item.proficiency,
        ])
      );

      const updated = await apiRequest<Profile>(
        "/api/me/",
        {
          method: "PATCH",
          body: JSON.stringify({
            skills: draftMatching.skills.map((skill) => ({
              skill,
              proficiency:
                existing.get(skill) || "beginner",
            })),
            preferred_roles: draftMatching.roles,
            interests: draftMatching.tracks,
            interested_events: draftMatching.hackathons,
          }),
        }
      );

      setProfile(updated);
      setActiveModal(null);
    } catch (error) {
      setSaveError(
        error instanceof Error
          ? error.message
          : "Could not save matching information."
      );
    } finally {
      setSaving(false);
    }
  }

  async function saveContacts() {
    setSaving(true);
    setSaveError("");

    try {
      for (const method of contacts) {
        const nextValue = (
          draftContacts[String(method.id)] || ""
        ).trim();

        if (nextValue !== method.value) {
          await apiRequest(
            `/api/me/contact-methods/${method.id}/`,
            {
              method: "PATCH",
              body: JSON.stringify({
                value: nextValue,
              }),
            }
          );
        }
      }

      const updated = await apiRequest<ContactMethod[]>(
        "/api/me/contact-methods/"
      );

      setContacts(updated);
      setActiveModal(null);
    } catch (error) {
      setSaveError(
        error instanceof Error
          ? error.message
          : "Could not save contact details."
      );
    } finally {
      setSaving(false);
    }
  }

  const name =
    profile?.display_name || "Rutgers Student";

  const initials =
    name
      .trim()
      .split(/\s+/)
      .map((part) => part[0])
      .slice(0, 2)
      .join("")
      .toUpperCase() || "R";

  return (
    <main className="min-h-screen bg-[#FAFAFA] text-gray-900">
      <div className="h-1 bg-[#CC0033]" />

      <div className="mx-auto max-w-5xl px-5 py-8 sm:px-8">
        <nav className="mb-10 flex flex-wrap items-center justify-between gap-5 border-b border-gray-200 pb-5">
          <Link
            href="/"
            className="flex items-center gap-3"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#CC0033] text-lg font-bold text-white">
              K
            </div>

            <span className="text-xl font-bold">
              Knight
              <span className="text-[#CC0033]">
                Connect
              </span>
            </span>
          </Link>

          <div className="flex flex-wrap items-center gap-6 text-sm font-medium text-gray-600">
            <span>Opportunity</span>
            <span>Post</span>

            <Link
              href="/requests"
              className="hover:text-[#CC0033]"
            >
              Requests
            </Link>

            <Link
              href="/profile"
              aria-current="page"
              className="border-b-2 border-[#CC0033] pb-1 font-semibold text-[#CC0033]"
            >
              Profile
            </Link>
          </div>
        </nav>

        <div className="mb-7">
          <h1 className="text-3xl font-bold">
            Your Profile
          </h1>

          <p className="mt-2 text-sm text-gray-500">
            Review the information KnightConnect uses
            to match you with hackathon teammates.
          </p>
        </div>

        {loading && (
          <div className="rounded-xl border border-gray-200 bg-white p-8 text-center text-gray-500">
            Loading your profile...
          </div>
        )}

        {pageError && (
          <div
            role="alert"
            className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700"
          >
            {pageError}

            <Link
              href="/login"
              className="ml-2 font-bold underline"
            >
              Login
            </Link>
          </div>
        )}

        {!loading && !profile && (
          <button
            type="button"
            onClick={() => void loadProfile()}
            className="rounded-md bg-[#CC0033] px-5 py-2 text-white"
          >
            Try Again
          </button>
        )}

        {profile && (
          <>
            <section className="mb-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#FCE7EC] text-xl font-bold text-[#CC0033]">
                    {initials}
                  </div>

                  <div>
                    <h2 className="text-lg font-bold">
                      {name}
                    </h2>

                    <p className="mt-1 text-sm text-gray-500">
                      {profile.major || "Major not added"}
                      {" · "}
                      {displayYear(profile.year)}
                    </p>

                    <span className="mt-2 inline-block rounded-full bg-green-50 px-3 py-1 text-xs font-medium text-green-700">
                      ✓ Rutgers Account
                    </span>
                  </div>
                </div>

                <EditButton onClick={openProfileEditor} />
              </div>

              {profile.bio && (
                <p className="mt-5 text-sm text-gray-600">
                  {profile.bio}
                </p>
              )}
            </section>

            <section className="mb-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold">
                Matching Context
              </h2>

              <p className="mb-6 mt-1 text-sm text-gray-500">
                This information is visible to potential
                teammates and helps them understand how
                you can contribute to a hackathon.
              </p>

              <div className="grid gap-4 md:grid-cols-2">
                <InfoBox
                  title="Skills"
                  items={profile.skills.map((item) =>
                    displaySlug(item.skill, catalog.skills)
                  )}
                />

                <InfoBox
                  title="Roles I Can Contribute To"
                  items={profile.preferred_roles.map(
                    (value) =>
                      displaySlug(value, catalog.roles)
                  )}
                />

                <InfoBox
                  title="Interested Tracks"
                  items={profile.interests.map((value) =>
                    displaySlug(value, catalog.interests)
                  )}
                />

                <InfoBox
                  title="Interested Hackathons"
                  items={profile.interested_events.map(
                    (value) =>
                      displaySlug(value, catalog.events)
                  )}
                />

                <div className="rounded-lg bg-gray-50 p-4">
                  <h3 className="mb-3 text-sm font-semibold">
                    Event Availability
                  </h3>

                  {profile.availability?.length ? (
                    <Tags items={profile.availability} />
                  ) : (
                    <p className="text-sm text-gray-400">
                      Not specified
                    </p>
                  )}

                  <p className="mt-2 text-xs text-gray-500">
                    Your availability is shown to
                    teammates considering you for an event.
                  </p>
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <EditButton onClick={openMatchingEditor} />
              </div>
            </section>

            <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold">
                Contact Details
              </h2>

              <p className="mb-6 mt-1 text-sm text-gray-500">
                These details stay private until a
                connection request is accepted.
              </p>

              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-lg bg-gray-50 p-4">
                  <p className="mb-2 text-xs text-gray-500">
                    Rutgers Login Email
                  </p>

                  <p className="break-all text-sm font-semibold">
                    {profile.email}
                  </p>

                  <p className="mt-2 text-xs text-gray-500">
                    Used for signing in. Not editable here.
                  </p>
                </div>

                {contacts.map((method) => (
                  <div
                    key={method.id}
                    className="rounded-lg bg-gray-50 p-4"
                  >
                    <p className="mb-2 text-xs capitalize text-gray-500">
                      {method.kind}
                    </p>

                    <p className="break-all text-sm font-semibold">
                      {method.value}
                    </p>
                  </div>
                ))}

                {contacts.length === 0 && (
                  <div className="rounded-lg bg-gray-50 p-4 text-sm text-gray-400">
                    No sharing contact methods added yet.
                  </div>
                )}
              </div>

              <div className="mt-5 rounded-lg border border-[#F4C6D1] bg-[#FFF5F7] p-4">
                <p className="text-sm font-semibold text-[#A00028]">
                  🔒 Your contact information is private
                </p>

                <p className="mt-1 text-xs text-gray-600">
                  Contact methods are shared with
                  another student only after a
                  connection request is accepted.
                </p>
              </div>

              <div className="mt-6 flex justify-end">
                <EditButton onClick={openContactEditor} />
              </div>
            </section>
          </>
        )}

        <footer className="mt-10 border-t border-gray-200 pt-5 text-center text-xs text-gray-400">
          KnightConnect · Connecting Rutgers Students
        </footer>
      </div>

      {activeModal === "profile" && (
        <Modal
          title="Edit Your Profile"
          onClose={() => setActiveModal(null)}
          onSave={saveProfile}
          saving={saving}
          error={saveError}
        >
          <TextField
            label="Name"
            value={draftProfile.display_name}
            onChange={(value) =>
              setDraftProfile((prev) => ({
                ...prev,
                display_name: value,
              }))
            }
            required
          />

          <TextField
            label="Major"
            value={draftProfile.major}
            onChange={(value) =>
              setDraftProfile((prev) => ({
                ...prev,
                major: value,
              }))
            }
          />

          <label className="block text-sm font-semibold">
            Year

            <select
              value={draftProfile.year}
              onChange={(event) =>
                setDraftProfile((prev) => ({
                  ...prev,
                  year: event.target.value,
                }))
              }
              className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 font-normal"
            >
              <option value="">
                Select your year
              </option>

              {YEAR_OPTIONS.map((option) => (
                <option
                  key={option.value}
                  value={option.value}
                >
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block text-sm font-semibold">
            Bio

            <textarea
              value={draftProfile.bio}
              onChange={(event) =>
                setDraftProfile((prev) => ({
                  ...prev,
                  bio: event.target.value,
                }))
              }
              rows={3}
              className="mt-2 w-full rounded-md border border-gray-300 bg-white px-3 py-2 font-normal outline-none focus:border-[#CC0033]"
              placeholder="Tell teammates a little about yourself..."
            />
          </label>
        </Modal>
      )}

      {activeModal === "matching" && (
        <Modal
          title="Edit Matching Context"
          onClose={() => setActiveModal(null)}
          onSave={saveMatching}
          saving={saving}
          error={saveError}
        >
          <p className="text-sm text-gray-500">
            Select the skills, roles, tracks,
            and hackathons you're interested in.
          </p>

          <ChoiceGroup
            title="Skills"
            options={catalog.skills}
            selected={draftMatching.skills}
            onChange={(skills) =>
              setDraftMatching((prev) => ({
                ...prev,
                skills,
              }))
            }
          />

          <ChoiceGroup
            title="Preferred Roles"
            options={catalog.roles}
            selected={draftMatching.roles}
            onChange={(roles) =>
              setDraftMatching((prev) => ({
                ...prev,
                roles,
              }))
            }
          />

          <ChoiceGroup
            title="Interested Tracks"
            options={catalog.interests}
            selected={draftMatching.tracks}
            onChange={(tracks) =>
              setDraftMatching((prev) => ({
                ...prev,
                tracks,
              }))
            }
          />

          <ChoiceGroup
            title="Interested Hackathons"
            options={catalog.events}
            selected={draftMatching.hackathons}
            onChange={(hackathons) =>
              setDraftMatching((prev) => ({
                ...prev,
                hackathons,
              }))
            }
          />

          <p className="text-xs text-gray-500">
            Event availability will be connected
            separately after we confirm the
            backend's supported options.
          </p>
        </Modal>
      )}

      {activeModal === "contact" && (
        <Modal
          title="Edit Contact Information"
          onClose={() => setActiveModal(null)}
          onSave={saveContacts}
          saving={saving}
          error={saveError}
        >
          <p className="text-sm text-gray-500">
            Your Rutgers login email cannot be
            changed here. Existing contact
            methods can be updated.
          </p>

          {contacts.length === 0 ? (
            <p className="rounded-lg bg-gray-50 p-4 text-sm text-gray-600">
              You don't have any sharing contact
              methods yet. We'll add the ability
              to create Discord and portfolio
              methods next.
            </p>
          ) : (
            contacts.map((method) => (
              <TextField
                key={method.id}
                label={method.kind}
                value={
                  draftContacts[String(method.id)] || ""
                }
                onChange={(value) =>
                  setDraftContacts((prev) => ({
                    ...prev,
                    [String(method.id)]: value,
                  }))
                }
              />
            ))
          )}

          <div className="rounded-lg bg-[#FFF5F7] p-4">
            <p className="text-sm font-semibold text-[#A00028]">
              🔒 Privacy Reminder
            </p>

            <p className="mt-1 text-xs text-gray-600">
              Sharing contact details are only
              revealed after a connection is accepted.
            </p>
          </div>
        </Modal>
      )}
    </main>
  );
}
