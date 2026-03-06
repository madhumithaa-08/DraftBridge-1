import React, { useState, useEffect } from 'react';
import './SideBySideView.css';

/**
 * SideBySideView Component
 * 
 * Displays two design versions side by side with synchronized navigation
 * and difference highlighting
 */
const SideBySideView = ({ sourceVersion, targetVersion, comparison, loading }) => {
  const [selectedElement, setSelectedElement] = useState(null);
  const [highlightDifferences, setHighlightDifferences] = useState(true);
  const [syncNavigation, setSyncNavigation] = useState(true);
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panPosition, setPanPosition] = useState({ x: 0, y: 0 });

  // Reset view when versions change
  useEffect(() => {
    setSelectedElement(null);
    setZoomLevel(1);
    setPanPosition({ x: 0, y: 0 });
  }, [sourceVersion?.id, targetVersion?.id]);

  const renderVersionView = (version, isSource = true) => {
    const versionType = isSource ? 'source' : 'target';
    const elements = version.designSnapshot.elements || [];
    
    return (
      <div className={`version-view ${versionType}`}>
        <div className="version-header">
          <h4>
            {isSource ? 'Source' : 'Target'} Version: v{version.versionNumber}
          </h4>
          <div className="version-info">
            <span className="author">{version.metadata.author}</span>
            <span className="date">
              {new Date(version.createdAt).toLocaleDateString()}
            </span>
          </div>
        </div>
        
        <div className="version-viewport">
          <div 
            className="design-canvas"
            style={{
              transform: `scale(${zoomLevel}) translate(${panPosition.x}px, ${panPosition.y}px)`
            }}
          >
            {/* Render design elements */}
            {elements.map((element, index) => {
              const elementDifferences = comparison?.differences.filter(
                diff => diff.elementId === element.id
              ) || [];
              
              const hasChanges = elementDifferences.length > 0;
              const isSelected = selectedElement === element.id;
              
              return (
                <div
                  key={element.id || index}
                  className={`design-element ${hasChanges && highlightDifferences ? 'has-changes' : ''} ${isSelected ? 'selected' : ''}`}
                  onClick={() => setSelectedElement(element.id)}
                  style={getElementStyle(element)}
                  title={getElementTooltip(element, elementDifferences)}
                >
                  <div className="element-content">
                    {renderElementContent(element)}
                  </div>
                  
                  {hasChanges && highlightDifferences && (
                    <div className="change-indicator">
                      <span className="change-count">{elementDifferences.length}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
        
        <div className="version-stats">
          <span>Elements: {elements.length}</span>
          {comparison && (
            <span>
              Changes: {comparison.differences.filter(d => 
                elements.some(e => e.id === d.elementId)
              ).length}
            </span>
          )}
        </div>
      </div>
    );
  };

  const getElementStyle = (element) => {
    const spatial = element.spatialProperties;
    const visual = element.visualProperties;
    
    return {
      position: 'absolute',
      left: `${spatial.position.x}px`,
      top: `${spatial.position.y}px`,
      width: `${spatial.boundingBox.max.x - spatial.boundingBox.min.x}px`,
      height: `${spatial.boundingBox.max.y - spatial.boundingBox.min.y}px`,
      backgroundColor: visual.color || '#f0f0f0',
      opacity: visual.opacity || 1,
      border: '1px solid #ccc',
      borderRadius: '4px',
    };
  };

  const renderElementContent = (element) => {
    const material = element.materialProperties;
    return (
      <div className="element-info">
        <div className="element-name">{material.name}</div>
        <div className="element-type">{material.type}</div>
      </div>
    );
  };

  const getElementTooltip = (element, differences) => {
    let tooltip = `${element.materialProperties.name} (${element.materialProperties.type})`;
    
    if (differences.length > 0) {
      tooltip += `\n\nChanges:\n${differences.map(d => `• ${d.description}`).join('\n')}`;
    }
    
    return tooltip;
  };

  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(prev * 1.2, 3));
  };

  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(prev / 1.2, 0.1));
  };

  const handleResetView = () => {
    setZoomLevel(1);
    setPanPosition({ x: 0, y: 0 });
  };

  const renderElementDetails = () => {
    if (!selectedElement || !comparison) return null;
    
    const elementDifferences = comparison.differences.filter(
      diff => diff.elementId === selectedElement
    );
    
    if (elementDifferences.length === 0) return null;
    
    return (
      <div className="element-details">
        <h4>Element Changes</h4>
        <div className="changes-list">
          {elementDifferences.map((diff, index) => (
            <div key={index} className={`change-item ${diff.impact}`}>
              <div className="change-header">
                <span className="change-type">{diff.changeType}</span>
                <span className={`impact-badge ${diff.impact}`}>{diff.impact}</span>
              </div>
              <div className="change-description">{diff.description}</div>
              {diff.property && (
                <div className="change-property">
                  Property: <code>{diff.property}</code>
                </div>
              )}
              {diff.sourceValue !== undefined && diff.targetValue !== undefined && (
                <div className="change-values">
                  <div className="old-value">
                    From: <code>{JSON.stringify(diff.sourceValue)}</code>
                  </div>
                  <div className="new-value">
                    To: <code>{JSON.stringify(diff.targetValue)}</code>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="side-by-side-loading">
        <div className="loading-spinner"></div>
        <p>Loading comparison view...</p>
      </div>
    );
  }

  return (
    <div className="side-by-side-view">
      {/* Controls */}
      <div className="view-controls">
        <div className="control-group">
          <label>
            <input
              type="checkbox"
              checked={highlightDifferences}
              onChange={(e) => setHighlightDifferences(e.target.checked)}
            />
            Highlight Differences
          </label>
          
          <label>
            <input
              type="checkbox"
              checked={syncNavigation}
              onChange={(e) => setSyncNavigation(e.target.checked)}
            />
            Sync Navigation
          </label>
        </div>
        
        <div className="zoom-controls">
          <button onClick={handleZoomOut} title="Zoom Out">−</button>
          <span className="zoom-level">{Math.round(zoomLevel * 100)}%</span>
          <button onClick={handleZoomIn} title="Zoom In">+</button>
          <button onClick={handleResetView} title="Reset View">⌂</button>
        </div>
      </div>

      {/* Side by Side Views */}
      <div className="comparison-views">
        {renderVersionView(sourceVersion, true)}
        {renderVersionView(targetVersion, false)}
      </div>

      {/* Element Details Panel */}
      {selectedElement && renderElementDetails()}
    </div>
  );
};

export default SideBySideView;