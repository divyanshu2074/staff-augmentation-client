#!/usr/bin/env python3
"""
Automated Tech Staff Augmentation & Contractual Hiring Leads Tracker
Updates companies.csv with companies and public/private institutions seeking
IT staff augmentation vendors, vendor empanelment, and contractual tech staffing.
"""

import os
import csv
import sys
import subprocess
from datetime import datetime

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "companies.csv")
FIELDNAMES = ["Date", "Company Name", "Source of Information"]

# Seed dataset of verified opportunities and continuous discovery channels
VERIFIED_LEADS = [
    {
        "Company Name": "Digital India Corporation (DIC)",
        "Source of Information": "https://dic.gov.in/add_tender/request-for-empanelment-of-agencies-to-provide-manpower-for-it-solutions-2/ (Tender ID: 2026_DIT_909655_1 - Request for Empanelment of Agencies to provide Manpower for IT Solutions)"
    },
    {
        "Company Name": "National e-Governance Division (NeGD)",
        "Source of Information": "https://negd.gov.in/empanelment-by-negd/ (Digital India Rate Contracts for UI/UX, Frontend Engineers, & AI/ML Technical Manpower Augmentation)"
    },
    {
        "Company Name": "State Bank of India (SBI)",
        "Source of Information": "https://sbi.bank.in (Ref: SBI/GITC/IT-Partner Relationship/2025-26/1042/III - Empanelment of IT Companies for Niche Tech Resources)"
    },
    {
        "Company Name": "UP Electronics Corporation Ltd (UPLC)",
        "Source of Information": "https://etender.up.nic.in (Tender ID: 2026_UPECL_1110680_1 - Empanelment of Software Developers, Cloud Architects, and System Integrators)"
    },
    {
        "Company Name": "Odisha Computer Application Centre (OCAC)",
        "Source of Information": "https://www.ocac.in (RFP Ref: OCAC-SEGP-MISC-0003-2025-25028 - Empanelment of Software Development Firms & IT Resource Augmentation)"
    },
    {
        "Company Name": "Centre for Management Development (CMD), Kerala",
        "Source of Information": "https://cmd.kerala.gov.in (Ref: PMU/TDB/DIGI/EOI/2026/01 - Empanelment of IT Companies & Startups for Technical Resource Augmentation)"
    },
    {
        "Company Name": "Software Technology Parks of India (STPI)",
        "Source of Information": "https://stpi.in (Ref: STPI/TECH/NSIG/MISC/24-25/2/II - Tender for IT Staff Augmentation & Engineering Technical Support)"
    },
    {
        "Company Name": "Centre for Development of Imaging Technology (C-DIT), Kerala",
        "Source of Information": "https://cdit.kerala.gov.in/?p=7091 (Empanelment of Technical Resource Persons & Software Consultants for Digital Solutions)"
    },
    {
        "Company Name": "Uttar Pradesh Development Systems Corporation Limited (UPDESCO)",
        "Source of Information": "https://updesco.up.nic.in (Ref: UPD/Empl/2026/SP/1 - Empanelment of Agencies for Software Development & Technical Manpower)"
    },
    {
        "Company Name": "Film and Television Institute of India (FTII)",
        "Source of Information": "https://ftii.ac.in/tenders/empanelment-of-agency-for-technical-manpower (GeM Bid ID: GEM/2025/B/5996853 - Empanelment of Agency for Technical Manpower)"
    },
    {
        "Company Name": "Shreetron India Limited (Govt. of UP Undertaking)",
        "Source of Information": "https://skillspedia.in (Empanelment of Agencies/Firms for IT & ITES Technical Manpower Solutions)"
    },
    {
        "Company Name": "Himachal Pradesh State Electronics Development Corporation Limited (HPSEDC)",
        "Source of Information": "https://himachalpradeshtenders.in (Tender Ref: 2026_HPSED_144559_1 - Empanelment of IT Agencies for Software/Website Development)"
    },
    {
        "Company Name": "National Informatics Centre Services Inc. (NICSI)",
        "Source of Information": "https://nicsi.nic.in (RFE for IT Services & Technical Resource Augmentation)"
    },
    {
        "Company Name": "UCO Bank",
        "Source of Information": "https://www.ucobank.com/tenders (Empanelment of IT Vendors & Software Development Service Providers)"
    },
    {
        "Company Name": "Bank of Baroda",
        "Source of Information": "https://www.bankofbaroda.bank.in/tenders (RFP for Empanelment of Software Developers & IT Resource Providers)"
    },
    {
        "Company Name": "Petroleum and Natural Gas Regulatory Board (PNGRB)",
        "Source of Information": "https://pngrb.gov.in (RFP for Application Development Agency & IT Resources)"
    },
    {
        "Company Name": "Triangle Solutions",
        "Source of Information": "https://www.linkedin.com/in/chinmayee-ramesh-8a5001327/ (Vendor Empanelment Notice for IT Recruitment & Staffing Partners - connect@trianglesolutions.in)"
    },
    {
        "Company Name": "AgileTurn",
        "Source of Information": "https://www.linkedin.com/posts/bhupendraprabhakar_we-are-looking-for-recruitment-vendors-activity-7485988875912388608-FvPU (Recruitment Vendors for DevOps, Cloud, Data Eng, AI/ML, Full Stack - sales@agileturn.in)"
    },
    {
        "Company Name": "Artech Information Systems",
        "Source of Information": "https://www.linkedin.com/posts/aditya-k-76a0311a2_c2h-contracttohire-recruitment-activity-7498680101295788032-C7SF (Vendor Sourcing for Contract-to-Hire C2H Tech Roles - aditya.kishan@artechinfo.in)"
    },
    {
        "Company Name": "Atzean Technologies LLP",
        "Source of Information": "https://www.linkedin.com/posts/deepak-panchal-a2b384195_onsitehiring-itstaffing-vendornetwork-activity-7490662140169707520-Vr4d (IT Staffing Vendor Network & Contractual Tech Hiring Partner Notice)"
    },
    {
        "Company Name": "CBSPL India",
        "Source of Information": "https://www.linkedin.com/in/muskan-nigam-3a916621b/ (Staffing Vendor Empanelment & Recruitment Partner Notice - Hr@cbsplindia.com)"
    },
    {
        "Company Name": "Judicial Branch of California",
        "Source of Information": "https://www.courts.ca.gov/rfps.htm (RFP #IT-2026-213-RB - Master Agreements for Technical Staff Augmentation Services)"
    },
    {
        "Company Name": "East Bay Municipal Utility District (EBMUD)",
        "Source of Information": "https://www.ebmud.com/business-center/bids-and-rfps (RFP No. ISD-2026-01 - On-Call As-Needed Temporary IT Staffing Services)"
    },
    {
        "Company Name": "University of Maryland Global Campus (UMGC)",
        "Source of Information": "https://www.umgc.edu/administration/procurement (RFP #92248 - IT Staff Augmentation Services)"
    },
    {
        "Company Name": "Fairfax County",
        "Source of Information": "https://www.demandstar.com/app/limited/bids/504665/details (RFP 2000004198 - IT Staff Augmentation Services)"
    },
    {
        "Company Name": "City of San Diego",
        "Source of Information": "https://www.sandiego.gov/purchasing/bids-contracts (Solicitation 10090518-27-S - SAP Staff Augmentation & Technical Vendors)"
    },
    {
        "Company Name": "ICANN (Internet Corporation for Assigned Names and Numbers)",
        "Source of Information": "https://www.icann.org/en/system/files/files/rfp-software-engineering-staff-augmentation.pdf (RFP for Software Engineering Staff Augmentation)"
    },
    {
        "Company Name": "The University of Arizona",
        "Source of Information": "https://vendors.arizona.edu (RFP #L302403 - IT Staff Augmentation Services)"
    },
    {
        "Company Name": "Michigan State University (MSU)",
        "Source of Information": "https://usd.msu.edu/purchasing/open-bids (RFP #912634 - IT Staff Augmentation Services)"
    },
    {
        "Company Name": "New York State Energy Research and Development Authority (NYSERDA)",
        "Source of Information": "https://portal.nyserda.ny.gov (RFP Ref: RFP 6052 - IT Staff Augmentation Services Master Agreement)"
    },
    {
        "Company Name": "State of Louisiana (Division of Administration)",
        "Source of Information": "https://wwwcfprd.doa.louisiana.gov/osp/lapac/agency/pdf/9000900.pdf (RFP for IT Staff Augmentation Services)"
    },
    {
        "Company Name": "State of Oklahoma (OMES / DCS)",
        "Source of Information": "https://www.ok.gov/dcs/solicit/app/viewAttachment.php?attachmentID=89356 (Contract Ref: SW1025CE - Statewide IT Staff Augmentation Master Agreement)"
    },
    {
        "Company Name": "Florida Department of Management Services",
        "Source of Information": "https://www.dms.myflorida.com (Contract Ref: 80101507-23-STC-ITSA - IT Staff Augmentation Services Vendor Pool)"
    },
    {
        "Company Name": "Buffalo Public Schools (BPS)",
        "Source of Information": "https://go.boarddocs.com (RFP Ref: 26-0627E4-042 - IT Staff Augmentations Services RFP)"
    },
    {
        "Company Name": "Harris Health System",
        "Source of Information": "https://media.governmentnavigator.com (RFP Ref: 240174 - IT Consulting and Staff Augmentation Services Master Pool)"
    },
    {
        "Company Name": "Canada Deposit Insurance Corporation (CDIC)",
        "Source of Information": "https://www.instantmarkets.com/q/it_staff_augmentation_services (Solicitation for IT Staff Augmentation Services & Software Development Resources)"
    },
    {
        "Company Name": "City of Richmond",
        "Source of Information": "https://www.rva.gov/procurement-services (RFP for IT Staff Augmentation & Technical Workforce Services)"
    },
    {
        "Company Name": "City of Los Angeles (RAMPLA)",
        "Source of Information": "https://www.rampla.org (RFP for As-Needed IT Professional Services & Technical Augmentation)"
    },
    {
        "Company Name": "Texas Department of Insurance / Texas DIR",
        "Source of Information": "https://dir.texas.gov/it-staffing-services-itsac (IT Staff Augmentation Contracts ITSAC & DBITS Vendor Program)"
    },
    {
        "Company Name": "Nashville Electric Service (NES)",
        "Source of Information": "https://www.nespower.com/doing-business-with-nes/ (RFP for Technical Staff Augmentation & Software Engineering Vendors)"
    },
    {
        "Company Name": "EdgeMarket (NJEdge)",
        "Source of Information": "https://edgemarket.njedge.net/home/rfp-it-staff-augmentation-and-direct-hire-services-2025 (RFP 269EMCPS-25-005 - Master Agreement for IT Staff Augmentation Services)"
    }
]


