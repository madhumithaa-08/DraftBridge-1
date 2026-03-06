import SketchUploader from '@/src/components/SketchUploader';

export const metadata = {
  title: 'Upload Sketch - DraftBridge',
  description: 'Upload your architectural sketch and transform it into a professional 3D visualization',
};

export default function UploadPage() {
  return (
    <main className="min-h-screen gradient-bg py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header Section */}
        <div className="text-center mb-12 animate-fade-in">
          <h1 className="section-title mb-4">
            Transform Your Sketch
          </h1>
          <p className="text-xl text-neutral-600 max-w-2xl mx-auto">
            Upload your hand-drawn architectural sketch and watch AI transform it
            into a professional 3D visualization
          </p>
        </div>

        {/* Progress Steps */}
        <div className="max-w-3xl mx-auto mb-12">
          <div className="flex items-center justify-between">
            <div className="flex flex-col items-center flex-1">
              <div className="w-12 h-12 bg-primary-600 text-white rounded-full flex items-center justify-center font-bold mb-2">
                1
              </div>
              <p className="text-sm font-medium text-neutral-700">Upload</p>
            </div>
            <div className="flex-1 h-1 bg-neutral-200 mx-4"></div>
            <div className="flex flex-col items-center flex-1">
              <div className="w-12 h-12 bg-neutral-200 text-neutral-600 rounded-full flex items-center justify-center font-bold mb-2">
                2
              </div>
              <p className="text-sm font-medium text-neutral-600">Analyze</p>
            </div>
            <div className="flex-1 h-1 bg-neutral-200 mx-4"></div>
            <div className="flex flex-col items-center flex-1">
              <div className="w-12 h-12 bg-neutral-200 text-neutral-600 rounded-full flex items-center justify-center font-bold mb-2">
                3
              </div>
              <p className="text-sm font-medium text-neutral-600">Visualize</p>
            </div>
          </div>
        </div>

        {/* Main Upload Component */}
        <SketchUploader />

        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
          <div className="card text-center">
            <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h3 className="font-semibold mb-2">Lightning Fast</h3>
            <p className="text-sm text-neutral-600">
              AI analysis completes in seconds, not hours
            </p>
          </div>

          <div className="card text-center">
            <div className="w-12 h-12 bg-accent-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-accent-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <h3 className="font-semibold mb-2">Secure & Private</h3>
            <p className="text-sm text-neutral-600">
              Your designs are encrypted and never shared
            </p>
          </div>

          <div className="card text-center">
            <div className="w-12 h-12 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
              </svg>
            </div>
            <h3 className="font-semibold mb-2">Professional Quality</h3>
            <p className="text-sm text-neutral-600">
              Export-ready files for any CAD/BIM software
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
