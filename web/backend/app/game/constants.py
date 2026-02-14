"""
Uplink Game Constants
Faithfully transcribed from uplink/src/game/data/data.h and data.cpp
"""

# ============================================================
# Starting conditions of world
# ============================================================
WORLD_START_DATE = (0, 0, 0, 24, 2, 2010)  # sec, min, hour, day, month, year
GAME_START_DATE = (0, 0, 0, 24, 3, 2010)

COMPANYSIZE_AVERAGE = 20
COMPANYSIZE_RANGE = 20
COMPANYGROWTH_AVERAGE = 10  # percent
COMPANYGROWTH_RANGE = 20  # percent
COMPANYALIGNMENT_AVERAGE = 0
COMPANYALIGNMENT_RANGE = 50

# ============================================================
# Starting conditions of player
# ============================================================
PLAYER_START_BALANCE = 3000
PLAYER_START_CREDITRATING = 10
PLAYER_START_UPLINKRATING = 0
PLAYER_START_NEUROMANCERRATING = 5

PLAYER_START_GATEWAYNAME = "Gateway ALPHA"
PLAYER_START_CPUTYPE = "CPU ( 60 Ghz )"
PLAYER_START_MODEMSPEED = 1
PLAYER_START_MEMORYSIZE = 24

# ============================================================
# Number of things to create at start
# ============================================================
NUM_STARTING_COMPANIES = 30
NUM_STARTING_BANKS = 7
NUM_STARTING_PEOPLE = 50
NUM_STARTING_AGENTS = 30
NUM_STARTING_MISSIONS = 20
NUM_STARTING_PHOTOS = 20
NUM_STARTING_VOICES = 4

# ============================================================
# Tick rates for hacking tools
# ============================================================
TICKSREQUIRED_COPY = 45
TICKSREQUIRED_DELETE = 9
TICKSREQUIRED_DECRYPT = 90
TICKSREQUIRED_DEFRAG = 3  # per memory slot
TICKSREQUIRED_DICTIONARYHACKER = 0.2  # ticks per word
TICKSREQUIRED_LOGDELETER = 60
TICKSREQUIRED_LOGUNDELETER = 60
TICKSREQUIRED_LOGMODIFIER = 50
TICKSREQUIRED_ANALYSEPROXY = 50
TICKSREQUIRED_DISABLEPROXY = 100
TICKSREQUIRED_ANALYSEFIREWALL = 40
TICKSREQUIRED_DISABLEFIREWALL = 80
TICKSREQUIRED_BYPASSCYPHER = 0.1  # per element
TICKSREQUIRED_SCANLANSYSTEM = 70
TICKSREQUIRED_SCANLANLINKS = 100
TICKSREQUIRED_SPOOFLANSYSTEM = 100
TICKSREQUIRED_FORCELANLOCK = 100
TICKSREQUIRED_LANSCAN = 300

TIMEREQUIRED_DELETEONELOG = 300  # ms, used in ConsoleScreen
TIMEREQUIRED_DELETEONEGIGAQUAD = 150

# ============================================================
# Trace speeds (seconds per link, -1 = no trace)
# ============================================================
TRACESPEED_VARIANCE = 0.1

TRACESPEED_PUBLICACCESSSERVER = -1
TRACESPEED_INTERNALSERVICESMACHINE = 15
TRACESPEED_CENTRALMAINFRAME = 5
TRACESPEED_PUBLICBANKSERVER = 5
TRACESPEED_LAN = 5

TRACESPEED_UPLINK_INTERNALSERVICESMACHINE = 5
TRACESPEED_UPLINK_TESTMACHINE = 30
TRACESPEED_UPLINK_PUBLICACCESSSERVER = -1

TRACESPEED_GLOBALCRIMINALDATABASE = 10
TRACESPEED_INTERNATIONALSOCIALSECURITYDATABASE = 15
TRACESPEED_CENTRALMEDICALDATABASE = 25
TRACESPEED_GLOBALINTELLIGENCEAGENCY = 5
TRACESPEED_INTERNATIONALACADEMICDATABASE = 35
TRACESPEED_INTERNIC = 15
TRACESPEED_STOCKMARKET = 20
TRACESPEED_PROTOVISION = 30

