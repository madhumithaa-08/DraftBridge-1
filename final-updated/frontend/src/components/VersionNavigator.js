import React, { useState } from 'react';
import './VersionNavigator.css';

/**
 * VersionNavigator Component
 * 
 * Provides navigation controls for moving between versions and restoration functionality
 */
const VersionNavigator = ({ 
  versions, 
  sourceVersion, 
  targetVersion, 
  onNavigate, 
  onRestore 
}) => {
  const [showRestoreConfirm, setShowRestoreConfirm] = useState(null);

  const getVersionIndex = (version) => {
    return versions.findIndex(v => v.id === version.id);
  };

  const canNavigate = (version, direction) => {
    const index = getVersionIndex(version);
    if (direction === 'next') {
      return index > 0; // Can go to newer version
    } else {
      return index < versions.length - 1; // Can go to older version
    }
  };

  const getNavigationInfo = (version, direction) => {
    const index = getVersionIndex(version);
    let targetIndex;
    
    if (direction === 'next' && index > 0) {
      targetIndex = index - 1;
    } else if (direction === 'previous' && index < versions.length - 1) {
      targetIndex = index + 1;
    } else {
      return null;
    }
    
    const targetVersion = versions[targetIndex];
    return {
      version: targetVersion,
      versionNumber: targetVersion.versionNumber,
      author: targetVersion.metadata.author,
      date: new Date(targetVersion.createdAt).toLocaleDateString(),
    };
  };

  const handleRestore = (versionId) => {
    if (showRestoreConfirm === versionId) {
      onRestore(versionId);
      setShowRestoreConfirm(null);
    } else {
      setShowRestoreConfirm(versionId);
    }
  };

  const renderVersionCard = (version, type) => {
    const isSource = type === 'source';
    const canGoNext = canNavigate(version, 'next');
    const canGoPrevious = canNavigate(version, 'previous');
    const nextInfo = getNavigationInfo(version, 'next');
    const previousInfo = getNavigationInfo(version, 'previous');
    
    return (
      <div className={`version-card ${type}`}>
        <div className="version-card-header">
          <h4>{isSource ? 'Source' : 'Target'} Version</h4>
          <div className="version-actions">
            <button
              className="restore-button"
              onClick={() => handleRestore(version.id)}
              title={`Restore version ${version.versionNumber}`}
            >
              {showRestoreConfirm === version.id ? 'Confirm Restore?' : '↩️ Restore'}
            </button>
          </div>
        </div>
        
        <div className="version-info">
          <div className="version-number">v{version.versionNumber}</div>
          <div className="version-metadata">
            <div className="author">{version.metadata.author}</div>
            <div className="date">
              {new Date(version.createdAt).toLocaleDateString()}
            </div>
          </div>
          {version.metadata.comment && (
            <div className="version-comment">{version.metadata.comment}</div>
          )}
        </div>
        
        <div className="navigation-controls">
          <button
            className="nav-button previous"
            onClick={() => onNavigate('previous', type)}
            disabled={!canGoPrevious}
            title={previousInfo ? `Go to v${previousInfo.versionNumber} by ${previousInfo.author}` : 'No older version'}
          >
            <span className="nav-icon">←</span>
            <span className="nav-label">Older</span>
            {previousInfo && (
              <div className="nav-preview">
                v{previousInfo.versionNumber} - {previousInfo.author}
              </div>
            )}
          </button>
          
          <div className="version-position">
            {getVersionIndex(version) + 1} of {versions.length}
          </div>
          
          <button
            className="nav-button next"
            onClick={() => onNavigate('next', type)}
            disabled={!canGoNext}
            title={nextInfo ? `Go to v${nextInfo.versionNumber} by ${nextInfo.author}` : 'No newer version'}
          >
            <span className="nav-label">Newer</span>
            <span className="nav-icon">→</span>
            {nextInfo && (
              <div className="nav-preview">
                v{nextInfo.versionNumber} - {nextInfo.author}
              </div>
            )}
          </button>
        </div>
        
        {version.changesSummary && version.changesSummary.totalChanges > 0 && (
          <div className="changes-summary">
            <div className="changes-title">Changes in this version:</div>
            <div className="changes-stats">
              {version.changesSummary.elementsAdded > 0 && (
                <span className="change-stat added">
                  +{version.changesSummary.elementsAdded}
                </span>
              )}
              {version.changesSummary.elementsModified > 0 && (
                <span className="change-stat modified">
                  ~{version.changesSummary.elementsModified}
                </span>
              )}
              {version.changesSummary.elementsDeleted > 0 && (
                <span className="change-stat deleted">
                  -{version.changesSummary.elementsDeleted}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderVersionTimeline = () => {
    const sourceIndex = getVersionIndex(sourceVersion);
    const targetIndex = getVersionIndex(targetVersion);
    const minIndex = Math.min(sourceIndex, targetIndex);
    const maxIndex = Math.max(sourceIndex, targetIndex);
    
    return (
      <div className="version-timeline">
        <div className="timeline-header">
          <h4>Version Timeline</h4>
          <div className="timeline-info">
            Comparing {Math.abs(targetIndex - sourceIndex)} version{Math.abs(targetIndex - sourceIndex) !== 1 ? 's' : ''} apart
          </div>
        </div>
        
        <div className="timeline-track">
          {versions.slice(minIndex, maxIndex + 1).map((version, index) => {
            const actualIndex = minIndex + index;
            const isSource = actualIndex === sourceIndex;
            const isTarget = actualIndex === targetIndex;
            const isBetween = actualIndex > minIndex && actualIndex < maxIndex;
            
            return (
              <div
                key={version.id}
                className={`timeline-point ${isSource ? 'source' : ''} ${isTarget ? 'target' : ''} ${isBetween ? 'between' : ''}`}
                title={`v${version.versionNumber} - ${version.metadata.author} (${new Date(version.createdAt).toLocaleDateString()})`}
              >
                <div className="point-marker"></div>
                <div className="point-label">
                  v{version.versionNumber}
                  {isSource && <span className="point-type"> (Source)</span>}
                  {isTarget && <span className="point-type"> (Target)</span>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const renderQuickActions = () => {
    return (
      <div className="quick-actions">
        <h4>Quick Actions</h4>
        <div className="action-buttons">
          <button
            className="action-button"
            onClick={() => {
              // Swap versions
              const temp = sourceVersion;
              onNavigate('swap', 'source');
            }}
            title="Swap source and target versions"
          >
            ⇄ Swap Versions
          </button>
          
          <button
            className="action-button"
            onClick={() => {
              // Go to latest version for target
              if (versions.length > 0) {
                const latestVersion = versions[0];
                if (latestVersion.id !== targetVersion.id) {
                  // This would need to be handled by parent component
                  console.log('Navigate to latest version');
                }
              }
            }}
            title="Set target to latest version"
          >
            📍 Latest Version
          </button>
          
          <button
            className="action-button"
            onClick={() => {
              // Go to first version for source
              if (versions.length > 0) {
                const firstVersion = versions[versions.length - 1];
                if (firstVersion.id !== sourceVersion.id) {
                  // This would need to be handled by parent component
                  console.log('Navigate to first version');
                }
              }
            }}
            title="Set source to first version"
          >
            🏁 First Version
          </button>
        </div>
      </div>
    );
  };

  if (!sourceVersion || !targetVersion || !versions.length) {
    return (
      <div className="version-navigator empty">
        <p>No versions available for navigation</p>
      </div>
    );
  }

  return (
    <div className="version-navigator">
      <div className="navigator-header">
        <h3>Version Navigation</h3>
      </div>
      
      <div className="navigator-content">
        <div className="version-cards">
          {renderVersionCard(sourceVersion, 'source')}
          {renderVersionCard(targetVersion, 'target')}
        </div>
        
        {renderVersionTimeline()}
        {renderQuickActions()}
      </div>
      
      {showRestoreConfirm && (
        <div className="restore-confirm-overlay" onClick={() => setShowRestoreConfirm(null)}>
          <div className="restore-confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <h4>Confirm Version Restore</h4>
            <p>
              Are you sure you want to restore version {versions.find(v => v.id === showRestoreConfirm)?.versionNumber}?
              This will create a new version based on the selected version.
            </p>
            <div className="confirm-actions">
              <button
                className="confirm-button"
                onClick={() => handleRestore(showRestoreConfirm)}
              >
                Yes, Restore
              </button>
              <button
                className="cancel-button"
                onClick={() => setShowRestoreConfirm(null)}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VersionNavigator;