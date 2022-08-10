OSV = "Other situations of violence (OSV)"

CONFLICT_TYPES = {
    "International armed conflict(IAC)": [
        "Military Occupation",
        "IAC (other than occupation)",
        "Other (IAC)",
        "Unclear (IAC)",
        "Unknown (IAC)"
    ],
    "Non-International armed conflict (NIAC)": [
        "NSAG(s) vs. State actor(s)",
        "NSAG(s) vs. NSAG(s)",
        "Other (NIAC)",
        "Unclear (NIAC)",
        "Unknown (NIAC)"
    ],
    OSV: [
        "Civilian-state violence",
        "Crime-related",
        "Communal violence",
        "Other (OSV)",
        "Unclear (OSV)",
        "Unknown (OSV)"
    ],
    "Other": ["Other (Other)", "Unclear (Other)", "Unknown (Other)"],
    "Unknown": ["Unclear (Unknown)", "Unknown (Unknown)"]
}

DISASTERS = {
    "Geophysical": {
        "Geophysical": {
            "Earthquake": ["Earthquake", "Tsunami"],
            "Mass Movement": ["Dry mass movement", "Sinkhole"],
            "Volcanic activity": ["Volcanic activity"],
        }
    },
    "Weather related": {
        "Climatological": {
            "Desertification": ["Desertification"],
            "Drought": ["Drought"],
            "Erosion": ["Erosion"],
            "Salinisation": ["Salinization"],
            "Sea level Rise": ["Sea level rise"],
            "Wildfire": ["Wildfire"],
        },
        "Hydrological": {
            "Flood": ["Dam release flood", "Flood"],
            "Mass Movement": ["Avalanche", "Landslide/Wet mass movement"],
            "Wave action": ["Rogue Wave"],
        },
        "Meteorological": {
            "Extreme Temperature": ["Cold wave", "Heat wave"],
            "Storm": ["Hailstorm", "Sand/dust storm", "Storm", "Storm surge",
                      "Tornado", "Typhoon/Hurricane/Cyclone", "Winter storm/Blizzard"]
        }
    },
    "Unknown": {
        "Unknown": {
            "Unknown": ["Unknown"]
        }
    }
}

OSV_SUB_TYPE = [
    "Religious tensions",
    "Agricultural/Pastoralist tensions",
    "Host/Displaced tensions",
    "Elections",
    "Demonstrations",
    "Police operations",
    "Other"
]
