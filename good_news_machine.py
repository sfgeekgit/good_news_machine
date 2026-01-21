#!/usr/bin/env python3
"""
Good News Machine - MVP
=======================

Scans global development indicators to detect positive trends and milestone
crossings, then outputs a "news feed" of human progress stories.

Usage:
    python good_news_machine.py

Output:
    - good_news.json: Array of detected good news stories
    - Console summary of findings

Requirements:
    pip install pandas scipy requests

Expanding to more indicators:
    1. Look at owid_data_sources.md for the full list of 50+ indicators
    2. Add a new entry to the INDICATORS list below
    3. Run the script again

Author: Built for Hex-a-thon hackathon
"""

import json
import os
from datetime import datetime
from dataclasses import dataclass
from typing import Literal

import pandas as pd
import requests
from scipy import stats

# =============================================================================
# CONFIGURATION
# =============================================================================

# Directory to cache downloaded data (will be created if it doesn't exist)
DATA_DIR = "data"

# Output file for the news feed
OUTPUT_FILE = "good_news.json"

# Minimum years of data required to detect a trend
MIN_YEARS_FOR_TREND = 10

# P-value threshold for statistical significance
P_VALUE_THRESHOLD = 0.05

# Minimum R-squared to consider a trend "strong"
MIN_R_SQUARED = 0.5

# How recent must a milestone be to count as "news"? (years)
MILESTONE_RECENCY_YEARS = 10


# =============================================================================
# INDICATOR DEFINITIONS
# =============================================================================
#
# Each indicator needs:
#   - name: Short identifier (used in output)
#   - display_name: Human-readable name for headlines
#   - url: Direct link to OWID CSV download
#   - value_column: Name of the column containing the metric
#   - good_direction: "down" if lower is better, "up" if higher is better
#   - milestones: List of thresholds that count as newsworthy crossings
#   - milestone_templates: Dict mapping milestone values to headline templates
#   - unit: For display (e.g., "per 1,000 live births")
#
# To add more indicators:
#   1. Find the dataset on ourworldindata.org
#   2. Click "Download" tab, copy the GitHub CSV link
#   3. Open the CSV to find the exact column name for the metric
#   4. Add an entry following the pattern below
#

INDICATORS = [
    # =========================================================================
    # HOW TO ADD MORE INDICATORS:
    # 
    # 1. Go to any OWID chart page (e.g., ourworldindata.org/grapher/child-mortality)
    # 2. The CSV URL is just: https://ourworldindata.org/grapher/[chart-name].csv
    # 3. Download the CSV and check the column names
    # 4. Add an entry below following this pattern
    # 
    # See owid_data_sources.md for 50+ indicator ideas with chart names
    # =========================================================================
    {
        "name": "child_mortality",
        "display_name": "child mortality rate",
        "url": "https://ourworldindata.org/grapher/child-mortality.csv",
        "value_column": "Child mortality rate",
        "good_direction": "down",
        "milestones": [10, 5, 2.5, 1],  # deaths per 100 live births (i.e., 100, 50, 25, 10 per 1,000)
        "milestone_templates": {
            10: "{country}'s child mortality fell below 100 per 1,000 for the first time",
            5: "{country}'s child mortality fell below 50 per 1,000 for the first time",
            2.5: "{country}'s child mortality fell below 25 per 1,000 for the first time",
            1: "{country} achieved under 10 per 1,000 child mortality for the first time",
        },
        "unit": "deaths per 100 live births",
    },
    {
        "name": "life_expectancy",
        "display_name": "life expectancy",
        "url": "https://ourworldindata.org/grapher/life-expectancy.csv",
        "value_column": "Period life expectancy at birth",
        "good_direction": "up",
        "milestones": [60, 70, 75, 80],  # years
        "milestone_templates": {
            60: "{country}'s life expectancy rose above 60 years for the first time",
            70: "{country}'s life expectancy rose above 70 years for the first time",
            75: "{country}'s life expectancy rose above 75 years for the first time",
            80: "{country}'s life expectancy rose above 80 years for the first time",
        },
        "unit": "years",
    },
    {
        "name": "extreme_poverty",
        "display_name": "extreme poverty rate",
        "url": "https://ourworldindata.org/grapher/share-of-population-in-extreme-poverty.csv",
        "value_column": "Share of population in poverty ($3 a day, 2021 prices)",
        "good_direction": "down",
        "milestones": [50, 25, 10, 5],  # percent
        "milestone_templates": {
            50: "{country} reduced extreme poverty below 50% for the first time",
            25: "{country} reduced extreme poverty below 25% for the first time",
            10: "{country} reduced extreme poverty to single digits for the first time",
            5: "{country} nearly eliminated extreme poverty (below 5%)",
        },
        "unit": "% of population",
    },
    {
        "name": "literacy",
        "display_name": "literacy rate",
        "url": "https://ourworldindata.org/grapher/cross-country-literacy-rates.csv",
        "value_column": "Literacy rate",
        "good_direction": "up",
        "milestones": [50, 75, 90, 95],  # percent
        "milestone_templates": {
            50: "Majority of {country}'s adults can now read and write",
            75: "{country}'s literacy rate rose above 75% for the first time",
            90: "{country} achieved near-universal literacy (above 90%)",
            95: "{country} achieved 95%+ literacy rate",
        },
        "unit": "% of adults",
    },
    {
        "name": "electricity_access",
        "display_name": "electricity access",
        "url": "https://ourworldindata.org/grapher/share-of-the-population-with-access-to-electricity.csv",
        "value_column": "Access to electricity (% of population)",
        "good_direction": "up",
        "milestones": [50, 75, 90, 99],  # percent
        "milestone_templates": {
            50: "Majority of {country}'s population now has electricity",
            75: "{country}'s electricity access rose above 75% for the first time",
            90: "{country} achieved near-universal electricity access (above 90%)",
            99: "{country} achieved universal electricity access",
        },
        "unit": "% of population",
    },
]


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TrendResult:
    """Result of trend analysis for one country/indicator pair."""
    country: str
    indicator: str
    display_name: str
    direction: Literal["improving", "worsening", "flat"]
    slope: float
    p_value: float
    r_squared: float
    start_year: int
    end_year: int
    start_value: float
    end_value: float
    percent_change: float
    unit: str


