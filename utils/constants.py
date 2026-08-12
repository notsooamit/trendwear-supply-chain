# Shared constants used across the project

REGIONS = ["North_America", "Europe", "Asia_Pacific", "Latin_America"]
SEASONS = ["SS26", "FW26", "SS27", "FW27"]
CATEGORIES = ["Jackets", "Shirts", "Trousers", "Dresses", "Activewear", "Outerwear"]
URGENCY_LEVELS = ["Normal", "High", "Critical"]
RISK_CATEGORIES = ["Low", "Medium", "High"]

# Optimization defaults
DEFAULT_COST_WEIGHT = 1.0
DEFAULT_RISK_WEIGHT = 0.3
DEFAULT_LEAD_TIME_WEIGHT = 0.1
DEFAULT_QUALITY_THRESHOLD = 80.0

# ML model defaults
TEST_SPLIT_RATIO = 0.2
RANDOM_STATE = 42

# Display
CURRENCY_FORMAT = "${:,.2f}"
PCT_FORMAT = "{:.1f}%"
