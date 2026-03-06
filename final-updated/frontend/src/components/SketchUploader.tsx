'use client';

import { useState } from 'react';
import Image from 'next/image';

interface SketchUploadResponse {
  design_id: string;
  sketch_id: string;
  status: string;
  s3_key: string;
  uploaded_at: string;
}

interface RenderResponse {
  render_id: string;
  design_id: string;
  image_url: string;
  s3_key: string;
  prompt_used: string;
  created_at: string;
}

export default function SketchUploader() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<SketchUploadResponse | null>(null);
  const [render, setRender] = useState<RenderResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setAnalysis(null);
      setRender(null);
      setError(null);

      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result as string);
      };
      reader.readAsDataURL(selectedFile);
    }
  };

  const analyzeSketch = async () => {
    if (!file) return;
    
    setLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/sketches`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let detail = `Server error (${response.status})`;
        try {
          const body = await response.json();
          if (body && body.detail) {
            detail = body.detail;
          }
        } catch {
          // response body wasn't JSON — use status text
          detail = `Server error: ${response.status} ${response.statusText}`;
        }
        throw new Error(detail);
      }

      const result = await response.json();
      setAnalysis(result);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to analyze sketch. Please try again.';
      setError(errorMsg);
      console.error('Analysis failed:', errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const generateRender = async () => {
    if (!analysis) return;
    
    setLoading(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/renders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          design_id: analysis.design_id,
          style: 'photorealistic',
          materials: {},
          lighting: 'natural',
        }),
      });

      if (!response.ok) {
        let detail = `Server error (${response.status})`;
        try {
          const body = await response.json();
          if (body && body.detail) {
            detail = body.detail;
          }
        } catch {
          detail = `Server error: ${response.status} ${response.statusText}`;
        }
        throw new Error(detail);
      }

      const result = await response.json();
      setRender(result);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to generate render. Please try again.';
      setError(errorMsg);
      console.error('Render failed:', errorMsg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* File Upload Section */}
      <div className="card">
        <h2 className="text-2xl font-display font-bold mb-6">Upload Your Sketch</h2>
        <div className="border-2 border-dashed border-neutral-300 rounded-xl p-12 text-center hover:border-primary-400 transition-colors bg-gradient-to-br from-neutral-50 to-white">
          <input
            type="file"
            accept="image/*"
            onChange={handleFileUpload}
            className="hidden"
            id="file-upload"
          />
          <label htmlFor="file-upload" className="cursor-pointer">
            <div className="mx-auto w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <p className="text-lg font-medium text-neutral-700 mb-2">
              Click to upload or drag and drop
            </p>
            <p className="text-sm text-neutral-500">
              JPEG, PNG, or WEBP up to 10MB
            </p>
          </label>
        </div>
        
        {file && (
          <div className="mt-6 animate-slide-up">
            <div className="flex items-center justify-between bg-primary-50 p-4 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="font-medium text-neutral-900">{file.name}</p>
                  <p className="text-sm text-neutral-600">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              </div>
              <button
                onClick={analyzeSketch}
                disabled={loading}
                className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Analyzing...
                  </span>
                ) : (
                  'Analyze Sketch'
                )}
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 animate-slide-down">
            {error}
          </div>
        )}
      </div>

      {/* Preview and Analysis Results */}
      {(preview || analysis) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Preview */}
          {preview && (
            <div className="card animate-fade-in">
              <h3 className="text-xl font-semibold mb-4">Your Sketch</h3>
              <div className="relative aspect-video bg-neutral-100 rounded-lg overflow-hidden">
                <Image
                  src={preview}
                  alt="Sketch preview"
                  fill
                  className="object-contain"
                />
              </div>
            </div>
          )}

          {/* Analysis Results */}
          {analysis && (
            <div className="card animate-slide-up">
              <h3 className="text-xl font-semibold mb-4">Analysis Results</h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-neutral-600">Design ID</p>
                    <p className="font-mono text-xs text-neutral-900">{analysis.design_id.slice(0, 12)}...</p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600">Status</p>
                    <p className="text-lg font-bold text-primary-600 capitalize">{analysis.status}</p>
                  </div>
                </div>

                <div className="pt-4 border-t">
                  <p className="text-sm text-neutral-600">Sketch ID</p>
                  <p className="font-mono text-xs text-neutral-900">{analysis.sketch_id}</p>
                </div>

                <div className="pt-4 border-t">
                  <p className="text-sm text-neutral-600">Uploaded At</p>
                  <p className="text-sm text-neutral-900">{new Date(analysis.uploaded_at).toLocaleString()}</p>
                </div>

                <button
                  onClick={generateRender}
                  disabled={loading}
                  className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Generating 3D Model...' : 'Generate 3D Visualization'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Render Results */}
      {render && (
        <div className="card animate-scale-in">
          <h3 className="text-2xl font-display font-bold mb-6">3D Visualization</h3>
          <div className="relative aspect-video bg-neutral-900 rounded-lg overflow-hidden mb-6">
            <Image
              src={render.image_url}
              alt="Generated 3D Render"
              fill
              className="object-contain"
            />
          </div>
          
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="p-4 bg-neutral-50 rounded-lg">
              <p className="text-sm text-neutral-600 mb-1">Render ID</p>
              <p className="font-mono text-xs text-neutral-900">{render.render_id.slice(0, 8)}...</p>
            </div>
            <div className="p-4 bg-neutral-50 rounded-lg">
              <p className="text-sm text-neutral-600 mb-1">Design ID</p>
              <p className="font-mono text-xs text-neutral-900">{render.design_id.slice(0, 8)}...</p>
            </div>
            <div className="p-4 bg-neutral-50 rounded-lg">
              <p className="text-sm text-neutral-600 mb-1">Created At</p>
              <p className="font-medium text-neutral-900">{new Date(render.created_at).toLocaleDateString()}</p>
            </div>
          </div>

          <div className="mt-6 flex gap-4">
            <button className="btn-primary flex-1">
              Export to CAD
            </button>
            <button className="btn-secondary flex-1">
              Download Render
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
