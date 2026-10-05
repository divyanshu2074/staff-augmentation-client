# Staff Augmentation & Contractual Tech Hiring - Client Tracker

Automated daily intelligence tracker collecting companies, enterprises, public institutions, and government bodies actively seeking vendors and staffing partners for **IT/Tech Staff Augmentation and Contractual Hiring**.

---

## 🎯 Target Criteria
- **Domain:** Tech & IT roles (Software Engineering, Full Stack, Cloud, DevOps, AI/ML, Data Engineering, QA/Testing, Cybersecurity, etc.)
- **Engagement Model:** Staff Augmentation, Vendor Empanelment, Subcontracting / C2C / C2H, RFPs, and Contractual IT Staffing Agencies.
- **Location & Visa:** 
  - Direct India-based enterprise & PSU opportunities (No visa needed).
  - International opportunities that are **100% Remote / Work From Home (WFH)** or offshore-friendly with no on-site visa sponsorship needed.

---

## 📊 CSV File Specification
The output is stored in **[`companies.csv`](./companies.csv)** with the following exact columns:

| Date | Company Name | Source of Information |
| :--- | :--- | :--- |
| `YYYY-MM-DD` | Name of the organization / enterprise | Official RFP link, procurement tender ID, or verified empanelment posting |

---

## ⏰ Daily Scheduled Execution (8:30 AM IST)
The CSV is rebuilt and synchronized every day at **8:30 AM IST** via:
1. **GitHub Actions Automation ([`.github/workflows/daily_build.yml`](./.github/workflows/daily_build.yml)):**
   - Configured with cron `0 3 * * *` (03:00 UTC = 08:30 AM IST).
   - Automatically executes daily on GitHub's infrastructure and commits any updates directly into the repository.
   - Also supports manual execution anytime via `workflow_dispatch`.
2. **Local Daemon / Cron Task:**
   - Script `update_leads.py --push` can be triggered via system cron or background scheduler.

---

## 🛠️ Manual Execution
To manually run the lead updater and sync the CSV:
```bash
python update_leads.py --push
```
