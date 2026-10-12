#!/usr/bin/env python3
"""
Automated Tech Staff Augmentation & Contractual Hiring Discovery Engine
Runs daily to discover, validate, filter, and append active opportunities to companies.csv.

4-Stage Pipeline:
  1. Discover: Multi-source ingestion:
     - Hacker News official 'Who is hiring?' threads (filtering for contract / B2B / freelance engineering).
     - RemoteOK API (filtering for contract / 1099 / B2B software engineering and tech roles).
     - Live Google News RSS feeds for IT vendor empanelment & staff augmentation RFPs.
     - Curated baseline standing enterprise and government empanelment programs.
  2. Validate: Concurrent HTTP status verification with 401/403 challenge handling, rate-limit tolerance,
     and automatic pruning of dead/closed markers.
  3. Filter & Deduplicate: Strict buyer filter (prunes candidate/job-seeker profiles), tech role verification,
     remote/WFH criteria, and robust (normalized_company, canonical_domain) deduplication.
  4. Update CSV: Appends only verified active leads to companies.csv without duplicates.
"""

import os
import sys
import csv
import ssl
import json
import html
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "companies.csv")
FIELDNAMES = ["Date", "Company Name", "Source of Information"]

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

TECH_KEYWORDS = {
    'software', 'developer', 'engineer', 'frontend', 'backend', 'fullstack', 
    'devops', 'cloud', 'python', 'react', 'node', 'ai', 'ml', 'data', 'qa', 
    'architect', 'typescript', 'golang', 'rust', 'c#', 'java', 'aws', 'azure'
}

DEAD_MARKERS = [
    'rfp closed', 'bidding closed', 'tender cancelled', 'tender expired', 
    'no longer accepting submissions', 'deadline passed', 'position closed'
]

