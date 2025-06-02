import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  const [teamMatches, setTeamMatches] = useState([]);
  const [scrapingStatus, setScrapingStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Multi-season and team selection state
  const [selectedSeasons, setSelectedSeasons] = useState(['2024-25']);
  const [selectedTeam, setSelectedTeam] = useState('');
  const [availableSeasons] = useState(['2024-25', '2023-24', '2022-23', '2021-22', '2020-21', '2019-20']);
  const [availableTeams, setAvailableTeams] = useState([]);
  
  // UI state
  const [activeTab, setActiveTab] = useState('scrape');
  const [exportLoading, setExportLoading] = useState(false);
  const [scrapingMode, setScrapingMode] = useState('single'); // 'single', 'multi', 'team'

  useEffect(() => {
    fetchAvailableData();
  }, []);

  const fetchAvailableData = async () => {
    try {
      const teamsRes = await axios.get(`${API_BASE_URL}/api/teams`);
      setAvailableTeams(teamsRes.data.teams || []);
    } catch (error) {
      console.error('Error fetching available data:', error);
    }
  };

  const startSingleSeasonScraping = async () => {
    try {
      setLoading(true);
      const season = selectedSeasons[0];
      const response = await axios.post(`${API_BASE_URL}/api/scrape-season/${season}`);
      const statusId = response.data.status_id;
      
      // Poll for status updates
      pollScrapingStatus(statusId);
      
    } catch (error) {
      console.error('Error starting single season scrape:', error);
      setLoading(false);
    }
  };

  const startMultiSeasonScraping = async () => {
    try {
      setLoading(true);
      const request = {
        seasons: selectedSeasons,
        target_team: selectedTeam || null
      };
      
      const response = await axios.post(`${API_BASE_URL}/api/scrape-team-multi-season`, request);
      const statusId = response.data.status_id;
      
      // Poll for status updates
      pollScrapingStatus(statusId);
      
    } catch (error) {
      console.error('Error starting multi-season scrape:', error);
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
          fetchTeamMatches();
          fetchAvailableData(); // Refresh available data
        }
      }
    } catch (error) {
      console.error('Error polling status:', error);
      setLoading(false);
    }
  };

  const fetchTeamMatches = async (season = null, team = null) => {
    try {
      setLoading(true);
      let url = `${API_BASE_URL}/api/team-matches`;
      const params = new URLSearchParams();
      
      if (season) params.append('season', season);
      if (team) params.append('team', team);
      
      if (params.toString()) {
        url += `?${params.toString()}`;
      }
      
      const response = await axios.get(url);
      setTeamMatches(response.data);
    } catch (error) {
      console.error('Error fetching team matches:', error);
      setTeamMatches([]);
    } finally {
      setLoading(false);
    }
  };

  const exportCSV = async () => {
    try {
      setExportLoading(true);
      
      const response = await axios.post(
        `${API_BASE_URL}/api/export-team-csv`,
        {
          seasons: selectedSeasons.length > 0 ? selectedSeasons : null,
          teams: selectedTeam ? [selectedTeam] : null,
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
      link.setAttribute('download', `fbref_team_matches_${selectedSeasons.join('_')}.csv`);
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

  const handleSeasonToggle = (season) => {
    setSelectedSeasons(prev => 
      prev.includes(season)
        ? prev.filter(s => s !== season)
        : [...prev, season]
    );
  };

  const StatsCard = ({ title, value, description, color = "blue" }) => (
    <div className={`bg-white rounded-lg shadow-md p-6 border-l-4 border-${color}-500`}>
      <h3 className="text-lg font-semibold text-gray-800 mb-2">{title}</h3>
      <p className={`text-3xl font-bold text-${color}-600 mb-1`}>{value}</p>
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
                <h1 className="text-2xl font-bold text-gray-900">FBref Team Analyzer</h1>
                <p className="text-sm text-gray-600">Multi-Season Team Performance & Referee Analysis</p>
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
                Export & Analyze
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Overview Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <StatsCard
            title="Team Matches"
            value={teamMatches.length.toLocaleString()}
            description="Team-focused match records"
            color="blue"
          />
          <StatsCard
            title="Selected Seasons"
            value={selectedSeasons.length}
            description="Seasons for analysis"
            color="green"
          />
          <StatsCard
            title="Available Teams"
            value={availableTeams.length}
            description="Teams with data"
            color="purple"
          />
          <StatsCard
            title="Target Team"
            value={selectedTeam || "All"}
            description="Focus team analysis"
            color="orange"
          />
        </div>

        {/* Scrape Tab */}
        {activeTab === 'scrape' && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <h2 className="text-xl font-bold text-gray-800 mb-6 flex items-center">
              <span className="w-6 h-6 bg-blue-500 rounded mr-3 flex items-center justify-center">
                <span className="text-white text-sm">🔍</span>
              </span>
              Multi-Season Team Data Scraping
            </h2>

            {/* Scraping Mode Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-3">Scraping Mode</label>
              <div className="flex space-x-4">
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="single"
                    checked={scrapingMode === 'single'}
                    onChange={(e) => setScrapingMode(e.target.value)}
                    className="mr-2"
                  />
                  <span>Single Season (All Teams)</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="multi"
                    checked={scrapingMode === 'multi'}
                    onChange={(e) => setScrapingMode(e.target.value)}
                    className="mr-2"
                  />
                  <span>Multi-Season (All Teams)</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="radio"
                    value="team"
                    checked={scrapingMode === 'team'}
                    onChange={(e) => setScrapingMode(e.target.value)}
                    className="mr-2"
                  />
                  <span>Team-Focused (Multi-Season)</span>
                </label>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Season Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Select Seasons {scrapingMode === 'single' ? '(Select One)' : '(Select Multiple)'}
                </label>
                <div className="max-h-40 overflow-y-auto border border-gray-300 rounded-lg p-3 bg-gray-50">
                  {availableSeasons.map(season => (
                    <label key={season} className="flex items-center space-x-2 text-sm hover:bg-gray-100 p-2 rounded">
                      <input
                        type={scrapingMode === 'single' ? 'radio' : 'checkbox'}
                        checked={selectedSeasons.includes(season)}
                        onChange={() => {
                          if (scrapingMode === 'single') {
                            setSelectedSeasons([season]);
                          } else {
                            handleSeasonToggle(season);
                          }
                        }}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="font-medium">{season} Season</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Team Selection */}
              {(scrapingMode === 'team') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Target Team (Optional)
                  </label>
                  <select
                    value={selectedTeam}
                    onChange={(e) => setSelectedTeam(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    disabled={loading}
                  >
                    <option value="">All Teams</option>
                    {availableTeams.map(team => (
                      <option key={team} value={team}>{team}</option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-1">
                    Select a specific team to only scrape matches where they played
                  </p>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 mt-6">
              <button
                onClick={scrapingMode === 'single' ? startSingleSeasonScraping : startMultiSeasonScraping}
                disabled={loading || selectedSeasons.length === 0}
                className="flex-1 bg-gradient-to-r from-blue-500 to-purple-600 text-white px-6 py-3 rounded-lg hover:from-blue-600 hover:to-purple-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium"
              >
                {loading ? 'Scraping...' : 
                  scrapingMode === 'single' ? `Scrape ${selectedSeasons[0]} Season` :
                  scrapingMode === 'team' ? `Scrape ${selectedTeam || 'All Teams'} (${selectedSeasons.length} Seasons)` :
                  `Scrape ${selectedSeasons.length} Seasons`
                }
              </button>
            </div>

            {/* Scraping Status */}
            {scrapingStatus && (
              <div className="mt-6 p-4 bg-gray-50 rounded-lg border">
                <h3 className="font-medium text-gray-800 mb-3">Scraping Progress</h3>
                <div className="space-y-3">
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
                  
                  {scrapingStatus.request_type !== 'single_season' && (
                    <div className="flex justify-between text-sm">
                      <span>Seasons Progress:</span>
                      <span>{scrapingStatus.completed_seasons} / {scrapingStatus.total_seasons}</span>
                    </div>
                  )}
                  
                  <div className="flex justify-between text-sm">
                    <span>Matches Scraped:</span>
                    <span>{scrapingStatus.matches_scraped} / {scrapingStatus.total_matches}</span>
                  </div>
                  
                  {scrapingStatus.current_season && (
                    <div className="text-sm text-gray-600">
                      <span className="font-medium">Current Season:</span> {scrapingStatus.current_season}
                    </div>
                  )}
                  
                  {scrapingStatus.target_team && (
                    <div className="text-sm text-gray-600">
                      <span className="font-medium">Target Team:</span> {scrapingStatus.target_team}
                    </div>
                  )}
                  
                  {scrapingStatus.current_match && (
                    <div className="text-sm text-gray-600 truncate">
                      <span className="font-medium">Current:</span> {scrapingStatus.current_match}
                    </div>
                  )}
                  
                  {scrapingStatus.total_matches > 0 && (
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                        className="bg-gradient-to-r from-blue-500 to-purple-600 h-3 rounded-full transition-all duration-300"
                        style={{
                          width: `${Math.max(5, (scrapingStatus.matches_scraped / scrapingStatus.total_matches) * 100)}%`
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
              Export Team Match Data
            </h2>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Season Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Season Filter
                </label>
                <div className="max-h-32 overflow-y-auto border border-gray-300 rounded-lg p-2">
                  {availableSeasons.map(season => (
                    <label key={season} className="flex items-center space-x-2 text-sm hover:bg-gray-50 p-1 rounded">
                      <input
                        type="checkbox"
                        checked={selectedSeasons.includes(season)}
                        onChange={() => handleSeasonToggle(season)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span>{season}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Team Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Team Filter (Optional)
                </label>
                <select
                  value={selectedTeam}
                  onChange={(e) => setSelectedTeam(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">All Teams</option>
                  {availableTeams.map(team => (
                    <option key={team} value={team}>{team}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-4 mt-6">
              <button
                onClick={() => fetchTeamMatches(null, selectedTeam)}
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

        {/* Team Matches Table */}
        {teamMatches.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-800">Team Match Data Preview</h2>
              <p className="text-sm text-gray-600">Showing {teamMatches.length} team match records</p>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Team</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Match</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Result</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Referee</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Key Stats</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {teamMatches.slice(0, 10).map((match, index) => (
                    <tr key={match.id || index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="text-sm font-medium text-gray-900">{match.team_name}</div>
                          <span className={`ml-2 px-2 py-1 text-xs rounded-full ${
                            match.is_home ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {match.is_home ? 'H' : 'A'}
                          </span>
                        </div>
                        <div className="text-sm text-gray-500">{match.season}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">
                          {match.home_team} vs {match.away_team}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {match.team_score} - {match.opponent_score}
                        </div>
                        <div className={`text-xs ${
                          match.team_score > match.opponent_score ? 'text-green-600' :
                          match.team_score < match.opponent_score ? 'text-red-600' :
                          'text-gray-600'
                        }`}>
                          {match.team_score > match.opponent_score ? 'W' :
                           match.team_score < match.opponent_score ? 'L' : 'D'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {match.match_date ? new Date(match.match_date).toLocaleDateString() : 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {match.referee || 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div>Poss: {match.possession}%</div>
                        <div>Shots: {match.shots} ({match.shots_on_target} on target)</div>
                        <div>xG: {match.expected_goals?.toFixed(2)}</div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {teamMatches.length > 10 && (
              <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
                <p className="text-sm text-gray-600">
                  Showing first 10 of {teamMatches.length} total team match records. Export to CSV to see all data.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Enhanced Help Section */}
        <div className="mt-8 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-6 border border-blue-200">
          <h3 className="text-lg font-semibold text-blue-800 mb-3">🚀 Enhanced Features</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-blue-700">
            <div>
              <p><strong>Multi-Season Analysis:</strong> Select multiple seasons to analyze team performance trends</p>
              <p><strong>Team-Focused Scraping:</strong> Target specific teams to collect only their match data</p>
            </div>
            <div>
              <p><strong>Referee Bias Analysis:</strong> Complete referee and VAR official data for bias studies</p>
              <p><strong>Performance Metrics:</strong> 16 key statistics per team per match for deep analysis</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
