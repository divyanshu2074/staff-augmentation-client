# Staff Augmentation & Contractual Tech Hiring - Client Tracker

Automated daily intelligence tracker collecting companies, enterprises, public institutions, and government bodies actively seeking vendors and staffing partners for **IT/Tech Staff Augmentation, Contractual Tech Hiring, C2C / Subcontracting, and Vendor Empanelment**.

---

## 🎯 Target Criteria
- **Domain:** Tech & IT roles only (Software Engineering, Full Stack, Cloud, DevOps, AI/ML, Data Engineering, QA/Testing, Cybersecurity, etc.)
- **Engagement Model:** Staff Augmentation, Vendor Empanelment, Subcontracting / C2C / C2H, RFPs, and Contractual IT Staffing Agencies.
- **Location & Visa:** 
  - Direct India-based enterprise & PSU opportunities (No visa needed).
  - International opportunities that are **100% Remote / Work From Home (WFH)** or offshore-friendly with no on-site visa sponsorship needed.

---

## 🏗️ 4-Stage Automated Pipeline (`update_leads.py`)

Unlike static list scripts, the engine runs an end-to-end 4-stage pipeline on every execution:

```
[1. Discover] ---> [2. Validate] ---> [3. Filter & Deduplicate] ---> [4. Update CSV]
Multi-Source       Concurrent HTTP     Buyer Signals + Tech +         Append Active
Ingestion          & Dead Pruning      Canonical URL Keys             Leads to CSV
```

1. **Stage 1: Multi-Source Dynamic Discovery**
   - **Hacker News Tech Hiring API:** Ingests live monthly buyer requirements looking for contract, B2B, or freelance engineering teams.
   - **RemoteOK API:** Filters for active 1099, contractor, and B2B software engineering and tech postings.
   - **Live Procurement & Tender Feeds:** Monitors real-time Google News RSS queries for IT vendor empanelment notices and staff augmentation RFPs.
   - **Standing Solicitations Registry:** Curated baseline of active enterprise and government vendor programs.

2. **Stage 2: Concurrent Evidence Validation**
   - Multi-threaded HTTP status validation with configurable timeouts and connection pooling.
   - Detects anti-bot defenses (e.g. LinkedIn HTTP 999, Cloudflare 401/403) and differentiates them from dead 404 links.
   - Scans response content for dead markers (`rfp closed`, `tender cancelled`, `no longer accepting submissions`) and automatically prunes expired leads.

3. **Stage 3: Buyer Filter & Resilient Deduplication**
   - Strictly purges job seeker / candidate posts (`seeking work`, `seeking freelancer`).
   - Normalizes company names (stripping legal suffixes like `Inc`, `LLC`, `Pvt Ltd`).
   - Generates canonical `(normalized_company, canonical_domain_url)` keys to prevent duplicates even when listing titles or descriptions change.

4. **Stage 4: CSV Separation & Persistence**
   - **`companies.csv`**: Contains active, verified, time-stamped client/vendor staffing opportunities with exact columns `Date | Company Name | Source of Information`.
   - **`partner_channels.csv`**: Preserves continuous agency registration and intake portals (e.g., Turing, BairesDev, YASH Technologies) separately from time-sensitive demands.

---

## 📊 CSV File Specifications

### 1. Active Opportunities: [`companies.csv`](./companies.csv)
| Date | Company Name | Source of Information |
| :--- | :--- | :--- |
| `YYYY-MM-DD` | Organization / Buyer | Direct posting link, RFP link, or verified opportunity description |

### 2. Standing Channels: [`partner_channels.csv`](./partner_channels.csv)
| Date | Company Name | Source of Information |
| :--- | :--- | :--- |
| `YYYY-MM-DD` | Platform / Agency | Permanent vendor empanelment & onboarding portal |

---

## ⏰ Daily Scheduled Execution (8:30 AM IST)
The CSVs are rebuilt and synchronized daily at **8:30 AM IST** via:
1. **GitHub Actions ([`.github/workflows/daily_build.yml`](./.github/workflows/daily_build.yml)):**
   - Configured with cron `0 3 * * *` (03:00 UTC = 08:30 AM IST).
   - Automatically executes daily on GitHub's infrastructure and commits any updates directly into the repository.
   - Can also be triggered manually anytime via `workflow_dispatch`.
2. **Local / CLI Trigger:**
   ```bash
   python update_leads.py --push
   ```
