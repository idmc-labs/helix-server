STOCK = 'STOCK'
FLOW = 'FLOW'

# FIGURE TAGS
FIGURE_TAGS = [
    'Protracted (1 year)',
    'Crime-induced displacement',
    'Transboundary disaster',
    'Protracted',
    'Indigenous communities affected',
    'Multi-causality',
    'Protracted (5 years)',
    'Chronic/repeated displacement',
]

LESS_THAN_FIVE = "<5"
FIVE_TO_FOURTEEN = "5-14"
FIFTEEN_TO_TWENTRY_FOUR = "15-24"
ZERO_TO_SEVENTEEN = "0-17"
EIGHTEEN_TO_FIFTYNINE = "18-59"
SIXTY_PLUS = "60+"
OTHER_AGES = "Other ages"


AGE_CATEGORIES_TO_EXPORT = {
    LESS_THAN_FIVE: ["0-1", "0-2", "0-3", "0-4", "2-5", "3-5"],
    FIVE_TO_FOURTEEN: ["5-9", "5-11", "5-14", "6-11", "6-12"],
    FIFTEEN_TO_TWENTRY_FOUR: ["15-17", "15-18", "15-24"],
    ZERO_TO_SEVENTEEN: [
        "0-1", "0-10", "0-14", "0-15", "0-16", "0-17", "0-2", "0-3", "0-4",
        "0-5", "0-6", "0-9", "1-3", "1-4", "1-5", "1-12", "10-14"
    ],
    EIGHTEEN_TO_FIFTYNINE: ["18-24", "18-25", "18-59"],
    SIXTY_PLUS: ["60+"],
    OTHER_AGES: [
        "0-18", "10-19", "10-24", "11-18", "12+", "12-17", "12-18", "13-17",
        "13-19", "15-59", "15-64", "16-59", "17-59", "18+", "18-60", "18-64",
        "19+", "20+", "20-59", "26-59", "5+", "5-17", "5-18", "50+", "6-17",
        "6-18", "65+", "unknown"
    ],
}
