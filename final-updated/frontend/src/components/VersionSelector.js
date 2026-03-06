import React from 'react';
import './VersionSelector.css';

/**
 * VersionSelector Component
 * 
 * Dropdown selector for choosing design versions with metadata display
 */
const VersionSelector = ({ 
  versions, 
  selectedVersion, 
  onVersionSelect, 
  placeholder = "Select a version",
  disabled = false 
}) => {
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const getVersionDisplayName = (version) => {
    const versionNumber = `v${version.versionNumber}`;
    const author = version.metadata.author || 'Unknown';
    const date = formatDate(version.createdAt);
    
    return `${versionNumber} - ${author} (${date})`;
  };

  const getVersionDescription = (version) => {
    const comment = version.metadata.comment;
    const changes = version.changesSummary;
    
    let description = '';
    if (comment) {
      description += comment;
    }
    
    if (changes.totalChanges > 0) {
      const changeParts = [];
      if (changes.elementsAdded > 0) changeParts.push(`+${changes.elementsAdded} added`);
      if (changes.elementsModified > 0) changeParts.push(`~${changes.elementsModified} modified`);
      if (changes.elementsDeleted > 0) changeParts.push(`-${changes.elementsDeleted} deleted`);
      
      if (changeParts.length > 0) {
        description += (description ? ' • ' : '') + changeParts.join(', ');
      }
    }
    
    return description || 'No description available';
  };

  const getVersionStatusBadge = (version) => {
    const status = version.status;
    const isMainline = version.metadata.milestone;
    
    if (isMainline) return 'milestone';
    return status;
  };

  return (
    <div className="version-selector">
      <select
        value={selectedVersion?.id || ''}
        onChange={(e) => {
          const version = versions.find(v => v.id === e.target.value);
          onVersionSelect(version);
        }}
        disabled={disabled || versions.length === 0}
        className="version-select"
      >
        <option value="" disabled>
          {versions.length === 0 ? 'No versions available' : placeholder}
        </option>
        
        {versions.map((version) => (
          <option key={version.id} value={version.id}>
            {getVersionDisplayName(version)}
          </option>
        ))}
      </select>
      
      {selectedVersion && (
        <div className="version-details">
          <div className="version-header">
            <span className="version-number">v{selectedVersion.versionNumber}</span>
            <span className={`version-status ${getVersionStatusBadge(selectedVersion)}`}>
              {getVersionStatusBadge(selectedVersion)}
            </span>
            {selectedVersion.metadata.tags && selectedVersion.metadata.tags.length > 0 && (
              <div className="version-tags">
                {selectedVersion.metadata.tags.map((tag, index) => (
                  <span key={index} className="version-tag">{tag}</span>
                ))}
              </div>
            )}
          </div>
          
          <div className="version-metadata">
            <div className="metadata-row">
              <span className="metadata-label">Author:</span>
              <span className="metadata-value">{selectedVersion.metadata.author}</span>
            </div>
            <div className="metadata-row">
              <span className="metadata-label">Created:</span>
              <span className="metadata-value">{formatDate(selectedVersion.createdAt)}</span>
            </div>
            <div className="metadata-row">
              <span className="metadata-label">Changes:</span>
              <span className="metadata-value">
                {selectedVersion.changesSummary.totalChanges} total changes
              </span>
            </div>
          </div>
          
          <div className="version-description">
            {getVersionDescription(selectedVersion)}
          </div>
          
          {selectedVersion.changesSummary.totalChanges > 0 && (
            <div className="changes-summary">
              <div className="change-counts">
                {selectedVersion.changesSummary.elementsAdded > 0 && (
                  <span className="change-count added">
                    +{selectedVersion.changesSummary.elementsAdded} added
                  </span>
                )}
                {selectedVersion.changesSummary.elementsModified > 0 && (
                  <span className="change-count modified">
                    ~{selectedVersion.changesSummary.elementsModified} modified
                  </span>
                )}
                {selectedVersion.changesSummary.elementsDeleted > 0 && (
                  <span className="change-count deleted">
                    -{selectedVersion.changesSummary.elementsDeleted} deleted
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default VersionSelector;