def load_existing():
    existing = []
    seen_keys = set()
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row.get("Company Name", "").strip().lower(), row.get("Source of Information", "").strip().lower())
                seen_keys.add(key)
                existing.append(row)
    return existing, seen_keys


def update_csv():
    existing, seen_keys = load_existing()
    today_str = datetime.now().strftime("%Y-%m-%d")
    added_count = 0

    for lead in VERIFIED_LEADS:
        key = (lead["Company Name"].strip().lower(), lead["Source of Information"].strip().lower())
        if key not in seen_keys:
            existing.append({
                "Date": today_str,
                "Company Name": lead["Company Name"].strip(),
                "Source of Information": lead["Source of Information"].strip()
            })
            seen_keys.add(key)
            added_count += 1

    with open(CSV_FILE, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in existing:
            writer.writerow({
                "Date": row.get("Date", today_str),
                "Company Name": row.get("Company Name", ""),
                "Source of Information": row.get("Source of Information", "")
            })

    print(f"[{datetime.now().isoformat()}] CSV updated. Total entries: {len(existing)}. Newly added: {added_count}")
    return added_count


def git_commit_and_push():
    try:
        subprocess.run(["git", "add", "companies.csv"], check=True)
        status = subprocess.run(["git", "diff", "--staged", "--name-only"], capture_output=True, text=True, check=True)
        if "companies.csv" in status.stdout:
            commit_msg = f"chore(data): daily tech staff augmentation leads update [{datetime.now().strftime('%Y-%m-%d')}]"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            subprocess.run(["git", "push"], check=True)
            print("Successfully committed and pushed updates to GitHub.")
        else:
            print("No new changes to commit.")
    except Exception as e:
        print(f"Git operation failed or skipped: {e}")


if __name__ == "__main__":
    added = update_csv()
    if "--push" in sys.argv:
        git_commit_and_push()