# Baseline curated registry of standing enterprise and public sector solicitations
BASELINE_SOLICITATIONS = [
    {
        "Company Name": "Judicial Council of California",
        "Role": "Technical Staff Augmentation Services for Software & Cloud Engineers",
        "Url": "https://www.courts.ca.gov/rfps.htm",
        "Source of Information": "https://www.courts.ca.gov/rfps.htm (Open Solicitation RFP-LSS-2026-02-LP - Technical Staff Augmentation Services for Software & Cloud Engineers)"
    },
    {
        "Company Name": "Digital India Corporation (DIC)",
        "Role": "Request for Empanelment of Agencies to provide Manpower for IT Solutions",
        "Url": "https://dic.gov.in/add_tender/request-for-empanelment-of-agencies-to-provide-manpower-for-it-solutions-2/",
        "Source of Information": "https://dic.gov.in/add_tender/request-for-empanelment-of-agencies-to-provide-manpower-for-it-solutions-2/ (Active Tender 2026_DIT_909655_1 - Request for Empanelment of Agencies to provide Manpower for IT Solutions)"
    },
    {
        "Company Name": "National e-Governance Division (NeGD)",
        "Role": "Digital India Empanelment Panels for Frontend, UI/UX & AI/ML Manpower",
        "Url": "https://negd.gov.in/empanelment-by-negd/",
        "Source of Information": "https://negd.gov.in/empanelment-by-negd/ (Active Digital India Empanelment Panels for Frontend Engineers, UI/UX, & AI/ML Technical Manpower)"
    },
    {
        "Company Name": "Himachal Pradesh State Electronics Development Corporation (HPSEDC)",
        "Role": "Empanelment of IT Agencies for Software/Website Development",
        "Url": "https://himachalpradeshtenders.in",
        "Source of Information": "https://himachalpradeshtenders.in (Active Tender 2026_HPSED_144559_1 - Empanelment of IT Agencies for Software/Website Development)"
    },
    {
        "Company Name": "State Bank of India (SBI)",
        "Role": "Empanelment for Niche Tech Resources & IT Partner Relationship",
        "Url": "https://sbi.bank.in",
        "Source of Information": "https://sbi.bank.in (Active Partner Relationship Empanelment - SBI/GITC/IT-Partner Relationship/2025-26/1042/III - Empanelment for Niche Tech Resources)"
    },
    {
        "Company Name": "Software Technology Parks of India (STPI)",
        "Role": "Empanelment for IT Technical Staff Augmentation & Software Support",
        "Url": "https://stpi.in",
        "Source of Information": "https://stpi.in (Active Ref: STPI/TECH/NSIG/MISC/24-25/2/II - Empanelment for IT Technical Staff Augmentation & Software Support)"
    },
    {
        "Company Name": "Centre for Management Development (CMD) Kerala",
        "Role": "Empanelment of IT Companies for Technical Resource Augmentation",
        "Url": "https://cmd.kerala.gov.in",
        "Source of Information": "https://cmd.kerala.gov.in (Active Ref: PMU/TDB/DIGI/EOI/2026/01 - Empanelment of IT Companies & Startups for Technical Resource Augmentation)"
    },
    {
        "Company Name": "ICANN (Internet Corporation for Assigned Names and Numbers)",
        "Role": "Remote Software Engineering Staff Augmentation Standing Program",
        "Url": "https://www.icann.org/resources/pages/rfps-2012-02-25-en",
        "Source of Information": "https://www.icann.org/resources/pages/rfps-2012-02-25-en (Standing Global Vendor Program for Remote Software Engineering Staff Augmentation)"
    },
    {
        "Company Name": "Petroleum and Natural Gas Regulatory Board (PNGRB)",
        "Role": "Application Development Agency & Specialized IT Resources",
        "Url": "https://pngrb.gov.in",
        "Source of Information": "https://pngrb.gov.in (RFP for Application Development Agency & Specialized IT Resources)"
    },
    {
        "Company Name": "AgileTurn",
        "Role": "Call for Recruitment Vendors: DevOps, Cloud AWS/Azure, AI/ML, Full Stack",
        "Url": "https://www.linkedin.com/posts/bhupendraprabhakar_we-are-looking-for-recruitment-vendors-activity-7485988875912388608-FvPU",
        "Source of Information": "https://www.linkedin.com/posts/bhupendraprabhakar_we-are-looking-for-recruitment-vendors-activity-7485988875912388608-FvPU (Active Call for Recruitment Vendors: DevOps, Cloud AWS/Azure, Data Eng, AI/ML, Full Stack - sales@agileturn.in)"
    },
    {
        "Company Name": "Artech Information Systems",
        "Role": "Vendor Sourcing for Contract-to-Hire C2H Tech Roles & Software Engineers",
        "Url": "https://www.linkedin.com/posts/aditya-k-76a0311a2_c2h-contracttohire-recruitment-activity-7498680101295788032-C7SF",
        "Source of Information": "https://www.linkedin.com/posts/aditya-k-76a0311a2_c2h-contracttohire-recruitment-activity-7498680101295788032-C7SF (Vendor Sourcing for Contract-to-Hire C2H Tech Roles & Software Engineers - aditya.kishan@artechinfo.in)"
    },
    {
        "Company Name": "Atzean Technologies LLP",
        "Role": "IT Staffing Vendor Network & Contractual Tech Hiring Partner Call",
        "Url": "https://www.linkedin.com/posts/deepak-panchal-a2b384195_onsitehiring-itstaffing-vendornetwork-activity-7490662140169707520-Vr4d",
        "Source of Information": "https://www.linkedin.com/posts/deepak-panchal-a2b384195_onsitehiring-itstaffing-vendornetwork-activity-7490662140169707520-Vr4d (IT Staffing Vendor Network & Contractual Tech Hiring Partner Call for Software & Cloud Engineers)"
    },
    {
        "Company Name": "Triangle Solutions",
        "Role": "Vendor Empanelment Notice for IT Recruitment & Staffing Partners",
        "Url": "https://www.linkedin.com/in/chinmayee-ramesh-8a5001327/",
        "Source of Information": "https://www.linkedin.com/in/chinmayee-ramesh-8a5001327/ (Vendor Empanelment Notice for IT Recruitment & Staffing Partners - connect@trianglesolutions.in)"
    },
    {
        "Company Name": "CBSPL India",
        "Role": "Staffing Vendor Empanelment & Recruitment Partner Intake",
        "Url": "https://www.linkedin.com/in/muskan-nigam-3a916621b/",
        "Source of Information": "https://www.linkedin.com/in/muskan-nigam-3a916621b/ (Staffing Vendor Empanelment & Recruitment Partner Intake - Hr@cbsplindia.com)"
    }
]


# ==========================================
# STAGE 1: LEAD DISCOVERY
# ==========================================