TRACESPEED_MODIFIER_NOACCOUNT = 0.1
TRACESPEED_MODIFIER_HASACCOUNT = 0.7
TRACESPEED_MODIFIER_ADMINACCESS = 1.0
TRACESPEED_MODIFIER_CENTRALMAINFRAME = 1.3
TRACESPEED_MODIFIER_PUBLICBANKSERVERADMIN = 1.6

# ============================================================
# Hack difficulties (ticks per letter)
# ============================================================
HACKDIFFICULTY_VARIANCE = 0.15

HACKDIFFICULTY_PUBLICACCESSSERVER = 6
HACKDIFFICULTY_INTERNALSERVICESMACHINE = 45
HACKDIFFICULTY_CENTRALMAINFRAME = 80
HACKDIFFICULTY_PUBLICBANKSERVER = 100
HACKDIFFICULTY_PUBLICBANKSERVER_ADMIN = 300
HACKDIFFICULTY_LOCALMACHINE = 20

HACKDIFFICULTY_LANTERMINAL = 75
HACKDIFFICULTY_LANAUTHENTICATIONSERVER = 150
HACKDIFFICULTY_LANLOGSERVER = 300
HACKDIFFICULTY_LANMODEM = 200
HACKDIFFICULTY_LANMAINSERVER = 500

HACKDIFFICULTY_UPLINK_INTERNALSERVICESMACHINE = 300
HACKDIFFICULTY_UPLINK_TESTMACHINE = 30
HACKDIFFICULTY_UPLINK_PUBLICACCESSSERVER = 30

HACKDIFFICULTY_ARCCENTRALMAINFRAME = 600
HACKDIFFICULTY_ARUNMORCENTRALMAINFRAME = 600
HACKDIFFICULTY_GLOBALCRIMINALDATABASE = 180
HACKDIFFICULTY_INTERNATIONALSOCIALSECURITYDATABASE = 120
HACKDIFFICULTY_CENTRALMEDICALDATABASE = 120
HACKDIFFICULTY_GLOBALINTELLIGENCEAGENCY = 450
HACKDIFFICULTY_INTERNATIONALACADEMICDATABASE = 90
HACKDIFFICULTY_INTERNIC = 70
HACKDIFFICULTY_STOCKMARKET = 120
HACKDIFFICULTY_PROTOVISION = -1  # unhackable

# Security level -> difficulty modifier
#                              level:  0    1    2    3    4    5    6    7    8    9    10
HACKDIFFICULTY_SECURITYMODIFIER = [0.0, 2.0, 1.5, 1.2, 1.0, 1.0, 0.9, 0.7, 0.5, 0.5, 0.5]

# Min company size for security features
MINCOMPANYSIZE_MONITOR = 1
MINCOMPANYSIZE_PROXY = 8
MINCOMPANYSIZE_FIREWALL = 10
MAXCOMPANYSIZE_WARNINGMAIL = 5
MAXCOMPANYSIZE_FINE = 12

# ============================================================
# Mission probabilities by agent rating (index 0-16)
# ============================================================
PROB_MISSION_STEALFILE =      [30, 40, 30, 15,  5, 30, 15, 10,  0,  0,  0,  5,  5,  5,  5,  5,  5]
PROB_MISSION_DESTROYFILE =    [30, 40, 30, 15, 40, 10, 15,  5,  0,  0,  0,  5,  5,  5,  5,  5,  5]
PROB_MISSION_CHANGEDATA =     [25, 15, 25, 60, 40, 30, 20, 15, 15,  5,  0,  5,  5,  5,  5,  5,  5]
PROB_MISSION_FINDDATA =       [15,  5, 15, 10, 15, 30, 15, 15,  5,  0,  0,  5,  5,  5,  5,  5,  5]
PROB_MISSION_REMOVECOMPUTER = [ 0,  0,  0,  0,  0,  0, 35, 25, 20,  5, 10, 20, 20, 20, 20, 20, 20]
PROB_MISSION_CHANGEACCOUNT =  [ 0,  0,  0,  0,  0,  0,  0, 30, 20, 25, 30, 20, 20, 20, 20, 20, 20]
PROB_MISSION_REMOVEUSER =     [ 0,  0,  0,  0,  0,  0,  0,  0, 40, 25, 30, 20, 20, 20, 20, 20, 20]
PROB_MISSION_FRAMEUSER =      [ 0,  0,  0,  0,  0,  0,  0,  0,  0, 40, 30, 20, 20, 20, 20, 20, 20]
PROB_MISSION_REMOVECOMPANY =  [ 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0]
PROB_MISSION_SPECIAL =        [ 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0]
PROB_MISSION_TRACEUSER =      [ 0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0]

