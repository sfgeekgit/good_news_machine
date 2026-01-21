# Good News Machine

### THIS PITCH FILE IS A DEMO of what the END RESULT of this project might look like. This was written before anything else, so it might not be 100% accurate. When in doubt, assume the project has changed since this draft was written.


## Inspiration

Progress is happening all the time — but it doesn't make headlines.

Media incentives favor crisis, conflict, and decline. Meanwhile, child mortality drops, literacy rises, poverty falls, and clean energy expands — and almost nobody notices.

We wanted to build something that finds these stories automatically.

## What it does

The Good News Machine scans decades of global development data to surface statistically significant improvements that flew under the radar.

Think of it as a newsfeed for human progress.

For each country and indicator, we detect:

- sustained positive trends
- acceleration in improvement
- milestone crossings (e.g., "child mortality fell below 50 per 1,000 for the first time")

Users can explore:

- a global feed of recent "discoveries"
- country deep-dives showing all improving indicators
- indicator views showing which countries are improving fastest
- the methodology behind each detected trend

## How we built it

We used:

- Our World in Data long-run development datasets (child mortality, life expectancy, poverty, literacy, clean energy, electricity access, and more)
- Hex SQL and Python notebooks for data processing and trend detection
- Statistical methods (linear regression, threshold detection) to identify meaningful improvement
- Hex AI to generate natural-language summaries of detected trends
- Hex's app builder to create an interactive feed and explorer

The entire pipeline lives in a single reproducible Hex project.

## Key insights

The data shows that:

- dozens of countries have halved child mortality in the last 20 years
- extreme poverty has fallen to historic lows in regions that rarely make the news
- clean energy adoption is accelerating faster than most people realize
- many improvements are invisible simply because no one is looking

Progress is uneven — but it's persistent, and it's measurable.

## Why it matters

Public perception shapes policy, funding, and hope.

When people believe nothing is improving, they disengage. When they see evidence of progress, they invest in more of it.

The Good News Machine:

- counters doom-scrolling with data
- gives journalists and educators ready-made stories
- helps decision-makers identify what's working
- reminds us that effort compounds

## What's next

- Add automated refresh when OWID datasets update
- Expand to more indicators (sanitation, vaccination, maternal mortality)
- Build email/RSS alerts for new milestone crossings
- Enable user-submitted "good news hunts" for custom indicators
