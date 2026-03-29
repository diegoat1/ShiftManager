# Share Workflow

This document describes the practical workflow for sharing ShiftManager with someone who may be interested in the product.

## Objective

Share a live link that lets the recipient understand, in a few minutes:

- what the product does
- which problem it solves
- what the current experience already covers
- why the matching and assignment logic is useful

## Important Constraint

In the current codebase there is no login gate in front of the main UI flow. Because of that:

- only share a demo or controlled environment
- do not share a production database publicly
- assume that anyone with the URL can browse the available demo data and actions

## Recommended Sharing Setup

Use a deployed Railway environment as the shareable demo.

Before sending the link, confirm:

1. the app is deployed successfully
2. `https://your-domain/health` returns `{"status":"ok"}`
3. `https://your-domain/` opens correctly
4. the dashboard loads data
5. the calendar has visible shifts

If the database was fresh at deploy time, the app should auto-seed demo data and generate a ready-to-show dataset.

## Which Link To Share

Use one of these depending on the conversation:

- General intro: `https://your-domain/`
- Doctor management angle: `https://your-domain/#/medici`
- Institution/network angle: `https://your-domain/#/strutture`
- Best product demo angle: `https://your-domain/#/calendario`

### Best default choice

If you only send one link, use:

`https://your-domain/#/calendario`

Reason:

- it shows the operational value fastest
- it makes the shift volume visible
- it exposes the eligibility and ranking modal
- it demonstrates actual assignment, not just data storage

## Suggested Demo Narrative

When the recipient opens the link, guide them through this order:

1. Dashboard
2. Institutions
3. Calendar
4. Shift modal
5. Eligible doctors and assignment ranking

### 1. Dashboard

Use it to explain:

- how many doctors and institutions exist
- how many monthly shifts are present
- how many shifts are still incomplete

### 2. Institutions

Use it to show:

- the healthcare structure types
- multiple sites per institution
- site-level operational constraints

### 3. Calendar

Select a site and show:

- monthly coverage
- open vs partially filled vs filled shifts
- the fact that the system is operationally organized by site

### 4. Shift modal

Open a shift and show:

- required doctors
- current assignments
- pay
- timing
- status

### 5. Ranking and assignment

This is the strongest demo moment. Show that:

- the system filters out ineligible doctors
- remaining doctors are ranked
- the ranking is explainable through a score breakdown
- assignments update the shift status

## Outbound Message Template

You can send something like this with the link:

```text
Ti condivido una demo di ShiftManager, uno strumento per gestire turni medici e assegnazioni per strutture sanitarie.

Qui puoi vedere:
- anagrafica medici e strutture
- calendario turni per sede
- controllo eleggibilita dei medici
- ranking automatico dei candidati per ogni turno

Link demo:
https://your-domain/#/calendario
```

## Workflow To Share With An Interested Person

1. Deploy or identify the demo environment you want to expose.
2. Verify `/health`, root load, and seeded demo data.
3. Decide the entry link based on the audience.
4. Send a short message explaining what they should look at first.
5. If possible, guide them to open one shift from the calendar.
6. Show the eligible-doctor ranking and explain why one doctor appears above another.
7. Collect feedback on:
   - data completeness
   - assignment rules
   - usability
   - missing controls
8. After the conversation, note whether the next step is:
   - pilot
   - custom workflow discussion
   - authentication and permissions
   - production hardening

## Audience-Specific Link Strategy

### For a clinic or healthcare operator

Send:

- `/#/calendario`

Focus on:

- coverage
- open shifts
- assignment speed
- rule-based matching

### For an operations manager

Send:

- `/`
- then direct them to `/#/calendario`

Focus on:

- dashboard summary
- incomplete shifts
- site-by-site planning

### For a technical stakeholder

Send:

- `/`

Explain briefly that:

- frontend and API are in the same deployment
- matching is rule-based and explainable
- the dataset is auto-generated on empty environments

## Pre-Send Checklist

- Demo environment is not pointing to sensitive real data
- Health endpoint is green
- Dashboard counts are visible
- At least one site has shifts in the calendar
- At least one shift opens its modal correctly
- Eligible doctors appear for at least one shift
- You are comfortable with the lack of login in the current version

## Recommended Follow-Up After Sharing

After someone reviews the link, the most useful follow-up questions are:

- Which user role do you imagine using this first?
- Which assignment rules are mandatory in your context?
- Would you need approval workflows before confirming an assignment?
- Do you need private access per organization or per branch?
- Would you use this first as a planning tool, a marketplace, or an internal scheduler?