PROB_GENERATETRACEHACKERMISSION = 30

# ============================================================
# Mission payments (multiplied by difficulty)
# ============================================================
PAYMENT_MISSION_VARIANCE = 0.3

PAYMENT_MISSION_STEALFILE = 900
PAYMENT_MISSION_STEALALLFILES = 1500
PAYMENT_MISSION_DESTROYFILE = 800
PAYMENT_MISSION_DESTROYALLFILES = 1400
PAYMENT_MISSION_FINDDATA = 1000
PAYMENT_MISSION_FINDDATA_FINANCIAL = 1200
PAYMENT_MISSION_CHANGEDATA = 1000
PAYMENT_MISSION_CHANGEDATA_ACADEMIC = 1000
PAYMENT_MISSION_CHANGEDATA_SOCIAL = 1200
PAYMENT_MISSION_CHANGEDATA_CRIMINAL = 1500
PAYMENT_MISSION_FRAMEUSER = 2200
PAYMENT_MISSION_TRACEUSER = 1800
PAYMENT_MISSION_CHANGEACCOUNT = 1700
PAYMENT_MISSION_REMOVECOMPUTER = 1600
PAYMENT_MISSION_REMOVECOMPANY = 2000
PAYMENT_MISSION_REMOVEUSER = 1900

# Special mission payments
PAYMENT_SPECIALMISSION_BACKFIRE = 15000
PAYMENT_SPECIALMISSION_TRACER = 10000
PAYMENT_SPECIALMISSION_TAKEMETOYOURLEADER = 30000
PAYMENT_SPECIALMISSION_ARCINFILTRATION = 30000
PAYMENT_SPECIALMISSION_COUNTERATTACK = 50000
PAYMENT_SPECIALMISSION_MAIDENFLIGHT = 10000
PAYMENT_SPECIALMISSION_DARWIN = 15000
PAYMENT_SPECIALMISSION_SAVEITFORTHEJURY = 20000
PAYMENT_SPECIALMISSION_SHINYHAMMER = 30000
PAYMENT_SPECIALMISSION_GRANDTOUR = 50000
PAYMENT_SPECIALMISSION_MOLE = 50000

# ============================================================
# Mission minimum difficulty ratings
# ============================================================
DIFFICULTY_MISSION_VARIANCE = 2

MINDIFFICULTY_MISSION_STEALFILE = 2
MINDIFFICULTY_MISSION_STEALALLFILES = 5
MINDIFFICULTY_MISSION_DESTROYFILE = 2
MINDIFFICULTY_MISSION_DESTROYALLFILES = 5
MINDIFFICULTY_MISSION_FINDDATA = 2
MINDIFFICULTY_MISSION_FINDDATA_FINANCIAL = 5
MINDIFFICULTY_MISSION_CHANGEDATA = 3
MINDIFFICULTY_MISSION_CHANGEDATA_ACADEMIC = 3
MINDIFFICULTY_MISSION_CHANGEDATA_SOCIAL = 4
MINDIFFICULTY_MISSION_CHANGEDATA_CRIMINAL = 5
MINDIFFICULTY_MISSION_FRAMEUSER = 9
MINDIFFICULTY_MISSION_TRACEUSER = 7
MINDIFFICULTY_MISSION_TRACEUSER_BANKFRAUD = 8
MINDIFFICULTY_MISSION_CHANGEACCOUNT = 7
MINDIFFICULTY_MISSION_REMOVECOMPUTER = 6
MINDIFFICULTY_MISSION_REMOVECOMPANY = 8
MINDIFFICULTY_MISSION_REMOVEUSER = 8

