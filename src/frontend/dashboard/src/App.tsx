import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import {
  ACCORDION_SECTIONS,
  ContestCategory,
} from './electionCatalog';
import {
  ParsedContest,
  ParsedElectionSummary,
  parseElectionXml,
} from './electionParser';
import { RaceCard } from './RaceCard';

const REFRESH_INTERVAL = 30000; // 30 seconds

type AppMode = 'dashboard' | 'supervisors' | 'measures' | 'single-race' | 'embeds';

interface RouteConfig {
  mode: AppMode;
  raceSlugs: string[];
  demoPct: string | null;
}

function getRouteConfig(): RouteConfig {
  const params = new URLSearchParams(window.location.search);
  const demoPct = params.get('demo');
  const raceParam = params.get('race') || params.get('embed');
  const viewParam = (params.get('view') || '').toLowerCase();

  if (raceParam) {
    const slugs = raceParam
      .split(',')
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean);
    if (slugs.length > 0) {
      return { mode: 'single-race', raceSlugs: slugs, demoPct };
    }
  }

  if (viewParam === 'supervisors' || viewParam === 'bos') {
    return { mode: 'supervisors', raceSlugs: [], demoPct };
  }
  if (viewParam === 'measures') {
    return { mode: 'measures', raceSlugs: [], demoPct };
  }
  if (viewParam === 'embeds' || viewParam === 'directory') {
    return { mode: 'embeds', raceSlugs: [], demoPct };
  }

  return { mode: 'dashboard', raceSlugs: [], demoPct };
}

function buildDataCandidateUrls(demoPct: string | null): string[] {
  const baseUrl = import.meta.env.BASE_URL || '/';
  const normalizedBase = baseUrl.endsWith('/') ? baseUrl : `${baseUrl}/`;

  if (demoPct !== null) {
    const pctNum = Math.max(0, Math.min(100, parseInt(demoPct, 10) || 0));
    const padded = String(pctNum).padStart(3, '0');
    return [
      `${normalizedBase}data/test_results_${padded}.xml`,
      `http://localhost:5001/api/results/${pctNum}`,
    ];
  }

  const customUrl = import.meta.env.VITE_ELECTION_DATA_URL;
  const urls: string[] = [];
  if (customUrl) {
    urls.push(customUrl);
  }

  if (import.meta.env.DEV) {
    // Vite dev middleware live proxy to sfelections.org/results/20261103/data/summary.xml
    urls.push('/api/sf-live.xml');
  }

  // Static synced XML on GitHub Pages / public folder
  urls.push(`${normalizedBase}data/summary.xml`);
  return urls;
}