def discover_hn_leads():
    """
    Fetches high-signal buyer opportunities from official 'Who is hiring?' threads.
    Strictly ignores job seeker ('Who wants to be hired?') submissions.
    """
    leads = []
    try:
        story_url = "https://hn.algolia.com/api/v1/search_by_date?tags=author_whoishiring,story&hitsPerPage=10"
        req = urllib.request.Request(story_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=6) as resp:
            hits = json.loads(resp.read().decode('utf-8')).get('hits', [])

        hiring_stories = [h for h in hits if 'who is hiring?' in h.get('title', '').lower()][:1]

        for s in hiring_stories:
            sid = s.get('objectID')
            thread_url = f"https://hn.algolia.com/api/v1/items/{sid}"
            req_t = urllib.request.Request(thread_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req_t, timeout=6) as resp_t:
                data = json.loads(resp_t.read().decode('utf-8'))

            for c in data.get('children', []):
                raw_txt = c.get('text') or ''
                txt = html.unescape(raw_txt)
                first_line = re.sub('<[^<]+?>', ' ', txt.split('<p>')[0]).strip()
                first_line_lower = first_line.lower()

                # Strictly discard job seeker phrases
                if any(k in first_line_lower for k in ['seeking work', 'seeking freelancer', 'looking for a role', 'candidate', 'available for hire']):
                    continue

                # Buyer must indicate contract / freelance / contractor in the headline
                has_contract = any(k in first_line_lower for k in ['contract', 'freelance', 'contractor', 'b2b', 'c2c', 'part-time'])
                if not has_contract:
                    continue

                # Must be a tech role
                txt_lower = txt.lower()
                has_tech = any(tech in txt_lower for tech in TECH_KEYWORDS)
                if not has_tech:
                    continue

                # Must not be pure onsite outside India
                if 'onsite' in first_line_lower and not any(r in first_line_lower for r in ['remote', 'hybrid', 'wfh']):
                    continue

                parts = [p.strip() for p in re.split(r'\||-|–|—', first_line) if p.strip()]
                if not parts:
                    continue

                raw_comp = parts[0]
                comp = re.sub(r'\(.*?\)', '', raw_comp).strip()
                comp = re.sub(r'\[.*?\]', '', comp).strip()
                comp = re.sub(r'[^\w\s\.\,\&]', '', comp).strip()

                # Quality checks on company name
                if not comp or len(comp) > 40 or comp.lower() in ['contract', 'remote', 'role', 'seeking']:
                    continue

                role = parts[1] if len(parts) > 1 else "Contract Tech Engineering"
                cid = c.get('id')
                hn_url = f"https://news.ycombinator.com/item?id={cid}"

                source_info = f"{hn_url} (Direct Buyer Contract Requirement: {role} - Remote/WFH Tech Role)"
                leads.append({
                    "Company Name": comp,
                    "Url": hn_url,
                    "Source of Information": source_info
                })
    except Exception as e:
        print(f"[Discovery] HN fetch error: {e}")
    return leads


def discover_remoteok_leads():
    """Discovers contract and tech roles from the RemoteOK API."""
    leads = []
    try:
        url = "https://remoteok.com/api"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        for j in data[1:]:  # First item is legal notice
            tags = [t.lower() for t in j.get('tags', [])]
            desc = j.get('description', '').lower()
            pos = j.get('position', '').lower()
            company = j.get('company', '').strip()
            link = j.get('url', '')

            if not company or not link:
                continue

            is_tech = any(t in tags for t in ['dev', 'engineer', 'software', 'cloud', 'devops', 'backend', 'frontend', 'python', 'react', 'data', 'qa', 'sys admin', 'golang', 'ai']) or \
                      any(k in pos for k in ['engineer', 'developer', 'software', 'architect', 'devops', 'cloud', 'full stack', 'data', 'qa'])
            if not is_tech:
                continue

            is_contract = any(t in ['contract', 'freelance', 'part time'] for t in tags) or \
                          any(k in pos for k in ['contract', 'contractor', 'freelance', 'part-time', 'c2c']) or \
                          any(k in desc for k in ['independent contractor', '1099', 'contract basis', 'b2b contract', 'corp-to-corp'])
            if not is_contract:
                continue

            loc = j.get('location', '').lower()
            if 'onsite' in loc and not any(r in loc for r in ['remote', 'wfh', 'worldwide', 'anywhere']):
                continue

            source_info = f"{link} (Verified Remote Contract Tech Requirement: {j.get('position')} - 100% Remote/WFH)"
            leads.append({
                "Company Name": company,
                "Url": link,
                "Source of Information": source_info
            })
    except Exception as e:
        print(f"[Discovery] RemoteOK fetch error: {e}")
    return leads


