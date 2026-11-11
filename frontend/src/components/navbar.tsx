"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";

export function Navbar() {
  const pathname = usePathname();
  const requestsActive = pathname === "/requests";
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const profileMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isProfileMenuOpen) {
      return;
    }

    function handleOutsideClick(event: MouseEvent) {
      if (
        profileMenuRef.current &&
        !profileMenuRef.current.contains(event.target as Node)
      ) {
        setIsProfileMenuOpen(false);
      }
    }

    function handleEscapeKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsProfileMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handleOutsideClick);
    document.addEventListener("keydown", handleEscapeKey);

    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
      document.removeEventListener("keydown", handleEscapeKey);
    };
  }, [isProfileMenuOpen]);

  return (
    <nav className="flex flex-wrap items-center justify-between gap-5 border-b border-gray-200 pb-5">
      <Link href="/" className="flex items-center gap-3">
        <span className="text-xl font-bold">
          Knight<span className="text-(--color-scarlet)">Connect</span>
        </span>
      </Link>

      <div className="flex flex-wrap items-center gap-6 text-sm font-medium">
        <span className="text-gray-500">Opportunity</span>
        <span className="text-gray-500">Post</span>

        <Link
          href="/requests"
          aria-current={requestsActive ? "page" : undefined}
          className={
            requestsActive
              ? "border-b-2 border-(--color-scarlet) pb-1 font-semibold text-(--color-scarlet)"
              : "text-gray-600 transition hover:text-(--color-scarlet)"
          }
        >
          Requests
        </Link>

        <div ref={profileMenuRef} className="relative">
          <button
            type="button"
            onClick={() => setIsProfileMenuOpen(!isProfileMenuOpen)}
            className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-200 text-(--color-nav-icon) transition hover:bg-gray-300"
          >
            <UserRound size={20} />
          </button>

          {isProfileMenuOpen && (
            <div className="absolute right-0 mt-2 w-48 rounded-md border border-gray-200 bg-white shadow-lg">
              <Link
                href="/profile"
                onClick={() => setIsProfileMenuOpen(false)}
                className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              >
                View Profile
              </Link>
              <Link
                href="/settings"
                className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              >
                Settings
              </Link>
              <Link
                href="/logout"
                className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
              >
                Logout
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
