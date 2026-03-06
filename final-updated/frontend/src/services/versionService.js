/**
 * Version Service
 * 
 * Handles API calls related to version management and comparison
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class VersionService {
  constructor() {
    this.baseURL = `${API_BASE_URL}/api/versions`;
  }

  /**
   * Get version history for a design
   */
  async getVersionHistory(designId) {
    try {
      const response = await fetch(`${this.baseURL}/${designId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch version history: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching version history:', error);
      throw error;
    }
  }

  /**
   * Get a specific version by design ID and version number
   */
  async getVersion(designId, version) {
    try {
      const response = await fetch(`${this.baseURL}/${designId}/${version}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch version: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching version:', error);
      throw error;
    }
  }

  /**
   * Compare two versions of a design
   */
  async compareVersions(designId, versionA, versionB) {
    try {
      const response = await fetch(`${this.baseURL}/${designId}/compare`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          version_a: versionA,
          version_b: versionB,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to compare versions: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error comparing versions:', error);
      throw error;
    }
  }
}

export default new VersionService();