# ============================================================
# NPC agent skills
# ============================================================
AGENT_UPLINKRATINGAVERAGE = 7
AGENT_UPLINKRATINGVARIANCE = 7

MINREQUIREDRATING_DELETELOGLEVEL1 = 2
MINREQUIREDRATING_DELETELOGLEVEL2 = 3
MINREQUIREDRATING_DELETELOGLEVEL3 = 4
MINREQUIREDRATING_UNDELETELOGLEVEL1 = 7
MINREQUIREDRATING_UNDELETELOGLEVEL2 = 7
MINREQUIREDRATING_UNDELETELOGLEVEL3 = 9
MINREQUIREDRATING_HACKBANKSERVER = 6
MINREQUIREDRATING_HACKGOVERNMENTCOMPUTER = 8

# ============================================================
# Time constants (in game minutes)
# ============================================================
TIME_TOPAYLEGALFINE = 7 * 24 * 60  # 7 days
TIME_LEGALACTION = 3 * 60  # 3 hours
TIME_LEGALACTION_WARNING = 2  # 2 minutes
TIME_TACTICALACTION = 5  # 5 minutes
TIME_TACTICALACTION_WARNING = 1

TIME_TOINSTALLHARDWARE = 14 * 60  # 14 hours
TIME_TOINSTALLHARDWARE_WARNING = 30  # 30 min
TIME_TOCHANGEGATEWAY = 24 * 60  # 24 hours

TIME_TOEXPIRELOGS = 40 * 24 * 60  # 40 days
TIME_TOEXPIRENEWS = 30 * 24 * 60
TIME_TOEXPIREMISSIONS = 30 * 24 * 60

TIME_TODEMOGAMEOVER = 0
TIME_TOCOVERBANKROBBERY = 2
TIME_REVELATIONREPRODUCE = 3
TIME_ARCBUSTED_WITHPLAYER = 15
TIME_ARCBUSTED_WITHOUTPLAYER = 10

FREQUENCY_GENERATENEWMISSION = 12 * 60  # 12 hours
FREQUENCY_CHECKFORSECURITYBREACHES = 8 * 60
FREQUENCY_CHECKMISSIONDUEDATES = 24 * 60
FREQUENCY_GIVEMISSIONTONPC = 8 * 60
FREQUENCY_EXPIREOLDSTUFF = 7 * 24 * 60
FREQUENCY_ADDINTERESTONLOANS = 30 * 24 * 60
FREQUENCY_DEMOGENERATENEWMISSION = 4 * 60

# ============================================================
# Costs
# ============================================================
COST_UPLINK_PERMONTH = 300
COST_UPLINK_NEWGATEWAY = 1000
GATEWAY_PARTEXCHANGEVALUE = 0.75

SMALLLOAN_MAX = 3000
SMALLLOAN_INTEREST = 0.2
MEDIUMLOAN_MAX = 7000
MEDIUMLOAN_INTEREST = 0.4
LARGELOAN_MAX = 10000
LARGELOAN_INTEREST = 0.7
MAXLOAN_INTEREST = 1.0

# ============================================================
# Uplink Ratings
# ============================================================
UPLINKRATING = [
    ("Unregistered", 0),
    ("Registered", 1),
    ("Beginner", 2),
    ("Novice", 6),
    ("Confident", 15),
    ("Intermediate", 35),
    ("Skilled", 60),
    ("Experienced", 90),
    ("Knowledgeable", 125),
    ("Uber-Skilled", 160),
    ("Professional", 220),
    ("Elite", 300),
    ("Mage", 400),
    ("Expert", 600),
    ("Veteren", 1000),
    ("Techno-mage", 1500),
    ("TERMINAL", 2500),
]