@dataclass
class MilestoneResult:
    """Result of milestone detection for one country/indicator pair."""
    country: str
    indicator: str
    display_name: str
    milestone_value: float
    crossed_year: int
    headline: str
    previous_value: float
    new_value: float
    unit: str


# =============================================================================
# DATA FETCHING
# =============================================================================

def ensure_data_dir():
    """Create data directory if it doesn't exist."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created directory: {DATA_DIR}")


def download_dataset(indicator: dict, force_refresh: bool = False) -> pd.DataFrame:
    """
    Download a dataset from OWID, with local caching.
    
    Args:
        indicator: Indicator config dictionary
        force_refresh: If True, re-download even if cached
        
    Returns:
        DataFrame with the dataset
    """
    ensure_data_dir()
    
    cache_path = os.path.join(DATA_DIR, f"{indicator['name']}.csv")
    
    # Use cached version if available and not forcing refresh
    if os.path.exists(cache_path) and not force_refresh:
        print(f"  Loading cached: {indicator['name']}")
        return pd.read_csv(cache_path)
    
    # Download fresh
    print(f"  Downloading: {indicator['name']}...")
    try:
        response = requests.get(indicator["url"], timeout=30)
        response.raise_for_status()
        
        # Save to cache
        with open(cache_path, "wb") as f:
            f.write(response.content)
        
        return pd.read_csv(cache_path)
    
    except requests.RequestException as e:
        print(f"  ERROR downloading {indicator['name']}: {e}")
        return None


def load_all_datasets(force_refresh: bool = False) -> dict:
    """
    Load all configured indicator datasets.
    
    Returns:
        Dict mapping indicator name to DataFrame
    """
    print("\n📥 Loading datasets...")
    datasets = {}
    
    for indicator in INDICATORS:
        df = download_dataset(indicator, force_refresh)
        if df is not None:
            datasets[indicator["name"]] = df
    
    print(f"  Loaded {len(datasets)}/{len(INDICATORS)} datasets\n")
    return datasets


# =============================================================================
# DATA CLEANING
# =============================================================================

def clean_dataset(df: pd.DataFrame, indicator: dict) -> pd.DataFrame:
    """
    Standardize dataset format for analysis.
    
    OWID datasets have varying column names. This function normalizes them.
    
    Args:
        df: Raw DataFrame from OWID
        indicator: Indicator config dictionary
        
    Returns:
        Cleaned DataFrame with columns: country, year, value
    """
    df = df.copy()
    
    # Find the country column (OWID uses "Entity" or "Country")
    country_col = None
    for col in ["Entity", "Country", "country", "entity"]:
        if col in df.columns:
            country_col = col
            break
    
    if country_col is None:
        print(f"  WARNING: No country column found in {indicator['name']}")
        print(f"  Available columns: {list(df.columns)}")
        return None
    
    # Find the year column
    year_col = None
    for col in ["Year", "year", "date", "Date"]:
        if col in df.columns:
            year_col = col
            break
    
    if year_col is None:
        print(f"  WARNING: No year column found in {indicator['name']}")
        print(f"  Available columns: {list(df.columns)}")
        return None
    
    # Find the value column
    value_col = indicator["value_column"]
    if value_col not in df.columns:
        # Try to find a partial match (OWID column names can be very long)
        partial_matches = [c for c in df.columns if value_col.lower() in c.lower()]
        if partial_matches:
            print(f"  NOTE: Exact column '{value_col}' not found, using partial match: '{partial_matches[0]}'")
            value_col = partial_matches[0]
        else:
            print(f"  WARNING: Column '{value_col}' not found in {indicator['name']}")
            print(f"  Available columns:")
            for col in df.columns:
                print(f"    - {col}")
            print(f"\n  TIP: Update the 'value_column' field in the INDICATORS config")
            return None
    
    # Build clean dataframe
    clean_df = pd.DataFrame({
        "country": df[country_col],
        "year": pd.to_numeric(df[year_col], errors="coerce"),
        "value": pd.to_numeric(df[value_col], errors="coerce"),
    })
    
    # Remove rows with missing data
    clean_df = clean_df.dropna()
    
    # Remove aggregate regions (keep only countries)
    # OWID includes things like "World", "Africa", "High income", etc.
    aggregates = [
        "World", "Africa", "Asia", "Europe", "North America", "South America",
        "Oceania", "European Union", "High income", "Low income", "Middle income",
        "Upper middle income", "Lower middle income", "OECD", "G20",
        "Latin America and the Caribbean", "Sub-Saharan Africa",
        "East Asia and Pacific", "Middle East and North Africa",
        "South Asia", "Europe and Central Asia", "North America (WB)",
        "African Union", "Americas (WHO)", "Eastern Mediterranean (WHO)",
        "Europe (WHO)", "South-East Asia (WHO)", "Western Pacific (WHO)",
    ]
    clean_df = clean_df[~clean_df["country"].isin(aggregates)]
    
    # Sort by country and year
    clean_df = clean_df.sort_values(["country", "year"]).reset_index(drop=True)
    
    return clean_df


# =============================================================================
# TREND DETECTION
# =============================================================================

def detect_trend(country_data: pd.DataFrame, indicator: dict) -> TrendResult | None:
    """
    Detect if a country shows a statistically significant improving trend.
    
    Uses linear regression over the most recent data period.
    
    Args:
        country_data: DataFrame with year and value columns for one country
        indicator: Indicator config dictionary
        
    Returns:
        TrendResult if significant trend found, None otherwise
    """
    if len(country_data) < MIN_YEARS_FOR_TREND:
        return None
    
    # Use most recent contiguous data
    country_data = country_data.sort_values("year")
    
    # Get recent window (last N years of available data)
    recent = country_data.tail(MIN_YEARS_FOR_TREND)
    
    years = recent["year"].values
    values = recent["value"].values
    
    # Perform linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(years, values)
    r_squared = r_value ** 2
    
    # Determine if trend is improving
    good_direction = indicator["good_direction"]
    if good_direction == "down":
        is_improving = slope < 0
    else:  # up
        is_improving = slope > 0
    
    # Check statistical significance
    if p_value > P_VALUE_THRESHOLD:
        return None  # Not statistically significant
    
    if r_squared < MIN_R_SQUARED:
        return None  # Trend not strong enough
    
    if not is_improving:
        return None  # Trend is in wrong direction (not good news)
    
    # Calculate percent change
    start_value = values[0]
    end_value = values[-1]
    if start_value != 0:
        percent_change = ((end_value - start_value) / abs(start_value)) * 100
    else:
        percent_change = 0
    
    return TrendResult(
        country=country_data["country"].iloc[0],
        indicator=indicator["name"],
        display_name=indicator["display_name"],
        direction="improving",
        slope=slope,
        p_value=p_value,
        r_squared=r_squared,
        start_year=int(years[0]),
        end_year=int(years[-1]),
        start_value=start_value,
        end_value=end_value,
        percent_change=percent_change,
        unit=indicator["unit"],
    )


def find_all_trends(df: pd.DataFrame, indicator: dict) -> list[TrendResult]:
    """
    Find all countries with significant improving trends for an indicator.
    
    Args:
        df: Cleaned DataFrame for the indicator
        indicator: Indicator config dictionary
        
    Returns:
        List of TrendResult objects
    """
    results = []
    
    for country in df["country"].unique():
        country_data = df[df["country"] == country]
        trend = detect_trend(country_data, indicator)
        if trend is not None:
            results.append(trend)
    
    # Sort by strength of improvement (percent change)
    results.sort(key=lambda x: abs(x.percent_change), reverse=True)
    
    return results


# =============================================================================
# MILESTONE DETECTION
# =============================================================================

def detect_milestones(country_data: pd.DataFrame, indicator: dict) -> list[MilestoneResult]:
    """
    Detect if a country has crossed any milestone thresholds.
    
    Args:
        country_data: DataFrame with year and value columns for one country
        indicator: Indicator config dictionary
        
    Returns:
        List of MilestoneResult objects for milestones crossed
    """
    results = []
    country = country_data["country"].iloc[0]
    country_data = country_data.sort_values("year")
    
    good_direction = indicator["good_direction"]
    current_year = datetime.now().year
    
    for milestone in indicator["milestones"]:
        # Find when this milestone was crossed
        for i in range(1, len(country_data)):
            prev_row = country_data.iloc[i - 1]
            curr_row = country_data.iloc[i]
            
            prev_value = prev_row["value"]
            curr_value = curr_row["value"]
            year = int(curr_row["year"])
            
            # Check if milestone was crossed in the right direction
            crossed = False
            if good_direction == "down":
                # Good news = value went below milestone
                if prev_value >= milestone > curr_value:
                    crossed = True
            else:  # up
                # Good news = value went above milestone
                if prev_value <= milestone < curr_value:
                    crossed = True
            
            if crossed:
                # Check if recent enough to be "news"
                if current_year - year <= MILESTONE_RECENCY_YEARS:
                    headline_template = indicator["milestone_templates"].get(
                        milestone, 
                        f"{{country}} crossed {milestone} {indicator['unit']} milestone"
                    )
                    headline = headline_template.format(country=country)
                    
                    results.append(MilestoneResult(
                        country=country,
                        indicator=indicator["name"],
                        display_name=indicator["display_name"],
                        milestone_value=milestone,
                        crossed_year=year,
                        headline=headline,
                        previous_value=prev_value,
                        new_value=curr_value,
                        unit=indicator["unit"],
                    ))
                break  # Only count first crossing of each milestone
    
    return results


def find_all_milestones(df: pd.DataFrame, indicator: dict) -> list[MilestoneResult]:
    """
    Find all recent milestone crossings for an indicator.
    
    Args:
        df: Cleaned DataFrame for the indicator
        indicator: Indicator config dictionary
        
    Returns:
        List of MilestoneResult objects
    """
    results = []
    
    for country in df["country"].unique():
        country_data = df[df["country"] == country]
        milestones = detect_milestones(country_data, indicator)
        results.extend(milestones)
    
    # Sort by recency
    results.sort(key=lambda x: x.crossed_year, reverse=True)
    
    return results


# =============================================================================
# STORY GENERATION
# =============================================================================

def trend_to_story(trend: TrendResult) -> dict:
    """Convert a TrendResult to a news story dict."""
    
    # Generate headline
    if trend.percent_change < 0:
        change_word = "fell"
        change_pct = abs(trend.percent_change)
    else:
        change_word = "rose"
        change_pct = trend.percent_change
    
    headline = (
        f"{trend.country}'s {trend.display_name} {change_word} "
        f"{change_pct:.0f}% over {trend.end_year - trend.start_year} years"
    )
    
    # Generate detail
    detail = (
        f"From {trend.start_value:.1f} in {trend.start_year} "
        f"to {trend.end_value:.1f} {trend.unit} in {trend.end_year}"
    )
    
    return {
        "type": "trend",
        "country": trend.country,
        "indicator": trend.indicator,
        "indicator_display": trend.display_name,
        "headline": headline,
        "detail": detail,
        "year": trend.end_year,
        "start_year": trend.start_year,
        "start_value": round(trend.start_value, 2),
        "end_value": round(trend.end_value, 2),
        "percent_change": round(trend.percent_change, 1),
        "statistical_confidence": round(1 - trend.p_value, 3),
        "trend_strength": round(trend.r_squared, 3),
        "unit": trend.unit,
    }


def milestone_to_story(milestone: MilestoneResult) -> dict:
    """Convert a MilestoneResult to a news story dict."""
    
    detail = (
        f"Crossed from {milestone.previous_value:.1f} to {milestone.new_value:.1f} "
        f"{milestone.unit}"
    )
    
    return {
        "type": "milestone",
        "country": milestone.country,
        "indicator": milestone.indicator,
        "indicator_display": milestone.display_name,
        "headline": milestone.headline,
        "detail": detail,
        "year": milestone.crossed_year,
        "milestone_value": milestone.milestone_value,
        "previous_value": round(milestone.previous_value, 2),
        "new_value": round(milestone.new_value, 2),
        "unit": milestone.unit,
    }


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def run_analysis(force_refresh: bool = False) -> list[dict]:
    """
    Run the full Good News Machine analysis pipeline.
    
    Args:
        force_refresh: If True, re-download all data
        
    Returns:
        List of news story dictionaries
    """
    print("=" * 60)
    print("🌟 GOOD NEWS MACHINE 🌟")
    print("=" * 60)
    
    # Load all data
    datasets = load_all_datasets(force_refresh)
    
    all_stories = []
    
    # Process each indicator
    for indicator in INDICATORS:
        name = indicator["name"]
        
        if name not in datasets:
            print(f"⚠️  Skipping {name} (failed to load)")
            continue
        
        print(f"📊 Analyzing: {indicator['display_name']}")
        
        # Clean the data
        df = clean_dataset(datasets[name], indicator)
        if df is None or len(df) == 0:
            print(f"  ⚠️  No valid data after cleaning")
            continue
        
        print(f"  {len(df['country'].unique())} countries, {len(df)} data points")
        
        # Find trends
        trends = find_all_trends(df, indicator)
        print(f"  ✅ Found {len(trends)} countries with improving trends")
        
        # Find milestones
        milestones = find_all_milestones(df, indicator)
        print(f"  🎯 Found {len(milestones)} recent milestone crossings")
        
        # Convert to stories
        for trend in trends[:20]:  # Top 20 per indicator
            all_stories.append(trend_to_story(trend))
        
        for milestone in milestones:
            all_stories.append(milestone_to_story(milestone))
        
        print()
    
    # Sort all stories by year (most recent first)
    all_stories.sort(key=lambda x: x["year"], reverse=True)
    
    return all_stories


def save_results(stories: list[dict]):
    """Save results to JSON file."""
    with open(OUTPUT_FILE, "w") as f:
        json.dump(stories, f, indent=2)
    print(f"💾 Saved {len(stories)} stories to {OUTPUT_FILE}")


def print_summary(stories: list[dict]):
    """Print a human-readable summary of findings."""
    print("\n" + "=" * 60)
    print("📰 TOP STORIES")
    print("=" * 60)
    
    # Show top 10 stories
    for i, story in enumerate(stories[:10], 1):
        print(f"\n{i}. [{story['year']}] {story['headline']}")
        print(f"   {story['detail']}")
    
    print("\n" + "=" * 60)
    print("📈 SUMMARY BY INDICATOR")
    print("=" * 60)
    
    # Count by indicator
    from collections import Counter
    indicator_counts = Counter(s["indicator"] for s in stories)
    type_counts = Counter(s["type"] for s in stories)
    
    print(f"\nTotal stories: {len(stories)}")
    print(f"  Trends: {type_counts.get('trend', 0)}")
    print(f"  Milestones: {type_counts.get('milestone', 0)}")
    
    print("\nBy indicator:")
    for indicator, count in indicator_counts.most_common():
        print(f"  {indicator}: {count}")


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Good News Machine - Find positive trends in global development data")
    parser.add_argument("--refresh", action="store_true", help="Force re-download of all datasets")
    args = parser.parse_args()
    
    # Run the analysis
    stories = run_analysis(force_refresh=args.refresh)
    
    # Save results
    save_results(stories)
    
    # Print summary
    print_summary(stories)
    
    print("\n✨ Done! Check good_news.json for the full feed.")
