import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen">
      {/* Hero Section */}
      <section className="gradient-bg py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center animate-fade-in">
            <div className="inline-block mb-4">
              <span className="bg-primary-100 text-primary-700 px-4 py-2 rounded-full text-sm font-semibold">
                🚀 AI-Powered Architecture Platform
              </span>
            </div>
            <h1 className="section-title mb-6 animate-slide-up">
              Transform Sketches into<br />Professional Architecture
            </h1>
            <p className="text-xl text-neutral-600 mb-8 max-w-2xl mx-auto text-balance">
              DraftBridge turns hand-drawn sketches into stunning 3D visualizations,
              complete with compliance checks and export-ready CAD/BIM files.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link href="/upload" className="btn-primary text-lg px-8 py-4">
                Start Building →
              </Link>
              <button className="btn-secondary text-lg px-8 py-4">
                Watch Demo
              </button>
            </div>
            
            {/* Stats */}
            <div className="grid grid-cols-3 gap-8 max-w-2xl mx-auto mt-16">
              <div className="animate-slide-up">
                <div className="text-3xl font-bold text-primary-600">10x</div>
                <div className="text-sm text-neutral-600">Faster Design</div>
              </div>
              <div className="animate-slide-up" style={{ animationDelay: '0.1s' }}>
                <div className="text-3xl font-bold text-primary-600">100%</div>
                <div className="text-sm text-neutral-600">Compliant</div>
              </div>
              <div className="animate-slide-up" style={{ animationDelay: '0.2s' }}>
                <div className="text-3xl font-bold text-primary-600">50+</div>
                <div className="text-sm text-neutral-600">Export Formats</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 px-4 sm:px-6 lg:px-8 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-display font-bold mb-4">
              Everything You Need
            </h2>
            <p className="text-xl text-neutral-600 max-w-2xl mx-auto">
              From sketch to construction-ready files in minutes
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="card group hover:-translate-y-1 transition-transform">
              <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg flex items-center justify-center mb-4 group-hover:shadow-glow transition-shadow">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2">Sketch Recognition</h3>
              <p className="text-neutral-600">
                Advanced AI analyzes hand-drawn sketches and extracts architectural elements with precision
              </p>
            </div>

            <div className="card group hover:-translate-y-1 transition-transform">
              <div className="w-12 h-12 bg-gradient-to-br from-accent-500 to-accent-600 rounded-lg flex items-center justify-center mb-4 group-hover:shadow-glow transition-shadow">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2">3D Visualization</h3>
              <p className="text-neutral-600">
                Generate photorealistic 3D renders and walkthroughs from your sketches instantly
              </p>
            </div>

            <div className="card group hover:-translate-y-1 transition-transform">
              <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center mb-4 group-hover:shadow-glow transition-shadow">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2">Compliance Checking</h3>
              <p className="text-neutral-600">
                Automatic verification against building codes and regulations before construction
              </p>
            </div>

            <div className="card group hover:-translate-y-1 transition-transform">
              <div className="w-12 h-12 bg-gradient-to-br from-primary-600 to-primary-700 rounded-lg flex items-center justify-center mb-4 group-hover:shadow-glow transition-shadow">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2">CAD/BIM Export</h3>
              <p className="text-neutral-600">
                Export to AutoCAD, Revit, SketchUp, and 50+ other formats for seamless workflow
              </p>
            </div>

            <div className="card group hover:-translate-y-1 transition-transform">
              <div className="w-12 h-12 bg-gradient-to-br from-accent-500 to-accent-600 rounded-lg flex items-center justify-center mb-4 group-hover:shadow-glow transition-shadow">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2">AI Design Assistant</h3>
              <p className="text-neutral-600">
                Get intelligent suggestions for materials, layouts, and optimizations
              </p>
            </div>

            <div className="card group hover:-translate-y-1 transition-transform">
              <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-accent-600 rounded-lg flex items-center justify-center mb-4 group-hover:shadow-glow transition-shadow">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold mb-2">Version Control</h3>
              <p className="text-neutral-600">
                Track changes, compare versions, and collaborate with your team in real-time
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="py-20 px-4 sm:px-6 lg:px-8 gradient-bg">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-display font-bold mb-4">
              Simple 3-Step Process
            </h2>
            <p className="text-xl text-neutral-600 max-w-2xl mx-auto">
              From concept to construction in minutes
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary-600 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4">
                1
              </div>
              <h3 className="text-xl font-semibold mb-2">Upload Sketch</h3>
              <p className="text-neutral-600">
                Take a photo or scan your hand-drawn architectural sketch
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-primary-600 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4">
                2
              </div>
              <h3 className="text-xl font-semibold mb-2">AI Processing</h3>
              <p className="text-neutral-600">
                Our AI analyzes, enhances, and generates 3D models automatically
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-primary-600 text-white rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-4">
                3
              </div>
              <h3 className="text-xl font-semibold mb-2">Export & Build</h3>
              <p className="text-neutral-600">
                Download construction-ready files in your preferred format
              </p>
            </div>
          </div>

          <div className="text-center mt-12">
            <Link href="/upload" className="btn-primary text-lg px-8 py-4">
              Try It Now - It's Free
            </Link>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-primary-600 to-accent-600 text-white">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl md:text-5xl font-display font-bold mb-6">
            Ready to Transform Your Workflow?
          </h2>
          <p className="text-xl mb-8 text-primary-100">
            Join thousands of architects and designers using DraftBridge
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/upload" className="bg-white text-primary-600 px-8 py-4 rounded-lg font-semibold hover:bg-neutral-100 transition-colors text-lg">
              Get Started Free
            </Link>
            <button className="border-2 border-white text-white px-8 py-4 rounded-lg font-semibold hover:bg-white/10 transition-colors text-lg">
              Schedule Demo
            </button>
          </div>
        </div>
      </section>
    </main>
  );
}
