# md-to-gdoc — Setup Guide

## Table of Contents

- [Prerequisites](#prerequisites)
- [Step 1 — Install the gws CLI](#step-1--install-the-gws-cli)
- [Step 2 — Create a GCP Project and Enable APIs](#step-2--create-a-gcp-project-and-enable-apis)
- [Step 3 — Create OAuth Credentials](#step-3--create-oauth-credentials)
- [Step 4 — Authenticate](#step-4--authenticate)
- [Verify Installation](#verify-installation)
- [Troubleshooting](#troubleshooting)

## Prerequisites

- Node.js (for `npm install`)
- A Google Cloud Platform account
- A browser for OAuth consent

## Step 1 — Install the gws CLI

```bash
npm install -g @googleworkspace/cli
```

Verify: `which gws`

## Step 2 — Create a GCP Project and Enable APIs

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project (or use an existing one)
3. Navigate to **APIs & Services > Library**
4. Enable **Google Docs API**
5. Enable **Google Drive API**

## Step 3 — Create OAuth Credentials

1. In the GCP Console, go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Select **Desktop app** as the application type
4. Download the client secret JSON file
5. Save it to the gws config directory:

```bash
mkdir -p ~/.config/gws
cp ~/Downloads/client_secret_*.json ~/.config/gws/client_secret.json
```

## Step 4 — Authenticate

```bash
gws auth login
```

This opens a browser window for Google OAuth consent.

> **Note:** If `gws auth setup` fails with a port-binding error, skip it and use `gws auth login` directly — it uses a different callback port that avoids the issue.

## Verify Installation

Test with a simple markdown file:

```
/md-to-gdoc:md-to-gdoc test.md
```

It should create a Google Doc and return the URL.

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `gws: command not found` | CLI not installed | Run `npm install -g @googleworkspace/cli` |
| `invalid_grant` error | Auth token expired | Run `gws auth login` again |
| Port-binding error during auth | `gws auth setup` localhost conflict | Use `gws auth login` instead (different port) |
| API not enabled | Docs/Drive API not turned on | Enable both APIs in GCP Console (Step 2) |
| Permission denied | OAuth scope insufficient | Re-authenticate with `gws auth login` |
