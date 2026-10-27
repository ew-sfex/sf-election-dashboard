import json
from datetime import datetime
from pathlib import Path
import random
import xml.etree.ElementTree as ET


class ElectionDataGenerator:
    """
    Generates realistic 2026 San Francisco General Election XML and JSON snapshots
    that match the exact SSRS XML schema published at:
    https://sfelections.org/results/20261103/data/summary.xml
    """

    def __init__(self, seed: int = 20261103):
        self.rng = random.Random(seed)
        self.total_precincts = 514
        self.total_tabulators = 1061
        self.total_registered = 533714

        # Full 2026 SF contest list with realistic final vote targets (VBM, ED),
        # precinct count, registered voters in SF, and whether Write-in appears.
        self.contests = [
            # Statewide Offices
            {
                "id": "GOVERNOR   ",
                "precincts": 514,
                "registered": 533714,
                "candidates": [
                    ("STEVE HILTON ", 42100, 14800),
                    ("XAVIER BECERRA ", 248900, 49200),
                ],
                "has_writein": False,
            },
            {
                "id": "LIEUTENANT GOVERNOR   ",
                "precincts": 514,
                "registered": 533714,
                "candidates": [
                    ("GLORIA ROMERO ", 48200, 15100),
                    ("FIONA MA ", 239400, 46800),
                ],
                "has_writein": False,
            },
            {
                "id": "SECRETARY OF STATE   ",
                "precincts": 514,
                "registered": 533714,
                "candidates": [
                    ("DONALD P. (DON) WAGNER ", 44900, 14200),
                    ("SHIRLEY N. WEBER ", 241800, 47600),
                ],
                "has_writein": False,
            },
            {
                "id": "CONTROLLER   ",
                "precincts": 514,
                "registered": 533714,
                "candidates": [
                    ("MALIA M. COHEN ", 245600, 48900),
                    ("HERB W MORGAN ", 43100, 13900),
                ],
                "has_writein": False,
            },
            {
                "id": "TREASURER   ",
                "precincts": 514,
                "registered": 533714,
                "candidates": [
                    ("JENNIFER HAWKS ", 43800, 14100),
                    ("ELENI KOUNALAKIS ", 246100, 48200),
                ],
                "has_writein": False,
            },
            {
                "id": "ATTORNEY GENERAL   ",
                "precincts": 514,
                "registered": 533714,
                "candidates": [
                    ("ROB BONTA ", 244200, 47900),
                    ("MICHAEL E. GATES ", 45600, 14900),
                ],
                "has_writein": False,
            },
            {
                "id": "INSURANCE COMMISSIONER   ",
                "precincts": 514,
                "registered": 533714,
                "candidates": [
                    ("JANE KIM ", 164800, 36400),
                    ("BEN ALLEN ", 118900, 22800),
                ],
                "has_writein": False,
            },
            {
                "id": "BOARD OF EQUALIZATION MEMBER, DISTRICT 2   ",
                "precincts": 514,
                "registered": 533714,
                "candidates": [
                    ("JOHN PIMENTEL ", 112400, 23100),
                    ("SALLY J. LIEBER ", 164200, 33800),
                ],
                "has_writein": False,
            },
            # Congress & State Legislature
            {
                "id": "UNITED STATES REPRESENTATIVE, DISTRICT 11   ",
                "precincts": 453,
                "registered": 470222,
                "candidates": [
                    ("SCOTT WIENER ", 148200, 29400),
                    ("CONNIE CHAN ", 121900, 26800),
                ],
                "has_writein": False,
            },
            {
                "id": "UNITED STATES REPRESENTATIVE, DISTRICT 15   ",
                "precincts": 61,
                "registered": 63492,
                "candidates": [
                    ("CHARLES HOELTER ", 7420, 2180),
                    ("KEVIN MULLIN ", 26840, 5410),
                ],
                "has_writein": False,
            },
            {
                "id": "STATE SENATOR, DISTRICT 2   ",
                "precincts": 1,
                "registered": 0,
                "candidates": [
                    ("DAMON CONNOLLY ", 0, 0),
                    ("TIEF GIBBS ", 0, 0),
                ],
                "has_writein": False,
            },
            {
                "id": "STATE ASSEMBLY MEMBER, DISTRICT 12   ",
                "precincts": 1,
                "registered": 0,
                "candidates": [
                    ("JACKIE ELWARD ", 0, 0),
                    ("ERIC LUCAN ", 0, 0),
                ],
                "has_writein": False,
            },
            {
                "id": "STATE ASSEMBLY MEMBER, DISTRICT 17   ",
                "precincts": 298,
                "registered": 302455,
                "candidates": [
                    ("MATT HANEY ", 138400, 26200),
                    ("MANUEL NORIS-BARRERA ", 28900, 7400),
                ],
                "has_writein": False,
            },
            {
                "id": "STATE ASSEMBLY MEMBER, DISTRICT 18   ",
                "precincts": 1,
                "registered": 0,
                "candidates": [
                    ("MIA BONTA ", 0, 0),
                    ("ANDRE SANDFORD ", 0, 0),
                ],
                "has_writein": False,
            },
            {
                "id": "STATE ASSEMBLY MEMBER, DISTRICT 19   ",
                "precincts": 214,
                "registered": 231259,
                "candidates": [
                    ("PHILIP LOUIS WING ", 38200, 10400),
                    ("CATHERINE STEFANI ", 94600, 18900),
                ],
                "has_writein": False,
            },
            # Judicial Confirmations
            *[
                {
                    "id": f"{justice}   ",
                    "precincts": 514,
                    "registered": 533714,
                    "candidates": [
                        ("YES ", 210000 + idx * 1300, 41000 + idx * 250),
                        ("NO ", 54000 + idx * 700, 12500 + idx * 180),
                    ],
                    "has_writein": False,
                }
                for idx, justice in enumerate(
                    [
                        "ASSOCIATE JUSTICE OF THE SUPREME COURT (JOSHUA GROBAN)",
                        "ASSOCIATE JUSTICE OF THE SUPREME COURT (KELLI M. EVANS)",
                        "ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 1 (MONIQUE LANGHORNE WILSON)",
                        "ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 1 (CHARLES A. SMILEY)",
                        "ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 1 (KATHLEEN M. BANKE)",
                        "PRESIDING JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 2 (THERESE M. STEWART)",
                        "ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 2 (TARA M. DESAUTELS)",
                        "ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 3 (IOANA PETROU)",
                        "ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 3 (VICTOR A. RODRIGUEZ)",
                        "PRESIDING JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 4 (TRACIE L. BROWN)",
                        "ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 5 (DANNY Y. CHOU)",
                        "ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 5 (MARK SIMONS)",
                        "ASSOCIATE JUSTICE COURT OF APPEAL, FIRST DISTRICT, DIVISION 5 (GORDON BURNS)",
                    ]
                )
            ],
            {
                "id": "SUPERINTENDENT OF PUBLIC INSTRUCTION   ",
                "precincts": 514,
                "registered": 533714,
                "candidates": [
                    ("SONJA SHAW ", 52400, 14800),
                    ("RICHARD BARRERA ", 214600, 42100),
                ],
                "has_writein": True,
            },
            # Local Education & Citywide
            {
                "id": "MEMBER, BOARD OF EDUCATION   ",
                "precincts": 514,
                "registered": 533714,
                "candidates": [
                    ("RYAN HAZELTON ", 112400, 21800),
                    ("PHIL KIM ", 138900, 26400),
                    ("VIRGINIA CHEUNG ", 129600, 24900),
                    ("LAURANCE LEE ", 98200, 19400),
                    ("AUTUMN BROWN GARIBAY ", 84100, 17200),
                    ("ALIDA FISHER ", 119800, 23600),
                    ("REINA TELLO ", 76400, 15900),
                    ("TIM TUNG ", 62300, 13100),
                ],
                "has_writein": True,
            },
            {
                "id": "TRUSTEE, COMMUNITY COLLEGE BOARD FULL TERM   ",
                "precincts": 514,
                "registered": 533714,
                "candidates": [
                    ("LISA P WYNN II ", 82400, 16800),
                    ("ROME MOSES JONES ", 74200, 15100),
                    ("LEAH LACROIX ", 134600, 25900),
                    ("MONROE LACE ", 68900, 14200),
                    ("JEREMY LEE ", 126800, 24100),
                    ("ELIJAH BALL ", 59400, 12300),
                    ("BUNNY MCFADDEN ", 94200, 18900),
                    ("ERWIN TAM ", 118500, 22700),
                ],
                "has_writein": True,
            },
            {
                "id": "TRUSTEE, COMMUNITY COLLEGE BOARD PARTIAL TERM   ",
                "precincts": 514,
                "registered": 533714,
                "candidates": [
                    ("RUTH FERGUSON ", 236400, 44800),
                ],
                "has_writein": True,
            },
            {
                "id": "BART BOARD OF DIRECTORS, DISTRICT 8   ",
                "precincts": 244,
                "registered": 261730,
                "candidates": [
                    ("SARA BARZ ", 122800, 23400),
                ],
                "has_writein": True,
            },
            {
                "id": "ASSESSOR-RECORDER   ",
                "precincts": 514,
                "registered": 533714,
                "candidates": [
                    ("JOAQUÍN TORRES ", 254100, 47900),
                ],
                "has_writein": True,
            },
            {
                "id": "PUBLIC DEFENDER   ",
                "precincts": 514,
                "registered": 533714,
                "candidates": [
                    ("MANO RAJU ", 248900, 46800),
                ],
                "has_writein": True,
            },
            # Board of Supervisors (even districts in 2026)
            {
                "id": "MEMBER, BOARD OF SUPERVISORS, DISTRICT 2   ",
                "precincts": 47,
                "registered": 50676,
                "candidates": [
                    ("STEPHEN SHERRILL ", 11840, 2410),
                    ("NICHOLAS BERG ", 9420, 2680),
                    ("MONTHANUS RATANAPAKDEE ", 4210, 1120),
                    ("GUY MCCOY ", 1890, 540),
                ],
                "has_writein": True,
            },
            {
                "id": "MEMBER, BOARD OF SUPERVISORS, DISTRICT 4   ",
                "precincts": 47,
                "registered": 50949,
                "candidates": [
                    ("ALAN WONG ", 11260, 2590),
                    ("ALBERT CHOW ", 10680, 2940),
                    ("JEREMY JULIAN GRECO ", 2840, 760),
                ],
                "has_writein": True,
            },
            {
                "id": "MEMBER, BOARD OF SUPERVISORS, DISTRICT 6   ",
                "precincts": 43,
                "registered": 38526,
                "candidates": [
                    ("MATT DORSEY ", 11420, 2380),
                    ("ALEX BEHREND ", 8190, 2140),
                ],
                "has_writein": True,
            },
            {
                "id": "MEMBER, BOARD OF SUPERVISORS, DISTRICT 8   ",
                "precincts": 58,
                "registered": 60309,
                "candidates": [
                    ("DARSHINI PATEL ", 11480, 2640),
                    ("MICHAEL T. NGUYEN ", 4620, 1080),
                    ('EMANUEL "MANNY" YEKUTIEL ', 16890, 3420),
                    ("GARY MCCOY ", 2190, 580),
                ],
                "has_writein": True,
            },
            {
                "id": "MEMBER, BOARD OF SUPERVISORS, DISTRICT 10   ",
                "precincts": 51,
                "registered": 45343,
                "candidates": [
                    ("JESSICA PESSECOW ", 3120, 740),
                    ('ELLSWORTH "ELL" M. JENNISON, JR. ', 2480, 610),
                    ("MIKE TROUBLE LIN ", 2890, 690),
                    ('PEARCI "PJ" BASTIANY III ', 4260, 980),
                    ("DIONJAY (DJ) BROOKTER ", 3640, 840),
                    ("DEANDRA BRYANT ", 2190, 520),
                    ("SHAWN M. RICHARD ", 1980, 490),
                    ("J.R. EPPLER ", 4890, 1120),
                    ("THEO ELLINGTON ", 5420, 1340),
                    ("JAMO MUHAMMAD ", 1420, 380),
                ],
                "has_writein": True,
            },
            # Statewide Propositions
            *[
                {
                    "id": f"Proposition {num}   ",
                    "precincts": 514,
                    "registered": 533714,
                    "candidates": (
                        [
                            ("BONDS - YES ", yes_vbm, yes_ed),
                            ("BONDS - NO ", no_vbm, no_ed),
                        ]
                        if is_bond
                        else [
                            ("YES ", yes_vbm, yes_ed),
                            ("NO ", no_vbm, no_ed),
                        ]
                    ),
                    "has_writein": False,
                }
                for num, is_bond, yes_vbm, yes_ed, no_vbm, no_ed in [
                    (1, True, 212400, 42100, 96800, 21400),
                    (2, False, 228900, 45600, 81200, 18900),
                    (3, False, 246100, 49200, 64800, 15200),
                    (4, False, 198400, 39800, 110200, 24100),
                    (5, False, 176200, 36400, 132400, 27900),
                    (37, True, 204600, 41200, 102900, 22800),
                    (38, True, 189400, 38100, 118200, 25400),
                    (39, False, 164200, 33900, 142800, 29600),
                    (40, False, 218900, 43800, 89400, 19800),
                    (41, False, 148200, 31400, 158900, 32900),
                    (42, False, 231400, 46200, 76800, 17400),
                    (43, False, 194800, 39200, 112600, 24600),
                    (44, False, 172600, 35100, 134900, 28400),
                    (45, False, 208400, 41900, 99200, 21800),
                ]
            ],
            # Local Measures
            *[
                {
                    "id": f"Measure {letter}   ",
                    "precincts": 514,
                    "registered": 533714,
                    "candidates": [
                        ("YES ", yes_vbm, yes_ed),
                        ("NO ", no_vbm, no_ed),
                    ],
                    "has_writein": False,
                }
                for letter, yes_vbm, yes_ed, no_vbm, no_ed in [
                    ("RTM", 196400, 38900, 114200, 25400),
                    ("A", 214800, 42600, 96400, 21800),
                    ("B", 184200, 36800, 126900, 27400),
                    ("C", 142600, 29400, 168400, 34900),
                    ("D", 169800, 34200, 141200, 30100),
                    ("E", 202400, 40800, 108600, 23600),
                    ("F", 156400, 31800, 154200, 32600),
                    ("G", 224600, 44900, 86400, 19200),
                    ("H", 178900, 35900, 131800, 28400),
                    ("I", 191200, 38400, 119600, 26100),
                    ("J", 209400, 41800, 101400, 22400),
                ]
            ],
        ]

    @staticmethod
    def _scale_votes(final_vbm: int, final_ed: int, pct: float) -> tuple[int, int]:
        """
        Monotonically scale VBM and Election Day votes as reporting progresses:
        - pct == 0.0: 0 votes (pre-8:45 PM placeholder)
        - pct == 0.25: Report #1 (~8:45 PM) — ~75% of VBM, 0% of ED
        - pct == 0.50: Report #2 (~9:45 PM) — ~82% of VBM, ~35% of ED
        - pct == 0.75: Report #3 (~10:45 PM) — ~90% of VBM, ~75% of ED
        - pct >= 1.00: Report #4 (Final night / full count) — 100% of VBM and ED
        """
        if pct <= 0.0:
            return 0, 0
        if pct <= 0.25:
            vbm_factor = 0.75 * (pct / 0.25)
            ed_factor = 0.0
        elif pct <= 0.50:
            vbm_factor = 0.75 + 0.07 * ((pct - 0.25) / 0.25)
            ed_factor = 0.35 * ((pct - 0.25) / 0.25)
        elif pct <= 0.75:
            vbm_factor = 0.82 + 0.08 * ((pct - 0.50) / 0.25)
            ed_factor = 0.35 + 0.40 * ((pct - 0.50) / 0.25)
        else:
            vbm_factor = 0.90 + 0.10 * min(1.0, (pct - 0.75) / 0.25)
            ed_factor = 0.75 + 0.25 * min(1.0, (pct - 0.75) / 0.25)

        return int(round(final_vbm * vbm_factor)), int(round(final_ed * ed_factor))

    def create_vote_groups(self, parent: ET.Element, ed_votes: int, vbm_votes: int) -> None:
        cg_collection = ET.SubElement(parent, "cgGroup_Collection")

        cg_ed = ET.SubElement(cg_collection, "cgGroup")
        cg_ed.set("countingGroupName", "Election Day")
        cg_ed.set("vot7", str(ed_votes))

        cg_vbm = ET.SubElement(cg_collection, "cgGroup")
        cg_vbm.set("countingGroupName", "Vote by Mail")
        cg_vbm.set("vot7", str(vbm_votes))

    def create_candidate_element(
        self, parent: ET.Element, name: str, ed_votes: int, vbm_votes: int
    ) -> None:
        ch_group = ET.SubElement(parent, "chGroup")
        cand_box = ET.SubElement(ch_group, "candidateNameTextBox4")
        cand_box.set("candidateNameTextBox4", name)

        tb2 = ET.SubElement(cand_box, "Textbox2")
        tb2.set("Textbox2", "")
        tb2.set("Textbox14", "")

        self.create_vote_groups(cand_box, ed_votes, vbm_votes)

        tb13 = ET.SubElement(cand_box, "Textbox13")
        tb13.set("vot8", str(ed_votes + vbm_votes))
        tb13.set("Textbox17", "N/A")

    def create_contest_statistics(
        self,
        parent: ET.Element,
        total_precincts: int,
        registered: int,
        ed_ballots: int,
        vbm_ballots: int,
        percent_reporting: float,
    ) -> None:
        stats = ET.SubElement(parent, "ContestStatistics")
        report = ET.SubElement(stats, "Report")
        report.set("Name", "ContestStatisticsRPT")

        tablix22 = ET.SubElement(report, "Tablix22")
        details_tab = ET.SubElement(tablix22, "DetailsTab_Collection")
        tab = ET.SubElement(details_tab, "DetailsTab")
        reported_tabs = int(round(self.total_tabulators * percent_reporting))
        tab.set(
            "reportedTab",
            f"Tabulators Reported: {reported_tabs} of {self.total_tabulators} {percent_reporting:.10f}",
        )

        tablix2 = ET.SubElement(report, "Tablix2")
        details = ET.SubElement(tablix2, "Details_Collection")
        detail = ET.SubElement(details, "Details")
        reported_precincts = (
            0
            if percent_reporting <= 0.25 and total_precincts > 1
            else int(round(total_precincts * percent_reporting))
        )
        pct_ratio = (reported_precincts / total_precincts) if total_precincts > 0 else 0
        detail.set(
            "Textbox2",
            f"Precincts Reported: {reported_precincts} of {total_precincts} {pct_ratio}",
        )

        # Ballots cast vs registered voters
        total_ballots = ed_ballots + vbm_ballots
        turnout_ratio = (total_ballots / registered) if registered > 0 else 0
        tb9 = ET.SubElement(report, "Textbox9")
        tb9.set("ballots2", f"{total_ballots} / {registered} ")
        tb9.set("Textbox40", f"{turnout_ratio}")

    def generate_test_file(self, filename: str | Path, percent_reporting: float = 0.0) -> None:
        report_num = {0.0: 0, 0.25: 1, 0.5: 2, 0.75: 3, 1.0: 4}.get(percent_reporting, 1)
        report_timestamps = {
            0: "2026-11-03T19:45:00",
            1: "2026-11-03T20:47:12",
            2: "2026-11-03T21:48:05",
            3: "2026-11-03T22:49:31",
            4: "2026-11-03T23:42:18",
        }
        ts = report_timestamps.get(report_num, datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))

        root = ET.Element("Report")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        root.set("xmlns", "ElectionSummaryReportRPT")
        root.set("Name", "ElectionSummaryReportRPT")

        title = ET.SubElement(root, "Title")
        report_title = ET.SubElement(title, "Report")
        report_title.set("Name", "Title")
        report_title.set("Textbox11", "Election Summary Report")
        report_title.set("Textbox3", "General Election")
        report_title.set("Textbox2", "San Francisco")
        report_title.set("Textbox9", ts)
        report_title.set(
            "Textbox8",
            f"City and County of San Francisco\nNovember 3, 2026 Consolidated General Election\nSummary Report - {report_num}",
        )

        # Compute citywide ballots from Governor contest
        gov = self.contests[0]
        gov_vbm = 0
        gov_ed = 0
        for _, fvbm, fed in gov["candidates"]:
            vbm, ed = self._scale_votes(fvbm, fed, percent_reporting)
            gov_vbm += vbm
            gov_ed += ed
        city_ballots = gov_vbm + gov_ed
        city_turnout = city_ballots / self.total_registered if self.total_registered else 0

        reg_turnout = ET.SubElement(root, "RegistrationAndTurnout")
        report_rt = ET.SubElement(reg_turnout, "Report")
        report_rt.set("Name", "RegistrationAndTurnout")
        tablix10 = ET.SubElement(report_rt, "Tablix10")
        eg_coll = ET.SubElement(tablix10, "electorGroupId2_Collection")
        eg = ET.SubElement(eg_coll, "electorGroupId2")
        eg.set("electorGroupId2", "Total")
        eg.set("ballots2", str(city_ballots * 4))
        eg.set("ballots3", str(city_ballots))
        eg.set("Textbox32", str(self.total_registered))
        eg.set("Textbox6", str(city_turnout))

        d_ed = ET.SubElement(eg, "Details1")
        d_ed.set("countingGroup1", "Election Day")
        d_ed.set("Textbox171", str(gov_ed))
        d_ed.set("Textbox173", str(gov_ed / self.total_registered))

        d_vbm = ET.SubElement(eg, "Details1")
        d_vbm.set("countingGroup1", "Vote by Mail")
        d_vbm.set("Textbox171", str(gov_vbm))
        d_vbm.set("Textbox173", str(gov_vbm / self.total_registered))

        # Match live SF SSRS hierarchy:
        # Report > tabBatchIdList > TabBatchGroup_Collection > TabBatchGroup > ElectionSummarySubReport > Report > contestList > ContestIdGroup_Collection > ContestIdGroup
        tab_batch_list = ET.SubElement(root, "tabBatchIdList")
        tab_batch_coll = ET.SubElement(tab_batch_list, "TabBatchGroup_Collection")
        tab_batch = ET.SubElement(tab_batch_coll, "TabBatchGroup")
        tab_batch.set("contestId", "")
        summary = ET.SubElement(tab_batch, "ElectionSummarySubReport")
        report_sum = ET.SubElement(summary, "Report")
        report_sum.set("Name", "ElectionSummarySubReportRPT")

        tablix2 = ET.SubElement(report_sum, "Tablix2")
        details = ET.SubElement(tablix2, "Details_Collection")
        detail = ET.SubElement(details, "Details")
        reported_precincts = (
            0
            if percent_reporting <= 0.25
            else int(round(self.total_precincts * percent_reporting))
        )
        detail.set(
            "reported",
            f"Precincts Reported: {reported_precincts} of {self.total_precincts} ({reported_precincts / self.total_precincts:.1%})",
        )

        contest_list = ET.SubElement(report_sum, "contestList")
        contest_coll = ET.SubElement(contest_list, "ContestIdGroup_Collection")

        for contest in self.contests:
            contest_group = ET.SubElement(contest_coll, "ContestIdGroup")
            contest_group.set("contestId", contest["id"])

            results = ET.SubElement(contest_group, "CandidateResults")
            results_report = ET.SubElement(results, "Report")
            results_report.set("Name", "CandidateResultsRPT")
            tablix1 = ET.SubElement(results_report, "Tablix1")
            ch_coll = ET.SubElement(tablix1, "chGroup_Collection")

            total_ed = 0
            total_vbm = 0
            for cand_name, final_vbm, final_ed in contest["candidates"]:
                vbm_votes, ed_votes = self._scale_votes(final_vbm, final_ed, percent_reporting)
                total_ed += ed_votes
                total_vbm += vbm_votes
                self.create_candidate_element(ch_coll, cand_name, ed_votes, vbm_votes)

            if contest.get("has_writein"):
                self.create_candidate_element(ch_coll, "Write-in ", 0, 0)

            self.create_contest_statistics(
                contest_group,
                contest["precincts"],
                contest["registered"],
                total_ed,
                total_vbm,
                percent_reporting,
            )

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(filename, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    generator = ElectionDataGenerator()

    percentages = [0.0, 0.25, 0.50, 0.75, 1.0]
    for pct in percentages:
        out_path = out_dir / f"test_results_{int(pct * 100):03d}.xml"
        generator.generate_test_file(out_path, pct)
        size_kb = out_path.stat().st_size / 1024
        print(f"Generated {out_path.name} ({pct:.0%} reporting, {size_kb:.1f} KB)")
