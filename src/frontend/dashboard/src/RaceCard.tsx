import { ParsedContest } from './electionParser';

interface RaceCardProps {
  contest: ParsedContest;
  /** Compact footer with timestamp when rendered as a standalone article embed. */
  isStandaloneEmbed?: boolean;
  lastUpdatedFormatted?: string;
}

export function RaceCard({
  contest,
  isStandaloneEmbed = false,
  lastUpdatedFormatted,
}: RaceCardProps) {
  const showSfScopeBadge =
    contest.scope === 'statewide' || contest.scope === 'multi-county';

  const leaderLabel = contest.seats > 1 ? `Top ${contest.seats}` : 'Leading';

  return (
    <article className="bg-white rounded-lg border border-gray-200 p-4 sm:p-5 flex flex-col justify-between">
      <div>
        {/* Card Header */}
        <div className="flex items-start justify-between gap-3 mb-2">
          <div>
            <h3 className="text-base sm:text-lg font-bold text-gray-900 leading-snug">
              {contest.title}
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {contest.ruleLabel} · {contest.precinctsLabel}
            </p>
          </div>

          {showSfScopeBadge && (
            <span
              className="shrink-0 inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-50 text-amber-900 border border-amber-300"
              title={contest.scopeNote}
            >
              SF Votes Only
            </span>
          )}
        </div>

        {/* Multi-county / Statewide SF-only note */}
        {contest.scopeNote && (
          <div className="mb-3 px-2.5 py-1.5 rounded bg-gray-50 border border-gray-200 text-xs text-gray-600">
            <span className="font-semibold text-gray-800">Note: </span>
            {contest.scopeNote}
          </div>
        )}

        {/* Two-tone Bar Legend */}
        <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-gray-500 mb-3 pb-2 border-b border-gray-100">
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1">
              <span
                className="inline-block w-2.5 h-2.5 rounded-sm"
                style={{ backgroundColor: '#EAB308' }}
              />
              <span
                className="inline-block w-2.5 h-2.5 rounded-sm"
                style={{ backgroundColor: '#4B5563' }}
              />
              <span>Mail</span>
            </span>
            <span className="inline-flex items-center gap-1">
              <span
                className="inline-block w-2.5 h-2.5 rounded-sm"
                style={{ backgroundColor: '#FDE047' }}
              />
              <span
                className="inline-block w-2.5 h-2.5 rounded-sm"
                style={{ backgroundColor: '#9CA3AF' }}
              />
              <span>Election Day</span>
            </span>
          </div>
          <span>
            {contest.totalVotes > 0
              ? `${contest.totalVotes.toLocaleString()} total votes`
              : 'Awaiting first returns'}
          </span>
        </div>

        {/* Vertically Stacked Candidate Rows (Ordered by Votes Descending) */}
        <div className="divide-y divide-gray-100">
          {contest.candidates.map((candidate) => {
            const mailBarColor = candidate.isLeader ? '#EAB308' : '#4B5563';
            const edBarColor = candidate.isLeader ? '#FDE047' : '#9CA3AF';

            return (
              <div key={candidate.name} className="py-2.5 first:pt-0 last:pb-0">
                {/* Candidate Name + Percentage & Total Votes */}
                <div className="flex items-baseline justify-between gap-2 mb-1.5">
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className={`text-sm truncate ${
                        candidate.isLeader
                          ? 'font-bold text-gray-900'
                          : 'font-medium text-gray-800'
                      }`}
                    >
                      {candidate.displayName}
                    </span>
                    {candidate.isLeader && (
                      <span
                        className="shrink-0 inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide text-gray-950"
                        style={{ backgroundColor: '#FACC15' }}
                      >
                        {leaderLabel}
                      </span>
                    )}
                  </div>

                  <div className="shrink-0 text-right">
                    <span
                      className={`text-sm tabular-nums ${
                        candidate.isLeader
                          ? 'font-bold text-gray-900'
                          : 'font-semibold text-gray-700'
                      }`}
                    >
                      {candidate.percentage.toFixed(1)}%
                    </span>
                    <span className="ml-1.5 text-xs text-gray-500 tabular-nums">
                      ({candidate.totalVotes.toLocaleString()})
                    </span>
                  </div>
                </div>

                {/* Horizontal Two-Tone Bar (Mail + Election Day) */}
                <div className="w-full bg-gray-100 rounded h-3.5 overflow-hidden flex">
                  {candidate.mailPercentageOfRace > 0 && (
                    <div
                      className="h-full transition-all duration-500"
                      style={{
                        width: `${Math.min(100, candidate.mailPercentageOfRace)}%`,
                        backgroundColor: mailBarColor,
                      }}
                      title={`Vote by Mail: ${candidate.voteByMail.toLocaleString()} votes`}
                    />
                  )}
                  {candidate.electionDayPercentageOfRace > 0 && (
                    <div
                      className="h-full transition-all duration-500"
                      style={{
                        width: `${Math.min(
                          100 - candidate.mailPercentageOfRace,
                          candidate.electionDayPercentageOfRace
                        )}%`,
                        backgroundColor: edBarColor,
                      }}
                      title={`Election Day: ${candidate.electionDay.toLocaleString()} votes`}
                    />
                  )}
                </div>

                {/* Mail vs. Election Day Sub-caption */}
                <div className="flex items-center justify-between text-[11px] text-gray-500 mt-1 tabular-nums">
                  <span>
                    Mail: {candidate.voteByMail.toLocaleString()} · Election Day:{' '}
                    {candidate.electionDay.toLocaleString()}
                  </span>
                  {contest.totalVotes === 0 && (
                    <span className="text-gray-400">0 votes reported</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Standalone Embed Footer */}
      {isStandaloneEmbed && (
        <div className="mt-4 pt-2.5 border-t border-gray-200 flex flex-wrap items-center justify-between gap-2 text-[11px] text-gray-500">
          <span>Source: SF Dept. of Elections</span>
          {lastUpdatedFormatted && <span>Updated {lastUpdatedFormatted}</span>}
        </div>
      )}
    </article>
  );
}
