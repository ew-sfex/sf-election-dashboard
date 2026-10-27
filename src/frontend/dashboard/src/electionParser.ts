import { XMLParser } from 'fast-xml-parser';
import {
  CONTEST_CATALOG,
  ContestCategory,
  JurisdictionScope,
  findContestByXmlId,
} from './electionCatalog';

export interface ParsedCandidate {
  name: string;
  displayName: string;
  voteByMail: number;
  electionDay: number;
  totalVotes: number;
  percentage: number;
  mailPercentageOfRace: number;
  electionDayPercentageOfRace: number;
  isLeader: boolean;
  isWriteIn: boolean;
}

export interface ParsedContest {
  slug: string;
  xmlId: string;
  title: string;
  shortTitle: string;
  category: ContestCategory;
  scope: JurisdictionScope;
  scopeNote?: string;
  seats: number;
  isRcv: boolean;
  ruleLabel: string;
  hiddenZeroVoterOverlap: boolean;
  precinctsReported: number;
  totalPrecincts: number;
  precinctsLabel: string;
  ballotsCast: number;
  registeredVoters: number;
  totalVotes: number;
  candidates: ParsedCandidate[];
}

export interface ParsedElectionSummary {
  electionTitle: string;
  reportTitle: string;
  timestampIso: string;
  registeredVoters: number;
  totalBallotsCast: number;
  voteByMailBallots: number;
  electionDayBallots: number;
  turnoutPercentage: number;
  precinctsReported: number;
  totalPrecincts: number;
  hasAnyVotes: boolean;
  contests: ParsedContest[];
}

function asArray<T>(val: T | T[] | undefined | null): T[] {
  if (val === undefined || val === null) return [];
  return Array.isArray(val) ? val : [val];
}

