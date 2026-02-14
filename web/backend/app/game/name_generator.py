"""Random name generator for Uplink world population."""
import random

FIRST_NAMES = [
    "James", "John", "Robert", "Michael", "David", "Richard", "Joseph", "Thomas",
    "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Donald",
    "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian", "George",
    "Timothy", "Ronald", "Edward", "Jason", "Jeffrey", "Ryan", "Jacob",
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan",
    "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret", "Sandra",
    "Ashley", "Dorothy", "Kimberly", "Emily", "Donna", "Michelle", "Carol",
    "Amanda", "Melissa", "Deborah", "Stephanie", "Rebecca", "Sharon", "Laura",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    "Walker", "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen",
    "Hill", "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera",
    "Campbell", "Mitchell", "Carter", "Roberts", "Gomez", "Phillips", "Evans",
    "Turner", "Diaz", "Parker", "Cruz", "Edwards", "Collins", "Reyes",
]

COMPANY_PREFIXES = [
    "Global", "United", "International", "National", "Pacific", "Atlantic",
    "Northern", "Southern", "Central", "Western", "Eastern", "Trans",
    "Apex", "Prime", "Elite", "Core", "Nexus", "Vertex", "Quantum", "Cyber",
    "Digital", "Tech", "Net", "Data", "Micro", "Macro", "Ultra", "Meta",
]

COMPANY_SUFFIXES = [
    "Systems", "Technologies", "Computing", "Networks", "Solutions",
    "Dynamics", "Industries", "Corporation", "Enterprises", "Services",
    "Communications", "Electronics", "Software", "Security", "Consulting",
    "Research", "Analytics", "Digital", "Innovations", "Labs",
]

def generate_name(rng: random.Random | None = None) -> str:
    r = rng or random
    return f"{r.choice(FIRST_NAMES)} {r.choice(LAST_NAMES)}"

def generate_company_name(rng: random.Random | None = None) -> str:
    r = rng or random
    return f"{r.choice(COMPANY_PREFIXES)} {r.choice(COMPANY_SUFFIXES)}"

def generate_ip(rng: random.Random | None = None) -> str:
    r = rng or random
    return f"{r.randint(100,999)}.{r.randint(1,999)}.{r.randint(1,999)}.{r.randint(1,999)}"
