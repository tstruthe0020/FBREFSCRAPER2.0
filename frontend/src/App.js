import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [matches, setMatches] = useState([]);
  const [scrapingStatus, setScrapingStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedSeason, setSelectedSeason] = useState('2023-24');
  const [selectedTeams, setSelectedTeams] = useState([]);
  const [availableSeasons, setAvailableSeasons] = useState(['2023-24']);
  const [availableTeams, setAvailableTeams] = useState([]);
  const [activeTab, setActiveTab] = useState('scrape');
  const [exportLoading, setExportLoading] = useState(false);

  useEffect(() => {
    fetchAvailableData();
  }, []);

  const fetchAvailableData = async () => {
    try {
      const [seasonsRes, teamsRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/api/seasons`),
        axios.get(`${API_BASE_URL}/api/teams`)
      ]);
      
      setAvailableSeasons(seasonsRes.data.seasons || ['2023-24']);
      setAvailableTeams(teamsRes.data.teams || []);
    } catch (error) {
      console.error('Error fetching available data:', error);
    }
  };

  const startScraping = async () => {
    try {
      setLoading(true);
      const response = await axios.post(`${API_BASE_URL}/api/scrape-season/${selectedSeason}`);
      const statusId = response.data.status_id;
      
      // Poll for status updates
      pollScrapingStatus(statusId);
      
    } catch (error) {
      console.error('Error starting scrape:', error);
      setLoading(false);
    }
  };

  const pollScrapingStatus = async (statusId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/scraping-status/${statusId}`);
      setScrapingStatus(response.data);
      
      if (response.data.status === 'running') {
        setTimeout(() => pollScrapingStatus(statusId), 3000);
      } else {
        setLoading(false);
        if (response.data.status === 'completed') {
          fetchMatches();
          fetchAvailableData(); // Refresh available data
        }
      }
    } catch (error) {
      console.error('Error polling status:', error);
      setLoading(false);
    }
  };

  const fetchMatches = async (season = null, team = null) => {
    try {
      setLoading(true);
      let url = `${API_BASE_URL}/api/matches`;
      const params = new URLSearchParams();
      
      if (season) params.append('season', season);
      if (team) params.append('team', team);
      
      if (params.toString()) {
        url += `?${params.toString()}`;
      }
      
      const response = await axios.get(url);
      setMatches(response.data);
    } catch (error) {
      console.error('Error fetching matches:', error);
      setMatches([]);
    } finally {
      setLoading(false);
    }
  };

  const exportCSV = async () => {
    try {
      setExportLoading(true);
      
      const response = await axios.post(
        `${API_BASE_URL}/api/export-csv`,
        {
          season: selectedSeason === 'all' ? null : selectedSeason,
          teams: selectedTeams.length > 0 ? selectedTeams : null,
          referee: null
        },
        {
          responseType: 'blob'
        }
      );
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `fbref_matches_${selectedSeason}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Error exporting CSV:', error);
    } finally {
      setExportLoading(false);
    }
  };

  const handleTeamToggle = (team) => {
    setSelectedTeams(prev => 
      prev.includes(team)
        ? prev.filter(t => t !== team)
        : [...prev, team]
    );
  };

  const StatsCard = ({ title, value, description }) => (
    <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-blue-500">
      <h3 className="text-lg font-semibold text-gray-800 mb-2">{title}</h3>
      <p className="text-3xl font-bold text-blue-600 mb-1">{value}</p>
      <p className="text-sm text-gray-600">{description}</p>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-lg border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center mr-3">
                <span className="text-white font-bold text-lg">⚽</span>
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">FBref Match Scraper</h1>
                <p className="text-sm text-gray-600">Premier League Match Report Data Extraction</p>
              </div>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setActiveTab('scrape')}
                className={`px-4 py-2 rounded-lg font-medium transition-all ${
                  activeTab === 'scrape'
                    ? 'bg-blue-500 text-white shadow-lg'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                Scrape Data
              </button>
              <button
                onClick={() => setActiveTab('export')}
                className={`px-4 py-2 rounded-lg font-medium transition-all ${
                  activeTab === 'export'
                    ? 'bg-blue-500 text-white shadow-lg'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                Export Data
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <StatsCard
            title="Total Matches"
            value={matches.length.toLocaleString()}
            description="Scraped match reports"
          />
          <StatsCard
            title="Available Seasons"
            value={availableSeasons.length}
            description="Seasons with data"
          />
          <StatsCard
            title="Teams Tracked"
            value={availableTeams.length}
            description="Premier League teams"
          />
        </div>

        {/* Scrape Tab */}
        {activeTab === 'scrape' && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <h2 className="text-xl font-bold text-gray-800 mb-6 flex items-center">
              <span className="w-6 h-6 bg-blue-500 rounded mr-3 flex items-center justify-center">
                <span className="text-white text-sm">🔍</span>
              </span>
              Scrape Match Reports
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Season
                </label>
                <select
                  value={selectedSeason}
                  onChange={(e) => setSelectedSeason(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={loading}
                >
                  <option value="2023-24">2023-24 Season</option>
                  <option value="2022-23">2022-23 Season</option>
                  <option value="2021-22">2021-22 Season</option>
                  <option value="2020-21">2020-21 Season</option>
                  <option value="2019-20">2019-20 Season</option>
                </select>
              </div>

              <div className="flex items-end">
                <button
                  onClick={startScraping}
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white px-6 py-2 rounded-lg hover:from-blue-600 hover:to-purple-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium"
                >
                  {loading ? 'Scraping...' : `Scrape ${selectedSeason} Season`}
                </button>
              </div>
            </div>

            {/* Scraping Status */}
            {scrapingStatus && (
              <div className="mt-6 p-4 bg-gray-50 rounded-lg border">
                <h3 className="font-medium text-gray-800 mb-2">Scraping Progress</h3>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Status:</span>
                    <span className={`font-medium ${
                      scrapingStatus.status === 'completed' ? 'text-green-600' :
                      scrapingStatus.status === 'failed' ? 'text-red-600' :
                      'text-blue-600'
                    }`}>
                      {scrapingStatus.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span>Progress:</span>
                    <span>{scrapingStatus.matches_scraped} / {scrapingStatus.total_matches}</span>
                  </div>
                  {scrapingStatus.current_match && (
                    <div className="text-sm text-gray-600">
                      <span className="font-medium">Current:</span> {scrapingStatus.current_match}
                    </div>
                  )}
                  {scrapingStatus.total_matches > 0 && (
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full transition-all"
                        style={{
                          width: `${(scrapingStatus.matches_scraped / scrapingStatus.total_matches) * 100}%`
                        }}
                      ></div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Export Tab */}
        {activeTab === 'export' && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <h2 className="text-xl font-bold text-gray-800 mb-6 flex items-center">
              <span className="w-6 h-6 bg-green-500 rounded mr-3 flex items-center justify-center">
                <span className="text-white text-sm">📊</span>
              </span>
              Export Match Data
            </h2>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Season Filter
                </label>
                <select
                  value={selectedSeason}
                  onChange={(e) => setSelectedSeason(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="all">All Seasons</option>
                  {availableSeasons.map(season => (
                    <option key={season} value={season}>{season} Season</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Team Filter (Optional)
                </label>
                <div className="max-h-32 overflow-y-auto border border-gray-300 rounded-lg p-2">
                  {availableTeams.slice(0, 10).map(team => (
                    <label key={team} className="flex items-center space-x-2 text-sm hover:bg-gray-50 p-1 rounded">
                      <input
                        type="checkbox"
                        checked={selectedTeams.includes(team)}
                        onChange={() => handleTeamToggle(team)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span>{team}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 mt-6">
              <button
                onClick={() => fetchMatches(selectedSeason === 'all' ? null : selectedSeason, selectedTeams[0])}
                disabled={loading}
                className="flex-1 bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 transition-all font-medium"
              >
                {loading ? 'Loading...' : 'Preview Data'}
              </button>
              <button
                onClick={exportCSV}
                disabled={exportLoading}
                className="flex-1 bg-green-500 text-white px-6 py-2 rounded-lg hover:bg-green-600 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 transition-all font-medium"
              >
                {exportLoading ? 'Exporting...' : 'Export CSV'}
              </button>
            </div>
          </div>
        )}

        {/* Matches Table */}
        {matches.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-800">Match Data Preview</h2>
              <p className="text-sm text-gray-600">Showing {matches.length} matches</p>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Match</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Referee</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Key Stats</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {matches.slice(0, 10).map((match, index) => (
                    <tr key={match.id || index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {match.home_team} vs {match.away_team}
                        </div>
                        <div className="text-sm text-gray-500">{match.season}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {match.home_score} - {match.away_score}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {match.match_date ? new Date(match.match_date).toLocaleDateString() : 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {match.referee || 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div>Poss: {match.home_possession}% - {match.away_possession}%</div>
                        <div>Shots: {match.home_shots} - {match.away_shots}</div>
                        <div>xG: {match.home_expected_goals?.toFixed(2)} - {match.away_expected_goals?.toFixed(2)}</div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {matches.length > 10 && (
              <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
                <p className="text-sm text-gray-600">
                  Showing first 10 of {matches.length} total matches. Export to CSV to see all data.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Help Section */}
        <div className="mt-8 bg-blue-50 rounded-lg p-6 border border-blue-200">
          <h3 className="text-lg font-semibold text-blue-800 mb-3">📋 Usage Instructions</h3>
          <div className="space-y-2 text-sm text-blue-700">
            <p><strong>1. Scrape Data:</strong> Select a season and click "Scrape" to extract match reports from FBref.com</p>
            <p><strong>2. Monitor Progress:</strong> Watch the real-time scraping progress with detailed status updates</p>
            <p><strong>3. Export Data:</strong> Filter by season/teams and export to CSV for external analysis</p>
            <p><strong>4. Key Stats:</strong> Includes possession, shots, xG, fouls, cards, referee details, and more</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
