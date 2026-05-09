#!/usr/bin/env python3
"""
Creates all missing JonOps Airtable tables.
Run once. Safe to re-run — skips tables that already exist.
"""

import json
import os
import sys
import urllib.request
import urllib.error

AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json"
}

def api_request(method, url, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read()), None
    except urllib.error.HTTPError as e:
        return None, json.loads(e.read())

def get_existing_tables():
    result, err = api_request("GET", f"https://api.airtable.com/v0/meta/bases/{AIRTABLE_BASE_ID}/tables")
    if err:
        print(f"ERROR fetching tables: {err}")
        sys.exit(1)
    return {t["name"]: t["id"] for t in result.get("tables", [])}

def create_table(name, fields):
    print(f"  Creating: {name}...")
    data = {"name": name, "fields": fields}
    result, err = api_request("POST", f"https://api.airtable.com/v0/meta/bases/{AIRTABLE_BASE_ID}/tables", data)
    if err:
        print(f"  ERROR: {err}")
        return False
    print(f"  ✓ Created: {name} (ID: {result.get('id')})")
    return True

# ─── TABLE DEFINITIONS ────────────────────────────────────────────────────────

TABLES = [
    {
        "name": "Keywords",
        "fields": [
            {"name": "Keyword", "type": "singleLineText"},
            {"name": "Search Volume", "type": "number", "options": {"precision": 0}},
            {"name": "Difficulty", "type": "number", "options": {"precision": 0}},
            {"name": "Intent", "type": "singleSelect", "options": {"choices": [
                {"name": "Informational", "color": "blueLight2"},
                {"name": "Commercial", "color": "greenLight2"},
                {"name": "Transactional", "color": "purpleLight2"},
                {"name": "Navigational", "color": "grayLight2"},
            ]}},
            {"name": "Status", "type": "singleSelect", "options": {"choices": [
                {"name": "Queue", "color": "yellowLight2"},
                {"name": "Researching", "color": "blueLight2"},
                {"name": "Published", "color": "greenLight2"},
                {"name": "Skipped", "color": "grayLight2"},
            ]}},
            {"name": "Date Published", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
            {"name": "Notes", "type": "multilineText"},
        ]
    },
    {
        "name": "Content Calendar",
        "fields": [
            {"name": "Title", "type": "singleLineText"},
            {"name": "Keyword", "type": "singleLineText"},
            {"name": "Status", "type": "singleSelect", "options": {"choices": [
                {"name": "Queued", "color": "yellowLight2"},
                {"name": "Researching", "color": "blueLight2"},
                {"name": "Writing", "color": "purpleLight2"},
                {"name": "Draft", "color": "grayLight2"},
                {"name": "Scheduled", "color": "cyanLight2"},
                {"name": "Published", "color": "greenLight2"},
            ]}},
            {"name": "WP Post ID", "type": "number", "options": {"precision": 0}},
            {"name": "WP URL", "type": "url"},
            {"name": "Publish Date", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
            {"name": "Featured Image URL", "type": "url"},
            {"name": "Category", "type": "singleLineText"},
            {"name": "Word Count", "type": "number", "options": {"precision": 0}},
            {"name": "Notes", "type": "multilineText"},
        ]
    },
    {
        "name": "Research",
        "fields": [
            {"name": "Keyword", "type": "singleLineText"},
            {"name": "Source URL", "type": "url"},
            {"name": "Source Title", "type": "singleLineText"},
            {"name": "Content", "type": "multilineText"},
            {"name": "Summary", "type": "multilineText"},
            {"name": "SERP Position", "type": "number", "options": {"precision": 0}},
            {"name": "Date Scraped", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
        ]
    },
    {
        "name": "Generated Images",
        "fields": [
            {"name": "Name", "type": "singleLineText"},
            {"name": "Image URL", "type": "url"},
            {"name": "Image Model", "type": "singleLineText"},
            {"name": "Prompt", "type": "multilineText"},
            {"name": "Site", "type": "singleLineText"},
            {"name": "Article Title", "type": "singleLineText"},
            {"name": "Status", "type": "singleSelect", "options": {"choices": [
                {"name": "Uploaded", "color": "greenLight2"},
                {"name": "Pending", "color": "yellowLight2"},
                {"name": "Failed", "color": "redLight2"},
            ]}},
        ]
    },
    {
        "name": "Reference Images",
        "fields": [
            {"name": "Title", "type": "singleLineText"},
            {"name": "Subject", "type": "singleLineText"},
            {"name": "Source URL", "type": "url"},
            {"name": "Image URL", "type": "url"},
            {"name": "Notes", "type": "multilineText"},
            {"name": "Source Type", "type": "singleSelect", "options": {"choices": [
                {"name": "Wikipedia", "color": "blueLight2"},
                {"name": "Getty Previews", "color": "purpleLight2"},
                {"name": "3rd Party Site", "color": "grayLight2"},
                {"name": "Official Artist", "color": "greenLight2"},
                {"name": "Press Photo", "color": "yellowLight2"},
                {"name": "Creative Commons", "color": "cyanLight2"},
            ]}},
        ]
    },
    {
        "name": "Leads",
        "fields": [
            {"name": "Name", "type": "singleLineText"},
            {"name": "Email", "type": "email"},
            {"name": "Company", "type": "singleLineText"},
            {"name": "Website", "type": "url"},
            {"name": "Status", "type": "singleSelect", "options": {"choices": [
                {"name": "New", "color": "yellowLight2"},
                {"name": "Verified", "color": "blueLight2"},
                {"name": "Invalid", "color": "redLight2"},
                {"name": "Subscribed", "color": "greenLight2"},
                {"name": "Unsubscribed", "color": "grayLight2"},
            ]}},
            {"name": "Source", "type": "singleSelect", "options": {"choices": [
                {"name": "WooCommerce Order", "color": "greenLight2"},
                {"name": "Fluent Form", "color": "blueLight2"},
                {"name": "Lead Scrape", "color": "purpleLight2"},
                {"name": "Manual", "color": "grayLight2"},
            ]}},
            {"name": "Notes", "type": "multilineText"},
        ]
    },
    {
        "name": "B2B Queries",
        "fields": [
            {"name": "Query", "type": "singleLineText"},
            {"name": "Target Type", "type": "singleSelect", "options": {"choices": [
                {"name": "Google Maps", "color": "greenLight2"},
                {"name": "LinkedIn", "color": "blueLight2"},
                {"name": "Both", "color": "purpleLight2"},
            ]}},
            {"name": "Business Category", "type": "singleLineText"},
            {"name": "Region", "type": "singleLineText"},
            {"name": "Score", "type": "number", "options": {"precision": 1}},
            {"name": "Priority", "type": "singleSelect", "options": {"choices": [
                {"name": "High", "color": "redLight2"},
                {"name": "Medium", "color": "yellowLight2"},
                {"name": "Low", "color": "grayLight2"},
            ]}},
            {"name": "Status", "type": "singleSelect", "options": {"choices": [
                {"name": "Queued", "color": "yellowLight2"},
                {"name": "Running", "color": "blueLight2"},
                {"name": "Done", "color": "greenLight2"},
                {"name": "Paused", "color": "grayLight2"},
            ]}},
            {"name": "Notes", "type": "multilineText"},
        ]
    },
    {
        "name": "Published Posts",
        "fields": [
            {"name": "Title", "type": "singleLineText"},
            {"name": "URL", "type": "url"},
            {"name": "Published Date", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
            {"name": "Category", "type": "singleLineText"},
            {"name": "Focus Keyword", "type": "singleLineText"},
            {"name": "Word Count", "type": "number", "options": {"precision": 0}},
            {"name": "Featured Image URL", "type": "url"},
            {"name": "Social Posted", "type": "checkbox", "options": {"color": "greenBright", "icon": "check"}},
            {"name": "Newsletter Featured", "type": "checkbox", "options": {"color": "blueBright", "icon": "check"}},
            {"name": "WP Post ID", "type": "number", "options": {"precision": 0}},
        ]
    },
    {
        "name": "Social Queue",
        "fields": [
            {"name": "Topic", "type": "singleLineText"},
            {"name": "Research Brief", "type": "multilineText"},
            {"name": "Platform Fit", "type": "multipleSelects", "options": {"choices": [
                {"name": "FB-IG", "color": "blueLight2"},
                {"name": "Twitter", "color": "cyanLight2"},
                {"name": "Pinterest", "color": "redLight2"},
                {"name": "LinkedIn", "color": "blueLight2"},
                {"name": "GMB", "color": "greenLight2"},
            ]}},
            {"name": "Status", "type": "singleSelect", "options": {"choices": [
                {"name": "Queued", "color": "yellowLight2"},
                {"name": "In Progress", "color": "blueLight2"},
                {"name": "Used", "color": "greenLight2"},
                {"name": "Skipped", "color": "grayLight2"},
            ]}},
            {"name": "Priority", "type": "singleSelect", "options": {"choices": [
                {"name": "High", "color": "redLight2"},
                {"name": "Medium", "color": "yellowLight2"},
                {"name": "Low", "color": "grayLight2"},
            ]}},
            {"name": "Source", "type": "singleLineText"},
            {"name": "Date Added", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
        ]
    },
    {
        "name": "Social Posts Log",
        "fields": [
            {"name": "Post ID", "type": "singleLineText"}, {"name": "Platform", "type": "singleSelect", "options": {"choices": [
                {"name": "Facebook", "color": "blueLight2"},
                {"name": "Instagram", "color": "pinkLight2"},
                {"name": "Twitter", "color": "cyanLight2"},
                {"name": "Pinterest", "color": "redLight2"},
                {"name": "LinkedIn", "color": "blueLight2"},
                {"name": "GMB", "color": "greenLight2"},
            ]}},
            {"name": "Post Type", "type": "singleSelect", "options": {"choices": [
                {"name": "Blog Repurpose", "color": "blueLight2"},
                {"name": "Research Queue", "color": "purpleLight2"},
            ]}},
            {"name": "Caption Preview", "type": "multilineText"},
            {"name": "Metricool Post ID", "type": "singleLineText"},
            {"name": "Scheduled Time", "type": "dateTime", "options": {"dateFormat": {"name": "iso"}, "timeFormat": {"name": "24hour"}, "timeZone": "Asia/Makassar"}},
            {"name": "Source Post URL", "type": "url"},
            {"name": "Image URL", "type": "url"},
        ]
    },
    {
        "name": "Newsletter Queue",
        "fields": [
            {"name": "Main Topic", "type": "singleLineText"},
            {"name": "Subject Line Options", "type": "multilineText"},
            {"name": "Research Brief", "type": "multilineText"},
            {"name": "Featured Post URL", "type": "url"},
            {"name": "CTA", "type": "singleLineText"},
            {"name": "Status", "type": "singleSelect", "options": {"choices": [
                {"name": "Queued", "color": "yellowLight2"},
                {"name": "In Progress", "color": "blueLight2"},
                {"name": "Sent", "color": "greenLight2"},
                {"name": "Skipped", "color": "grayLight2"},
            ]}},
            {"name": "Week Target", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
        ]
    },
    {
        "name": "Newsletter Log",
        "fields": [
            {"name": "Subject", "type": "singleLineText"},
            {"name": "Send Date", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
            {"name": "Sendy Campaign ID", "type": "singleLineText"},
            {"name": "List Sent To", "type": "singleLineText"},
            {"name": "Subscriber Count", "type": "number", "options": {"precision": 0}},
            {"name": "Open Rate", "type": "percent", "options": {"precision": 1}},
            {"name": "Click Rate", "type": "percent", "options": {"precision": 1}},
        ]
    },
    {
        "name": "Market Intelligence",
        "fields": [
            {"name": "Scan Date", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
            {"name": "Key Trends", "type": "multilineText"},
            {"name": "Top SERP Players", "type": "multilineText"},
            {"name": "Content Gaps", "type": "multilineText"},
            {"name": "Keyword Opportunities", "type": "multilineText"},
            {"name": "Competitor Moves", "type": "multilineText"},
            {"name": "Action Items", "type": "multilineText"},
        ]
    },
    {
        "name": "Outreach Queries",
        "fields": [
            {"name": "Query", "type": "singleLineText"},
            {"name": "Niche", "type": "singleLineText"},
            {"name": "Region", "type": "singleLineText"},
            {"name": "Score", "type": "number", "options": {"precision": 1}},
            {"name": "Priority", "type": "singleSelect", "options": {"choices": [
                {"name": "High", "color": "redLight2"},
                {"name": "Medium", "color": "yellowLight2"},
                {"name": "Low", "color": "grayLight2"},
            ]}},
            {"name": "Status", "type": "singleSelect", "options": {"choices": [
                {"name": "Queued", "color": "yellowLight2"},
                {"name": "Running", "color": "blueLight2"},
                {"name": "Done", "color": "greenLight2"},
                {"name": "Paused", "color": "grayLight2"},
            ]}},
            {"name": "Leads Found", "type": "number", "options": {"precision": 0}},
            {"name": "Last Run", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
            {"name": "Notes", "type": "multilineText"},
        ]
    },
    {
        "name": "Outreach Leads",
        "fields": [
            {"name": "Website", "type": "url"},
            {"name": "Blog Name", "type": "singleLineText"},
            {"name": "Email", "type": "email"},
            {"name": "All Emails", "type": "multilineText"},
            {"name": "Email Source Page", "type": "url"},
            {"name": "Niche", "type": "singleLineText"},
            {"name": "Region", "type": "singleLineText"},
            {"name": "MV Status", "type": "singleSelect", "options": {"choices": [
                {"name": "Valid", "color": "greenLight2"},
                {"name": "Catch-All", "color": "yellowLight2"},
                {"name": "Invalid", "color": "redLight2"},
                {"name": "Pending", "color": "grayLight2"},
            ]}},
            {"name": "BB Status", "type": "singleSelect", "options": {"choices": [
                {"name": "Valid", "color": "greenLight2"},
                {"name": "Risky", "color": "yellowLight2"},
                {"name": "Invalid", "color": "redLight2"},
                {"name": "Skipped", "color": "grayLight2"},
            ]}},
            {"name": "Final Status", "type": "singleSelect", "options": {"choices": [
                {"name": "Verified", "color": "greenLight2"},
                {"name": "Risky", "color": "yellowLight2"},
                {"name": "Invalid", "color": "redLight2"},
                {"name": "Pending", "color": "grayLight2"},
            ]}},
            {"name": "Outreach Status", "type": "singleSelect", "options": {"choices": [
                {"name": "Not Started", "color": "grayLight2"},
                {"name": "Contacted", "color": "blueLight2"},
                {"name": "Replied", "color": "greenLight2"},
                {"name": "No Response", "color": "yellowLight2"},
                {"name": "Not Interested", "color": "redLight2"},
                {"name": "Converted", "color": "purpleLight2"},
            ]}},
            {"name": "Instantly Campaign ID", "type": "singleLineText"},
            {"name": "Notes", "type": "multilineText"},
        ]
    },
    {
        "name": "B2B Leads",
        "fields": [
            {"name": "Company", "type": "singleLineText"},
            {"name": "Contact Name", "type": "singleLineText"},
            {"name": "Email", "type": "email"},
            {"name": "Title / Role", "type": "singleLineText"},
            {"name": "Phone", "type": "phoneNumber"},
            {"name": "Location", "type": "singleLineText"},
            {"name": "Source", "type": "singleSelect", "options": {"choices": [
                {"name": "LinkedIn", "color": "blueLight2"},
                {"name": "Google Maps", "color": "greenLight2"},
                {"name": "Apollo", "color": "purpleLight2"},
                {"name": "Manual", "color": "grayLight2"},
            ]}},
            {"name": "Industry", "type": "singleLineText"},
            {"name": "Lead Score", "type": "number", "options": {"precision": 0}},
            {"name": "Status", "type": "singleSelect", "options": {"choices": [
                {"name": "Raw", "color": "grayLight2"},
                {"name": "Verified", "color": "blueLight2"},
                {"name": "Contacted", "color": "yellowLight2"},
                {"name": "Replied", "color": "greenLight2"},
                {"name": "Qualified", "color": "purpleLight2"},
                {"name": "Not Interested", "color": "redLight2"},
                {"name": "Customer", "color": "greenBright"},
            ]}},
            {"name": "Notes", "type": "multilineText"},
            {"name": "Date Added", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
        ]
    },
    {
        "name": "Social Mining Queue",
        "fields": [
            {"name": "Post Title", "type": "singleLineText"},
            {"name": "Platform", "type": "singleSelect", "options": {"choices": [
                {"name": "Reddit", "color": "orangeLight2"},
                {"name": "Instagram", "color": "pinkLight2"},
                {"name": "Facebook", "color": "blueLight2"},
            ]}},
            {"name": "Post URL", "type": "url"},
            {"name": "Post Body Preview", "type": "multilineText"},
            {"name": "Author", "type": "singleLineText"},
            {"name": "Subreddit/Account", "type": "singleLineText"},
            {"name": "Engagement Score", "type": "number", "options": {"precision": 0}},
            {"name": "Comment Count", "type": "number", "options": {"precision": 0}},
            {"name": "Keyword Match", "type": "singleLineText"},
            {"name": "Relevance Score", "type": "number", "options": {"precision": 1}},
            {"name": "Found Date", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
            {"name": "Status", "type": "singleSelect", "options": {"choices": [
                {"name": "New", "color": "yellowLight2"},
                {"name": "Drafted", "color": "blueLight2"},
                {"name": "Approved", "color": "greenLight2"},
                {"name": "Skipped", "color": "grayLight2"},
                {"name": "Expired", "color": "redLight2"},
            ]}},
            {"name": "Notes", "type": "multilineText"},
        ]
    },
    {
        "name": "Social Mining Drafts",
        "fields": [
            {"name": "Queue Record ID", "type": "singleLineText"},
            {"name": "Platform", "type": "singleSelect", "options": {"choices": [
                {"name": "Reddit", "color": "orangeLight2"},
                {"name": "Instagram", "color": "pinkLight2"},
                {"name": "Facebook", "color": "blueLight2"},
            ]}},
            {"name": "Draft Response", "type": "multilineText"},
            {"name": "Astrology Data Used", "type": "multilineText"},
            {"name": "Is Follow-Up", "type": "checkbox", "options": {"color": "greenBright", "icon": "check"}},
            {"name": "Parent Comment URL", "type": "url"},
            {"name": "Thread Depth", "type": "number", "options": {"precision": 0}},
            {"name": "Contains CTA", "type": "checkbox", "options": {"color": "redBright", "icon": "check"}},
            {"name": "Status", "type": "singleSelect", "options": {"choices": [
                {"name": "Draft", "color": "yellowLight2"},
                {"name": "Ready", "color": "blueLight2"},
                {"name": "Posted", "color": "greenLight2"},
                {"name": "Skipped", "color": "grayLight2"},
            ]}},
            {"name": "Posted Date", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
            {"name": "Posted By", "type": "singleSelect", "options": {"choices": [
                {"name": "Agent", "color": "purpleLight2"},
                {"name": "VA", "color": "blueLight2"},
                {"name": "Jon", "color": "greenLight2"},
            ]}},
            {"name": "Response Permalink", "type": "url"},
            {"name": "Log Record ID", "type": "singleLineText"},
            {"name": "Notes", "type": "multilineText"},
        ]
    },
    {
        "name": "Social Mining Log",
        "fields": [
            {"name": "Draft Record ID", "type": "singleLineText"},
            {"name": "Queue Record ID", "type": "singleLineText"},
            {"name": "Platform", "type": "singleSelect", "options": {"choices": [
                {"name": "Reddit", "color": "orangeLight2"},
                {"name": "Instagram", "color": "pinkLight2"},
                {"name": "Facebook", "color": "blueLight2"},
            ]}},
            {"name": "Original Post URL", "type": "url"},
            {"name": "Response Permalink", "type": "url"},
            {"name": "Posted By", "type": "singleSelect", "options": {"choices": [
                {"name": "Agent", "color": "purpleLight2"},
                {"name": "VA", "color": "blueLight2"},
                {"name": "Jon", "color": "greenLight2"},
            ]}},
            {"name": "Posted Date", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
            {"name": "Upvotes", "type": "number", "options": {"precision": 0}},
            {"name": "Reply Count", "type": "number", "options": {"precision": 0}},
            {"name": "Follow-Up Needed", "type": "checkbox", "options": {"color": "yellowBright", "icon": "check"}},
            {"name": "Follow-Up Done", "type": "checkbox", "options": {"color": "greenBright", "icon": "check"}},
            {"name": "Follow-Up Count", "type": "number", "options": {"precision": 0}},
            {"name": "Conversation Status", "type": "singleSelect", "options": {"choices": [
                {"name": "Active", "color": "greenLight2"},
                {"name": "Complete", "color": "blueLight2"},
                {"name": "Expired", "color": "grayLight2"},
            ]}},
            {"name": "Last Checked", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
            {"name": "Days Monitored", "type": "number", "options": {"precision": 0}},
            {"name": "Notes", "type": "multilineText"},
        ]
    },
    {
        "name": "GSC Opportunities",
        "fields": [
            {"name": "Date", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
            {"name": "Brand", "type": "singleLineText"},
            {"name": "Type", "type": "singleSelect", "options": {"choices": [
                {"name": "CTR-Rewrite", "color": "blueLight2"},
                {"name": "Content-Refresh", "color": "purpleLight2"},
                {"name": "Brand-Defense", "color": "redLight2"},
            ]}},
            {"name": "Page URL", "type": "url"},
            {"name": "Target Query", "type": "singleLineText"},
            {"name": "Current Title", "type": "singleLineText"},
            {"name": "Current Description", "type": "multilineText"},
            {"name": "Current CTR", "type": "number", "options": {"precision": 4}},
            {"name": "Current Position", "type": "number", "options": {"precision": 1}},
            {"name": "Impressions", "type": "number", "options": {"precision": 0}},
            {"name": "Suggested Action", "type": "multilineText"},
            {"name": "Suggested Title", "type": "singleLineText"},
            {"name": "Suggested Description", "type": "multilineText"},
            {"name": "Confidence", "type": "number", "options": {"precision": 2}},
            {"name": "Status", "type": "singleSelect", "options": {"choices": [
                {"name": "Pending Review", "color": "yellowLight2"},
                {"name": "Auto-Applied", "color": "greenLight2"},
                {"name": "Skipped", "color": "grayLight2"},
                {"name": "Apply-Failed", "color": "redLight2"},
                {"name": "Rolled-Back", "color": "orangeLight2"},
            ]}},
            {"name": "Notes", "type": "multilineText"},
            {"name": "Snapshot Path", "type": "singleLineText"},
        ]
    },
    {
        "name": "GA4 Insights",
        "fields": [
            {"name": "Date", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
            {"name": "Brand", "type": "singleLineText"},
            {"name": "Source/Medium", "type": "singleLineText"},
            {"name": "Sessions", "type": "number", "options": {"precision": 0}},
            {"name": "Sessions Prior 30d", "type": "number", "options": {"precision": 0}},
            {"name": "Conversions", "type": "number", "options": {"precision": 0}},
            {"name": "Conversions Prior 30d", "type": "number", "options": {"precision": 0}},
            {"name": "Trend", "type": "singleSelect", "options": {"choices": [
                {"name": "Up", "color": "greenLight2"},
                {"name": "Flat", "color": "grayLight2"},
                {"name": "Down", "color": "redLight2"},
            ]}},
            {"name": "Notes", "type": "multilineText"},
        ]
    },
]

# ─── MAIN ─────────────────────────────────────────────────────────────────────

# Map human-friendly table names to .env var names
ENV_VAR_MAP = {
    "Keywords": "AIRTABLE_KEYWORDS_TABLE",
    "Content Calendar": "AIRTABLE_CONTENT_TABLE",
    "Research": "AIRTABLE_RESEARCH_TABLE",
    "Generated Images": "AIRTABLE_GENERATED_IMAGES_TABLE",
    "Reference Images": "AIRTABLE_REFERENCE_IMAGES_TABLE",
    "Leads": "AIRTABLE_LEADS_TABLE",
    "B2B Queries": "AIRTABLE_B2B_QUERIES_TABLE",
    "Published Posts": "AIRTABLE_PUBLISHED_POSTS_TABLE",
    "Social Queue": "AIRTABLE_SOCIAL_QUEUE_TABLE",
    "Social Posts Log": "AIRTABLE_SOCIAL_POSTS_LOG_TABLE",
    "Newsletter Queue": "AIRTABLE_NEWSLETTER_QUEUE_TABLE",
    "Newsletter Log": "AIRTABLE_NEWSLETTER_LOG_TABLE",
    "Market Intelligence": "AIRTABLE_MARKET_INTEL_TABLE",
    "Outreach Queries": "AIRTABLE_OUTREACH_QUERIES_TABLE",
    "Outreach Leads": "AIRTABLE_OUTREACH_LEADS_TABLE",
    "B2B Leads": "AIRTABLE_B2B_LEADS_TABLE",
    "Social Mining Queue": "AIRTABLE_SOCIAL_MINING_QUEUE_TABLE",
    "Social Mining Drafts": "AIRTABLE_SOCIAL_MINING_DRAFTS_TABLE",
    "Social Mining Log": "AIRTABLE_SOCIAL_MINING_LOG_TABLE",
    "GSC Opportunities": "AIRTABLE_GSC_OPPORTUNITIES_TABLE",
    "GA4 Insights": "AIRTABLE_GA4_INSIGHTS_TABLE",
}

def main():
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        print("ERROR: AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set in environment.")
        sys.exit(1)

    print(f"Connecting to base: {AIRTABLE_BASE_ID}")
    existing = get_existing_tables()
    print(f"Found {len(existing)} existing tables.")
    print()

    created = 0
    skipped = 0

    for table in TABLES:
        if table["name"] in existing:
            print(f"  SKIP: {table['name']} already exists")
            skipped += 1
        else:
            success = create_table(table["name"], table["fields"])
            if success:
                created += 1

    print()
    print(f"Done. Created: {created} | Skipped: {skipped}")
    print()

    # Re-fetch after creation, then emit .env block
    final = get_existing_tables()
    print("─── Copy this block into your .env file ───")
    print()
    for table in TABLES:
        env_var = ENV_VAR_MAP.get(table["name"])
        table_id = final.get(table["name"])
        if env_var and table_id:
            print(f"{env_var}={table_id}")
    print()
    print("───────────────────────────────────────────")

if __name__ == "__main__":
    main()
