
"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type LoginStep = "email" | "code";

function getCookie(name: string): string | null {
  const cookies = document.cookie.split(";");

  for (const cookie of cookies) {
    const [key, ...value] = cookie.trim().split("=");

    if (key === name) {
      return decodeURIComponent(value.join("="));
    }
  }

  return null;
}

async function getCsrfToken(): Promise<string> {
  const response = await fetch(`${API_URL}/api/auth/csrf/`, {
    credentials: "include",
  });

  if (!response.ok) {
    throw new Error("Could not connect to the login server.");
  }

  const data = await response.json();
  return data.csrf_token || getCookie("csrftoken") || "";
}

async function postAuth(
  endpoint: string,
  body: Record<string, string>
) {
  const csrfToken = await getCsrfToken();

  const response = await fetch(`${API_URL}${endpoint}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify(body),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const firstError = Object.values(data)[0];

    if (Array.isArray(firstError)) {
      throw new Error(String(firstError[0]));
    }

    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Something went wrong. Please try again."
    );
  }

  return data;
}

export default function LoginPage() {
  const router = useRouter();

  const [step, setStep] = useState<LoginStep>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function handleRequestCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");

    const normalizedEmail = email.trim().toLowerCase();

    if (
      !normalizedEmail.endsWith("@rutgers.edu") &&
      !normalizedEmail.endsWith("@scarletmail.rutgers.edu")
    ) {
      setError("Please enter a valid Rutgers email address.");
      return;
    }

    setLoading(true);

    try {
      await postAuth("/api/auth/request-code/", {
        email: normalizedEmail,
      });

      setEmail(normalizedEmail);
      setStep("code");
      setMessage("Your verification code has been requested!");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to request a code."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!/^\d{6}$/.test(code.trim())) {
      setError("Please enter the six-digit verification code.");
      return;
    }

    setLoading(true);

    try {
      await postAuth("/api/auth/verify-code/", {
        email,
        code: code.trim(),
      });

      router.push("/profile");
      router.refresh();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to verify your code."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f8f8fa] text-gray-900">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <a
            href="/"
            className="text-2xl font-extrabold tracking-tight text-[#CC0033]"
          >
            KnightConnect
          </a>

          <span className="text-sm font-medium text-gray-500">
            Rutgers University
          </span>
        </div>
      </header>

      <div className="flex min-h-[calc(100vh-85px)] items-center justify-center px-5 py-12">
        <div className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-8 shadow-sm sm:p-10">
          <div className="mb-7 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#CC0033] text-2xl font-bold text-white">
            K
          </div>

          <h1 className="text-3xl font-bold tracking-tight">
            {step === "email" ? "Welcome to KnightConnect" : "Check your code"}
          </h1>

          <p className="mt-3 text-sm leading-6 text-gray-600">
            {step === "email"
              ? "Connect with Rutgers students, discover hackathons, and find your next teammate."
              : `Enter the six-digit verification code for ${email}.`}
          </p>

          {error && (
            <div
              role="alert"
              className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
            >
              {error}
            </div>
          )}

          {message && (
            <div
              role="status"
              className="mt-6 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800"
            >
              {message}
            </div>
          )}

          {step === "email" ? (
            <form onSubmit={handleRequestCode} className="mt-7 space-y-5">
              <div>
                <label
                  htmlFor="email"
                  className="mb-2 block text-sm font-semibold"
                >
                  Rutgers email
                </label>

                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="netid@scarletmail.rutgers.edu"
                  className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm outline-none transition focus:border-[#CC0033] focus:ring-2 focus:ring-red-100"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-xl bg-[#CC0033] px-5 py-3 font-semibold text-white transition hover:bg-[#a9002a] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Sending code..." : "Continue with Rutgers Email"}
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerifyCode} className="mt-7 space-y-5">
              <div>
                <label
                  htmlFor="code"
                  className="mb-2 block text-sm font-semibold"
                >
                  Verification code
                </label>

                <input
                  id="code"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  required
                  value={code}
                  onChange={(event) =>
                    setCode(event.target.value.replace(/\D/g, ""))
                  }
                  placeholder="123456"
                  className="w-full rounded-xl border border-gray-300 px-4 py-3 text-center text-2xl font-bold tracking-[0.4em] outline-none transition focus:border-[#CC0033] focus:ring-2 focus:ring-red-100"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-xl bg-[#CC0033] px-5 py-3 font-semibold text-white transition hover:bg-[#a9002a] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Verifying..." : "Verify & Sign In"}
              </button>

              <button
                type="button"
                onClick={() => {
                  setStep("email");
                  setCode("");
                  setError("");
                  setMessage("");
                }}
                className="w-full text-sm font-semibold text-[#CC0033] hover:underline"
              >
                Use a different email
              </button>
            </form>
          )}

          <div className="mt-8 border-t border-gray-100 pt-6">
            <p className="text-center text-xs leading-5 text-gray-500">
              Exclusively for the Rutgers community.
              <br />
              Your email is used to verify your student account.
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