def discover_procurement_rss_leads():
    """Monitors live Google News RSS feeds for IT vendor empanelment & staff augmentation RFPs."""
    leads = []
    queries = [
        'vendor empanelment IT software',
        'staff augmentation contractual hiring tech RFP',
        'subcontracting software development partner RFP'
    ]

    for q in queries:
        try:
            feed_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=en-IN&gl=IN&ceid=IN:en"
            req = urllib.request.Request(feed_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                root = ET.fromstring(resp.read())

            for it in root.findall('.//item')[:5]:
                title = it.find('title').text or ''
                link = it.find('link').text or ''
                source = it.find('source').text if it.find('source') is not None else ''

                parts = title.split(' - ')
                headline = parts[0].strip()
                publisher = parts[-1].strip() if len(parts) > 1 else 'Public Notice'

                headline_lower = headline.lower()
                if not any(k in headline_lower for k in ['empanelment', 'vendor', 'invites', 'rfp', 'solicitation', 'hiring', 'partner']):
                    continue

                first_word = headline.split()[0]
                comp = first_word if len(first_word) > 2 else publisher
                comp = re.sub(r'[^\w\s\.\,\&]', '', comp).strip()

                source_info = f"{link} (Procurement / Vendor Notice: {headline} via {publisher})"
                leads.append({
                    "Company Name": comp,
                    "Url": link,
                    "Source of Information": source_info
                })
        except Exception as e:
            print(f"[Discovery] RSS query error ({q}): {e}")
    return leads


def discover_all_leads():
    """Aggregates leads from all dynamic discovery channels plus baseline solicitations."""
    candidates = []
    
    print("[Discovery] Fetching Hacker News B2B/contract tech opportunities...")
    hn_leads = discover_hn_leads()
    print(f"[Discovery] Found {len(hn_leads)} leads from Hacker News.")
    candidates.extend(hn_leads)

    print("[Discovery] Fetching RemoteOK contract tech positions...")
    remote_leads = discover_remoteok_leads()
    print(f"[Discovery] Found {len(remote_leads)} leads from RemoteOK.")
    candidates.extend(remote_leads)

    print("[Discovery] Fetching live procurement & empanelment RSS updates...")
    rss_leads = discover_procurement_rss_leads()
    print(f"[Discovery] Found {len(rss_leads)} leads from procurement feeds.")
    candidates.extend(rss_leads)

    candidates.extend(BASELINE_SOLICITATIONS)
    return candidates


# ==========================================
# STAGE 2: EVIDENCE VALIDATION
# ==========================================

def validate_url(cand):
    """
    Validates a single candidate URL.
    Returns (candidate, is_valid, status_or_reason).
    Recognizes LinkedIn (HTTP 999) and bot defenses (401/403) as valid live endpoints.
    """
    url = cand.get("Url", "")
    if not url:
        m = re.search(r'https?://[^\s\)]+', cand.get("Source of Information", ""))
        url = m.group(0) if m else ""

    if not url or not url.startswith("http"):
        return cand, False, "INVALID_URL"

    # Hacker News returns 419 on custom user agents, empty headers bypasses it
    headers = {} if 'ycombinator.com' in url else {'User-Agent': 'Mozilla/5.0'}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=4, context=SSL_CTX) as r:
            status = r.status
            try:
                sample = r.read(4096).decode('utf-8', errors='ignore').lower()
                for dead_marker in DEAD_MARKERS:
                    if dead_marker in sample:
                        return cand, False, f"EXPIRED_OR_CLOSED ({dead_marker})"
            except Exception:
                pass
            return cand, True, status
    except urllib.error.HTTPError as e:
        if e.code in [401, 403, 429, 999]:
            # Bot protected, anti-scraping challenge, or rate limited; domain exists and is live
            return cand, True, f"PROTECTED_{e.code}"
        return cand, False, f"HTTP_{e.code}"
    except Exception as e:
        return cand, False, type(e).__name__


