export type ContestCategory =
  | 'supervisors'
  | 'measures'
  | 'congress_leg'
  | 'local_boards'
  | 'statewide'
  | 'propositions'
  | 'judicial';

export type JurisdictionScope =
  | 'sf-only'
  | 'sf-district'
  | 'multi-county'
  | 'statewide';

export interface ContestMetadata {
  slug: string;
  xmlId: string;
  title: string;
  shortTitle: string;
  category: ContestCategory;
  scope: JurisdictionScope;
  /** Note shown when SF votes represent only a portion of a multi-county or statewide race. */
  scopeNote?: string;
  /** Number of winners (e.g., 3 for School Board and Community College Board Full Term). */
  seats: number;
  /** Whether the contest uses Ranked-Choice Voting. */
  isRcv: boolean;
  /** Voting rule label shown in the card subtitle. */
  ruleLabel: string;
  /** True for the 3 zero-voter boundary overlap districts in SF's XML. */
  hiddenZeroVoterOverlap?: boolean;
}

export interface AccordionSectionConfig {
  id: ContestCategory;
  title: string;
  subtitle: string;
  scopeBanner?: string;
  defaultOpen: boolean;
}

export const ACCORDION_SECTIONS: AccordionSectionConfig[] = [
  {
    id: 'supervisors',
    title: 'Board of Supervisors',
    subtitle: 'Districts 2, 4, 6, 8, and 10 · Ranked-choice voting (first-choice preliminary tallies)',
    defaultOpen: true,
  },
  {
    id: 'measures',
    title: 'San Francisco Ballot Measures',
    subtitle: 'Measure RTM and Measures A through J · Citywide ballot measures',
    defaultOpen: true,
  },
  {
    id: 'congress_leg',
    title: 'U.S. Congress & California Legislature',
    subtitle: 'U.S. House Districts 11 & 15 · State Assembly Districts 17 & 19',
    scopeBanner:
      'District boundaries note: U.S. House District 11 and State Assembly District 17 are contained entirely within San Francisco (totals shown are the full district results). U.S. House District 15 and State Assembly District 19 also include portions of San Mateo County (totals shown for D15 and AD-19 are San Francisco votes only).',
    defaultOpen: true,
  },
  {
    id: 'local_boards',
    title: 'Education Boards, BART & Citywide Offices',
    subtitle: 'Board of Education, Community College Board, Assessor-Recorder, Public Defender & BART District 8',
    defaultOpen: true,
  },
  {
    id: 'statewide',
    title: 'California Statewide Offices (SF County Vote)',
    subtitle: 'Governor, Lt. Governor, Controller, Insurance Commissioner, Attorney General, Treasurer, Secretary of State, Superintendent & BOE',
    scopeBanner:
      'San Francisco County votes only: These contests are decided statewide (or across multi-county Board of Equalization District 2). Totals below show how San Francisco voters cast their ballots, not statewide totals.',
    defaultOpen: false,
  },
  {
    id: 'propositions',
    title: 'California Statewide Propositions (SF County Vote)',
    subtitle: 'Propositions 1–5 and Propositions 37–45',
    scopeBanner:
      'San Francisco County votes only: Statewide ballot propositions are decided by voters across all 58 California counties. Bars below show San Francisco County returns only.',
    defaultOpen: false,
  },
  {
    id: 'judicial',
    title: 'Supreme Court & Court of Appeal Judicial Confirmations (SF County Vote)',
    subtitle: '13 Yes / No judicial retention questions',
    scopeBanner:
      'San Francisco County votes only: Supreme Court justices are confirmed statewide and Court of Appeal justices are confirmed across the First Appellate District.',
    defaultOpen: false,
  },
];