function toInt(val: unknown): number {
  if (typeof val === 'number') return Number.isFinite(val) ? Math.trunc(val) : 0;
  if (typeof val === 'string') {
    const cleaned = val.replace(/,/g, '').trim();
    const parsed = parseInt(cleaned, 10);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function formatCandidateDisplayName(rawName: string): string {
  const trimmed = rawName.trim();
  if (!trimmed) return 'Candidate';
  if (trimmed === 'YES' || trimmed === 'NO') {
    return trimmed === 'YES' ? 'Yes' : 'No';
  }
  if (trimmed === 'BONDS - YES') return 'Yes (Bonds)';
  if (trimmed === 'BONDS - NO') return 'No (Bonds)';
  if (trimmed.toUpperCase() === 'WRITE-IN') return 'Write-in';

  // Convert UPPERCASE candidate names into readable Title Case while preserving initials and Roman numerals
  return trimmed
    .split(/\s+/)
    .map((word) => {
      if (/^(II|III|IV|JR\.|SR\.)$/i.test(word)) {
        return word.toUpperCase() === 'JR.'
          ? 'Jr.'
          : word.toUpperCase() === 'SR.'
            ? 'Sr.'
            : word.toUpperCase();
      }
      if (word.startsWith('"') && word.endsWith('"') && word.length > 2) {
        const inner = word.slice(1, -1);
        return `"${inner.charAt(0).toUpperCase()}${inner.slice(1).toLowerCase()}"`;
      }
      if (word.startsWith('(') && word.endsWith(')') && word.length > 2) {
        const inner = word.slice(1, -1);
        return `(${inner.charAt(0).toUpperCase()}${inner.slice(1).toLowerCase()})`;
      }
      return word
        .split(/(['’-])/)
        .map((part) =>
          /^[A-Za-zÀ-ÖØ-öø-ÿ]+$/.test(part)
            ? part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()
            : part
        )
        .join('');
    })
    .join(' ');
}

function parsePrecinctString(raw: string | undefined): {
  reported: number;
  total: number;
  label: string;
} {
  if (!raw) {
    return { reported: 0, total: 514, label: '0 of 514 precincts reporting' };
  }
  const match = raw.match(/Precincts Reported:\s*(\d+)\s*of\s*(\d+)/i);
  if (match) {
    const reported = toInt(match[1]);
    const total = toInt(match[2]);
    return {
      reported,
      total,
      label: `${reported.toLocaleString()} of ${total.toLocaleString()} precincts reporting`,
    };
  }
  return { reported: 0, total: 514, label: raw.trim() };
}

function parseBallotsAndRegistered(raw: string | undefined): {
  ballots: number;
  registered: number;
} {
  if (!raw) return { ballots: 0, registered: 0 };
  const parts = raw.split('/');
  if (parts.length === 2) {
    return {
      ballots: toInt(parts[0]),
      registered: toInt(parts[1]),
    };
  }
  return { ballots: 0, registered: 0 };
}

type XmlNode = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

export function parseElectionXml(xmlText: string): ParsedElectionSummary {
  const parser = new XMLParser({
    ignoreAttributes: false,
    attributeNamePrefix: '',
  });

  const parsed: XmlNode = parser.parse(xmlText);
  const reportRoot: XmlNode = parsed?.Report ?? {};

  // 1. Title metadata
  const titleReport: XmlNode = reportRoot?.Title?.Report ?? {};
  const timestampIso: string = titleReport?.Textbox9 ?? '';
  const rawTextbox8: string = titleReport?.Textbox8 ?? '';
  const titleLines = rawTextbox8
    .split(/\r?\n/)
    .map((s: string) => s.trim())
    .filter(Boolean);
  const electionTitle =
    titleLines[1] || 'November 3, 2026 Consolidated General Election';
  const reportTitle = titleLines[2] || 'Preliminary Summary Report';

  // 2. Registration and Turnout
  const electorGroup: XmlNode =
    reportRoot?.RegistrationAndTurnout?.Report?.Tablix10
      ?.electorGroupId2_Collection?.electorGroupId2 ?? {};
  const registeredVoters = toInt(electorGroup?.Textbox32) || 533714;
  const totalBallotsCast = toInt(electorGroup?.ballots3);
  const turnoutRatio = parseFloat(electorGroup?.Textbox6 ?? '0');
  const turnoutPercentage = Number.isFinite(turnoutRatio)
    ? turnoutRatio * 100
    : registeredVoters > 0
      ? (totalBallotsCast / registeredVoters)
      : 0;

  let electionDayBallots = 0;
  let voteByMailBallots = 0;
  for (const detail of asArray<XmlNode>(electorGroup?.Details1)) {
    const groupName = String(detail?.countingGroup1 ?? '');
    const count = toInt(detail?.Textbox171);
    if (groupName.toLowerCase().includes('election day')) {
      electionDayBallots = count;
    } else if (groupName.toLowerCase().includes('mail')) {
      voteByMailBallots = count;
    }
  }

  // 3. Locate ElectionSummarySubReport (supports both live tabBatchIdList wrapper and direct child)
  const subReport: XmlNode =
    reportRoot?.tabBatchIdList?.TabBatchGroup_Collection?.TabBatchGroup
      ?.ElectionSummarySubReport?.Report ??
    reportRoot?.ElectionSummarySubReport?.Report ??
    reportRoot?.ElectionSummarySubReport ??
    {};

  const overallPrecinctAttr =
    subReport?.Tablix2?.Details_Collection?.Details?.reported;
  const overallPrecincts = parsePrecinctString(overallPrecinctAttr);

  const rawContestGroups = asArray<XmlNode>(
    subReport?.contestList?.ContestIdGroup_Collection?.ContestIdGroup ??
      subReport?.contestList?.ContestIdGroup
  );

  let hasAnyVotes = false;
  const parsedContestsByXmlId = new Map<string, ParsedContest>();

  for (const group of rawContestGroups) {
    const rawContestId = String(group?.contestId ?? '').trim();
    if (!rawContestId) continue;

    const meta = findContestByXmlId(rawContestId);
    const slug =
      meta?.slug ??
      rawContestId
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '');

    // Contest statistics
    const statsReport: XmlNode = group?.ContestStatistics?.Report ?? {};
    const precinctText =
      statsReport?.Tablix2?.Details_Collection?.Details?.Textbox2;
    const precinctInfo = parsePrecinctString(precinctText);

    let ballotsCast = 0;
    let contestRegistered = 0;
    for (const tb9 of asArray<XmlNode>(statsReport?.Textbox9)) {
      if (tb9?.ballots2) {
        const br = parseBallotsAndRegistered(String(tb9.ballots2));
        ballotsCast = br.ballots;
        contestRegistered = br.registered;
      }
    }

    // Candidates (supports both SSRS chGroup and simple Candidate nodes)
    const chGroups = asArray<XmlNode>(
      group?.CandidateResults?.Report?.Tablix1?.chGroup_Collection?.chGroup
    );
    const simpleCandidates = asArray<XmlNode>(
      group?.CandidateResults?.Candidate
    );

    const rawCandidates: Array<{
      name: string;
      displayName: string;
      voteByMail: number;
      electionDay: number;
      totalVotes: number;
      isWriteIn: boolean;
    }> = [];

    if (chGroups.length > 0) {
      for (const ch of chGroups) {
        const candBox: XmlNode = ch?.candidateNameTextBox4 ?? {};
        const rawName = String(candBox?.candidateNameTextBox4 ?? '').trim();
        if (!rawName) continue;

        let edVotes = 0;
        let vbmVotes = 0;
        const cgList = asArray<XmlNode>(
          candBox?.cgGroup_Collection?.cgGroup
        );
        for (const cg of cgList) {
          const cgName = String(cg?.countingGroupName ?? '').toLowerCase();
          const votes = toInt(cg?.vot7);
          if (cgName.includes('election day')) {
            edVotes = votes;
          } else if (cgName.includes('mail')) {
            vbmVotes = votes;
          }
        }

        const reportedTotal = toInt(candBox?.Textbox13?.vot8);
        const totalVotes = reportedTotal > 0 ? reportedTotal : edVotes + vbmVotes;
        const isWriteIn = rawName.toUpperCase() === 'WRITE-IN';

        rawCandidates.push({
          name: rawName,
          displayName: formatCandidateDisplayName(rawName),
          voteByMail: vbmVotes,
          electionDay: edVotes,
          totalVotes,
          isWriteIn,
        });
      }
    } else if (simpleCandidates.length > 0) {
      for (const sc of simpleCandidates) {
        const rawName = String(sc?.name ?? '').trim();
        if (!rawName) continue;
        const edVotes = toInt(sc?.electionDay);
        const vbmVotes = toInt(sc?.voteByMail);
        const totalVotes = edVotes + vbmVotes;
        rawCandidates.push({
          name: rawName,
          displayName: formatCandidateDisplayName(rawName),
          voteByMail: vbmVotes,
          electionDay: edVotes,
          totalVotes,
          isWriteIn: rawName.toUpperCase() === 'WRITE-IN',
        });
      }
    }

    // Filter out 0-vote Write-in rows so they don't clutter candidate cards unless write-ins actually have votes
    const visibleCandidates = rawCandidates.filter(
      (c) => !c.isWriteIn || c.totalVotes > 0
    );

    const contestTotalVotes = visibleCandidates.reduce(
      (sum, c) => sum + c.totalVotes,
      0
    );
    if (contestTotalVotes > 0) {
      hasAnyVotes = true;
    }

    // Sort candidates by totalVotes descending as votes come in; preserve ballot order when 0 votes
    const sortedCandidates = [...visibleCandidates].sort((a, b) => {
      if (b.totalVotes !== a.totalVotes) {
        return b.totalVotes - a.totalVotes;
      }
      return 0;
    });

    const seats = meta?.seats ?? 1;
    const candidates: ParsedCandidate[] = sortedCandidates.map((c, index) => {
      const percentage =
        contestTotalVotes > 0 ? (c.totalVotes / contestTotalVotes) * 100 : 0;
      const mailPercentageOfRace =
        contestTotalVotes > 0 ? (c.voteByMail / contestTotalVotes) * 100 : 0;
      const electionDayPercentageOfRace =
        contestTotalVotes > 0 ? (c.electionDay / contestTotalVotes) * 100 : 0;
      const isLeader = contestTotalVotes > 0 && index < seats && c.totalVotes > 0;

      return {
        ...c,
        percentage,
        mailPercentageOfRace,
        electionDayPercentageOfRace,
        isLeader,
      };
    });

    const contestObj: ParsedContest = {
      slug,
      xmlId: rawContestId.toUpperCase(),
      title: meta?.title ?? formatCandidateDisplayName(rawContestId),
      shortTitle: meta?.shortTitle ?? formatCandidateDisplayName(rawContestId),
      category: meta?.category ?? 'local_boards',
      scope: meta?.scope ?? 'sf-only',
      scopeNote: meta?.scopeNote,
      seats,
      isRcv: meta?.isRcv ?? false,
      ruleLabel: meta?.ruleLabel ?? 'General election',
      hiddenZeroVoterOverlap: meta?.hiddenZeroVoterOverlap ?? false,
      precinctsReported: precinctInfo.reported,
      totalPrecincts: precinctInfo.total,
      precinctsLabel: precinctInfo.label,
      ballotsCast,
      registeredVoters: contestRegistered,
      totalVotes: contestTotalVotes,
      candidates,
    };

    parsedContestsByXmlId.set(rawContestId.toUpperCase(), contestObj);
  }

  // Order contests according to CONTEST_CATALOG first, followed by any unexpected XML contests
  const orderedContests: ParsedContest[] = [];
  const seenKeys = new Set<string>();

  for (const catItem of CONTEST_CATALOG) {
    const key = catItem.xmlId.toUpperCase();
    const found = parsedContestsByXmlId.get(key);
    if (found) {
      orderedContests.push(found);
      seenKeys.add(key);
    }
  }

  for (const [key, contest] of parsedContestsByXmlId.entries()) {
    if (!seenKeys.has(key)) {
      orderedContests.push(contest);
    }
  }

  return {
    electionTitle,
    reportTitle,
    timestampIso,
    registeredVoters,
    totalBallotsCast,
    voteByMailBallots,
    electionDayBallots,
    turnoutPercentage,
    precinctsReported: overallPrecincts.reported,
    totalPrecincts: overallPrecincts.total,
    hasAnyVotes,
    contests: orderedContests,
  };
}
