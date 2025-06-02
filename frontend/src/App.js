import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  // Core state
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  
  // Data state
  const [teamMatches, setTeamMatches] = useState([]);
  const [playerMatches, setPlayerMatches] = useState([]);
  const [availableTeams, setAvailableTeams] = useState([]);
  const [databaseSchema, setDatabaseSchema] = useState(null);
  
  // Scraping state
  const [scrapingStatus, setScrapingStatus] = useState(null);
  const [scrapingMode, setScrapingMode] = useState('single');
  const [selectedSeasons, setSelectedSeasons] = useState(['2024-25']);
  const [selectedTeam, setSelectedTeam] = useState('');
  
  // Analytics state
  const [analyticsFilters, setAnalyticsFilters] = useState({
    season: '',
    team: '',
    player: '',
    position: '',
    minMinutes: 0
  });
  
  // Export state
  const [exportLoading, setExportLoading] = useState(false);
  const [exportType, setExportType] = useState('team');
  
  // Constants
  const availableSeasons = ['2024-25', '2023-24', '2022-23', '2021-22', '2020-21', '2019-20'];
  const positions = ['GK', 'DF', 'MF', 'FW', 'All'];

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    try {
      // Fetch available teams
      const teamsRes = await axios.get(`${API_BASE_URL}/api/teams`);
      setAvailableTeams(teamsRes.data.teams || []);
      
      // Fetch database schema
      const schemaRes = await axios.get(`${API_BASE_URL}/api/database-schema`);
      setDatabaseSchema(schemaRes.data);
      
      // Fetch some initial data
      await Promise.all([
        fetchTeamMatches(),
        fetchPlayerMatches()
      ]);
      
    } catch (error) {
      console.error('Error fetching initial data:', error);
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
      setTeamMatches(response.data.matches || []);
    } catch (error) {
      console.error('Error fetching team matches:', error);
      setTeamMatches([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchPlayerMatches = async (season = null, team = null, player = null) => {
    try {
      let url = `${API_BASE_URL}/api/player-matches`;
      const params = new URLSearchParams();
      
      if (season) params.append('season', season);
      if (team) params.append('team', team);
      if (player) params.append('player', player);
      
      if (params.toString()) {
        url += `?${params.toString()}`;
      }
      
      const response = await axios.get(url);
      setPlayerMatches(response.data);
    } catch (error) {
      console.error('Error fetching player matches:', error);
      setPlayerMatches([]);
    }
  };

  const startScraping = async () => {
    try {
      setLoading(true);
      let response;
      
      if (scrapingMode === 'single') {
        response = await axios.post(`${API_BASE_URL}/api/scrape-season/${selectedSeasons[0]}`);
      } else {
        const request = {
          seasons: selectedSeasons,
          target_team: selectedTeam || null
        };
        response = await axios.post(`${API_BASE_URL}/api/scrape-team-multi-season`, request);
      }
      
      const statusId = response.data.status_id;
      pollScrapingStatus(statusId);
      
    } catch (error) {
      console.error('Error starting scraping:', error);
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
          await fetchInitialData();
        }
      }
    } catch (error) {
      console.error('Error polling status:', error);
      setLoading(false);
    }
  };

  const exportData = async () => {
    try {
      setExportLoading(true);
      
      const endpoint = exportType === 'team' ? 'export-team-csv' : 'export-player-csv';
      const filename = exportType === 'team' ? 'fbref_team_matches' : 'fbref_player_matches';
      
      const response = await axios.post(
        `${API_BASE_URL}/api/${endpoint}`,
        {
          seasons: selectedSeasons.length > 0 ? selectedSeasons : null,
          teams: selectedTeam ? [selectedTeam] : null,
        },
        { responseType: 'blob' }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${filename}_${selectedSeasons.join('_')}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
    } catch (error) {
      console.error('Error exporting data:', error);
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

  const applyAnalyticsFilters = async () => {
    await Promise.all([
      fetchTeamMatches(analyticsFilters.season, analyticsFilters.team),
      fetchPlayerMatches(analyticsFilters.season, analyticsFilters.team, analyticsFilters.player)
    ]);
  };

  const getStatsOverview = () => {
    const totalMatches = teamMatches.length;
    const totalPlayers = new Set(playerMatches.map(p => p.player_name)).size;
    const totalSeasons = new Set(teamMatches.map(m => m.season)).size;
    const totalTeams = new Set(teamMatches.map(m => m.team_name)).size;
    
    return { totalMatches, totalPlayers, totalSeasons, totalTeams };
  };

  const StatsCard = ({ title, value, description, icon, color = "blue" }) => (
    <div className={`stats-card bg-white rounded-xl shadow-lg p-6 border-l-4 border-${color}-500`}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-800 mb-1">{title}</h3>
          <p className={`text-3xl font-bold text-${color}-600 mb-2`}>{value}</p>
          <p className="text-sm text-gray-600">{description}</p>
        </div>
        <div className={`text-4xl text-${color}-500 opacity-20`}>{icon}</div>
      </div>
    </div>
  );

  const TabButton = ({ id, title, icon, isActive, onClick }) => (
    <button
      onClick={() => onClick(id)}
      className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-medium transition-all ${
        isActive
          ? 'bg-blue-500 text-white shadow-lg'
          : 'bg-white text-gray-600 hover:bg-gray-50 shadow-md'
      }`}
    >
      <span className="text-lg">{icon}</span>
      <span>{title}</span>
    </button>
  );

  const stats = getStatsOverview();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-xl border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center mr-4">
                <span className="text-white font-bold text-2xl">⚽</span>
              </div>
              <div>
                <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  FBref Analytics Pro
                </h1>
                <p className="text-sm text-gray-600">Comprehensive Football Data & Analytics Platform</p>
              </div>
            </div>
            <div className="flex space-x-3">
              <TabButton
                id="dashboard"
                title="Dashboard"
                icon="📊"
                isActive={activeTab === 'dashboard'}
                onClick={setActiveTab}
              />
              <TabButton
                id="scraping"
                title="Data Collection"
                icon="🔄"
                isActive={activeTab === 'scraping'}
                onClick={setActiveTab}
              />
              <TabButton
                id="team-analytics"
                title="Team Analytics"
                icon="🏆"
                isActive={activeTab === 'team-analytics'}
                onClick={setActiveTab}
              />
              <TabButton
                id="player-analytics"
                title="Player Analytics"
                icon="👤"
                isActive={activeTab === 'player-analytics'}
                onClick={setActiveTab}
              />
              <TabButton
                id="export"
                title="Export"
                icon="📋"
                isActive={activeTab === 'export'}
                onClick={setActiveTab}
              />
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-8">
            {/* Overview Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
              <StatsCard
                title="Team Matches"
                value={stats.totalMatches.toLocaleString()}
                description="Complete match records"
                icon="⚽"
                color="blue"
              />
              <StatsCard
                title="Players Tracked"
                value={stats.totalPlayers.toLocaleString()}
                description="Individual player records"
                icon="👤"
                color="green"
              />
              <StatsCard
                title="Seasons Analyzed"
                value={stats.totalSeasons}
                description="Historical coverage"
                icon="📅"
                color="purple"
              />
              <StatsCard
                title="Teams Covered"
                value={stats.totalTeams}
                description="Football clubs tracked"
                icon="🏆"
                color="orange"
              />
            </div>

            {/* Database Schema Overview */}
            {databaseSchema && (
              <div className="bg-white rounded-xl shadow-lg p-8">
                <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
                  <span className="mr-3">🗃️</span>
                  Enhanced Database Schema
                </h2>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6">
                    <h3 className="text-xl font-bold text-blue-800 mb-4">
                      📊 Team Match Data
                    </h3>
                    <p className="text-blue-700 mb-4">{databaseSchema.team_match_data.description}</p>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="font-medium">Total Fields:</span>
                        <span className="text-blue-600 font-bold">{databaseSchema.team_match_data.total_fields}+</span>
                      </div>
                      <div className="text-sm text-blue-600">
                        Categories: Advanced Shooting, Pressure Stats, Set Pieces, Progressive Actions
                      </div>
                    </div>
                  </div>
                  <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6">
                    <h3 className="text-xl font-bold text-green-800 mb-4">
                      👤 Player Match Data
                    </h3>
                    <p className="text-green-700 mb-4">{databaseSchema.player_match_data.description}</p>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="font-medium">Total Fields:</span>
                        <span className="text-green-600 font-bold">{databaseSchema.player_match_data.total_fields}+</span>
                      </div>
                      <div className="text-sm text-green-600">
                        Categories: Advanced Defense, Possession Details, Goalkeeper Specific
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Quick Actions */}
            <div className="bg-white rounded-xl shadow-lg p-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
                <span className="mr-3">🚀</span>
                Quick Actions
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <button
                  onClick={() => setActiveTab('scraping')}
                  className="bg-gradient-to-r from-blue-500 to-blue-600 text-white p-6 rounded-lg hover:from-blue-600 hover:to-blue-700 transition-all shadow-lg"
                >
                  <div className="text-2xl mb-2">🔄</div>
                  <div className="font-semibold">Start Data Collection</div>
                  <div className="text-sm opacity-90">Scrape new match data</div>
                </button>
                <button
                  onClick={() => setActiveTab('team-analytics')}
                  className="bg-gradient-to-r from-green-500 to-green-600 text-white p-6 rounded-lg hover:from-green-600 hover:to-green-700 transition-all shadow-lg"
                >
                  <div className="text-2xl mb-2">📈</div>
                  <div className="font-semibold">Team Analysis</div>
                  <div className="text-sm opacity-90">Analyze team performance</div>
                </button>
                <button
                  onClick={() => setActiveTab('export')}
                  className="bg-gradient-to-r from-purple-500 to-purple-600 text-white p-6 rounded-lg hover:from-purple-600 hover:to-purple-700 transition-all shadow-lg"
                >
                  <div className="text-2xl mb-2">📋</div>
                  <div className="font-semibold">Export Data</div>
                  <div className="text-sm opacity-90">Download comprehensive datasets</div>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Data Collection Tab */}
        {activeTab === 'scraping' && (
          <div className="space-y-8">
            <div className="bg-white rounded-xl shadow-lg p-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
                <span className="mr-3">🔄</span>
                Enhanced Data Collection
              </h2>

              {/* Scraping Mode Selection */}
              <div className="mb-8">
                <label className="block text-sm font-medium text-gray-700 mb-4">Collection Mode</label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <label className="flex items-center p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                    <input
                      type="radio"
                      value="single"
                      checked={scrapingMode === 'single'}
                      onChange={(e) => setScrapingMode(e.target.value)}
                      className="mr-3"
                    />
                    <div>
                      <div className="font-medium">Single Season</div>
                      <div className="text-sm text-gray-600">All teams, one season</div>
                    </div>
                  </label>
                  <label className="flex items-center p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                    <input
                      type="radio"
                      value="multi"
                      checked={scrapingMode === 'multi'}
                      onChange={(e) => setScrapingMode(e.target.value)}
                      className="mr-3"
                    />
                    <div>
                      <div className="font-medium">Multi-Season</div>
                      <div className="text-sm text-gray-600">All teams, multiple seasons</div>
                    </div>
                  </label>
                  <label className="flex items-center p-4 border rounded-lg cursor-pointer hover:bg-gray-50">
                    <input
                      type="radio"
                      value="team"
                      checked={scrapingMode === 'team'}
                      onChange={(e) => setScrapingMode(e.target.value)}
                      className="mr-3"
                    />
                    <div>
                      <div className="font-medium">Team-Focused</div>
                      <div className="text-sm text-gray-600">Specific team analysis</div>
                    </div>
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Season Selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Select Seasons {scrapingMode === 'single' ? '(Select One)' : '(Select Multiple)'}
                  </label>
                  <div className="max-h-48 overflow-y-auto border border-gray-300 rounded-lg p-4 bg-gray-50 space-y-2">
                    {availableSeasons.map(season => (
                      <label key={season} className="flex items-center space-x-3 p-2 hover:bg-white rounded cursor-pointer">
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
                {scrapingMode === 'team' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-3">
                      Target Team
                    </label>
                    <select
                      value={selectedTeam}
                      onChange={(e) => setSelectedTeam(e.target.value)}
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      disabled={loading}
                    >
                      <option value="">Select Team</option>
                      {availableTeams.map(team => (
                        <option key={team} value={team}>{team}</option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              {/* Start Scraping Button */}
              <div className="mt-8">
                <button
                  onClick={startScraping}
                  disabled={loading || selectedSeasons.length === 0}
                  className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white px-8 py-4 rounded-lg hover:from-blue-600 hover:to-purple-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold text-lg"
                >
                  {loading ? 'Collecting Data...' : 
                    scrapingMode === 'single' ? `Collect ${selectedSeasons[0]} Season` :
                    scrapingMode === 'team' ? `Collect ${selectedTeam || 'Team'} Data (${selectedSeasons.length} Seasons)` :
                    `Collect ${selectedSeasons.length} Seasons Data`
                  }
                </button>
              </div>

              {/* Scraping Progress */}
              {scrapingStatus && (
                <div className="mt-8 p-6 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200">
                  <h3 className="font-bold text-gray-800 mb-4 flex items-center">
                    <span className="mr-2">📊</span>
                    Data Collection Progress
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span>Status:</span>
                        <span className={`font-medium ${
                          scrapingStatus.status === 'completed' ? 'text-green-600' :
                          scrapingStatus.status === 'failed' ? 'text-red-600' :
                          'text-blue-600'
                        }`}>
                          {scrapingStatus.status.toUpperCase()}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Matches Scraped:</span>
                        <span className="font-medium">{scrapingStatus.matches_scraped} / {scrapingStatus.total_matches}</span>
                      </div>
                    </div>
                    <div className="space-y-2">
                      {scrapingStatus.current_season && (
                        <div className="flex justify-between">
                          <span>Current Season:</span>
                          <span className="font-medium">{scrapingStatus.current_season}</span>
                        </div>
                      )}
                      {scrapingStatus.target_team && (
                        <div className="flex justify-between">
                          <span>Target Team:</span>
                          <span className="font-medium">{scrapingStatus.target_team}</span>
                        </div>
                      )}
                    </div>
                  </div>
                  {scrapingStatus.total_matches > 0 && (
                    <div className="w-full bg-gray-200 rounded-full h-4 mt-4">
                      <div
                        className="bg-gradient-to-r from-blue-500 to-purple-600 h-4 rounded-full transition-all duration-300"
                        style={{
                          width: `${Math.max(5, (scrapingStatus.matches_scraped / scrapingStatus.total_matches) * 100)}%`
                        }}
                      ></div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Team Analytics Tab */}
        {activeTab === 'team-analytics' && (
          <div className="space-y-8">
            {/* Filters */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-800 mb-6 flex items-center">
                <span className="mr-3">🔍</span>
                Team Analytics Filters
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Season</label>
                  <select
                    value={analyticsFilters.season}
                    onChange={(e) => setAnalyticsFilters(prev => ({...prev, season: e.target.value}))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Seasons</option>
                    {availableSeasons.map(season => (
                      <option key={season} value={season}>{season}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Team</label>
                  <select
                    value={analyticsFilters.team}
                    onChange={(e) => setAnalyticsFilters(prev => ({...prev, team: e.target.value}))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Teams</option>
                    {availableTeams.map(team => (
                      <option key={team} value={team}>{team}</option>
                    ))}
                  </select>
                </div>
                <div className="flex items-end">
                  <button
                    onClick={applyAnalyticsFilters}
                    className="w-full bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-all"
                  >
                    Apply Filters
                  </button>
                </div>
              </div>
            </div>

            {/* Team Matches Table */}
            {teamMatches.length > 0 && (
              <div className="bg-white rounded-xl shadow-lg overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-purple-50">
                  <h2 className="text-xl font-bold text-gray-800">Team Match Analysis</h2>
                  <p className="text-sm text-gray-600">Comprehensive team performance data ({teamMatches.length} matches)</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Team & Match</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Result</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Possession</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Shots</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">xG</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Passing</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Defensive</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {teamMatches.slice(0, 20).map((match, index) => (
                        <tr key={match.id || index} className="hover:bg-gray-50">
                          <td className="px-6 py-4">
                            <div className="flex items-center">
                              <div>
                                <div className="text-sm font-medium text-gray-900">{match.team_name}</div>
                                <div className="text-xs text-gray-500">
                                  {match.home_team} vs {match.away_team}
                                </div>
                                <div className="text-xs text-gray-400">{match.season}</div>
                              </div>
                              <span className={`ml-2 px-2 py-1 text-xs rounded-full ${
                                match.is_home ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                              }`}>
                                {match.is_home ? 'H' : 'A'}
                              </span>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm font-medium text-gray-900">
                              {match.team_score} - {match.opponent_score}
                            </div>
                            <div className={`text-xs font-medium ${
                              match.team_score > match.opponent_score ? 'text-green-600' :
                              match.team_score < match.opponent_score ? 'text-red-600' :
                              'text-gray-600'
                            }`}>
                              {match.team_score > match.opponent_score ? 'WIN' :
                               match.team_score < match.opponent_score ? 'LOSS' : 'DRAW'}
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-900">{match.possession}%</div>
                            <div className="w-16 bg-gray-200 rounded-full h-2">
                              <div
                                className="bg-blue-500 h-2 rounded-full"
                                style={{ width: `${match.possession}%` }}
                              ></div>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-900">{match.shots}</div>
                            <div className="text-xs text-gray-500">({match.shots_on_target} on target)</div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-900">{match.expected_goals?.toFixed(2)}</div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-900">{match.passing_accuracy?.toFixed(1)}%</div>
                            <div className="text-xs text-gray-500">{match.passes_completed}/{match.passes_attempted}</div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-900">T:{match.tackles}</div>
                            <div className="text-xs text-gray-500">I:{match.interceptions} B:{match.blocks}</div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {teamMatches.length > 20 && (
                  <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
                    <p className="text-sm text-gray-600">
                      Showing first 20 of {teamMatches.length} total matches. Use filters or export for complete data.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Player Analytics Tab */}
        {activeTab === 'player-analytics' && (
          <div className="space-y-8">
            {/* Player Filters */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-800 mb-6 flex items-center">
                <span className="mr-3">👤</span>
                Player Analytics Filters
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Season</label>
                  <select
                    value={analyticsFilters.season}
                    onChange={(e) => setAnalyticsFilters(prev => ({...prev, season: e.target.value}))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Seasons</option>
                    {availableSeasons.map(season => (
                      <option key={season} value={season}>{season}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Team</label>
                  <select
                    value={analyticsFilters.team}
                    onChange={(e) => setAnalyticsFilters(prev => ({...prev, team: e.target.value}))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Teams</option>
                    {availableTeams.map(team => (
                      <option key={team} value={team}>{team}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Position</label>
                  <select
                    value={analyticsFilters.position}
                    onChange={(e) => setAnalyticsFilters(prev => ({...prev, position: e.target.value}))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">All Positions</option>
                    {positions.map(pos => (
                      <option key={pos} value={pos}>{pos}</option>
                    ))}
                  </select>
                </div>
                <div className="flex items-end">
                  <button
                    onClick={applyAnalyticsFilters}
                    className="w-full bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600 transition-all"
                  >
                    Apply Filters
                  </button>
                </div>
              </div>
            </div>

            {/* Player Data Table */}
            {playerMatches.length > 0 && (
              <div className="bg-white rounded-xl shadow-lg overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-green-50 to-blue-50">
                  <h2 className="text-xl font-bold text-gray-800">Player Performance Analysis</h2>
                  <p className="text-sm text-gray-600">Individual player statistics ({playerMatches.length} player records)</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Player</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Minutes</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Goals/Assists</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Shots</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">xG/xA</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Passing</th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Defensive</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {playerMatches.slice(0, 20).map((player, index) => (
                        <tr key={player.id || index} className="hover:bg-gray-50">
                          <td className="px-6 py-4">
                            <div>
                              <div className="text-sm font-medium text-gray-900">{player.player_name}</div>
                              <div className="text-xs text-gray-500">
                                {player.team_name} | {player.position}
                              </div>
                              <div className="text-xs text-gray-400">#{player.player_number}</div>
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-900">{player.minutes_played}'</div>
                            <div className={`text-xs ${player.started ? 'text-green-600' : 'text-orange-600'}`}>
                              {player.started ? 'Started' : 'Sub'}
                            </div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-900">{player.goals} / {player.assists}</div>
                            <div className="text-xs text-gray-500">Penalties: {player.penalty_goals}</div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-900">{player.shots}</div>
                            <div className="text-xs text-gray-500">({player.shots_on_target} on target)</div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-900">{player.expected_goals?.toFixed(2)} / {player.expected_assists?.toFixed(2)}</div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-900">{player.passing_accuracy?.toFixed(1)}%</div>
                            <div className="text-xs text-gray-500">{player.passes_completed}/{player.passes_attempted}</div>
                          </td>
                          <td className="px-6 py-4">
                            <div className="text-sm text-gray-900">T:{player.tackles}</div>
                            <div className="text-xs text-gray-500">I:{player.interceptions} F:{player.fouls_committed}</div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {playerMatches.length > 20 && (
                  <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
                    <p className="text-sm text-gray-600">
                      Showing first 20 of {playerMatches.length} total player records. Use filters or export for complete data.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Export Tab */}
        {activeTab === 'export' && (
          <div className="space-y-8">
            <div className="bg-white rounded-xl shadow-lg p-8">
              <h2 className="text-2xl font-bold text-gray-800 mb-6 flex items-center">
                <span className="mr-3">📋</span>
                Enhanced Data Export
              </h2>

              {/* Export Type Selection */}
              <div className="mb-8">
                <label className="block text-sm font-medium text-gray-700 mb-4">Export Type</label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <label className="flex items-center p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 border-blue-200">
                    <input
                      type="radio"
                      value="team"
                      checked={exportType === 'team'}
                      onChange={(e) => setExportType(e.target.value)}
                      className="mr-3"
                    />
                    <div>
                      <div className="font-semibold text-blue-800">Team Match Data</div>
                      <div className="text-sm text-gray-600">80+ team statistics per match</div>
                      <div className="text-xs text-blue-600 mt-1">Advanced shooting, passing, pressure stats</div>
                    </div>
                  </label>
                  <label className="flex items-center p-4 border-2 rounded-lg cursor-pointer hover:bg-gray-50 border-green-200">
                    <input
                      type="radio"
                      value="player"
                      checked={exportType === 'player'}
                      onChange={(e) => setExportType(e.target.value)}
                      className="mr-3"
                    />
                    <div>
                      <div className="font-semibold text-green-800">Player Match Data</div>
                      <div className="text-sm text-gray-600">75+ player statistics per match</div>
                      <div className="text-xs text-green-600 mt-1">Individual performance, positioning, advanced metrics</div>
                    </div>
                  </label>
                </div>
              </div>

              {/* Export Filters */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">Season Filter</label>
                  <div className="max-h-40 overflow-y-auto border border-gray-300 rounded-lg p-3 bg-gray-50 space-y-2">
                    {availableSeasons.map(season => (
                      <label key={season} className="flex items-center space-x-2 text-sm hover:bg-white p-2 rounded cursor-pointer">
                        <input
                          type="checkbox"
                          checked={selectedSeasons.includes(season)}
                          onChange={() => handleSeasonToggle(season)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="font-medium">{season}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-3">Team Filter (Optional)</label>
                  <select
                    value={selectedTeam}
                    onChange={(e) => setSelectedTeam(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">All Teams</option>
                    {availableTeams.map(team => (
                      <option key={team} value={team}>{team}</option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500 mt-2">
                    Select specific team or leave blank for all teams
                  </p>
                </div>
              </div>

              {/* Export Actions */}
              <div className="flex flex-col sm:flex-row gap-4">
                <button
                  onClick={exportData}
                  disabled={exportLoading || selectedSeasons.length === 0}
                  className="flex-1 bg-gradient-to-r from-green-500 to-green-600 text-white px-8 py-4 rounded-lg hover:from-green-600 hover:to-green-700 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-semibold"
                >
                  {exportLoading ? 'Exporting...' : 
                    `Export ${exportType === 'team' ? 'Team' : 'Player'} Data CSV`
                  }
                </button>
              </div>

              {/* Export Info */}
              <div className="mt-8 p-6 bg-gradient-to-r from-gray-50 to-blue-50 rounded-lg border border-gray-200">
                <h3 className="font-semibold text-gray-800 mb-3">📊 Export Details</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <p><strong>Selected Seasons:</strong> {selectedSeasons.length > 0 ? selectedSeasons.join(', ') : 'None selected'}</p>
                    <p><strong>Team Filter:</strong> {selectedTeam || 'All teams'}</p>
                  </div>
                  <div>
                    <p><strong>Export Type:</strong> {exportType === 'team' ? 'Team Match Data' : 'Player Match Data'}</p>
                    <p><strong>Fields Included:</strong> {exportType === 'team' ? '80+' : '75+'} comprehensive statistics</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;