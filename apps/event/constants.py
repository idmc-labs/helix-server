from dataclasses import dataclass


@dataclass(frozen=True)
class SubType:
    name: str
    idu_name: str


OTHER_SUB_TYPES = [
    SubType(name="Development", idu_name="development"),
    SubType(name="Eviction", idu_name="eviction"),
    SubType(name="Technical disaster", idu_name="a technical disaster"),
]

OSV = "Other situations of violence (OSV)"

CONFLICT_TYPES = {
    "International armed conflict (IAC)": [
        SubType(
            name="International armed conflict (IAC)",
            idu_name="international armed conflict",
        ),
    ],
    "Non-International armed conflict (NIAC)": [
        SubType(
            name="Non-International armed conflict (NIAC)",
            idu_name="non-international armed conflict",
        ),
    ],
    OSV: [
        SubType(
            name="Civilian-state violence",
            idu_name="civilian state violence",
        ),
        SubType(
            name="Crime-related violence",
            idu_name="crime-related violence",
        ),
        SubType(
            name="Communal violence",
            idu_name="communal violence",
        ),
        SubType(
            name="Other",
            idu_name="conflict",
        ),
    ],
    "Unclear/Unknown": [
        SubType(
            name="Unclear/Unknown",
            idu_name="conflict",
        ),
    ],
}

DISASTERS = {
    "Geophysical": {
        "Geophysical": {
            "Earthquake": [
                SubType(name="Earthquake", idu_name="an earthquake"),
                SubType(name="Tsunami", idu_name="a tsunami"),
            ],
            "Mass Movement": [
                SubType(name="Dry mass movement", idu_name="dry mass movement"),
                SubType(name="Sinkhole", idu_name="a sinkhole"),
            ],
            "Volcanic activity": [
                SubType(name="Volcanic activity", idu_name="volcanic activity"),
            ],
        }
    },
    "Weather related": {
        "Climatological": {
            "Desertification": [
                SubType(name="Desertification", idu_name="desertification"),
            ],
            "Drought": [
                SubType(name="Drought", idu_name="a drought"),
            ],
            "Erosion": [
                SubType(name="Erosion", idu_name="erosion"),
            ],
            "Salinisation": [
                SubType(name="Salinization", idu_name="salinization"),
            ],
            "Sea level Rise": [
                SubType(name="Sea level rise", idu_name="sea level rise"),
            ],
            "Wildfire": [
                SubType(name="Wildfire", idu_name="a wildfire"),
            ],
        },
        "Hydrological": {
            "Flood": [
                SubType(name="Dam release flood", idu_name="flooding caused by a dam release"),
                SubType(name="Flood", idu_name="flooding"),
            ],
            "Mass Movement": [
                SubType(name="Avalanche", idu_name="an avalanche"),
                SubType(name="Landslide/Wet mass movement", idu_name="a landslide"),
            ],
            "Wave action": [
                SubType(name="Rogue Wave", idu_name="a rogue wave"),
            ],
        },
        "Meteorological": {
            "Extreme Temperature": [
                SubType(name="Cold wave", idu_name="a cold wave"),
                SubType(name="Heat wave", idu_name="a heat wave"),
            ],
            "Storm": [
                SubType(name="Hailstorm", idu_name="a hailstorm"),
                SubType(name="Sand/dust storm", idu_name="a sandstorm"),
                SubType(name="Storm", idu_name="a storm"),
                SubType(name="Storm surge", idu_name="storm surge"),
                SubType(name="Tornado", idu_name="a tornado"),
                SubType(name="Typhoon/Hurricane/Cyclone", idu_name="a tropical cyclone"),
                SubType(name="Winter storm/Blizzard", idu_name="a winter storm"),
            ],
        },
    },
    "Mixed disasters": {
        "Mixed disasters": {
            "Mixed disasters": [
                SubType(name="Mixed disasters", idu_name="mixed disasters"),
            ],
        }
    },
}

OSV_SUB_TYPE = [
    "Religious tensions",
    "Agricultural/Pastoralist tensions",
    "Host/Displaced tensions",
    "Elections",
    "Demonstrations",
    "Police operations",
    "Other",
]
