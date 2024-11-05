import { useState, useEffect } from 'react';
import axios from 'axios';
import { XMLParser } from 'fast-xml-parser';

const ELECTION_DATA_URL = 'https://sfelections.org/results/20241105/data/summary.xml';
const REFRESH_INTERVAL = 15000; // 15 seconds

type ViewType = 'all' | 'mayor' | 'measures' | 'supervisors';

const getViewType = (): ViewType => {
  const params = new URLSearchParams(window.location.search);
  const view = params.get('view');
  if (view === 'mayor' || view === 'measures' || view === 'supervisors') {
    return view;
  }
  return 'all';
};

const filterRacesByView = (races: any[], view: ViewType) => {
  switch (view) {
    case 'mayor':
      return races.filter(race => race.contestId === 'MAYOR');
    case 'measures':
      return races.filter(race => race.contestId.startsWith('MEASURE '));
    case 'supervisors':
      return races.filter(race => race.contestId.includes('BOARD OF SUPERVISORS'));
    default:
      return races;
  }
};

const raceOrder = [
  // Countywide/Citywide Offices
  "MAYOR",
  "CITY ATTORNEY",
  "DISTRICT ATTORNEY",
  "SHERIFF",
  "TREASURER",
  // Board of Supervisors
  "MEMBER, BOARD OF SUPERVISORS, DISTRICT 1",
  "MEMBER, BOARD OF SUPERVISORS, DISTRICT 3",
  "MEMBER, BOARD OF SUPERVISORS, DISTRICT 5",
  "MEMBER, BOARD OF SUPERVISORS, DISTRICT 7",
  "MEMBER, BOARD OF SUPERVISORS, DISTRICT 9",
  "MEMBER, BOARD OF SUPERVISORS, DISTRICT 11",
  // SFUSD
  "MEMBER, BOARD OF EDUCATION",
  // CCSF
  "TRUSTEE, COMMUNITY COLLEGE BOARD",
  // BART
  "BART BOARD OF DIRECTORS, DISTRICT 7",
  "BART BOARD OF DIRECTORS, DISTRICT 9"
];

const filterRaces = (races: any[]) => {
  return races.filter(race => {
    // Include races in our explicit order list
    if (raceOrder.includes(race.contestId)) return true;
    
    // Include measures
    if (race.contestId.startsWith('MEASURE ')) {
      // Only include single letter measures A through O
      const measureLetter = race.contestId.slice(-1);
      return measureLetter >= 'A' && measureLetter <= 'O' && measureLetter.length === 1;
    }
    
    return false;
  });
};

const sortRaces = (races: any[]) => {
  return [...races].sort((a, b) => {
    const aIndex = raceOrder.indexOf(a.contestId);
    const bIndex = raceOrder.indexOf(b.contestId);
    
    // Handle explicitly ordered races
    if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
    if (aIndex !== -1) return -1;
    if (bIndex !== -1) return 1;
    
    // Handle measures
    const aMeasure = a.contestId.startsWith('MEASURE ');
    const bMeasure = b.contestId.startsWith('MEASURE ');
    
    if (aMeasure && bMeasure) {
      return a.contestId.slice(-1).localeCompare(b.contestId.slice(-1));
    }
    if (aMeasure) return 1;  // Measures go last
    if (bMeasure) return -1;
    
    // Everything else in alphabetical order
    return a.contestId.localeCompare(b.contestId);
  });
};

function App() {
  const [races, setRaces] = useState<any[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Helper function to format date string
  const formatDateTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

 

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        console.log('Fetching data...');
        const response = await axios.get(ELECTION_DATA_URL);
        const parser = new XMLParser({
          ignoreAttributes: false,
          attributeNamePrefix: ''
        });
        const result = parser.parse(response.data);
        console.log('Parsed result:', result);

        const contestList = result.Report.ElectionSummarySubReport.Report.contestList.ContestIdGroup;
        console.log('Contest list:', contestList);

        const view = getViewType();
        const filteredByType = filterRacesByView(contestList, view);
        const filteredByRace = filterRaces(filteredByType);
        const sortedRaces = sortRaces(filteredByRace);
        setRaces(sortedRaces);

        const timestamp = result.Report.Title.Report.Textbox9;
        setLastUpdated(new Date(timestamp).toLocaleString());
        setLoading(false);
      } catch (error) {
        console.error('Error fetching data:', error);
        setError('Failed to fetch election data');
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl text-red-600">{error}</div>
      </div>
    );
  }
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Loading election results...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-4">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">SF Election Results</h1>
          <div className="mt-1 text-sm text-gray-500">
            Last Updated: {formatDateTime(lastUpdated)}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {races.map((race) => (
            <div key={race.contestId} className="bg-white rounded-lg shadow-sm p-4">
              <h2 className="text-lg font-semibold mb-3 text-gray-900">{race.contestId}</h2>
              
              {race.candidates.map((candidate: any, index: number) => (
                <div key={candidate.name} className="mb-3">
                  <div className="flex justify-between items-center mb-1">
                    <div className="font-medium text-gray-900 flex items-center">
                      {candidate.name}
                      {index === 0 && <span className="ml-2 text-green-600">✓</span>}
                    </div>
                    <div className="font-semibold text-gray-900">
                      {candidate.percentage.toFixed(1)}%
                    </div>
                  </div>
                  
                  <div className="w-full bg-gray-100 rounded-full h-2.5 mb-1">
                    <div 
                      className={`h-2.5 rounded-full transition-all duration-500 ${
                        index === 0 ? 'bg-green-600' : 'bg-blue-600'
                      }`}
                      style={{ width: `${candidate.percentage}%` }}
                    />
                  </div>
                  
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>Total: {candidate.totalVotes.toLocaleString()}</span>
                    <div className="space-x-3">
                      <span>Election Day: {candidate.electionDay.toLocaleString()}</span>
                      <span>Mail: {candidate.voteByMail.toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;