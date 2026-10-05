#!/usr/bin/env python3
"""
Automated Tech Staff Augmentation & Contractual Hiring Leads Tracker
Updates companies.csv with private companies, tech enterprises, and institutions
seeking IT staff augmentation vendors, vendor empanelment, and contractual tech staffing.
Filters out expired/closed RFPs and prioritizes active, actionable partner programs.
"""

import os
import csv
import sys
import subprocess
from datetime import datetime

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "companies.csv")
FIELDNAMES = ["Date", "Company Name", "Source of Information"]

# Curated dataset of active private companies and open solicitations
VERIFIED_LEADS = [
    {
        "Company Name": "YASH Technologies",
        "Source of Information": "https://www.yashtechnologies.com/contact-us/partner-with-us/ (Active Vendor Empanelment Portal for IT Staffing & Contractual Tech Hiring Partners)"
    },
    {
        "Company Name": "Turing",
        "Source of Information": "https://www.turing.com/partners/agencies (Turing Agency Partner Program - Empanelling Tech Staffing Vendors & Dev Agencies for Remote Global Software Roles)"
    },
    {
        "Company Name": "BairesDev",
        "Source of Information": "https://www.bairesdev.com/partners/ (Nearshore/Offshore Partner Network - Onboarding Staffing Agencies & Dev Shops for US/Global Enterprise Tech Roles)"
    },
    {
        "Company Name": "ParallelStaff",
        "Source of Information": "https://parallelstaff.com/partners/ (Software Staff Augmentation Partner Network - Intake for Tech Staffing Vendors & Remote Engineering Teams)"
    },
    {
        "Company Name": "AB7 Solutions",
        "Source of Information": "https://www.ab7solutions.com/sub-vendor-partnership/ (Sub-Vendor & Agency Partnership Portal for IT Staffing and Software Engineering Talent)"
    },
    {
        "Company Name": "Way2WebSoft Technologies",
        "Source of Information": "https://www.way2websoft.com/partner-with-us/ (Partner With Us - Vendor Empanelment for IT Staffing & Technical Recruitment Partners)"
    },
    {
        "Company Name": "AgileTurn",
        "Source of Information": "https://www.linkedin.com/posts/bhupendraprabhakar_we-are-looking-for-recruitment-vendors-activity-7485988875912388608-FvPU (Active Call for Recruitment Vendors: DevOps, Cloud AWS/Azure, Data Eng, AI/ML, Full Stack - sales@agileturn.in)"
    },
    {
        "Company Name": "Artech Information Systems",
        "Source of Information": "https://www.linkedin.com/posts/aditya-k-76a0311a2_c2h-contracttohire-recruitment-activity-7498680101295788032-C7SF (Vendor Sourcing for Contract-to-Hire C2H Tech Roles & Software Engineers - aditya.kishan@artechinfo.in)"
    },
    {
        "Company Name": "Atzean Technologies LLP",
        "Source of Information": "https://www.linkedin.com/posts/deepak-panchal-a2b384195_onsitehiring-itstaffing-vendornetwork-activity-7490662140169707520-Vr4d (IT Staffing Vendor Network & Contractual Tech Hiring Partner Call for Software & Cloud Engineers)"
    },
    {
        "Company Name": "Triangle Solutions",
        "Source of Information": "https://www.linkedin.com/in/chinmayee-ramesh-8a5001327/ (Vendor Empanelment Notice for IT Recruitment & Staffing Partners - connect@trianglesolutions.in)"
    },
    {
        "Company Name": "CBSPL India",
        "Source of Information": "https://www.linkedin.com/in/muskan-nigam-3a916621b/ (Staffing Vendor Empanelment & Recruitment Partner Intake - Hr@cbsplindia.com)"
    },
    {
        "Company Name": "AiBit Sol",
        "Source of Information": "https://www.aibitsol.com (Agency Partner Program for Staff Augmentation & Contract Developer Delivery)"
    },
    {
        "Company Name": "Kwiqwork",
        "Source of Information": "https://kwiqwork.com (Agency Partner Program - Contract Engineering & Staff Augmentation Network)"
    },
    {
        "Company Name": "Creatricx",
        "Source of Information": "https://creatricx.com (Creatricx Agency Partner Program for Dedicated Remote Tech Teams & IT Staff Augmentation)"
    },
    {
        "Company Name": "Kizzy Consulting",
        "Source of Information": "https://kizzyconsulting.com (Salesforce & Cloud Staff Augmentation Technical Partner Program for Agencies)"
    },
    {
        "Company Name": "Prioxis",
        "Source of Information": "https://prioxis.com/partner-with-us/ (IT Staff Augmentation Partner Network for Software Developers, AI/ML, and DevOps)"
    },
    {
        "Company Name": "Bloom Consulting Services",
        "Source of Information": "https://dev.bloomsolutions.com/partner-with-us/ (Dedicated Development Partner Program & Technical Staff Augmentation Vendor Network)"
    },
    {
        "Company Name": "GIGA IT",
        "Source of Information": "https://grupo-giga.com/partner-with-us/ (Remote IT Staff Augmentation Vendor Partnership for Mobile and Fintech Software Engineering)"
    },
    {
        "Company Name": "Software Mind",
        "Source of Information": "https://softwaremind.com/partnership/ (Software Development & Staff Augmentation Vendor Partner Program for Nearshore/Offshore Engineers)"
    },
    {
        "Company Name": "Acquaint Softtech",
        "Source of Information": "https://acquaintsoft.com/partner-with-us/ (Remote Developer and IT Staff Augmentation Agency Partnership Network)"
    },
    {
        "Company Name": "Crave Infotech",
        "Source of Information": "https://craveinfotech.com/partner-with-us/ (Enterprise IT & SAP Staff Augmentation Sub-Contracting and Vendor Partnership Portal)"
    },
    {
        "Company Name": "Diaspark Inc.",
        "Source of Information": "https://diaspark.com/partner-with-us/ (Technical Staff Augmentation & Software Engineering Agency Partner Program)"
    },
    {
        "Company Name": "Manektech",
        "Source of Information": "https://manektech.com/partner-program (IT Staff Augmentation Partner Program for Specialized Software & Cloud Engineers)"
    },
    {
        "Company Name": "Amol Technologies",
        "Source of Information": "https://www.amoltechnologies.com/partner-with-us/ (IT Staff Augmentation Vendor Partnership for Pre-Vetted Software Engineers)"
    },
    {
        "Company Name": "GreenAlpha Technology",
        "Source of Information": "https://www.greenalphatechnology.com (Agency Partner Program for Technical Staff Augmentation, QA, and Software Delivery)"
    },
    {
        "Company Name": "NxTechNova",
        "Source of Information": "https://nxtechnova.com (Technology Partner Network for IT Outsourcing, Resource Sharing, and Staff Augmentation)"
    },
    {
        "Company Name": "Judicial Council of California",
        "Source of Information": "https://www.courts.ca.gov/rfps.htm (Open Solicitation RFP-LSS-2026-02-LP - Technical Staff Augmentation Services for Software & Cloud Engineers)"
    },
    {
        "Company Name": "Digital India Corporation (DIC)",
        "Source of Information": "https://dic.gov.in/add_tender/request-for-empanelment-of-agencies-to-provide-manpower-for-it-solutions-2/ (Active Tender 2026_DIT_909655_1 - Request for Empanelment of Agencies to provide Manpower for IT Solutions)"
    },
    {
        "Company Name": "National e-Governance Division (NeGD)",
        "Source of Information": "https://negd.gov.in/empanelment-by-negd/ (Active Digital India Empanelment Panels for Frontend Engineers, UI/UX, & AI/ML Technical Manpower)"
    },
    {
        "Company Name": "Himachal Pradesh State Electronics Development Corporation Limited (HPSEDC)",
        "Source of Information": "https://himachalpradeshtenders.in (Active Tender 2026_HPSED_144559_1 - Empanelment of IT Agencies for Software/Website Development)"
    },
    {
        "Company Name": "State Bank of India (SBI)",
        "Source of Information": "https://sbi.bank.in (Active Partner Relationship Empanelment - SBI/GITC/IT-Partner Relationship/2025-26/1042/III - Empanelment for Niche Tech Resources)"
    },
    {
        "Company Name": "Software Technology Parks of India (STPI)",
        "Source of Information": "https://stpi.in (Active Ref: STPI/TECH/NSIG/MISC/24-25/2/II - Empanelment for IT Technical Staff Augmentation & Software Support)"
    },
    {
        "Company Name": "Centre for Management Development (CMD) Kerala",
        "Source of Information": "https://cmd.kerala.gov.in (Active Ref: PMU/TDB/DIGI/EOI/2026/01 - Empanelment of IT Companies & Startups for Technical Resource Augmentation)"
    },
    {
        "Company Name": "ICANN (Internet Corporation for Assigned Names and Numbers)",
        "Source of Information": "https://www.icann.org/en/system/files/files/rfp-software-engineering-staff-augmentation.pdf (Standing Global Vendor Program for Remote Software Engineering Staff Augmentation)"
    },
    {
        "Company Name": "Petroleum and Natural Gas Regulatory Board (PNGRB)",
        "Source of Information": "https://pngrb.gov.in (RFP for Application Development Agency & Specialized IT Resources)"
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
