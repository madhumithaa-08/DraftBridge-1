'use client';

import { useState } from 'react';
import Image from 'next/image';
import ChatPanel from './ChatPanel';
import VideoStatusIndicator from './VideoStatusIndicator';

interface AnalysisResult {
  design_id: string;
  sketch_id: string;
  status: string;
  s3_key: string;
  uploaded_at: string;
  descriptive_summary?: string;
  rooms?: any[];
  architectural_elements?: any[];
}

interface RenderResponse {
  render_id: string;
  design_id: string;
  image_url: string;
  s3_key: string;
  prompt_used: string;
  created_at: string;
}

interface VideoResponse {
  video_id: string;
  design_id: string;
  status: string;
  invocation_arn?: string;
}

type WorkflowStage = 'upload' | 'analysis' | 'render' | 'chat' | 'refined-render' | 'video' | 'export';

const WORKFLOW_STEPS: { key: WorkflowStage; label: string }[] = [
  { key: 'analysis', label: 'Analysis' },
  { key: 'render', label: 'Render' },
  { key: 'chat', label: 'Chat Refinement' },
  { key: 'refined-render', label: 'Refined Render' },
  { key: 'video', label: 'Video' },
  { key: 'export', label: 'Export' },
];

function getStepStatus(step: WorkflowStage, current: WorkflowStage): 'completed' | 'current' | 'upcoming' {
  const order: WorkflowStage[] = ['upload', 'analysis', 'render', 'chat', 'refined-render', 'video', 'export'];
  const stepIdx = order.indexOf(step);
  const currentIdx = order.indexOf(current);
  if (stepIdx < currentIdx) return 'completed';
  if (stepIdx === currentIdx) return 'current';
  return 'upcoming';
}

