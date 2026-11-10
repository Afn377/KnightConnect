
import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#FAFAFA] text-gray-900">
      {/* Rutgers scarlet top border */}
      <div className="h-1 bg-[#CC0033]" />

      <div className="mx-auto max-w-5xl px-5 py-8 sm:px-8">
        {/* Navigation */}
        <nav className="flex flex-wrap items-center justify-between gap-5 border-b border-gray-200 pb-5">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#CC0033] text-lg font-bold text-white">
              K
            </div>

            <h1 className="text-xl font-bold">
              Knight
              <span className="text-[#CC0033]">
                Connect
              </span>
            </h1>
          </Link>

          <div className="flex flex-wrap items-center gap-6 text-sm font-medium">
            <span className="text-gray-500">
              Opportunity
            </span>

            <span className="text-gray-500">
              Post
            </span>

            <span className="text-gray-500">
            <Link
  href="/requests"
  className="text-gray-600 hover:text-[#CC0033]"
>
  Requests
</Link>
            </span>

            <Link
              href="/profile"
              className="rounded-md bg-[#CC0033] px-5 py-2 text-white transition hover:bg-[#A00028]"
            >
              My Profile
            </Link>
          </div>
        </nav>

        {/* Homepage Content */}
        <section className="py-24 text-center">
          <div className="mb-5 inline-block rounded-full bg-[#FCE7EC] px-4 py-2 text-sm font-medium text-[#A00028]">
            Built for Rutgers Students
          </div>

          <h2 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Welcome to{" "}
            <span className="text-[#CC0033]">
              KnightConnect
            </span>
          </h2>

          <p className="mx-auto mt-5 max-w-xl text-base leading-7 text-gray-600">
            Find hackathon teammates, discover exciting
            opportunities, and connect with students
            who share your interests and skills.
          </p>

          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link
              href="/profile"
              className="rounded-lg bg-[#CC0033] px-7 py-3 font-semibold text-white shadow-sm transition hover:bg-[#A00028]"
            >
              View My Profile
            </Link>
          </div>
        </section>

        {/* Feature Cards */}
        <section className="grid gap-5 pb-16 md:grid-cols-3">
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="mb-3 text-2xl">💻</div>
            <h3 className="text-lg font-bold">
              Find Teammates
            </h3>
            <p className="mt-2 text-sm text-gray-500">
              Connect with Rutgers students who have
              complementary skills.
            </p>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="mb-3 text-2xl">🚀</div>
            <h3 className="text-lg font-bold">
              Explore Opportunities
            </h3>
            <p className="mt-2 text-sm text-gray-500">
              Discover hackathons and projects
              you can join.
            </p>
          </div>

          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <div className="mb-3 text-2xl">🤝</div>
            <h3 className="text-lg font-bold">
              Build Connections
            </h3>
            <p className="mt-2 text-sm text-gray-500">
              Meet collaborators and start building
              something together.
            </p>
          </div>
        </section>

        <footer className="border-t border-gray-200 pt-5 text-center text-xs text-gray-400">
          KnightConnect · Connecting Rutgers Students
        </footer>
      </div>
    </main>
  );
}
