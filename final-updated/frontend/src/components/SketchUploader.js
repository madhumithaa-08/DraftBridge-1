import { useState } from 'react'
import Image from 'next/image'

export default function SketchUploader() {
  const [file, setFile] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [render, setRender] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleFileUpload = (event) => {
    const selectedFile = event.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setAnalysis(null)
      setRender(null)
    }
  }

  const analyzeSketch = async () => {
    if (!file) return
    
    setLoading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/sketches`, {
        method: 'POST',
        body: formData,
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Analysis failed')
      }

      const result = await response.json()
      setAnalysis(result)
    } catch (error) {
      console.error('Analysis failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const generateRender = async () => {
    if (!analysis) return
    
    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/renders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          design_id: analysis.design_id,
          style: 'photorealistic',
          materials: {},
          lighting: 'natural',
        }),
      })
      
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Render generation failed')
      }

      const result = await response.json()
      setRender(result)
    } catch (error) {
      console.error('Render failed:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-8">DraftBridge - AI Architectural Co-pilot</h1>
      
      {/* File Upload */}
      <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 mb-6">
        <input
          type="file"
          accept="image/*"
          onChange={handleFileUpload}
          className="mb-4"
        />
        {file && (
          <div className="mt-4">
            <p className="text-sm text-gray-600">Selected: {file.name}</p>
            <button
              onClick={analyzeSketch}
              disabled={loading}
              className="mt-2 bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:opacity-50"
            >
              {loading ? 'Analyzing...' : 'Analyze Sketch'}
            </button>
          </div>
        )}
      </div>

      {/* Analysis Results */}
      {analysis && (
        <div className="bg-gray-50 p-6 rounded-lg mb-6">
          <h2 className="text-xl font-semibold mb-4">Analysis Results</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h3 className="font-medium">Design ID:</h3>
              <p className="font-mono text-sm">{analysis.design_id}</p>
            </div>
            <div>
              <h3 className="font-medium">Status:</h3>
              <p className="capitalize">{analysis.status}</p>
            </div>
          </div>
          <div className="mt-4">
            <h3 className="font-medium">Sketch ID:</h3>
            <p className="font-mono text-sm">{analysis.sketch_id}</p>
          </div>
          <div className="mt-2">
            <h3 className="font-medium">Uploaded At:</h3>
            <p className="text-sm">{new Date(analysis.uploaded_at).toLocaleString()}</p>
          </div>
          <button
            onClick={generateRender}
            disabled={loading}
            className="mt-4 bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600 disabled:opacity-50"
          >
            {loading ? 'Generating...' : 'Generate 3D Render'}
          </button>
        </div>
      )}

      {/* Render Results */}
      {render && (
        <div className="bg-gray-50 p-6 rounded-lg">
          <h2 className="text-xl font-semibold mb-4">3D Visualization</h2>
          {render.image_url && (
            <img
              src={render.image_url}
              alt="Generated 3D Render"
              className="max-w-full h-auto rounded-lg shadow-lg"
            />
          )}
          <div className="mt-4 text-sm text-gray-600">
            <p>Render ID: {render.render_id}</p>
            <p>Design ID: {render.design_id}</p>
            <p>Created: {new Date(render.created_at).toLocaleString()}</p>
          </div>
        </div>
      )}
    </div>
  )
}
