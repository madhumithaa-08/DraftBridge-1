'use client';

import { useState, useEffect, useRef } from 'react';

interface VideoStatusIndicatorProps {
  videoId: string;
  onRetry: () => void;
}

export default function VideoStatusIndicator({ videoId, onRetry }: VideoStatusIndicatorProps) {
  const [status, setStatus] = useState<'processing' | 'complete' | 'failed'>('processing');
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    const pollStatus = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/videos/${videoId}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch video status (${response.status})`);
        }
        const data = await response.json();

        if (data.status === 'complete') {
          setStatus('complete');
          setVideoUrl(data.video_url);
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        } else if (data.status === 'failed') {
          setStatus('failed');
          setError(data.error || 'Video generation failed');
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        }
      } catch (err) {
        setStatus('failed');
        setError(err instanceof Error ? err.message : 'Failed to check video status');
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    };

    pollStatus();
    intervalRef.current = setInterval(pollStatus, 5000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [videoId, apiUrl]);

  if (status === 'processing') {
    return (
      <div className="card">
        <div className="flex flex-col items-center justify-center py-8 space-y-4">
          <div className="relative w-12 h-12">
            <div className="absolute inset-0 rounded-full border-4 border-neutral-200" />
            <div className="absolute inset-0 rounded-full border-4 border-primary-500 border-t-transparent animate-spin" />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-neutral-700">
              Generating walkthrough video...
            </p>
            <p className="text-xs text-neutral-400 mt-1">
              This may take a few minutes
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (status === 'complete' && videoUrl) {
    return (
      <div className="card">
        <div className="flex items-center gap-2 pb-3 border-b border-neutral-200 mb-4">
          <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm font-medium text-green-700">Video Ready</span>
        </div>
        <video
          src={videoUrl}
          controls
          autoPlay={false}
          className="w-full rounded-lg"
        >
          Your browser does not support the video tag.
        </video>
        <div className="mt-4 flex justify-end">
          <a
            href={videoUrl}
            download={`walkthrough-${videoId.slice(0, 8)}.mp4`}
            className="flex items-center gap-2 px-4 py-2.5 border border-neutral-300 rounded-xl text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download Video
          </a>
        </div>
      </div>
    );
  }

  if (status === 'failed') {
    return (
      <div className="card">
        <div className="flex flex-col items-center justify-center py-8 space-y-4">
          <svg className="w-12 h-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-center">
            <p className="text-sm font-medium text-red-700">
              Video generation failed
            </p>
            {error && (
              <p className="text-xs text-neutral-500 mt-1">{error}</p>
            )}
          </div>
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-primary-600 text-white rounded-xl text-sm font-medium hover:bg-primary-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return null;
}