NEUROMANCERRATING = [
    ("Morally bankrupt", -1024),
    ("Sociopathic", -512),
    ("Indiscriminate", -128),
    ("Notorious", -32),
    ("Untrustworthy", -16),
    ("Neutral", 0),
    ("Aggressive", 32),
    ("Single minded", 64),
    ("Activist", 256),
    ("Anarchic", 1024),
    ("Revolutionary", 2048),
]

# Neuromancer change per mission type (index = mission type)
# 0=Special, 1=Steal, 2=Destroy, 3=Find, 4=Change, 5=Frame, 6=Trace, 7=ChangeAccount, 8=RemoveComputer, 9=RemoveCompany, 10=RemoveUser
NEUROMANCERCHANGE = [0, 0, 5, 0, -5, -20, -30, -10, 30, 60, -60]

NEUROMANCERCHANGE_GATEWAYNEARMISS = 150
UPLINKCHANGE_GATEWAYNEARMISS = -30
NEUROMANCERCHANGE_ROBBANK = 0
UPLINKCHANGE_ROBBANK = 150

# ============================================================
# Physical gateway locations
# ============================================================
PHYSICALGATEWAYLOCATIONS = [
    {"city": "London", "country": "United Kingdom", "x": 282, "y": 69},
    {"city": "Tokyo", "country": "Japan", "x": 514, "y": 104},
    {"city": "Los Angeles", "country": "USA", "x": 91, "y": 125},
    {"city": "New York", "country": "USA", "x": 171, "y": 98},
    {"city": "Chicago", "country": "USA", "x": 138, "y": 88},
    {"city": "Moscow", "country": "Russia", "x": 331, "y": 70},
    {"city": "Hong Kong", "country": "China", "x": 485, "y": 133},
    {"city": "Sydney", "country": "Australia", "x": 547, "y": 244},
]

# ============================================================
# Fixed IP addresses
# ============================================================
IP_LOCALHOST = "127.0.0.1"
IP_INTERNIC = "458.615.48.651"
IP_ACADEMICDATABASE = "443.65.765.2"
IP_GLOBALCRIMINALDATABASE = "785.234.87.124"
IP_SOCIALSECURITYDATABASE = "653.76.235.432"
IP_CENTRALMEDICALDATABASE = "432.543.12.544"
IP_STOCKMARKETSYSTEM = "456.789.159.459"
IP_PROTOVISION = "284.345.42.283"
IP_OCP = "265.125.767.1"
IP_SJGAMES = "849.23.459.24"
IP_INTROVERSION = "128.128.128.128"

IP_UPLINKPUBLICACCESSSERVER = "234.773.0.666"
IP_UPLINKCREDITSMACHINE = "128.185.0.2"
IP_UPLINKINTERNALSERVICES = "128.185.0.8"
IP_UPLINKTESTMACHINE = "128.185.0.4"

NAME_UPLINKINTERNALSERVICES = "Uplink Internal Services System"

# ============================================================
# Screen types (from remoteinterface.h)
# ============================================================
SCREEN_UNKNOWN = 0
SCREEN_MESSAGESCREEN = 1
SCREEN_PASSWORDSCREEN = 2
SCREEN_MENUSCREEN = 3
SCREEN_BBSSCREEN = 4
SCREEN_DIALOGSCREEN = 5
SCREEN_FILESERVERSCREEN = 6
SCREEN_LINKSSCREEN = 7
SCREEN_LOGSCREEN = 8
SCREEN_SWSALESSCREEN = 9
SCREEN_HWSALESSCREEN = 10
SCREEN_RECORDSCREEN = 11
SCREEN_USERIDSCREEN = 12
SCREEN_ACCOUNTSCREEN = 13
SCREEN_CONTACTSCREEN = 14
SCREEN_NEWSSCREEN = 15
SCREEN_CRIMINALSCREEN = 16
SCREEN_SECURITYSCREEN = 17
SCREEN_ACADEMICSCREEN = 18
SCREEN_RANKINGSCREEN = 19
SCREEN_CONSOLESCREEN = 20
SCREEN_SOCSECSCREEN = 21
SCREEN_LOANSSCREEN = 22
SCREEN_SHARESLISTSCREEN = 23
SCREEN_SHARESVIEWSCREEN = 24
SCREEN_FAITHSCREEN = 25
SCREEN_CYPHERSCREEN = 26
SCREEN_VOICEANALYSIS = 27
SCREEN_COMPANYINFO = 28
SCREEN_VOICEPHONE = 29
SCREEN_HIGHSECURITYSCREEN = 30
SCREEN_NEARESTGATEWAY = 31
SCREEN_CHANGEGATEWAY = 32
SCREEN_CODECARD = 33
SCREEN_DISCONNECTEDSCREEN = 34
SCREEN_PROTOVISION = 35
SCREEN_NUCLEARWAR = 36
SCREEN_RADIOTRANSMITTER = 37