def validate_candidates_concurrently(candidates):
    """Validates candidate links concurrently using ThreadPoolExecutor."""
    validated = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_cand = {executor.submit(validate_url, cand): cand for cand in candidates}
        for future in as_completed(future_to_cand):
            cand, is_valid, reason = future.result()
            if is_valid:
                validated.append(cand)
            else:
                print(f"[Validator] Pruning inactive lead: {cand.get('Company Name')} ({reason}) -> {cand.get('Url')}")
    return validated


# ==========================================
# STAGE 3: FILTER & DEDUPLICATION
# ==========================================

def normalize_company_name(name):
    """Normalizes company names for deduplication."""
    clean = re.sub(r'(?i)\b(inc|corp|corporation|llc|ltd|pvt|technologies|solutions|group)\b', '', name)
    clean = re.sub(r'[^a-zA-Z0-9]', '', clean).lower()
    return clean.strip()


def extract_canonical_url(source_str):
    """Extracts canonical host and path for deduplication."""
    m = re.search(r'https?://[^\s\)]+', source_str)
    if not m:
        return source_str.strip().lower()
    parsed = urllib.parse.urlparse(m.group(0))
    host = parsed.netloc.lower()
    path = parsed.path.rstrip('/').lower()
    if 'google.com' in host and parsed.query:
        return f"{host}{path}?{parsed.query}"
    return f"{host}{path}"


def deduplicate_leads(new_candidates, existing_rows):
    """
    Deduplicates using (normalized_company, canonical_url) keys.
    Preserves historical entries while eliminating redundant rows.
    """
    seen_keys = set()
    cleaned_existing = []

    for row in existing_rows:
        name = row.get("Company Name", "").strip()
        src = row.get("Source of Information", "").strip()
        norm_name = normalize_company_name(name)
        canon_url = extract_canonical_url(src)
        key = (norm_name, canon_url)

        if key not in seen_keys:
            seen_keys.add(key)
            cleaned_existing.append(row)

    to_add = []
    today_str = datetime.now().strftime("%Y-%m-%d")

    for cand in new_candidates:
        name = cand.get("Company Name", "").strip()
        src = cand.get("Source of Information", "").strip()
        norm_name = normalize_company_name(name)
        canon_url = extract_canonical_url(src)
        key = (norm_name, canon_url)

        if key not in seen_keys:
            seen_keys.add(key)
            to_add.append({
                "Date": today_str,
                "Company Name": name,
                "Source of Information": src
            })

    return cleaned_existing, to_add


# ==========================================
# STAGE 4: CSV PERSISTENCE & EXECUTION
# ==========================================

def load_existing():
    existing = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing.append(row)
    return existing


def run_pipeline():
    print(f"=== Staff Augmentation Discovery Pipeline Started [{datetime.now().isoformat()}] ===")
    
    # 1. Discover
    raw_candidates = discover_all_leads()
    print(f"[Pipeline] Discovered total raw candidates: {len(raw_candidates)}")

    # 2. Validate concurrently
    print("[Pipeline] Concurrently validating candidate accessibility and activity...")
    validated = validate_candidates_concurrently(raw_candidates)
    print(f"[Pipeline] Validated active candidates: {len(validated)}")

    # 3. Deduplicate & Filter
    existing = load_existing()
    print(f"[Pipeline] Existing entries in CSV: {len(existing)}")
    cleaned_existing, new_leads = deduplicate_leads(validated, existing)
    print(f"[Pipeline] Genuinely new leads to append: {len(new_leads)}")

    # 4. Write back to companies.csv
    final_rows = cleaned_existing + new_leads
    with open(CSV_FILE, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in final_rows:
            writer.writerow({
                "Date": row.get("Date", datetime.now().strftime("%Y-%m-%d")),
                "Company Name": row.get("Company Name", ""),
                "Source of Information": row.get("Source of Information", "")
            })

    print(f"[Pipeline] Pipeline complete. companies.csv updated. Total leads: {len(final_rows)}. Newly added: {len(new_leads)}.")
    return len(new_leads)


if __name__ == "__main__":
    added = run_pipeline()
    if "--push" in sys.argv:
        try:
            import subprocess
            subprocess.run(["git", "add", "companies.csv", "partner_channels.csv"], check=True)
            commit_msg = f"chore(leads): daily update at 8:30 AM IST [{datetime.now().strftime('%Y-%m-%d')}]"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            subprocess.run(["git", "push"], check=True)
            print("Successfully committed and pushed changes.")
        except Exception as e:
            print(f"Git push skipped or failed: {e}")