function formatTimestamp(isoStr: string): string {
  if (!isoStr) return 'Pending first report';
  const parsed = new Date(isoStr);
  if (Number.isNaN(parsed.getTime())) {
    return isoStr;
  }
  return parsed.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function App() {
  const route = useMemo(() => getRouteConfig(), []);
  const [summary, setSummary] = useState<ParsedElectionSummary | null>(null);
  const [initialLoading, setInitialLoading] = useState<boolean>(true);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copiedSlug, setCopiedSlug] = useState<string | null>(null);

  // Accordion open/close state keyed by ContestCategory
  const [openSections, setOpenSections] = useState<Record<ContestCategory, boolean>>(
    () => {
      const initial: Record<string, boolean> = {};
      for (const sec of ACCORDION_SECTIONS) {
        initial[sec.id] = sec.defaultOpen;
      }
      return initial as Record<ContestCategory, boolean>;
    }
  );

  useEffect(() => {
    let isMounted = true;

    const fetchData = async () => {
      const candidateUrls = buildDataCandidateUrls(route.demoPct);
      let lastErr: unknown = null;

      // Use a 30-second bucket timestamp so browsers bypass stale CDN cache on live polls
      const cacheBust = Math.floor(Date.now() / REFRESH_INTERVAL);

      for (const rawUrl of candidateUrls) {
        const separator = rawUrl.includes('?') ? '&' : '?';
        const url =
          route.demoPct !== null ? rawUrl : `${rawUrl}${separator}_cb=${cacheBust}`;
        try {
          const response = await axios.get<string>(url, {
            responseType: 'text',
            timeout: 12000,
            headers: {
              'Cache-Control': 'no-cache',
            },
          });
          if (typeof response.data === 'string' && response.data.includes('<Report')) {
            const parsed = parseElectionXml(response.data);
            if (isMounted) {
              setSummary(parsed);
              setRefreshError(null);
              setInitialLoading(false);
            }
            return;
          }
        } catch (err) {
          lastErr = err;
        }
      }

      if (isMounted) {
        console.error('Election feed fetch error:', lastErr);
        setRefreshError('Unable to reach live election feed.');
        setInitialLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, REFRESH_INTERVAL);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [route.demoPct]);

  // Auto-resize height notification for parent article iframes
  useEffect(() => {
    if (route.mode === 'single-race' || route.mode === 'supervisors' || route.mode === 'measures') {
      const sendHeight = () => {
        const height = document.documentElement.scrollHeight;
        window.parent?.postMessage(
          {
            type: 'sf-election-embed-resize',
            height,
            races: route.raceSlugs,
          },
          '*'
        );
      };
      sendHeight();
      window.addEventListener('resize', sendHeight);
      return () => window.removeEventListener('resize', sendHeight);
    }
  }, [route.mode, route.raceSlugs, summary]);

  const visibleContests = useMemo(() => {
    if (!summary) return [];
    return summary.contests.filter((c) => !c.hiddenZeroVoterOverlap);
  }, [summary]);

  const formattedUpdated = useMemo(
    () => (summary ? formatTimestamp(summary.timestampIso) : ''),
    [summary]
  );

  const toggleSection = (id: ContestCategory) => {
    setOpenSections((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const setAllSections = (open: boolean) => {
    const next: Record<string, boolean> = {};
    for (const sec of ACCORDION_SECTIONS) {
      next[sec.id] = open;
    }
    setOpenSections(next as Record<ContestCategory, boolean>);
  };

  if (initialLoading && !summary) {
    return (
      <div className="flex items-center justify-center min-h-[240px] p-6 bg-gray-50 text-gray-700">
        <div className="text-center">
          <div className="text-base font-semibold">Loading 2026 SF Election Results…</div>
          <div className="text-xs text-gray-500 mt-1">
            San Francisco Department of Elections feed
          </div>
        </div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="flex items-center justify-center min-h-[240px] p-6 bg-gray-50">
        <div className="bg-white border border-red-200 rounded-lg p-4 max-w-md text-center">
          <div className="text-base font-bold text-red-700">
            {refreshError || 'Failed to load election data'}
          </div>
          <p className="text-xs text-gray-600 mt-1">
            The page will automatically retry every 30 seconds.
          </p>
        </div>
      </div>
    );
  }

  // ============================================================================
  // VIEW 1: SINGLE-RACE (OR MULTI-SLUG) ARTICLE EMBED (?race=bos-d2)
  // ============================================================================
  if (route.mode === 'single-race') {
    const matchedContests: ParsedContest[] = [];
    for (const slug of route.raceSlugs) {
      const found = summary.contests.find(
        (c) => c.slug.toLowerCase() === slug || c.xmlId.toLowerCase() === slug
      );
      if (found) matchedContests.push(found);
    }

    if (matchedContests.length === 0) {
      return (
        <div className="p-4 bg-white border border-gray-200 rounded-lg text-sm text-gray-700">
          Contest not found for slug:{' '}
          <code className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">
            {route.raceSlugs.join(', ')}
          </code>
        </div>
      );
    }

    return (
      <div className="bg-transparent p-1 space-y-4">
        {matchedContests.map((contest) => (
          <RaceCard
            key={contest.slug}
            contest={contest}
            isStandaloneEmbed={true}
            lastUpdatedFormatted={formattedUpdated}
          />
        ))}
      </div>
    );
  }

  // ============================================================================
  // VIEW 2: TRUNCATED BOARD OF SUPERVISORS OR MEASURES ROUNDUP (?view=supervisors)
  // ============================================================================
  if (route.mode === 'supervisors' || route.mode === 'measures') {
    const targetCategory: ContestCategory =
      route.mode === 'supervisors' ? 'supervisors' : 'measures';
    const contests = visibleContests.filter((c) => c.category === targetCategory);
    const headerTitle =
      route.mode === 'supervisors'
        ? 'San Francisco Board of Supervisors — 2026 Election Results'
        : 'San Francisco Ballot Measures — 2026 Election Results';
    const headerSub =
      route.mode === 'supervisors'
        ? 'Districts 2, 4, 6, 8, and 10 · First-choice preliminary tallies (Ranked-Choice Voting)'
        : 'Measure RTM and Measures A through J · Simple or supermajority thresholds as required';

    return (
      <div className="bg-gray-50 p-3 sm:p-5">
        <div className="max-w-6xl mx-auto">
          <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4 flex flex-wrap items-center justify-between gap-3 border-t-4 border-t-[#EAB308]">
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900">
                {headerTitle}
              </h1>
              <p className="text-xs sm:text-sm text-gray-600 mt-0.5">{headerSub}</p>
            </div>
            <div className="text-xs text-gray-500 text-right">
              <div className="font-semibold text-gray-800">{summary.reportTitle}</div>
              <div>Updated: {formattedUpdated}</div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {contests.map((contest) => (
              <RaceCard key={contest.slug} contest={contest} />
            ))}
          </div>

          <div className="mt-4 text-xs text-gray-500 flex flex-wrap items-center justify-between gap-2">
            <span>
              Source: San Francisco Department of Elections · {summary.precinctsReported} of{' '}
              {summary.totalPrecincts} precincts reporting
            </span>
            {route.demoPct !== null && (
              <span className="font-semibold text-amber-800">
                Demo Simulation ({route.demoPct}% reporting)
              </span>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ============================================================================
  // VIEW 3: INTERNAL NEWSROOM EMBED DIRECTORY (?view=embeds)
  // ============================================================================
  if (route.mode === 'embeds') {
    const originAndPath = `${window.location.origin}${window.location.pathname}`;
    const demoSuffix = route.demoPct !== null ? `&demo=${route.demoPct}` : '';

    const copySnippet = (slugKey: string, snippet: string) => {
      navigator.clipboard?.writeText(snippet);
      setCopiedSlug(slugKey);
      setTimeout(() => setCopiedSlug(null), 2000);
    };

    const filteredEmbeds = visibleContests.filter((c) => {
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      return (
        c.title.toLowerCase().includes(q) ||
        c.slug.toLowerCase().includes(q) ||
        c.candidates.some((cand) => cand.displayName.toLowerCase().includes(q))
      );
    });

    const bosIframe = `<iframe src="${originAndPath}?view=supervisors${demoSuffix}" width="100%" height="920" frameborder="0" style="border:0;width:100%;"></iframe>`;

    return (
      <div className="min-h-screen bg-gray-50 py-6 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-5 border-t-4 border-t-[#EAB308]">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <span className="inline-block px-2 py-0.5 text-xs font-bold uppercase tracking-wider bg-amber-100 text-amber-900 rounded mb-1">
                  Newsroom Tool
                </span>
                <h1 className="text-2xl font-bold text-gray-900">
                  2026 SF Election Article Embed Directory
                </h1>
                <p className="text-sm text-gray-600 mt-1">
                  Grab ready-to-paste <code className="font-mono text-xs">&lt;iframe&gt;</code>{' '}
                  codes for any individual race or the truncated Board of Supervisors roundup.
                  Reader-facing views never show embed buttons.
                </p>
              </div>
              <a
                href={route.demoPct !== null ? `?demo=${route.demoPct}` : './'}
                className="text-sm font-semibold text-gray-900 bg-amber-400 hover:bg-amber-300 px-3.5 py-2 rounded transition"
              >
                ← Back to Public Dashboard
              </a>
            </div>

            <div className="mt-4 pt-4 border-t border-gray-100 flex flex-wrap items-center justify-between gap-3">
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Filter by race title, candidate name, or slug (e.g. bos-d2, wiener, measure-a)…"
                className="w-full sm:w-96 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
              />
              <div className="flex items-center gap-2 text-xs text-gray-600">
                <span>Preview data:</span>
                {(['live', '25', '50', '100'] as const).map((mode) => {
                  const isCurrent =
                    (mode === 'live' && route.demoPct === null) ||
                    route.demoPct === mode;
                  const href =
                    mode === 'live'
                      ? '?view=embeds'
                      : `?view=embeds&demo=${mode}`;
                  return (
                    <a
                      key={mode}
                      href={href}
                      className={`px-2.5 py-1 rounded font-medium ${
                        isCurrent
                          ? 'bg-gray-900 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {mode === 'live' ? 'Live Feed' : `Demo ${mode}%`}
                    </a>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Truncated Supervisors Dashboard Embed Box */}
          <div className="bg-white rounded-lg border border-gray-200 p-4 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-gray-900">
                Truncated Board of Supervisors Dashboard (All 5 Supervisor Races)
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                URL:{' '}
                <a
                  href={`?view=supervisors${demoSuffix}`}
                  target="_blank"
                  rel="noreferrer"
                  className="underline text-amber-800"
                >
                  {originAndPath}?view=supervisors{demoSuffix}
                </a>
              </p>
            </div>
            <button
              type="button"
              onClick={() => copySnippet('bos-roundup', bosIframe)}
              className="px-3 py-1.5 rounded text-xs font-semibold bg-gray-900 text-white hover:bg-gray-800"
            >
              {copiedSlug === 'bos-roundup'
                ? 'Copied iframe!'
                : 'Copy Supervisors Board <iframe>'}
            </button>
          </div>

          {/* Individual Race Embed Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {filteredEmbeds.map((contest) => {
              const embedUrl = `${originAndPath}?race=${contest.slug}${demoSuffix}`;
              const estHeight = Math.max(240, 140 + contest.candidates.length * 58);
              const iframeCode = `<iframe src="${embedUrl}" width="100%" height="${estHeight}" frameborder="0" style="border:0;width:100%;"></iframe>`;

              return (
                <div
                  key={contest.slug}
                  className="bg-gray-100 rounded-lg p-3 border border-gray-200 space-y-2"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 px-1">
                    <div className="flex items-center gap-2">
                      <code className="text-xs font-bold bg-white px-2 py-0.5 rounded border border-gray-300 text-gray-900">
                        ?race={contest.slug}
                      </code>
                      <a
                        href={`?race=${contest.slug}${demoSuffix}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-amber-900 underline font-medium"
                      >
                        Open standalone ↗
                      </a>
                    </div>
                    <button
                      type="button"
                      onClick={() => copySnippet(contest.slug, iframeCode)}
                      className="px-2.5 py-1 rounded text-xs font-semibold bg-gray-900 text-white hover:bg-gray-800"
                    >
                      {copiedSlug === contest.slug ? 'Copied!' : 'Copy <iframe>'}
                    </button>
                  </div>

                  <RaceCard
                    contest={contest}
                    isStandaloneEmbed={true}
                    lastUpdatedFormatted={formattedUpdated}
                  />
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  // ============================================================================
  // VIEW 4: FULL PUBLIC DASHBOARD WITH CATEGORY ACCORDIONS (/)
  // ============================================================================
  const normalizedSearch = searchQuery.trim().toLowerCase();

  return (
    <div className="min-h-screen bg-gray-50 py-6">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-6">
        {/* Top Masthead & Turnout Summary */}
        <header className="bg-white rounded-lg border border-gray-200 p-5 border-t-4 border-t-[#EAB308]">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <span
                  className="inline-block px-2 py-0.5 text-xs font-bold uppercase tracking-wider text-gray-950 rounded"
                  style={{ backgroundColor: '#FACC15' }}
                >
                  Live Results
                </span>
                <span className="text-xs font-medium text-gray-500">
                  {summary.electionTitle}
                </span>
                {route.demoPct !== null && (
                  <span className="inline-block px-2 py-0.5 text-xs font-semibold bg-amber-100 text-amber-900 rounded">
                    Demo Mode: {route.demoPct}% Reporting
                  </span>
                )}
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
                San Francisco 2026 Election Results
              </h1>
              <p className="mt-1 text-xs sm:text-sm text-gray-600">
                Last Updated: <span className="font-medium text-gray-800">{formattedUpdated}</span>{' '}
                · {summary.reportTitle}
                {refreshError && (
                  <span className="ml-2 text-amber-700 font-medium">
                    (Using cached snapshot — retrying live feed)
                  </span>
                )}
              </p>
            </div>

            {/* Citywide Turnout Stats */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-gray-50 p-3 rounded-lg border border-gray-200 text-left">
              <div>
                <div className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold">
                  SF Turnout
                </div>
                <div className="text-lg font-bold text-gray-900 tabular-nums">
                  {summary.turnoutPercentage.toFixed(1)}%
                </div>
                <div className="text-[11px] text-gray-500 tabular-nums">
                  {summary.totalBallotsCast.toLocaleString()} ballots
                </div>
              </div>

              <div>
                <div className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold">
                  Precincts
                </div>
                <div className="text-lg font-bold text-gray-900 tabular-nums">
                  {summary.precinctsReported} / {summary.totalPrecincts}
                </div>
                <div className="text-[11px] text-gray-500">In-person reporting</div>
              </div>

              <div>
                <div className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold">
                  Vote by Mail
                </div>
                <div className="text-lg font-bold text-gray-900 tabular-nums">
                  {summary.voteByMailBallots.toLocaleString()}
                </div>
                <div className="text-[11px] text-gray-500">Ballots counted</div>
              </div>

              <div>
                <div className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold">
                  Election Day
                </div>
                <div className="text-lg font-bold text-gray-900 tabular-nums">
                  {summary.electionDayBallots.toLocaleString()}
                </div>
                <div className="text-[11px] text-gray-500">Ballots counted</div>
              </div>
            </div>
          </div>

          {/* Pre-8:45 PM Election Night Notice when all totals are 0 */}
          {!summary.hasAnyVotes && (
            <div className="mt-4 px-3.5 py-2.5 rounded-md bg-amber-50 border border-amber-200 text-xs sm:text-sm text-amber-950">
              <span className="font-semibold">Awaiting first preliminary results:</span> The San
              Francisco Department of Elections releases the first preliminary report on Election
              Night (Tuesday, November 3, 2026) at approximately 8:45 PM PST, followed by updates
              around 9:45 PM, 10:45 PM, and after all polling places report.
            </div>
          )}

          {/* Search & Expand/Collapse Controls */}
          <div className="mt-4 pt-4 border-t border-gray-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="relative flex-1 max-w-md">
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search races or candidates (e.g. District 2, Measure A, Wiener)…"
                className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#EAB308]"
              />
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setAllSections(true)}
                className="px-3 py-1.5 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded transition"
              >
                Expand All Sections
              </button>
              <button
                type="button"
                onClick={() => setAllSections(false)}
                className="px-3 py-1.5 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded transition"
              >
                Collapse All
              </button>
            </div>
          </div>
        </header>

        {/* Category Accordions */}
        <div className="space-y-4">
          {ACCORDION_SECTIONS.map((section) => {
            const sectionContests = visibleContests.filter((c) => {
              if (c.category !== section.id) return false;
              if (!normalizedSearch) return true;
              return (
                c.title.toLowerCase().includes(normalizedSearch) ||
                c.shortTitle.toLowerCase().includes(normalizedSearch) ||
                c.candidates.some((cand) =>
                  cand.displayName.toLowerCase().includes(normalizedSearch)
                )
              );
            });

            if (sectionContests.length === 0) {
              return null;
            }

            // Auto-open section when searching
            const isOpen = normalizedSearch ? true : openSections[section.id];

            return (
              <section
                key={section.id}
                className="bg-white rounded-lg border border-gray-200 overflow-hidden"
              >
                {/* Accordion Header Button */}
                <button
                  type="button"
                  onClick={() => toggleSection(section.id)}
                  aria-expanded={isOpen}
                  className="w-full px-4 sm:px-5 py-3.5 text-left flex items-center justify-between gap-4 hover:bg-gray-50 transition"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-base sm:text-lg font-bold text-gray-900">
                        {section.title}
                      </h2>
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-700">
                        {sectionContests.length}{' '}
                        {sectionContests.length === 1 ? 'contest' : 'contests'}
                      </span>
                      {section.scopeBanner && section.id !== 'congress_leg' && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-amber-50 text-amber-900 border border-amber-300">
                          SF County Totals Only
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{section.subtitle}</p>
                  </div>

                  <span
                    className="shrink-0 inline-flex items-center justify-center w-7 h-7 rounded-full bg-gray-100 text-gray-700 text-xs font-bold"
                    aria-hidden="true"
                  >
                    {isOpen ? '−' : '+'}
                  </span>
                </button>

                {/* Accordion Body */}
                {isOpen && (
                  <div className="p-4 sm:p-5 border-t border-gray-200 bg-gray-50/60 space-y-4">
                    {section.scopeBanner && (
                      <div className="px-3.5 py-2.5 rounded-md bg-amber-50 border border-amber-200 text-xs sm:text-sm text-amber-950">
                        {section.scopeBanner}
                      </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {sectionContests.map((contest) => (
                        <RaceCard key={contest.slug} contest={contest} />
                      ))}
                    </div>
                  </div>
                )}
              </section>
            );
          })}
        </div>

        {/* Footer */}
        <footer className="text-xs text-gray-500 pt-2 pb-8 flex flex-wrap items-center justify-between gap-3">
          <div>
            Data source: City and County of San Francisco Department of Elections (
            <code className="font-mono">sfelections.org</code>). Registered SF voters:{' '}
            {summary.registeredVoters.toLocaleString()}.
          </div>
          <div className="flex items-center gap-4">
            <a href="?view=supervisors" className="hover:underline text-gray-600">
              Supervisors View
            </a>
            <a href="?view=measures" className="hover:underline text-gray-600">
              Measures View
            </a>
            <a href="?view=embeds" className="hover:underline text-gray-600">
              Embed Directory
            </a>
          </div>
        </footer>
      </div>
    </div>
  );
}

export default App;