# ============================================================
# Software types
# ============================================================
SOFTWARETYPE_NONE = 0
SOFTWARETYPE_FILEUTIL = 1
SOFTWARETYPE_HWDRIVER = 2
SOFTWARETYPE_SECURITY = 3
SOFTWARETYPE_CRACKERS = 4
SOFTWARETYPE_BYPASSERS = 5
SOFTWARETYPE_LANTOOL = 6
SOFTWARETYPE_HUDUPGRADE = 9
SOFTWARETYPE_OTHER = 10

# ============================================================
# Hardware upgrade types
# ============================================================
GATEWAYUPGRADETYPE_CPU = 1
GATEWAYUPGRADETYPE_MODEM = 2
GATEWAYUPGRADETYPE_COOLING = 3
GATEWAYUPGRADETYPE_MEMORY = 4
GATEWAYUPGRADETYPE_SECURITY = 5
GATEWAYUPGRADETYPE_POWER = 6

# ============================================================
# Software catalog (name, type, cost, size, version, description)
# ============================================================
SOFTWARE_UPGRADES = [
    ("Decrypter", 4, 800, 2, 1, "DECRYPTER V1.0"),
    ("Decrypter", 4, 1200, 2, 2, "DECRYPTER V2.0"),
    ("Decrypter", 4, 1600, 2, 3, "DECRYPTER V3.0"),
    ("Decrypter", 4, 2200, 2, 4, "DECRYPTER V4.0"),
    ("Decrypter", 4, 3000, 3, 5, "DECRYPTER V5.0"),
    ("Decrypter", 4, 7000, 4, 6, "DECRYPTER V6.0"),
    ("Decrypter", 4, 15000, 5, 7, "DECRYPTER V7.0"),
    ("Decypher", 4, 3000, 2, 1, "DECYPHER V1.0"),
    ("Decypher", 4, 5000, 2, 2, "DECYPHER V2.0"),
    ("Decypher", 4, 8000, 2, 3, "DECYPHER V3.0"),
    ("Dictionary_Hacker", 4, 1000, 4, 1, "DICTIONARY HACKER V1.0"),
    ("File_Copier", 1, 100, 1, 1, "FILE COPIER V1.0"),
    ("File_Deleter", 1, 100, 1, 1, "FILE DELETER V1.0"),
    ("Defrag", 1, 5000, 2, 1, "DEFRAG V1.0"),
    ("Firewall_Bypass", 5, 3000, 1, 1, "FIREWALL BYPASS V1.0"),
    ("Firewall_Bypass", 5, 4000, 1, 2, "FIREWALL BYPASS V2.0"),
    ("Firewall_Bypass", 5, 6000, 1, 3, "FIREWALL BYPASS V3.0"),
    ("Firewall_Bypass", 5, 8000, 1, 4, "FIREWALL BYPASS V4.0"),
    ("Firewall_Bypass", 5, 10000, 1, 5, "FIREWALL BYPASS V5.0"),
    ("Firewall_Disable", 3, 2000, 1, 1, "FIREWALL DISABLE V1.0"),
    ("Firewall_Disable", 3, 3000, 1, 2, "FIREWALL DISABLE V2.0"),
    ("Firewall_Disable", 3, 4000, 1, 3, "FIREWALL DISABLE V3.0"),
    ("Firewall_Disable", 3, 6000, 2, 4, "FIREWALL DISABLE V4.0"),
    ("Firewall_Disable", 3, 8000, 3, 5, "FIREWALL DISABLE V5.0"),
    ("HUD_ConnectionAnalysis", 9, 20000, 3, 1, "CONNECTION ANALYSIS V1.0"),
    ("HUD_IRC-Client", 9, 4000, 2, 1, "IRC CLIENT V1.0"),
    ("HUD_MapShowTrace", 9, 5000, 1, 1, "MAP SHOW TRACE V1.0"),
    ("HUD_LANView", 9, 50000, 5, 1, "LAN VIEW V1.0"),
    ("IP_Lookup", 10, 500, 1, 1, "IP LOOKUP V1.0"),
    ("IP_Probe", 10, 2000, 3, 1, "IP PROBE V1.0"),
    ("IP_Probe", 10, 4000, 3, 2, "IP PROBE V2.0"),
    ("IP_Probe", 10, 5000, 3, 3, "IP PROBE V3.0"),
    ("LAN_Probe", 6, 15000, 3, 1, "LAN PROBE V1.0"),
    ("LAN_Probe", 6, 20000, 3, 2, "LAN PROBE V2.0"),
    ("LAN_Probe", 6, 30000, 4, 3, "LAN PROBE V3.0"),
    ("LAN_Scan", 6, 10000, 2, 1, "LAN SCAN V1.0"),
    ("LAN_Scan", 6, 15000, 2, 2, "LAN SCAN V2.0"),
    ("LAN_Scan", 6, 25000, 2, 3, "LAN SCAN V3.0"),
    ("LAN_Spoof", 6, 20000, 2, 1, "LAN SPOOF V1.0"),
    ("LAN_Spoof", 6, 30000, 3, 2, "LAN SPOOF V2.0"),
    ("LAN_Spoof", 6, 45000, 5, 3, "LAN SPOOF V3.0"),
    ("LAN_Force", 6, 15000, 2, 1, "LAN FORCE V1.0"),
    ("LAN_Force", 6, 20000, 3, 2, "LAN FORCE V2.0"),
    ("LAN_Force", 6, 25000, 4, 3, "LAN FORCE V3.0"),
    ("Log_Deleter", 3, 500, 1, 1, "LOG DELETER V1.0"),
    ("Log_Deleter", 3, 1000, 1, 2, "LOG DELETER V2.0"),
    ("Log_Deleter", 3, 2000, 1, 3, "LOG DELETER V3.0"),
    ("Log_Deleter", 3, 4000, 1, 4, "LOG DELETER V4.0"),
    ("Log_Modifier", 3, 4000, 2, 1, "LOG MODIFIER V1.0"),
    ("Log_Modifier", 3, 6000, 2, 2, "LOG MODIFIER V2.0"),
    ("Log_UnDeleter", 3, 5000, 1, 1, "LOG UNDELETER V1.0"),
    ("Monitor_Bypass", 5, 10000, 1, 1, "MONITOR BYPASS V1.0"),
    ("Monitor_Bypass", 5, 12000, 1, 2, "MONITOR BYPASS V2.0"),
    ("Monitor_Bypass", 5, 16000, 1, 3, "MONITOR BYPASS V3.0"),
    ("Monitor_Bypass", 5, 20000, 1, 4, "MONITOR BYPASS V4.0"),
    ("Monitor_Bypass", 5, 25000, 1, 5, "MONITOR BYPASS V5.0"),
    ("Password_Breaker", 4, 1500, 2, 1, "PASSWORD BREAKER V1.0"),
    ("Proxy_Bypass", 5, 6000, 1, 1, "PROXY BYPASS V1.0"),
    ("Proxy_Bypass", 5, 8000, 1, 2, "PROXY BYPASS V2.0"),
    ("Proxy_Bypass", 5, 12000, 1, 3, "PROXY BYPASS V3.0"),
    ("Proxy_Bypass", 5, 16000, 1, 4, "PROXY BYPASS V4.0"),
    ("Proxy_Bypass", 5, 20000, 1, 5, "PROXY BYPASS V5.0"),
    ("Proxy_Disable", 3, 3000, 1, 1, "PROXY DISABLE V1.0"),
    ("Proxy_Disable", 3, 4000, 1, 2, "PROXY DISABLE V2.0"),
    ("Proxy_Disable", 3, 6000, 1, 3, "PROXY DISABLE V3.0"),
    ("Proxy_Disable", 3, 8000, 2, 4, "PROXY DISABLE V4.0"),
    ("Proxy_Disable", 3, 10000, 3, 5, "PROXY DISABLE V5.0"),
    ("Trace_Tracker", 3, 300, 1, 1, "TRACE TRACKER V1.0"),
    ("Trace_Tracker", 3, 600, 1, 2, "TRACE TRACKER V2.0"),
    ("Trace_Tracker", 3, 1400, 2, 3, "TRACE TRACKER V3.0"),
    ("Trace_Tracker", 3, 2500, 3, 4, "TRACE TRACKER V4.0"),
    ("Voice_Analyser", 10, 5000, 4, 1, "VOICE ANALYSER V1.0"),
    ("Voice_Analyser", 10, 10000, 5, 2, "VOICE ANALYSER V2.0"),
]

