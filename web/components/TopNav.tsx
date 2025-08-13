export default function TopNav() {
  return (
    <nav className="bg-white border-b px-8 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-8">
          <h1 className="text-lg font-semibold">AI Maturity Tool</h1>
          <div className="flex space-x-6">
            <a href="/" className="text-sm hover:text-blue-600">Dashboard</a>
            <a href="/new" className="text-sm hover:text-blue-600">New Assessment</a>
          </div>
        </div>
      </div>
    </nav>
  );
}