export default function SketchUploader() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [render, setRender] = useState<RenderResponse | null>(null);
  const [refinedRender, setRefinedRender] = useState<RenderResponse | null>(null);
  const [refinedPrompt, setRefinedPrompt] = useState<string | null>(null);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [workflowStage, setWorkflowStage] = useState<WorkflowStage>('upload');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exportLoading, setExportLoading] = useState<string | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setAnalysis(null);
      setRender(null);
      setRefinedRender(null);
      setRefinedPrompt(null);
      setVideoId(null);
      setWorkflowStage('upload');
      setError(null);
      setExportLoading(null);
      setExportError(null);

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
      const response = await fetch(`${apiUrl}/api/sketches`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        let detail = `Server error (${response.status})`;
        try {
          const body = await response.json();
          if (body && body.detail) detail = body.detail;
        } catch {
          detail = `Server error: ${response.status} ${response.statusText}`;
        }
        throw new Error(detail);
      }

      const result = await response.json();
      setAnalysis(result);
      setWorkflowStage('analysis');
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
          if (body && body.detail) detail = body.detail;
        } catch {
          detail = `Server error: ${response.status} ${response.statusText}`;
        }
        throw new Error(detail);
      }

      const result = await response.json();
      setRender(result);
      setWorkflowStage('chat');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to generate render. Please try again.';
      setError(errorMsg);
      console.error('Render failed:', errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleReadyToRender = async (refinedPrompt: string) => {
    if (!analysis) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${apiUrl}/api/renders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          design_id: analysis.design_id,
          refined_prompt: refinedPrompt,
        }),
      });

      if (!response.ok) {
        let detail = `Server error (${response.status})`;
        try {
          const body = await response.json();
          if (body && body.detail) detail = body.detail;
        } catch {
          detail = `Server error: ${response.status} ${response.statusText}`;
        }
        throw new Error(detail);
      }

      const result = await response.json();
      setRefinedRender(result);
      setRefinedPrompt(refinedPrompt);
      setWorkflowStage('refined-render');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to generate refined render. Please try again.';
      setError(errorMsg);
      console.error('Refined render failed:', errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const generateVideo = async () => {
    if (!analysis) return;

    setLoading(true);
    setError(null);
    try {
      const requestBody: Record<string, string> = {
        design_id: analysis.design_id,
      };
      if (refinedPrompt) {
        requestBody.refined_prompt = refinedPrompt;
      }

      const response = await fetch(`${apiUrl}/api/videos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        let detail = `Server error (${response.status})`;
        try {
          const body = await response.json();
          if (body && body.detail) detail = body.detail;
        } catch {
          detail = `Server error: ${response.status} ${response.statusText}`;
        }
        throw new Error(detail);
      }

      const result: VideoResponse = await response.json();
      setVideoId(result.video_id);
      setWorkflowStage('video');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to start video generation. Please try again.';
      setError(errorMsg);
      console.error('Video generation failed:', errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleVideoRetry = () => {
    setVideoId(null);
    setWorkflowStage('refined-render');
  };

  const handleExport = async (format: string) => {
    if (!analysis) return;
    setExportLoading(format);
    setExportError(null);
    try {
      const response = await fetch(`${apiUrl}/api/exports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ design_id: analysis.design_id, format }),
      });
      if (!response.ok) {
        let detail = `Export failed (${response.status})`;
        try {
          const body = await response.json();
          if (body && body.detail) detail = body.detail;
        } catch { detail = `Server error: ${response.status}`; }
        throw new Error(detail);
      }
      const result = await response.json();
      if (result.download_url) {
        const a = document.createElement('a');
        a.href = result.download_url;
        a.download = `design-export.${format.toLowerCase()}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      }
      setWorkflowStage('export');
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExportLoading(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Workflow Stage Indicator */}
      {workflowStage !== 'upload' && (
        <div className="card">
          <div className="flex items-center justify-between">
            {WORKFLOW_STEPS.map((step, idx) => {
              const status = getStepStatus(step.key, workflowStage);
              return (
                <div key={step.key} className="flex items-center">
                  <div className="flex flex-col items-center">
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                        status === 'completed'
                          ? 'bg-green-500 text-white'
                          : status === 'current'
                          ? 'bg-primary-600 text-white'
                          : 'bg-neutral-200 text-neutral-400'
                      }`}
                    >
                      {status === 'completed' ? (
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        idx + 1
                      )}
                    </div>
                    <span
                      className={`text-xs mt-1 whitespace-nowrap ${
                        status === 'completed'
                          ? 'text-green-600 font-medium'
                          : status === 'current'
                          ? 'text-primary-600 font-medium'
                          : 'text-neutral-400'
                      }`}
                    >
                      {step.label}
                    </span>
                  </div>
                  {idx < WORKFLOW_STEPS.length - 1 && (
                    <div
                      className={`w-12 h-0.5 mx-2 mt-[-1rem] ${
                        getStepStatus(WORKFLOW_STEPS[idx + 1].key, workflowStage) !== 'upcoming'
                          ? 'bg-green-400'
                          : status === 'current' || status === 'completed'
                          ? 'bg-primary-300'
                          : 'bg-neutral-200'
                      }`}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

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
                {loading && workflowStage === 'upload' ? (
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

              {/* Descriptive Summary */}
              {analysis.descriptive_summary && (
                <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm font-medium text-blue-800 mb-1">AI Summary</p>
                  <p className="text-sm text-blue-700 leading-relaxed">{analysis.descriptive_summary}</p>
                </div>
              )}

              <div className="space-y-4">
                {/* Rooms */}
                {analysis.rooms && analysis.rooms.length > 0 && (
                  <div>
                    <p className="text-sm text-neutral-600 mb-2">Rooms Detected</p>
                    <div className="flex flex-wrap gap-2">
                      {analysis.rooms.map((room: any, idx: number) => (
                        <span key={idx} className="px-3 py-1 bg-primary-50 text-primary-700 rounded-full text-xs font-medium">
                          {room.name}{room.area ? ` (${room.area} sq ft)` : ''}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Architectural Elements */}
                {analysis.architectural_elements && analysis.architectural_elements.length > 0 && (
                  <div>
                    <p className="text-sm text-neutral-600 mb-2">Architectural Elements</p>
                    <div className="flex flex-wrap gap-2">
                      {analysis.architectural_elements.map((el: any, idx: number) => (
                        <span key={idx} className="px-3 py-1 bg-neutral-100 text-neutral-700 rounded-full text-xs font-medium">
                          {el.label || el.type}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div>
                    <p className="text-sm text-neutral-600">Design ID</p>
                    <p className="font-mono text-xs text-neutral-900">{analysis.design_id.slice(0, 12)}...</p>
                  </div>
                  <div>
                    <p className="text-sm text-neutral-600">Status</p>
                    <p className="text-lg font-bold text-primary-600 capitalize">{analysis.status}</p>
                  </div>
                </div>

                {workflowStage === 'analysis' && (
                  <button
                    onClick={generateRender}
                    disabled={loading}
                    className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        Generating 3D Model...
                      </span>
                    ) : (
                      'Generate 3D Visualization'
                    )}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Initial Render + Chat Panel (side by side) */}
      {render && (workflowStage === 'render' || workflowStage === 'chat') && analysis && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Render Image */}
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
          </div>

          {/* Chat Panel */}
          <ChatPanel
            designId={analysis.design_id}
            onReadyToRender={handleReadyToRender}
          />
        </div>
      )}

      {/* Refined Render */}
      {refinedRender && (workflowStage === 'refined-render') && (
        <div className="card animate-scale-in">
          <h3 className="text-2xl font-display font-bold mb-6">Refined 3D Visualization</h3>
          <div className="relative aspect-video bg-neutral-900 rounded-lg overflow-hidden mb-6">
            <Image
              src={refinedRender.image_url}
              alt="Refined 3D Render"
              fill
              className="object-contain"
            />
          </div>

          <div className="grid grid-cols-3 gap-4 text-center mb-6">
            <div className="p-4 bg-neutral-50 rounded-lg">
              <p className="text-sm text-neutral-600 mb-1">Render ID</p>
              <p className="font-mono text-xs text-neutral-900">{refinedRender.render_id.slice(0, 8)}...</p>
            </div>
            <div className="p-4 bg-neutral-50 rounded-lg">
              <p className="text-sm text-neutral-600 mb-1">Design ID</p>
              <p className="font-mono text-xs text-neutral-900">{refinedRender.design_id.slice(0, 8)}...</p>
            </div>
            <div className="p-4 bg-neutral-50 rounded-lg">
              <p className="text-sm text-neutral-600 mb-1">Created At</p>
              <p className="font-medium text-neutral-900">{new Date(refinedRender.created_at).toLocaleDateString()}</p>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={generateVideo}
              disabled={loading}
              className="btn-primary flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  Starting Video Generation...
                </span>
              ) : (
                'Generate Video'
              )}
            </button>
            <a
              href={refinedRender.image_url}
              download={`render-${refinedRender.render_id.slice(0, 8)}.png`}
              className="flex items-center gap-2 px-4 py-2.5 border border-neutral-300 rounded-xl text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download Image
            </a>
          </div>
        </div>
      )}

      {/* Video Status */}
      {videoId && workflowStage === 'video' && (
        <VideoStatusIndicator
          videoId={videoId}
          onRetry={handleVideoRetry}
        />
      )}

      {/* CAD/BIM Export Panel */}
      {analysis && (workflowStage === 'video' || workflowStage === 'export' || workflowStage === 'refined-render') && (
        <div className="card animate-fade-in">
          <h3 className="text-2xl font-display font-bold mb-2">Export Design</h3>
          <p className="text-sm text-neutral-500 mb-6">
            Download your design for use in AutoCAD, Revit, SketchUp, or Blender.
          </p>

          {exportError && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {exportError}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { format: 'DXF', label: 'DXF', desc: 'AutoCAD / BricsCAD', icon: '📐' },
              { format: 'IFC', label: 'IFC', desc: 'Revit / ArchiCAD', icon: '🏗️' },
              { format: 'OBJ', label: 'OBJ', desc: 'Blender / SketchUp', icon: '🎨' },
            ].map(({ format, label, desc, icon }) => (
              <button
                key={format}
                onClick={() => handleExport(format)}
                disabled={exportLoading !== null}
                className="flex items-center gap-3 p-4 border border-neutral-200 rounded-xl hover:border-primary-400 hover:bg-primary-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-left"
              >
                <span className="text-2xl">{icon}</span>
                <div className="flex-1">
                  <p className="font-semibold text-neutral-900">{label}</p>
                  <p className="text-xs text-neutral-500">{desc}</p>
                </div>
                {exportLoading === format ? (
                  <svg className="animate-spin h-5 w-5 text-primary-600" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