export const CONTEST_CATALOG: ContestMetadata[] = [
  // 1. Board of Supervisors (even-numbered districts in 2026)
  {
    slug: 'bos-d2',
    xmlId: 'MEMBER, BOARD OF SUPERVISORS, DISTRICT 2',
    title: 'Board of Supervisors — District 2',
    shortTitle: 'Supervisor District 2',
    category: 'supervisors',
    scope: 'sf-district',
    seats: 1,
    isRcv: true,
    ruleLabel: 'Ranked-choice voting · 1st-choice tally',
  },
  {
    slug: 'bos-d4',
    xmlId: 'MEMBER, BOARD OF SUPERVISORS, DISTRICT 4',
    title: 'Board of Supervisors — District 4',
    shortTitle: 'Supervisor District 4',
    category: 'supervisors',
    scope: 'sf-district',
    seats: 1,
    isRcv: true,
    ruleLabel: 'Ranked-choice voting · 1st-choice tally',
  },
  {
    slug: 'bos-d6',
    xmlId: 'MEMBER, BOARD OF SUPERVISORS, DISTRICT 6',
    title: 'Board of Supervisors — District 6',
    shortTitle: 'Supervisor District 6',
    category: 'supervisors',
    scope: 'sf-district',
    seats: 1,
    isRcv: true,
    ruleLabel: 'Ranked-choice voting · 1st-choice tally',
  },
  {
    slug: 'bos-d8',
    xmlId: 'MEMBER, BOARD OF SUPERVISORS, DISTRICT 8',
    title: 'Board of Supervisors — District 8',
    shortTitle: 'Supervisor District 8',
    category: 'supervisors',
    scope: 'sf-district',
    seats: 1,
    isRcv: true,
    ruleLabel: 'Ranked-choice voting · 1st-choice tally',
  },
  {
    slug: 'bos-d10',
    xmlId: 'MEMBER, BOARD OF SUPERVISORS, DISTRICT 10',
    title: 'Board of Supervisors — District 10',
    shortTitle: 'Supervisor District 10',
    category: 'supervisors',
    scope: 'sf-district',
    seats: 1,
    isRcv: true,
    ruleLabel: 'Ranked-choice voting · 1st-choice tally',
  },

  // 2. SF Local Measures
  {
    slug: 'measure-rtm',
    xmlId: 'Measure RTM',
    title: 'Measure RTM',
    shortTitle: 'Measure RTM',
    category: 'measures',
    scope: 'sf-only',
    seats: 1,
    isRcv: false,
    ruleLabel: 'SF Local Measure',
  },
  ...(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'] as const).map(
    (letter): ContestMetadata => ({
      slug: `measure-${letter.toLowerCase()}`,
      xmlId: `Measure ${letter}`,
      title: `Measure ${letter}`,
      shortTitle: `Measure ${letter}`,
      category: 'measures',
      scope: 'sf-only',
      seats: 1,
      isRcv: false,
      ruleLabel: 'SF Local Measure',
    })
  ),

  // 3. U.S. Congress & State Legislature (SF active districts)
  {
    slug: 'us-rep-d11',
    xmlId: 'UNITED STATES REPRESENTATIVE, DISTRICT 11',
    title: 'U.S. Representative — District 11',
    shortTitle: 'U.S. House District 11',
    category: 'congress_leg',
    scope: 'sf-district',
    scopeNote: 'Entirely within San Francisco (453 of 514 SF precincts; full district results)',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Top-two general election',
  },
  {
    slug: 'us-rep-d15',
    xmlId: 'UNITED STATES REPRESENTATIVE, DISTRICT 15',
    title: 'U.S. Representative — District 15',
    shortTitle: 'U.S. House District 15',
    category: 'congress_leg',
    scope: 'multi-county',
    scopeNote: 'San Francisco votes only (61 SF precincts) — District 15 also includes parts of San Mateo County',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Top-two general election',
  },
  {
    slug: 'assembly-d17',
    xmlId: 'STATE ASSEMBLY MEMBER, DISTRICT 17',
    title: 'State Assembly — District 17',
    shortTitle: 'State Assembly District 17',
    category: 'congress_leg',
    scope: 'sf-district',
    scopeNote: 'Entirely within eastern San Francisco (298 of 514 SF precincts; full district results)',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Top-two general election',
  },
  {
    slug: 'assembly-d19',
    xmlId: 'STATE ASSEMBLY MEMBER, DISTRICT 19',
    title: 'State Assembly — District 19',
    shortTitle: 'State Assembly District 19',
    category: 'congress_leg',
    scope: 'multi-county',
    scopeNote: 'San Francisco votes only (214 SF precincts) — District 19 also includes northern San Mateo County',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Top-two general election',
  },
  // Zero-voter boundary overlap districts in SF XML (hidden by default)
  {
    slug: 'state-senate-d2',
    xmlId: 'STATE SENATOR, DISTRICT 2',
    title: 'State Senator — District 2',
    shortTitle: 'State Senate District 2',
    category: 'congress_leg',
    scope: 'multi-county',
    scopeNote: 'San Francisco votes only (0 registered SF voters in boundary precinct)',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Top-two general election',
    hiddenZeroVoterOverlap: true,
  },
  {
    slug: 'assembly-d12',
    xmlId: 'STATE ASSEMBLY MEMBER, DISTRICT 12',
    title: 'State Assembly — District 12',
    shortTitle: 'State Assembly District 12',
    category: 'congress_leg',
    scope: 'multi-county',
    scopeNote: 'San Francisco votes only (0 registered SF voters in boundary precinct)',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Top-two general election',
    hiddenZeroVoterOverlap: true,
  },
  {
    slug: 'assembly-d18',
    xmlId: 'STATE ASSEMBLY MEMBER, DISTRICT 18',
    title: 'State Assembly — District 18',
    shortTitle: 'State Assembly District 18',
    category: 'congress_leg',
    scope: 'multi-county',
    scopeNote: 'San Francisco votes only (0 registered SF voters in boundary precinct)',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Top-two general election',
    hiddenZeroVoterOverlap: true,
  },

  // 4. SF Education Boards, BART & Citywide Offices
  {
    slug: 'board-of-education',
    xmlId: 'MEMBER, BOARD OF EDUCATION',
    title: 'Board of Education (SFUSD)',
    shortTitle: 'SF Board of Education',
    category: 'local_boards',
    scope: 'sf-only',
    seats: 3,
    isRcv: false,
    ruleLabel: 'Vote for up to 3 · Top 3 elected',
  },
  {
    slug: 'ccsf-full-term',
    xmlId: 'TRUSTEE, COMMUNITY COLLEGE BOARD FULL TERM',
    title: 'Community College Board — Full Term',
    shortTitle: 'College Board (Full Term)',
    category: 'local_boards',
    scope: 'sf-only',
    seats: 3,
    isRcv: false,
    ruleLabel: 'Vote for up to 3 · Top 3 elected',
  },
  {
    slug: 'ccsf-partial-term',
    xmlId: 'TRUSTEE, COMMUNITY COLLEGE BOARD PARTIAL TERM',
    title: 'Community College Board — Partial Term',
    shortTitle: 'College Board (Partial Term)',
    category: 'local_boards',
    scope: 'sf-only',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Vote for 1 · Unopposed',
  },
  {
    slug: 'assessor-recorder',
    xmlId: 'ASSESSOR-RECORDER',
    title: 'Assessor-Recorder',
    shortTitle: 'Assessor-Recorder',
    category: 'local_boards',
    scope: 'sf-only',
    seats: 1,
    isRcv: true,
    ruleLabel: 'Citywide office · Unopposed',
  },
  {
    slug: 'public-defender',
    xmlId: 'PUBLIC DEFENDER',
    title: 'Public Defender',
    shortTitle: 'Public Defender',
    category: 'local_boards',
    scope: 'sf-only',
    seats: 1,
    isRcv: true,
    ruleLabel: 'Citywide office · Unopposed',
  },
  {
    slug: 'bart-d8',
    xmlId: 'BART BOARD OF DIRECTORS, DISTRICT 8',
    title: 'BART Board of Directors — District 8',
    shortTitle: 'BART Board District 8',
    category: 'local_boards',
    scope: 'sf-district',
    scopeNote: 'Entirely within western/northern San Francisco (244 of 514 SF precincts; full district results)',
    seats: 1,
    isRcv: false,
    ruleLabel: 'District 8 · Unopposed',
  },

  // 5. Statewide Offices (SF County Vote)
  {
    slug: 'governor',
    xmlId: 'GOVERNOR',
    title: 'Governor',
    shortTitle: 'Governor (SF Vote)',
    category: 'statewide',
    scope: 'statewide',
    scopeNote: 'San Francisco County votes only — statewide contest',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Statewide office · SF County returns',
  },
  {
    slug: 'lt-governor',
    xmlId: 'LIEUTENANT GOVERNOR',
    title: 'Lieutenant Governor',
    shortTitle: 'Lt. Governor (SF Vote)',
    category: 'statewide',
    scope: 'statewide',
    scopeNote: 'San Francisco County votes only — statewide contest',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Statewide office · SF County returns',
  },
  {
    slug: 'controller',
    xmlId: 'CONTROLLER',
    title: 'State Controller',
    shortTitle: 'Controller (SF Vote)',
    category: 'statewide',
    scope: 'statewide',
    scopeNote: 'San Francisco County votes only — statewide contest',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Statewide office · SF County returns',
  },
  {
    slug: 'insurance-commissioner',
    xmlId: 'INSURANCE COMMISSIONER',
    title: 'Insurance Commissioner',
    shortTitle: 'Insurance Commissioner (SF Vote)',
    category: 'statewide',
    scope: 'statewide',
    scopeNote: 'San Francisco County votes only — statewide contest',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Statewide office · SF County returns',
  },
  {
    slug: 'attorney-general',
    xmlId: 'ATTORNEY GENERAL',
    title: 'Attorney General',
    shortTitle: 'Attorney General (SF Vote)',
    category: 'statewide',
    scope: 'statewide',
    scopeNote: 'San Francisco County votes only — statewide contest',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Statewide office · SF County returns',
  },
  {
    slug: 'state-treasurer',
    xmlId: 'TREASURER',
    title: 'State Treasurer',
    shortTitle: 'Treasurer (SF Vote)',
    category: 'statewide',
    scope: 'statewide',
    scopeNote: 'San Francisco County votes only — statewide contest',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Statewide office · SF County returns',
  },
  {
    slug: 'secretary-of-state',
    xmlId: 'SECRETARY OF STATE',
    title: 'Secretary of State',
    shortTitle: 'Secretary of State (SF Vote)',
    category: 'statewide',
    scope: 'statewide',
    scopeNote: 'San Francisco County votes only — statewide contest',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Statewide office · SF County returns',
  },
  {
    slug: 'superintendent-public-instruction',
    xmlId: 'SUPERINTENDENT OF PUBLIC INSTRUCTION',
    title: 'Superintendent of Public Instruction',
    shortTitle: 'State Superintendent (SF Vote)',
    category: 'statewide',
    scope: 'statewide',
    scopeNote: 'San Francisco County votes only — statewide contest',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Statewide nonpartisan office · SF County returns',
  },
  {
    slug: 'boe-d2',
    xmlId: 'BOARD OF EQUALIZATION MEMBER, DISTRICT 2',
    title: 'Board of Equalization — District 2',
    shortTitle: 'Board of Equalization D2 (SF Vote)',
    category: 'statewide',
    scope: 'multi-county',
    scopeNote: 'San Francisco County votes only — multi-county coastal district',
    seats: 1,
    isRcv: false,
    ruleLabel: 'Multi-county district · SF County returns',
  },

  // 6. Statewide Propositions (SF County Vote)
  ...([1, 2, 3, 4, 5, 37, 38, 39, 40, 41, 42, 43, 44, 45] as const).map(
    (num): ContestMetadata => ({
      slug: `prop-${num}`,
      xmlId: `Proposition ${num}`,
      title: `Proposition ${num}`,
      shortTitle: `Prop ${num} (SF Vote)`,
      category: 'propositions',
      scope: 'statewide',
      scopeNote: 'San Francisco County votes only — statewide proposition',
      seats: 1,
      isRcv: false,
      ruleLabel: 'CA Statewide Proposition · SF County returns',
    })
  ),

  // 7. Judicial Confirmations
  ...[
    {
      slug: 'justice-groban',
      xmlId: 'ASSOCIATE JUSTICE OF THE SUPREME COURT (JOSHUA GROBAN)',
      title: 'Supreme Court — Associate Justice Joshua Groban',
    },
    {
      slug: 'justice-evans',
      xmlId: 'ASSOCIATE JUSTICE OF THE SUPREME COURT (KELLI M. EVANS)',
      title: 'Supreme Court — Associate Justice Kelli M. Evans',
    },
    {
      slug: 'justice-wilson',
      xmlId: 'ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 1 (MONIQUE LANGHORNE WILSON)',
      title: 'Court of Appeal, Div. 1 — Justice Monique Langhorne Wilson',
    },
    {
      slug: 'justice-smiley',
      xmlId: 'ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 1 (CHARLES A. SMILEY)',
      title: 'Court of Appeal, Div. 1 — Justice Charles A. Smiley',
    },
    {
      slug: 'justice-banke',
      xmlId: 'ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 1 (KATHLEEN M. BANKE)',
      title: 'Court of Appeal, Div. 1 — Justice Kathleen M. Banke',
    },
    {
      slug: 'justice-stewart',
      xmlId: 'PRESIDING JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 2 (THERESE M. STEWART)',
      title: 'Court of Appeal, Div. 2 — Presiding Justice Therese M. Stewart',
    },
    {
      slug: 'justice-desautels',
      xmlId: 'ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 2 (TARA M. DESAUTELS)',
      title: 'Court of Appeal, Div. 2 — Justice Tara M. Desautels',
    },
    {
      slug: 'justice-petrou',
      xmlId: 'ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 3 (IOANA PETROU)',
      title: 'Court of Appeal, Div. 3 — Justice Ioana Petrou',
    },
    {
      slug: 'justice-rodriguez',
      xmlId: 'ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 3 (VICTOR A. RODRIGUEZ)',
      title: 'Court of Appeal, Div. 3 — Justice Victor A. Rodriguez',
    },
    {
      slug: 'justice-brown',
      xmlId: 'PRESIDING JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 4 (TRACIE L. BROWN)',
      title: 'Court of Appeal, Div. 4 — Presiding Justice Tracie L. Brown',
    },
    {
      slug: 'justice-chou',
      xmlId: 'ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 5 (DANNY Y. CHOU)',
      title: 'Court of Appeal, Div. 5 — Justice Danny Y. Chou',
    },
    {
      slug: 'justice-simons',
      xmlId: 'ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 5 (MARK SIMONS)',
      title: 'Court of Appeal, Div. 5 — Justice Mark Simons',
    },
    {
      slug: 'justice-burns',
      xmlId: 'ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 5 (GORDON BURNS)',
      title: 'Court of Appeal, Div. 5 — Justice Gordon Burns',
    },
  ].map(
    (j): ContestMetadata => ({
      slug: j.slug,
      xmlId: j.xmlId,
      title: j.title,
      shortTitle: j.title,
      category: 'judicial',
      scope: 'multi-county',
      scopeNote: 'San Francisco County votes only — statewide / appellate district confirmation',
      seats: 1,
      isRcv: false,
      ruleLabel: 'Judicial Confirmation (Yes / No) · SF County returns',
    })
  ),
];

const BY_XML_ID = new Map<string, ContestMetadata>(
  CONTEST_CATALOG.map((c) => [c.xmlId.toUpperCase(), c])
);

const BY_SLUG = new Map<string, ContestMetadata>(
  CONTEST_CATALOG.map((c) => [c.slug.toLowerCase(), c])
);

export function findContestByXmlId(rawXmlId: string): ContestMetadata | undefined {
  const normalized = rawXmlId.trim().toUpperCase();
  return BY_XML_ID.get(normalized);
}

export function findContestBySlug(slug: string): ContestMetadata | undefined {
  const normalized = slug.trim().toLowerCase();
  return BY_SLUG.get(normalized);
}
