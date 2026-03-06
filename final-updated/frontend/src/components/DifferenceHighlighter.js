import React, { useState, useMemo } from 'react';
import './DifferenceHighlighter.css';

/**
 * DifferenceHighlighter Component
 * 
 * Displays and highlights differences between versions with filtering and grouping
 */
const DifferenceHighlighter = ({ comparison, sourceVersion, targetVersion }) => {
  const [filterBy, setFilterBy] = useState('all'); // 'all', 'high', 'medium', 'low'
  const [groupBy, setGroupBy] = useState('element'); // 'element', 'type', 'impact'
  const [sortBy, setSortBy] = useState('impact'); // 'impact', 'element', 'type'
  const [expandedGroups, setExpandedGroups] = useState(new Set());
  const [selectedDifference, setSelectedDifference] = useState(null);

  // Process and filter differences
  const processedDifferences = useMemo(() => {
    let differences = comparison?.differences || [];
    
    // Filter by impact
    if (filterBy !== 'all') {
      differences = differences.filter(diff => diff.impact === filterBy);
    }
    
    // Sort differences
    differences.sort((a, b) => {
      switch (sortBy) {
        case 'impact':
          const impactOrder = { high: 3, medium: 2, low: 1 };
          return impactOrder[b.impact] - impactOrder[a.impact];
        case 'element':
          return a.elementId.localeCompare(b.elementId);
        case 'type':
          return (a.changeType || '').localeCompare(b.changeType || '');
        default:
          return 0;
      }
    });
    
    return differences;
  }, [comparison?.differences, filterBy, sortBy]);

  // Group differences
  const groupedDifferences = useMemo(() => {
    const groups = {};
    
    processedDifferences.forEach(diff => {
      let groupKey;
      
      switch (groupBy) {
        case 'element':
          groupKey = diff.elementId;
          break;
        case 'type':
          groupKey = diff.changeType || 'unknown';
          break;
        case 'impact':
          groupKey = diff.impact;
          break;
        default:
          groupKey = 'all';
      }
      
      if (!groups[groupKey]) {
        groups[groupKey] = [];
      }
      groups[groupKey].push(diff);
    });
    
    return groups;
  }, [processedDifferences, groupBy]);

  const getChangeTypeIcon = (changeType) => {
    switch (changeType) {
      case 'created': return '➕';
      case 'modified': return '✏️';
      case 'deleted': return '🗑️';
      case 'restored': return '↩️';
      case 'merged': return '🔀';
      default: return '❓';
    }
  };

  const getImpactColor = (impact) => {
    switch (impact) {
      case 'high': return '#ff4444';
      case 'medium': return '#ff8800';
      case 'low': return '#44aa44';
      default: return '#666666';
    }
  };

  const toggleGroup = (groupKey) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(groupKey)) {
      newExpanded.delete(groupKey);
    } else {
      newExpanded.add(groupKey);
    }
    setExpandedGroups(newExpanded);
  };

  const renderDifference = (difference, index) => {
    const isSelected = selectedDifference === difference;
    
    return (
      <div
        key={`${difference.elementId}-${index}`}
        className={`difference-item ${difference.impact} ${isSelected ? 'selected' : ''}`}
        onClick={() => setSelectedDifference(isSelected ? null : difference)}
      >
        <div className="difference-header">
          <span className="change-icon">
            {getChangeTypeIcon(difference.changeType)}
          </span>
          <span className="element-id">{difference.elementId}</span>
          <span 
            className="impact-badge"
            style={{ backgroundColor: getImpactColor(difference.impact) }}
          >
            {difference.impact}
          </span>
        </div>
        
        <div className="difference-description">
          {difference.description}
        </div>
        
        {difference.property && (
          <div className="difference-property">
            <strong>Property:</strong> <code>{difference.property}</code>
          </div>
        )}
        
        {isSelected && (
          <div className="difference-details">
            {difference.sourceValue !== undefined && (
              <div className="value-comparison">
                <div className="old-value">
                  <strong>Before:</strong>
                  <pre>{JSON.stringify(difference.sourceValue, null, 2)}</pre>
                </div>
                <div className="new-value">
                  <strong>After:</strong>
                  <pre>{JSON.stringify(difference.targetValue, null, 2)}</pre>
                </div>
              </div>
            )}
            
            <div className="difference-metadata">
              <div><strong>Change Type:</strong> {difference.changeType}</div>
              <div><strong>Element ID:</strong> {difference.elementId}</div>
              {difference.property && (
                <div><strong>Property Path:</strong> {difference.property}</div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderGroup = (groupKey, differences) => {
    const isExpanded = expandedGroups.has(groupKey);
    const groupStats = {
      total: differences.length,
      high: differences.filter(d => d.impact === 'high').length,
      medium: differences.filter(d => d.impact === 'medium').length,
      low: differences.filter(d => d.impact === 'low').length,
    };
    
    return (
      <div key={groupKey} className="difference-group">
        <div 
          className="group-header"
          onClick={() => toggleGroup(groupKey)}
        >
          <span className="expand-icon">
            {isExpanded ? '▼' : '▶'}
          </span>
          <span className="group-title">{groupKey}</span>
          <div className="group-stats">
            <span className="total-count">{groupStats.total} changes</span>
            {groupStats.high > 0 && (
              <span className="impact-count high">{groupStats.high} high</span>
            )}
            {groupStats.medium > 0 && (
              <span className="impact-count medium">{groupStats.medium} medium</span>
            )}
            {groupStats.low > 0 && (
              <span className="impact-count low">{groupStats.low} low</span>
            )}
          </div>
        </div>
        
        {isExpanded && (
          <div className="group-content">
            {differences.map((diff, index) => renderDifference(diff, index))}
          </div>
        )}
      </div>
    );
  };

  const renderSummaryStats = () => {
    const stats = {
      total: processedDifferences.length,
      high: processedDifferences.filter(d => d.impact === 'high').length,
      medium: processedDifferences.filter(d => d.impact === 'medium').length,
      low: processedDifferences.filter(d => d.impact === 'low').length,
      elements: new Set(processedDifferences.map(d => d.elementId)).size,
    };
    
    return (
      <div className="summary-stats">
        <div className="stat-item">
          <span className="stat-label">Total Changes:</span>
          <span className="stat-value">{stats.total}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Elements Affected:</span>
          <span className="stat-value">{stats.elements}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">High Impact:</span>
          <span className="stat-value high">{stats.high}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Medium Impact:</span>
          <span className="stat-value medium">{stats.medium}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Low Impact:</span>
          <span className="stat-value low">{stats.low}</span>
        </div>
      </div>
    );
  };

  if (!comparison || !comparison.differences || comparison.differences.length === 0) {
    return (
      <div className="difference-highlighter empty">
        <div className="empty-state">
          <h3>No Differences Found</h3>
          <p>The selected versions are identical or no comparison has been performed.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="difference-highlighter">
      <div className="highlighter-header">
        <h3>Version Differences</h3>
        
        {/* Controls */}
        <div className="highlighter-controls">
          <div className="control-group">
            <label>Filter by Impact:</label>
            <select value={filterBy} onChange={(e) => setFilterBy(e.target.value)}>
              <option value="all">All Changes</option>
              <option value="high">High Impact</option>
              <option value="medium">Medium Impact</option>
              <option value="low">Low Impact</option>
            </select>
          </div>
          
          <div className="control-group">
            <label>Group by:</label>
            <select value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
              <option value="element">Element</option>
              <option value="type">Change Type</option>
              <option value="impact">Impact Level</option>
            </select>
          </div>
          
          <div className="control-group">
            <label>Sort by:</label>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="impact">Impact Level</option>
              <option value="element">Element ID</option>
              <option value="type">Change Type</option>
            </select>
          </div>
        </div>
        
        {/* Summary Stats */}
        {renderSummaryStats()}
      </div>
      
      {/* Differences List */}
      <div className="differences-content">
        {Object.entries(groupedDifferences).map(([groupKey, differences]) =>
          renderGroup(groupKey, differences)
        )}
      </div>
      
      {/* Legend */}
      <div className="differences-legend">
        <h4>Legend</h4>
        <div className="legend-items">
          <div className="legend-item">
            <span className="icon">➕</span>
            <span>Created</span>
          </div>
          <div className="legend-item">
            <span className="icon">✏️</span>
            <span>Modified</span>
          </div>
          <div className="legend-item">
            <span className="icon">🗑️</span>
            <span>Deleted</span>
          </div>
          <div className="legend-item">
            <span className="impact-badge" style={{ backgroundColor: '#ff4444' }}>High</span>
            <span>High Impact</span>
          </div>
          <div className="legend-item">
            <span className="impact-badge" style={{ backgroundColor: '#ff8800' }}>Med</span>
            <span>Medium Impact</span>
          </div>
          <div className="legend-item">
            <span className="impact-badge" style={{ backgroundColor: '#44aa44' }}>Low</span>
            <span>Low Impact</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DifferenceHighlighter;