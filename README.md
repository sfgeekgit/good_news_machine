# Good News Machine

**Find the positive trends hiding in global development data.**

A tool that scans decades of Our World in Data indicators to detect:
- **Sustained positive trends** (statistically significant improvement over 10+ years)
- **Milestone crossings** (first time a country crosses a meaningful threshold)

Then outputs a "news feed" of human progress stories.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the analysis
python good_news_machine.py

# 3. Check the output
cat good_news.json
```

## Output

The script produces:
- `good_news.json` — Array of news stories ready for visualization
- Console summary of top findings

Each story looks like:
```json
{
  "type": "milestone",
  "country": "Ethiopia",
  "indicator": "child_mortality",
  "headline": "Ethiopia's child mortality fell below 50 per 1,000 for the first time",
  "detail": "Crossed from 52.3 to 48.1 deaths per 1,000 live births",
  "year": 2021,
  ...
}
```

## Adding More Indicators

The MVP includes 5 indicators. To add more:

1. Open `owid_data_sources.md` for the full list of 50+ indicators
2. Find the OWID dataset URL (click "Download" on any OWID chart)
3. Add an entry to the `INDICATORS` list in `good_news_machine.py`:

```python
{
    "name": "your_indicator_id",
    "display_name": "human readable name",
    "url": "https://raw.githubusercontent.com/owid/...",
    "value_column": "Exact Column Name From CSV",
    "good_direction": "down",  # or "up"
    "milestones": [50, 25, 10],  # thresholds that matter
    "milestone_templates": {
        50: "{country} crossed the 50 mark for the first time",
        # ...
    },
    "unit": "per 1,000 people",
}
```

## Configuration

Key parameters at the top of `good_news_machine.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MIN_YEARS_FOR_TREND` | 10 | Minimum years of data to detect a trend |
| `P_VALUE_THRESHOLD` | 0.05 | Statistical significance threshold |
| `MIN_R_SQUARED` | 0.5 | Minimum trend strength |
| `MILESTONE_RECENCY_YEARS` | 10 | How recent must a milestone be |

## Command Line Options

```bash
# Normal run (uses cached data if available)
python good_news_machine.py

# Force re-download all data
python good_news_machine.py --refresh
```

## Moving to Hex

When ready to move this into Hex:

1. Create a new Hex project
2. Copy the imports and config into the first cell
3. Copy each function into its own cell (or group related ones)
4. Run the cells top-to-bottom
5. Use Hex's visualization tools to display the results
6. Add interactive widgets (country selector, indicator filter, etc.)

## Files

```
good_news_machine/
├── good_news_machine.py   # Main script
├── requirements.txt       # Python dependencies
├── owid_data_sources.md   # Reference: 50+ indicators to add
├── good_news_machine_pitch.md  # Hackathon submission pitch
├── data/                  # Downloaded CSVs (auto-created)
└── good_news.json         # Output (auto-created)
```

## License

Built for the Hex-a-thon hackathon. Use freely.
