VIOLENCES = {
    # TYPE: SUB_TYPE
    "Military occupation": ["Military Occupation"],
    "International state-based armed conflict": ["International state-based armed conflict"],
    "Inter-communal violence": ["Agricultural/pastoralist", "Inter-religious violence",
                                "Inter-ethnic violence", "Other inter-communal conflict"],
    "Political and electoral violence ": ["Electoral violence", "Clashes between political groups", "Voter intimidation"],
    "Criminal violence": ["Banditry", "Cattle-rustling", "Cartel violence", "Organised crime violence"],
    "Rebel-rebel or rebel-government violence ": ["Intra-state", "Non-state"],
    "Other": ["Private security companies violence"],
}

TRIGGERS = {
    "Violence against civilians",
    "Battle",
    # FIXME: remove trailing whitespace
    "Explosions/remote violence ",
    "Riots",
    "Security operations and evictions",
    "Other",
}

SUB_TRIGGERS = {
    "Looting",
    "Vandalism",
    "Raid/clearance/search operations",
    "Demolitions/evictions",
    "Burning/torching of homes/housing destruction",
    "[Perceived] threat of attack/Intimidation",
    "Mob violence/lynching",
    "Knife/Machetes",
    "Shooting",
    "Shelling",
    "Chemical weapons",
    "Biological weapons",
    "Other",
    "Threat of attack",
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
    }
}

OSV_SUB_TYPE = [
    "Religious tensions",
    "Agricultural/pastoralist tensions",
    "Host/Displaced tensions",
    "Elections",
    "Demonstrations",
    "Police operatins",
    "Other"
]
