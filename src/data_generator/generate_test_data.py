# src/data_generator/generate_test_data.py

import xml.etree.ElementTree as ET
import random
from datetime import datetime

class ElectionDataGenerator:
    def __init__(self):
        # Define the contests and candidates we saw in the XML
        self.contests = {
            "MAYOR": [
                "LONDON BREED",
                "MARK FARRELL",
                "DANIEL LURIE",
                "AHSHA SAFAÍ"
            ],
            "DISTRICT ATTORNEY": [
                "BROOKE JENKINS",
                "RYAN KHOJASTEH"
            ]
        }
        self.total_precincts = 514
        self.total_tabulators = 1061

    def generate_test_file(self, filename, percent_reporting=0.1):
        # Create root element
        root = ET.Element("Report")
        root.set("xmlns", "ElectionSummaryReportRPT")
        
        # Add basic election info
        title = ET.SubElement(root, "Title")
        report = ET.SubElement(title, "Report")
        report.set("Name", "Title")
        report.set("Textbox11", "Election Summary Report")
        report.set("Textbox3", "General Election")
        report.set("Textbox2", "San Francisco")
        report.set("Textbox9", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
        
        # Add reporting stats
        reporting = ET.SubElement(root, "RegistrationAndTurnout")
        report_stats = ET.SubElement(reporting, "Report")
        report_stats.set("Name", "RegistrationAndTurnout")
        
        # Add contest results
        summary = ET.SubElement(root, "ElectionSummarySubReport")
        contest_list = ET.SubElement(summary, "contestList")
        
        # Add each contest
        for contest_name, candidates in self.contests.items():
            contest = ET.SubElement(contest_list, "ContestIdGroup")
            contest.set("contestId", contest_name)
            
            # Add candidate results
            results = ET.SubElement(contest, "CandidateResults")
            for candidate in candidates:
                cand_elem = ET.SubElement(results, "Candidate")
                cand_elem.set("name", candidate)
                cand_elem.set("electionDay", str(random.randint(1000, 5000)))
                cand_elem.set("voteByMail", str(random.randint(5000, 15000)))

        # Write to file
        tree = ET.ElementTree(root)
        tree.write(filename, encoding='utf-8', xml_declaration=True)

if __name__ == "__main__":
    generator = ElectionDataGenerator()
    generator.generate_test_file("test_results.xml")
    print("Test file generated successfully!")