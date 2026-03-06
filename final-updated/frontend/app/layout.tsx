import './globals.css';
import Header from '@/src/components/Header';

export const metadata = {
  title: 'DraftBridge - AI Architectural Co-Pilot',
  description: 'Transform hand-drawn sketches into professional architectural designs with AI-powered 3D visualization, compliance checking, and CAD/BIM export.',
  keywords: 'architecture, AI, 3D rendering, CAD, BIM, sketch to 3D, architectural design',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans">
        <Header />
        {children}
        <footer className="bg-neutral-900 text-white py-12 px-4">
          <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <h3 className="font-display font-bold text-lg mb-4">DraftBridge</h3>
              <p className="text-neutral-400 text-sm">
                AI-powered architectural platform transforming sketches into reality.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-neutral-400 text-sm">
                <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
                <li><a href="#pricing" className="hover:text-white transition-colors">Pricing</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Documentation</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-neutral-400 text-sm">
                <li><a href="#" className="hover:text-white transition-colors">About</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Blog</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Careers</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-neutral-400 text-sm">
                <li><a href="#" className="hover:text-white transition-colors">Privacy</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Terms</a></li>
                <li><a href="#" className="hover:text-white transition-colors">Security</a></li>
              </ul>
            </div>
          </div>
          <div className="max-w-7xl mx-auto mt-8 pt-8 border-t border-neutral-800 text-center text-neutral-400 text-sm">
            © 2026 DraftBridge. All rights reserved.
          </div>
        </footer>
      </body>
    </html>
  );
}
