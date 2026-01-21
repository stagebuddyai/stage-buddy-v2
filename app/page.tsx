export default function Home() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
      <main className="text-center p-8">
        <h1 className="text-5xl font-bold text-gray-800 mb-4">
          Welcome to Stage Buddy
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Next.js 16 with TypeScript, Tailwind CSS, and App Router
        </p>
        <div className="flex gap-4 justify-center">
          <a
            href="/docs"
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Get Started
          </a>
          <a
            href="https://github.com/stagebuddyai/stage-buddy-v2"
            className="px-6 py-3 bg-gray-800 text-white rounded-lg hover:bg-gray-900 transition-colors"
          >
            View on GitHub
          </a>
        </div>
      </main>
    </div>
  );
}
