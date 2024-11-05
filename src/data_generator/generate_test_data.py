import xml.etree.ElementTree as ET
from datetime import datetime
import random

class ElectionDataGenerator:
    def __init__(self):
        self.total_precincts = 514
        self.total_tabulators = 1061
        self.contests = {
            # Countywide/Citywide Offices
            "MAYOR": [
                ("LONDON BREED", ""),
                ("MARK FARRELL", ""),
                ("DANIEL LURIE", ""),
                ("AHSHA SAFAÍ", "")
            ],
            "CITY ATTORNEY": [
                ("DAVID CHIU", ""),
                ("JOE ALIOTO VERONESE", "")
            ],
            "DISTRICT ATTORNEY": [
                ("BROOKE JENKINS", ""),
                ("RYAN KHOJASTEH", "")
            ],
            "SHERIFF": [
                ("PAUL MIYAMOTO", "")
            ],
            "TREASURER": [
                ("JOSÉ CISNEROS", "")
            ],
            
            # Board of Supervisors
            "MEMBER, BOARD OF SUPERVISORS, DISTRICT 1": [
                ("CONNIE CHAN", ""),
                ("DAVID MILES", ""),
                ("SHERMAN R. D'SILVA", "")
            ],
            "MEMBER, BOARD OF SUPERVISORS, DISTRICT 3": [
                ("DANNY WOO", ""),
                ("JASON WU", "")
            ],
            "MEMBER, BOARD OF SUPERVISORS, DISTRICT 5": [
                ("DEAN PRESTON", ""),
                ("NOMVULA O'MEARA", "")
            ],
            "MEMBER, BOARD OF SUPERVISORS, DISTRICT 7": [
                ("JOEL ENGARDIO", ""),
                ("MYRNA MELGAR", "")
            ],
            "MEMBER, BOARD OF SUPERVISORS, DISTRICT 9": [
                ("HILLARY RONEN", "")
            ],
            "MEMBER, BOARD OF SUPERVISORS, DISTRICT 11": [
                ("AHSHA SAFAÍ", ""),
                ("SHARIFF SHAMIEH", "")
            ],
            
            # SFUSD
            "MEMBER, BOARD OF EDUCATION": [
                ("DAVID CAMPOS", ""),
                ("ROBERT COLEMAN", ""),
                ("MIKEY CUBA", "")
            ],
            
            # CCSF
            "TRUSTEE, COMMUNITY COLLEGE BOARD": [
                ("ANITA MARTINEZ", ""),
                ("VICK CHUNG", ""),
                ("WILLIAM WALKER", "")
            ],
            
            # BART
            "BART BOARD OF DIRECTORS, DISTRICT 7": [
                ("LATEEFAH SIMON", ""),
                ("MARK FOLEY", "")
            ],
            "BART BOARD OF DIRECTORS, DISTRICT 9": [
                ("BEVAN DUFTY", ""),
                ("MICHAEL PETRELIS", "")
            ]
        }
        
        # Add measures
        for measure in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O"]:
            if measure in ["A", "B"]:
                self.contests[f"MEASURE {measure}"] = [
                    ("BONDS - YES", ""),
                    ("BONDS - NO", "")
                ]
            else:
                self.contests[f"MEASURE {measure}"] = [
                    ("YES", ""),
                    ("NO", "")
                ]

    def create_vote_groups(self, parent, ed_votes=0, vbm_votes=0):
        cgGroup_Collection = ET.SubElement(parent, "cgGroup_Collection")
        
        # Election Day votes
        cgGroup_ed = ET.SubElement(cgGroup_Collection, "cgGroup")
        cgGroup_ed.set("countingGroupName", "Election Day")
        cgGroup_ed.set("vot7", str(ed_votes))
        
        # Vote by Mail votes
        cgGroup_vbm = ET.SubElement(cgGroup_Collection, "cgGroup")
        cgGroup_vbm.set("countingGroupName", "Vote by Mail")
        cgGroup_vbm.set("vot7", str(vbm_votes))
        
        return cgGroup_Collection

    def create_candidate_element(self, parent, name, party="", ed_votes=0, vbm_votes=0):
        chGroup = ET.SubElement(parent, "chGroup")
        
        # Candidate name and base info
        candidateNameBox = ET.SubElement(chGroup, "candidateNameTextBox4")
        candidateNameBox.set("candidateNameTextBox4", name)
        
        # Add textboxes
        textbox2 = ET.SubElement(candidateNameBox, "Textbox2")
        textbox2.set("Textbox2", "")
        textbox2.set("Textbox14", "")
        
        # Add vote groups
        self.create_vote_groups(candidateNameBox, ed_votes, vbm_votes)
        
        # Add total votes textbox
        textbox13 = ET.SubElement(candidateNameBox, "Textbox13")
        textbox13.set("vot8", str(ed_votes + vbm_votes))
        textbox13.set("Textbox17", "N/A")
        
        # Add party information if provided
        if party:
            partyGroup_Collection = ET.SubElement(chGroup, "partyGroup_Collection")
            partyGroup = ET.SubElement(partyGroup_Collection, "partyGroup")
            
            textbox2 = ET.SubElement(partyGroup, "Textbox2")
            textbox2.set("Textbox2", party)
            
            self.create_vote_groups(partyGroup, ed_votes, vbm_votes)
            
            textbox13 = ET.SubElement(partyGroup, "Textbox13")
            textbox13.set("vot9", str(ed_votes + vbm_votes))
            textbox13.set("Textbox18", "N/A")
        
        return chGroup

    def create_contest_statistics(self, parent, percent_reporting):
        stats = ET.SubElement(parent, "ContestStatistics")
        report = ET.SubElement(stats, "Report")
        report.set("Name", "ContestStatisticsRPT")
        
        # Add tabulator reporting
        tablix22 = ET.SubElement(report, "Tablix22")
        details_tab = ET.SubElement(tablix22, "DetailsTab_Collection")
        tab = ET.SubElement(details_tab, "DetailsTab")
        reported_tabulators = int(self.total_tabulators * percent_reporting)
        tab.set("reportedTab", f"Tabulators Reported: {reported_tabulators} of {self.total_tabulators} {percent_reporting:.10f}")
        
        # Add precinct reporting
        tablix2 = ET.SubElement(report, "Tablix2")
        details = ET.SubElement(tablix2, "Details_Collection")
        detail = ET.SubElement(details, "Details")
        reported_precincts = int(self.total_precincts * percent_reporting)
        detail.set("Textbox2", f"Precincts Reported: {reported_precincts} of {self.total_precincts} {int(percent_reporting * 100)}")

    def generate_test_file(self, filename, percent_reporting=0.1):
        # Create root element
        root = ET.Element("Report")
        root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        root.set("xmlns", "ElectionSummaryReportRPT")
        
        # Add title section
        title = ET.SubElement(root, "Title")
        report_title = ET.SubElement(title, "Report")
        report_title.set("Name", "Title")
        report_title.set("Textbox11", "Election Summary Report")
        report_title.set("Textbox3", "General Election")
        report_title.set("Textbox2", "San Francisco")
        report_title.set("Textbox9", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
        
        # Add registration and turnout section
        reg_turnout = ET.SubElement(root, "RegistrationAndTurnout")
        report_rt = ET.SubElement(reg_turnout, "Report")
        report_rt.set("Name", "RegistrationAndTurnout")
        
        # Add election summary section
        summary = ET.SubElement(root, "ElectionSummarySubReport")
        report_sum = ET.SubElement(summary, "Report")
        
        # Add reporting statistics
        tablix2 = ET.SubElement(report_sum, "Tablix2")
        details = ET.SubElement(tablix2, "Details_Collection")
        detail = ET.SubElement(details, "Details")
        reported_precincts = int(self.total_precincts * percent_reporting)
        detail.set("reported", f"Precincts Reported: {reported_precincts} of {self.total_precincts} ({percent_reporting:.1%})")
        
        # Add contest list
        contest_list = ET.SubElement(report_sum, "contestList")
        
        # Generate results for each contest
        for contest_name, candidates in self.contests.items():
            contest_group = ET.SubElement(contest_list, "ContestIdGroup")
            contest_group.set("contestId", contest_name)
            
            # Add contest statistics
            self.create_contest_statistics(contest_group, percent_reporting)
            
            # Add candidate results
            results = ET.SubElement(contest_group, "CandidateResults")
            results_report = ET.SubElement(results, "Report")
            results_report.set("Name", "CandidateResultsRPT")
            
            tablix1 = ET.SubElement(results_report, "Tablix1")
            chGroup_Collection = ET.SubElement(tablix1, "chGroup_Collection")
            
            # Generate results for each candidate
            total_votes = random.randint(10000, 50000)
            votes_remaining = total_votes
            
            for i, (candidate, party) in enumerate(candidates):
                if i == len(candidates) - 1:
                    # Last candidate gets remaining votes
                    ed_votes = random.randint(0, votes_remaining)
                    vbm_votes = votes_remaining - ed_votes
                else:
                    # Other candidates get random portion of remaining votes
                    max_votes = int(votes_remaining * 0.5)
                    candidate_votes = random.randint(0, max_votes)
                    ed_votes = random.randint(0, candidate_votes)
                    vbm_votes = candidate_votes - ed_votes
                    votes_remaining -= candidate_votes
                
                self.create_candidate_element(chGroup_Collection, candidate, party, ed_votes, vbm_votes)
        
        # Write to file
        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(filename, encoding="utf-8", xml_declaration=True)

if __name__ == "__main__":
    generator = ElectionDataGenerator()
    
    # Generate a series of test files with different reporting percentages
    percentages = [0.0, 0.25, 0.50, 0.75, 1.0]
    for i, pct in enumerate(percentages):
        filename = f"test_results_{int(pct * 100):03d}.xml"
        generator.generate_test_file(filename, pct)
        print(f"Generated {filename} with {pct:.1%} reporting")
        
        # Verify file size
        import os
        size = os.path.getsize(filename)
        print(f"File size: {size/1024:.1f}KB")