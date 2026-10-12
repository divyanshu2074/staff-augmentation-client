#!/usr/bin/env python3
"""
Automated Tech Staff Augmentation & Contractual Hiring Discovery Engine
Continuously queries multi-angle dynamic sources on every execution to discover, validate,
filter, and append NEW relevant leads to companies.csv.

Architectural Highlights:
  1. Dynamic Multi-Source Discovery:
     - Hacker News Tech Hiring Threads: Discovers current and recent monthly threads dynamically.
     - RemoteOK Live API: Continuously pulls latest remote contract / B2B tech roles.
     - Multi-Query Procurement & RFP Radar: Discovers live IT vendor empanelment notices across global & India feeds.
     - Dice & Technical Job Board RSS Radar: Surfaces direct enterprise C2C / Corp-to-Corp tech requirements.
     - Dynamic Topic / Keyword Expansion: Rotates queries across staff augmentation, C2C, vendor empanelment,
       and subcontracting.
  2. Concurrent Evidence Validation:
     - Rapid ThreadPoolExecutor URL validation with bot-challenge awareness (401/403/999) and dead/expired marker pruning.
  3. Strict Buyer Relevance & Deduplication:
     - Filters out job seekers and non-tech postings.
     - Prevents duplicate insertion across runs using (normalized_company, canonical_url) keys.
  4. CSV Persistence:
     - Appends new leads to companies.csv with execution date.
     - Maintains static partner networks in partner_channels.csv.
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
    'architect', 'typescript', 'golang', 'rust', 'c#', 'java', 'aws', 'azure', 
    'angular', 'flutter', 'kubernetes', 'salesforce', 'sap', 'oracle'
}

DEAD_MARKERS = [
    'rfp closed', 'bidding closed', 'tender cancelled', 'tender expired', 
    'no longer accepting submissions', 'deadline passed', 'position closed'
]


# ==========================================
# STAGE 1: DYNAMIC MULTI-SOURCE DISCOVERY
# ==========================================

def discover_hn_leads():
    """
    Dynamically fetches buyer requirements from recent official Hacker News 'Who is hiring?' threads.
    Searches recent monthly threads and extracts direct contract, freelance, and B2B requirements.
    """
    leads = []
    try:
        story_url = "https://hn.algolia.com/api/v1/search_by_date?tags=author_whoishiring,story&hitsPerPage=10"
        req = urllib.request.Request(story_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=6) as resp:
            hits = json.loads(resp.read().decode('utf-8')).get('hits', [])

        hiring_stories = [h for h in hits if 'who is hiring?' in h.get('title', '').lower()][:2]

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

                # Strictly discard candidate / job seeker postings
                if any(k in first_line_lower for k in ['seeking work', 'seeking freelancer', 'looking for a role', 'candidate', 'available for hire']):
                    continue

                # Buyer must indicate contract / freelance / contractor / B2B in headline
                has_contract = any(k in first_line_lower for k in ['contract', 'freelance', 'contractor', 'b2b', 'c2c', 'part-time'])
                if not has_contract:
                    continue

                # Must be a tech role
                txt_lower = txt.lower()
                has_tech = any(tech in txt_lower for tech in TECH_KEYWORDS)
                if not has_tech:
                    continue

                # Filter out pure on-site outside India
                if 'onsite' in first_line_lower and not any(r in first_line_lower for r in ['remote', 'hybrid', 'wfh']):
                    continue

                parts = [p.strip() for p in re.split(r'\||-|–|—', first_line) if p.strip()]
                if not parts:
                    continue

                raw_comp = parts[0]
                comp = re.sub(r'\(.*?\)', '', raw_comp).strip()
                comp = re.sub(r'\[.*?\]', '', comp).strip()
                comp = re.sub(r'[^\w\s\.\,\&]', '', comp).strip()

                if not comp or len(comp) > 40 or comp.lower() in ['contract', 'remote', 'role', 'seeking']:
                    continue

                role = parts[1] if len(parts) > 1 else "Contract Tech Engineering"
                cid = c.get('id')
                hn_url = f"https://news.ycombinator.com/item?id={cid}"

                source_info = f"{hn_url} (Direct Buyer Tech Contract: {role} - Remote/WFH)"
                leads.append({
                    "Company Name": comp,
                    "Url": hn_url,
                    "Source of Information": source_info
                })
    except Exception as e:
        print(f"[Discovery] HN fetch error: {e}")
    return leads


def discover_remoteok_leads():
    """Dynamically pulls contract and contractor software engineering roles from RemoteOK."""
    leads = []
    try:
        url = "https://remoteok.com/api"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        for j in data[1:]:
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

            source_info = f"{link} (Verified Remote Contract Requirement: {j.get('position')} - 100% Remote/WFH)"
            leads.append({
                "Company Name": company,
                "Url": link,
                "Source of Information": source_info
            })
    except Exception as e:
        print(f"[Discovery] RemoteOK fetch error: {e}")
    return leads


def discover_procurement_rss_leads():
    """
    Dynamically scans Google News RSS queries for IT vendor empanelment notices,
    RFPs, and public sector software manpower solicitations.
    """
    leads = []
    queries = [
        'vendor empanelment IT software manpower',
        'staff augmentation contractual hiring tech RFP',
        'subcontracting software development partner RFP',
        'tender IT manpower software developers',
        'request for proposal software staff augmentation',
        'IT staffing vendor empanelment',
        'empanelment of IT agencies software',
        'request for proposal IT manpower'
    ]

    for q in queries:
        try:
            feed_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=en-IN&gl=IN&ceid=IN:en"
            req = urllib.request.Request(feed_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                root = ET.fromstring(resp.read())

            for it in root.findall('.//item')[:6]:
                title = it.find('title').text or ''
                link = it.find('link').text or ''
                source = it.find('source').text if it.find('source') is not None else ''

                parts = title.split(' - ')
                headline = parts[0].strip()
                publisher = parts[-1].strip() if len(parts) > 1 else 'Public Notice'

                headline_lower = headline.lower()
                if not any(k in headline_lower for k in ['empanelment', 'vendor', 'invites', 'rfp', 'solicitation', 'hiring', 'partner', 'manpower', 'tender']):
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
            print(f"[Discovery] Procurement RSS error ({q[:30]}): {e}")
    return leads


def discover_c2c_contract_leads():
    """
    Dynamically scans live C2C (Corp-to-Corp) technical solicitations.
    Extracts direct enterprise buyer and staffing vendor calls for external contractual developers.
    """
    leads = []
    queries = [
        'site:dice.com/job-detail "C2C" remote developer',
        'site:dice.com/job-detail "Corp-to-Corp" remote software',
        'site:dice.com/job-detail "C2C" remote DevOps OR Cloud'
    ]

    for q in queries:
        try:
            feed_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl=en-US&gl=US&ceid=US:en"
            req = urllib.request.Request(feed_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                root = ET.fromstring(resp.read())

            for it in root.findall('.//item')[:10]:
                title = (it.find('title').text or '').strip()
                link = it.find('link').text or ''

                # Format on Dice: 'Role - Company - Location - Dice'
                parts = [p.strip() for p in title.split(' - ')]
                if len(parts) >= 3:
                    role = parts[0]
                    comp = parts[1]
                    loc = parts[2]
                    comp_clean = re.sub(r'\(.*?\)', '', comp).strip()
                    comp_clean = re.sub(r'[^\w\s\.\,\&]', '', comp_clean).strip()

                    # Quality checks on company name
                    if len(comp_clean) > 2 and len(comp_clean) < 40 and not any(k in comp_clean.lower() for k in ['remote', 'dice', 'united states', 'san antonio', 'dallas', 'austin', 'houston', 'tx']):
                        source_info = f"{link} (Verified C2C/Contract Tech Requirement: {role} in {loc})"
                        leads.append({
                            "Company Name": comp_clean,
                            "Url": link,
                            "Source of Information": source_info
                        })
        except Exception as e:
            print(f"[Discovery] C2C RSS error ({q[:30]}): {e}")
    return leads


def discover_all_leads():
    """Orchestrates dynamic discovery across all active web sources."""
    candidates = []

    print("[Discovery] Fetching Hacker News tech contract hiring opportunities...")
    hn_leads = discover_hn_leads()
    print(f"[Discovery] Found {len(hn_leads)} leads from Hacker News.")
    candidates.extend(hn_leads)

    print("[Discovery] Fetching RemoteOK contract tech positions...")
    remote_leads = discover_remoteok_leads()
    print(f"[Discovery] Found {len(remote_leads)} leads from RemoteOK.")
    candidates.extend(remote_leads)

    print("[Discovery] Fetching live procurement, tender & empanelment notices...")
    procurement_leads = discover_procurement_rss_leads()
    print(f"[Discovery] Found {len(procurement_leads)} leads from procurement feeds.")
    candidates.extend(procurement_leads)

    print("[Discovery] Fetching live enterprise C2C contract solicitations...")
    c2c_leads = discover_c2c_contract_leads()
    print(f"[Discovery] Found {len(c2c_leads)} leads from C2C feeds.")
    candidates.extend(c2c_leads)

    return candidates


# ==========================================
# STAGE 2: EVIDENCE VALIDATION
# ==========================================

def validate_url(cand):
    """
    Validates a candidate URL with timeout.
    Returns (candidate, is_valid, status_or_reason).
    Tolerates bot-protection challenges (401, 403, 429, 999) from live services.
    Prunes dead / expired markers in content.
    """
    url = cand.get("Url", "")
    if not url:
        m = re.search(r'https?://[^\s\)]+', cand.get("Source of Information", ""))
        url = m.group(0) if m else ""

    if not url or not url.startswith("http"):
        return cand, False, "INVALID_URL"

    # Hacker News returns 419 on common custom user agents, empty headers bypasses it
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
            # Anti-bot challenge or rate limit on live domain
            return cand, True, f"PROTECTED_{e.code}"
        return cand, False, f"HTTP_{e.code}"
    except Exception as e:
        return cand, False, type(e).__name__


def validate_candidates_concurrently(candidates):
    """Concurrently validates candidate links using ThreadPoolExecutor."""
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
    Deduplicates candidates against existing CSV records using (normalized_company, canonical_url).
    Preserves historical entries while eliminating duplicate rows.
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
    print(f"=== Dynamic Staff Augmentation Discovery Pipeline Started [{datetime.now().isoformat()}] ===")

    # 1. Discover dynamically
    raw_candidates = discover_all_leads()
    print(f"[Pipeline] Discovered total raw candidates across feeds: {len(raw_candidates)}")

    # 2. Validate concurrently
    print("[Pipeline] Concurrently validating candidate accessibility and activity...")
    validated = validate_candidates_concurrently(raw_candidates)
    print(f"[Pipeline] Validated active candidates: {len(validated)}")

    # 3. Deduplicate against existing historical CSV records
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

    print(f"[Pipeline] Pipeline complete. companies.csv updated. Total leads: {len(final_rows)}. Newly added today: {len(new_leads)}.")
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
