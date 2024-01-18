OSV = "Other situations of violence (OSV)"

CONFLICT_TYPES = {
    "International armed conflict(IAC)": [
        # "Military Occupation",  # TODO: Confirm with IDMC
        "International armed conflict(IAC)",
    ],
    "Non-International armed conflict (NIAC)": [
        "Non-International armed conflict (NIAC)",
    ],
    OSV: [
        "Civilian-state violence",
        "Crime-related",
        "Communal violence",
        "Other",
    ],
    "Unclear/Unknown": [
        "Unclear/Unknown",
    ]
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
