import React, { useState, useEffect } from 'react';
import versionService from '../services/versionService';
import VersionSelector from './VersionSelector';
import SideBySideView from './SideBySideView';
import DifferenceHighlighter from './DifferenceHighlighter';
import VersionNavigator from './VersionNavigator';
import './VersionComparison.css';

/**
 * VersionComparison Component
 * 
 * Main component for comparing design versions with side-by-side views,
 * difference highlighting, and version navigation functionality.
 */
const VersionComparison = ({ designId, initialSourceVersion, initialTargetVersion }) => {
  const [versions, setVersions] = useState([]);
  const [sourceVersion, setSourceVersion] = useState(initialSourceVersion);
  const [targetVersion, setTargetVersion] = useState(initialTargetVersion);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [comparisonOptions, setComparisonOptions] = useState({
    includeVisualChanges: true,
    includeSpatialChanges: true,
    includeMaterialChanges: true,
    ignoreMinorChanges: false,
    minorChangeThreshold: 0.01,
  });
  const [viewMode, setViewMode] = useState('side-by-side'); // 'side-by-side', 'overlay', 'differences-only'

  // Load version history on component mount
  useEffect(() => {
    if (designId) {
      loadVersionHistory();
    }
  }, [designId]);

  // Perform comparison when versions change
  useEffect(() => {
    if (sourceVersion && targetVersion && sourceVersion.id !== targetVersion.id) {
      performComparison();
    }
  }, [sourceVersion, targetVersion, comparisonOptions]);

  const loadVersionHistory = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const versionHistory = await versionService.getVersionHistory(designId, 50);
      setVersions(versionHistory.versions || []);
      
      // Set default versions if not provided
      if (!sourceVersion && versionHistory.versions.length > 1) {
        setSourceVersion(versionHistory.versions[1]); // Second most recent
      }
      if (!targetVersion && versionHistory.versions.length > 0) {
        setTargetVersion(versionHistory.versions[0]); // Most recent
      }
    } catch (err) {
      setError(`Failed to load version history: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const performComparison = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const comparisonResult = await versionService.compareVersions(
        sourceVersion.id,
        targetVersion.id,
        comparisonOptions
      );
      
      setComparison(comparisonResult);
    } catch (err) {
      setError(`Failed to compare versions: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleVersionSwap = () => {
    const temp = sourceVersion;
    setSourceVersion(targetVersion);
    setTargetVersion(temp);
  };

  const handleVersionNavigation = (direction, versionType) => {
    const currentVersion = versionType === 'source' ? sourceVersion : targetVersion;
    const currentIndex = versions.findIndex(v => v.id === currentVersion.id);
    
    let newIndex;
    if (direction === 'next' && currentIndex > 0) {
      newIndex = currentIndex - 1; // Newer version (lower index)
    } else if (direction === 'previous' && currentIndex < versions.length - 1) {
      newIndex = currentIndex + 1; // Older version (higher index)
    } else {
      return; // No navigation possible
    }
    
    const newVersion = versions[newIndex];
    if (versionType === 'source') {
      setSourceVersion(newVersion);
    } else {
      setTargetVersion(newVersion);
    }
  };

  const handleRestoreVersion = async (versionId) => {
    try {
      setLoading(true);
      const restoredVersion = await versionService.restoreVersion(
        versionId,
        `Restored version ${versionId} via comparison tool`
      );
      
      // Refresh version history to include the new restored version
      await loadVersionHistory();
      
      // Optionally set the restored version as the target
      setTargetVersion(restoredVersion);
      
      alert('Version restored successfully!');
    } catch (err) {
      setError(`Failed to restore version: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !comparison) {
    return (
      <div className="version-comparison-loading">
        <div className="loading-spinner"></div>
        <p>Loading version comparison...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="version-comparison-error">
        <h3>Error</h3>
        <p>{error}</p>
        <button onClick={loadVersionHistory} className="retry-button">
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="version-comparison">
      <div className="version-comparison-header">
        <h2>Version Comparison</h2>
        
        {/* Version Selectors */}
        <div className="version-selectors">
          <div className="version-selector-group">
            <label>Source Version (From):</label>
            <VersionSelector
              versions={versions}
              selectedVersion={sourceVersion}
              onVersionSelect={setSourceVersion}
              placeholder="Select source version"
            />
          </div>
          
          <button 
            className="swap-versions-button"
            onClick={handleVersionSwap}
            title="Swap versions"
          >
            ⇄
          </button>
          
          <div className="version-selector-group">
            <label>Target Version (To):</label>
            <VersionSelector
              versions={versions}
              selectedVersion={targetVersion}
              onVersionSelect={setTargetVersion}
              placeholder="Select target version"
            />
          </div>
        </div>

        {/* Comparison Options */}
        <div className="comparison-options">
          <h4>Comparison Options</h4>
          <div className="options-grid">
            <label>
              <input
                type="checkbox"
                checked={comparisonOptions.includeVisualChanges}
                onChange={(e) => setComparisonOptions(prev => ({
                  ...prev,
                  includeVisualChanges: e.target.checked
                }))}
              />
              Include Visual Changes
            </label>
            
            <label>
              <input
                type="checkbox"
                checked={comparisonOptions.includeSpatialChanges}
                onChange={(e) => setComparisonOptions(prev => ({
                  ...prev,
                  includeSpatialChanges: e.target.checked
                }))}
              />
              Include Spatial Changes
            </label>
            
            <label>
              <input
                type="checkbox"
                checked={comparisonOptions.includeMaterialChanges}
                onChange={(e) => setComparisonOptions(prev => ({
                  ...prev,
                  includeMaterialChanges: e.target.checked
                }))}
              />
              Include Material Changes
            </label>
            
            <label>
              <input
                type="checkbox"
                checked={comparisonOptions.ignoreMinorChanges}
                onChange={(e) => setComparisonOptions(prev => ({
                  ...prev,
                  ignoreMinorChanges: e.target.checked
                }))}
              />
              Ignore Minor Changes
            </label>
          </div>
        </div>

        {/* View Mode Selector */}
        <div className="view-mode-selector">
          <label>View Mode:</label>
          <select 
            value={viewMode} 
            onChange={(e) => setViewMode(e.target.value)}
          >
            <option value="side-by-side">Side by Side</option>
            <option value="overlay">Overlay</option>
            <option value="differences-only">Differences Only</option>
          </select>
        </div>
      </div>

      {/* Version Navigator */}
      {sourceVersion && targetVersion && (
        <VersionNavigator
          versions={versions}
          sourceVersion={sourceVersion}
          targetVersion={targetVersion}
          onNavigate={handleVersionNavigation}
          onRestore={handleRestoreVersion}
        />
      )}

      {/* Comparison Summary */}
      {comparison && (
        <div className="comparison-summary">
          <h3>Comparison Summary</h3>
          <div className="summary-stats">
            <div className="stat">
              <span className="stat-label">Total Differences:</span>
              <span className="stat-value">{comparison.summary.totalDifferences}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Elements Changed:</span>
              <span className="stat-value">{comparison.summary.elementsChanged}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Compatibility Score:</span>
              <span className="stat-value">
                {(comparison.summary.compatibilityScore * 100).toFixed(1)}%
              </span>
            </div>
          </div>
          
          {comparison.mergeAnalysis.conflicts.length > 0 && (
            <div className="conflicts-warning">
              <h4>⚠️ Conflicts Detected</h4>
              <p>{comparison.mergeAnalysis.conflicts.length} conflicts found that require attention.</p>
            </div>
          )}
        </div>
      )}

      {/* Main Comparison View */}
      {sourceVersion && targetVersion && comparison && (
        <div className="comparison-content">
          {viewMode === 'side-by-side' && (
            <SideBySideView
              sourceVersion={sourceVersion}
              targetVersion={targetVersion}
              comparison={comparison}
              loading={loading}
            />
          )}
          
          {viewMode === 'differences-only' && (
            <DifferenceHighlighter
              comparison={comparison}
              sourceVersion={sourceVersion}
              targetVersion={targetVersion}
            />
          )}
          
          {viewMode === 'overlay' && (
            <div className="overlay-view">
              <p>Overlay view coming soon...</p>
            </div>
          )}
        </div>
      )}

      {loading && comparison && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <p>Updating comparison...</p>
        </div>
      )}
    </div>
  );
};

export default VersionComparison;