# ============================================================
# Hardware catalog (name, type, cost, size, data/speed, description)
# ============================================================
HARDWARE_UPGRADES = [
    ("CPU ( 20 Ghz )", 1, 250, 0, 20, "CPU ( 20 Ghz )"),
    ("CPU ( 60 Ghz )", 1, 1000, 0, 60, "CPU ( 60 Ghz )"),
    ("CPU ( 80 Ghz )", 1, 1300, 0, 80, "CPU ( 80 Ghz )"),
    ("CPU ( 100 Ghz )", 1, 3000, 0, 100, "CPU ( 100 Ghz )"),
    ("CPU ( 120 Ghz )", 1, 5000, 0, 120, "CPU ( 120 Ghz )"),
    ("CPU ( 150 Ghz )", 1, 8000, 0, 150, "CPU ( 150 Ghz )"),
    ("CPU ( Turbo 200 Ghz )", 1, 12000, 0, 200, "CPU ( Turbo 200 Ghz )"),
    ("Modem ( 1 Gq / s )", 2, 1000, 0, 1, "Modem ( 1 Gq / s )"),
    ("Modem ( 2 Gq / s )", 2, 2000, 0, 2, "Modem ( 2 Gq / s )"),
    ("Modem ( 4 Gq / s )", 2, 4000, 0, 4, "Modem ( 4 Gq / s )"),
    ("Modem ( 6 Gq / s )", 2, 6000, 0, 6, "Modem ( 6 Gq / s )"),
    ("Modem ( 8 Gq / s )", 2, 8000, 0, 8, "Modem ( 8 Gq / s )"),
    ("Modem ( 10 Gq / s )", 2, 10000, 0, 10, "Modem ( 10 Gq / s )"),
    ("Memory ( 8 Gq )", 4, 3000, 0, 8, "Memory ( 8 Gq )"),
    ("Memory ( 16 Gq )", 4, 5500, 0, 16, "Memory ( 16 Gq )"),
    ("Memory ( 24 Gq )", 4, 8000, 0, 24, "Memory ( 24 Gq )"),
    ("Memory ( 32 Gq )", 4, 11000, 0, 32, "Memory ( 32 Gq )"),
    ("Gateway Self Destruct", 5, 20000, 1, 0, "Gateway Self Destruct"),
    ("Gateway Motion Sensor", 5, 10000, 1, 0, "Gateway Motion Sensor"),
]

# ============================================================
# Other constants
# ============================================================
PERCENTAGE_PEOPLEWITHCONVICTIONS = 20
PERCENTAGE_AGENTSWITHCONVICTIONS = 40
REVELATION_RELEASEUNCONTROLLED = 20
LAN_SUBNETRANGE = 1024
LAN_LINKPORTRANGE = 1024
RADIOTRANSMITTER_MINRANGE = 140
RADIOTRANSMITTER_MAXRANGE = 180

# Demo restrictions
DEMO_MAXUPLINKRATING = 4
DEMO_MAXGATEWAY = 2
WAREZ_MAXUPLINKRATING = 5
