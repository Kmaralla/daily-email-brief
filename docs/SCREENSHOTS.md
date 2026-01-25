# Screenshots Guide

This document describes the screenshots needed for the README.

## Required Screenshots

### 1. Dashboard Main View (`dashboard.png` or `dashboard-main.png`)
**Location:** Main dashboard page after setup
**What to capture:**
- Header with "Daily Email Brief Dashboard"
- Action buttons: Fetch Emails, Score Emails, Generate Brief
- Daily brief section (if available)
- Email list with importance scores
- Statistics panel

**How to take:**
1. Run `python main.py`
2. Complete setup and onboarding
3. Navigate to dashboard
4. Take full-page screenshot

### 2. Onboarding Flow (`onboarding.png`)
**Location:** Onboarding page during setup
**What to capture:**
- OAuth setup instructions
- Or email training interface (10 emails to review)
- Progress bar
- Step indicators

**How to take:**
1. Fresh install (or reset credentials)
2. Run `python main.py`
3. Navigate through onboarding
4. Capture the training interface

### 3. Email Training Interface (`training.png`)
**Location:** Email training page
**What to capture:**
- List of 10 sample emails
- Important/Not Important buttons
- Progress indicator
- Category labels

**How to take:**
1. Complete OAuth setup
2. Reach email training step
3. Capture the training interface

### 4. Preferences Page (`preferences.png`)
**Location:** Preferences configuration page
**What to capture:**
- Important senders section
- Brief settings
- Delivery preferences
- Form fields

**How to take:**
1. Navigate to `/preferences`
2. Capture the full preferences form

### 5. Daily Brief Example (`brief.png` or `brief-preview.png`)
**Location:** Dashboard after generating brief
**What to capture:**
- Generated brief text
- Statistics panel
- Email breakdown by category
- Top emails highlighted

**How to take:**
1. Fetch and score emails
2. Generate brief
3. Capture the brief display

### 6. Scoring View (`scoring.png`)
**Location:** Dashboard showing email scores
**What to capture:**
- Email list with importance scores
- Color-coded score badges
- Sorted by importance

**How to take:**
1. After scoring emails
2. Show the email list view
3. Highlight the scoring system

## Screenshot Specifications

- **Format:** PNG or JPG
- **Size:** Recommended 1200x800px or larger
- **Quality:** High resolution, clear text
- **Browser:** Use Chrome or Safari for best appearance
- **Theme:** Light mode (default)

## Adding Screenshots

1. Take screenshots using your browser's developer tools or screenshot tool
2. Save to `docs/screenshots/` directory
3. Name files as specified above
4. Update README.md to reference the actual files

## Alternative: Using Placeholder Services

If you don't have screenshots yet, you can:
- Use placeholder services like `https://via.placeholder.com/1200x800`
- Create mockups using design tools
- Use ASCII art diagrams (already included in README)

## Tips for Great Screenshots

1. **Clean State:** Use a fresh setup or anonymized data
2. **Highlight Features:** Use browser dev tools to highlight important elements
3. **Consistent Styling:** Use the same browser and zoom level
4. **Annotate:** Add arrows or labels to point out key features
5. **Multiple Views:** Show different states (empty, populated, etc.)
