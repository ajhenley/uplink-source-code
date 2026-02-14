# Uplink: Product Requirements Document

## 1. Product Overview

Uplink is a hacking simulation game set in 2010 where the player is an Uplink Agent — a freelance computer hacker operating through a corporation called Uplink. Players accept missions from a bulletin board, hack into corporate and government computer systems, steal and destroy data, manipulate records, launder money, and ultimately become entangled in a global conspiracy involving a self-replicating virus called Revelation.

The game originally shipped as a desktop C++ application (Windows/Linux) with an OpenGL-rendered interface. A browser-based web port reimplements the core gameplay using Phaser 3 (TypeScript) and FastAPI (Python).

**Game Start Date (in-world):** March 24, 2010

---

## 2. Game World

### 2.1 Virtual Locations

Every entity on the internet has a Virtual Location (VLocation) identified by an IP address and mapped to physical X/Y coordinates on a world map. The player navigates between locations by clicking the world map or entering IPs directly.

### 2.2 Companies

The world generates ~30 companies at game start, each with:

- **Size**: Average 20 employees (range 0-40), determines security tier and available screens
- **Alignment**: -50 to +50, affects news framing and plot interactions
- **Growth**: 10% annual average (range -10% to +30%)
- **Boss**: Named NPC who can be targeted by missions

Each company owns one or more computers. Companies with more employees have stronger security systems.

### 2.3 Key Organizations

| Organization | Role |
|---|---|
| **Uplink Corporation** | Player's employer. Hosts the BBS mission board, agent rankings, and internal services. |
| **ARC (Andromeda Research Corporation)** | Developer of the Revelation virus. Controlled by the Andromeda AI. Offers high-paying missions that advance the virus plot. |
| **Arunmor Corporation** | Counter-intelligence group developing Faith, the counter-virus. Offers missions to stop Revelation. |
| **Global Criminal Database** | Government system tracking criminal records worldwide. |
| **International Academic Database** | University records accessible to hackers for data modification missions. |
| **International Social Security Database** | Government social security records. |
| **InterNIC** | Internet registration authority; maps company names to IP addresses. |
| **International Stock Market** | Share trading for all companies. |

### 2.4 Banks

7 banks are generated at game start. Banks offer:

- **Account management**: Balance checking, transfers between accounts
- **Loans**: Small (3,000c max, 20% interest), Medium (7,000c, 40%), Large (10,000c, 70%)
- **Share trading**: Buy/sell company stocks through account screens
- **Interest accrual**: Applied monthly on outstanding loans

### 2.5 People & Agents

- **50 NPCs** generated at start with names, ages, and optional criminal records (20% have convictions)
- **30 NPC Agents** (AI hackers) with Uplink ratings averaging 7 (variance +-7). 40% have criminal convictions.
- NPC agents accept missions, compete with the player, and can be targeted by trace/frame missions

### 2.6 Physical Gateway Locations

Players choose a physical base from 8 cities:

| City | Country |
|---|---|
| London | United Kingdom |
| Tokyo | Japan |
| Los Angeles | USA |
| New York | USA |
| Chicago | USA |
| Moscow | Russia |
| Hong Kong | China |
| Sydney | Australia |

### 2.7 Time System

Game time starts at 00:00, March 24, 2010 (the world itself is generated a month earlier). Time advances continuously. The web port supports speed multipliers: 0x (paused), 1x (normal), 3x (fast), 8x (megafast).

---

## 3. Player Character

### 3.1 Starting Conditions

| Attribute | Starting Value |
|---|---|
| Balance | 3,000 credits |
| Uplink Rating | 0 (Unregistered) |
| Neuromancer Rating | 5 (Neutral) |
| Credit Rating | 10 |
| Gateway CPU | 60 GHz |
| Gateway Memory | 24 Gq |
| Gateway Modem | 1 Gq/s |
| Pre-installed Software | File Copier V1.0, File Deleter V1.0 |

### 3.2 Uplink Rating

Measures hacking skill and reputation. Advances by completing missions. Higher ratings unlock harder, better-paying missions.

| Threshold | Title |
|---|---|
| 0 | Unregistered |
| 1 | Registered |
| 2 | Beginner |
| 6 | Novice |
| 15 | Confident |
| 35 | Intermediate |
| 60 | Skilled |
| 90 | Experienced |
| 125 | Knowledgeable |
| 160 | Uber-Skilled |
| 220 | Professional |
| 300 | Elite |
| 400 | Mage |
| 600 | Expert |
| 1000 | Veteran |
| 1500 | Techno-mage |
| 2500 | TERMINAL |

### 3.3 Neuromancer Rating

Measures moral alignment. Positive values indicate activism/anarchy; negative values indicate malice/indiscrimination. Changes based on mission type completed.

| Threshold | Title |
|---|---|
| -1024 | Morally Bankrupt |
| -512 | Sociopathic |
| -128 | Indiscriminate |
| -32 | Notorious |
| -16 | Untrustworthy |
| 0 | Neutral |
| 32 | Aggressive |
| 64 | Single Minded |
| 256 | Activist |
| 1024 | Anarchic |
| 2048 | Revolutionary |

**Score changes by mission type:**

| Mission | Change |
|---|---|
| Steal File | 0 |
| Destroy File | +5 |
| Find Data | 0 |
| Change Data | -5 |
| Frame User | -20 |
| Trace User | -30 |
| Change Account | -10 |
| Remove Computer | +30 |
| Remove Company | +60 |
| Remove User | -60 |

### 3.4 Monthly Costs

- **Uplink subscription**: 300 credits/month (mandatory)
- **Gateway rental**: 1,000 credits for a new gateway
- **Trade-in**: 75% refund on old gateway value

---

## 4. Gateway (Player's Home Computer)

The gateway is the player's personal machine. All hacking software runs from it and all connections originate from it.

### 4.1 CPU Upgrades

| Model | Speed | Cost |
|---|---|---|
| CPU (20 GHz) | 20 GHz | 250c |
| CPU (60 GHz) | 60 GHz | 1,000c |
| CPU (80 GHz) | 80 GHz | 1,300c |
| CPU (100 GHz) | 100 GHz | 3,000c |
| CPU (120 GHz) | 120 GHz | 5,000c |
| CPU (150 GHz) | 150 GHz | 8,000c |
| CPU Turbo (200 GHz) | 200 GHz | 12,000c |

CPU speed directly affects how fast hacking tools operate (higher = faster).

### 4.2 Modems

| Model | Speed | Cost |
|---|---|---|
| Modem (1 Gq/s) | 1 Gq/s | 1,000c |
| Modem (2 Gq/s) | 2 Gq/s | 2,000c |
| Modem (4 Gq/s) | 4 Gq/s | 4,000c |
| Modem (6 Gq/s) | 6 Gq/s | 6,000c |
| Modem (8 Gq/s) | 8 Gq/s | 8,000c |
| Modem (10 Gq/s) | 10 Gq/s | 10,000c |

### 4.3 Memory

| Model | Capacity | Cost |
|---|---|---|
| Memory (8 Gq) | 8 Gq | 3,000c |
| Memory (16 Gq) | 16 Gq | 5,500c |
| Memory (24 Gq) | 24 Gq | 8,000c |
| Memory (32 Gq) | 32 Gq | 11,000c |

Software and stolen files consume memory. The Defrag tool consolidates fragmented space.

### 4.4 Security Hardware

| Item | Cost | Effect |
|---|---|---|
| Gateway Self Destruct | 20,000c | Destroys gateway and all evidence when activated |
| Gateway Motion Sensor | 10,000c | Detects people approaching physical gateway location |

---

## 5. Software Catalog

All software is purchased from vendor computers, stored in gateway memory, and run via the task manager.

### 5.1 Cracking Tools

| Software | Versions | Cost Range | Size | Function |
|---|---|---|---|---|
| Password Breaker | V1.0 | 1,500c | 2 Gq | Cracks passwords letter-by-letter. Guaranteed but slow. |
| Dictionary Hacker | V1.0 | 1,000c | 4 Gq | Fast dictionary attack (10,000 words). Not guaranteed. |
| Decrypter | V1.0-V7.0 | 800-15,000c | 2-5 Gq | Decrypts files encrypted by matching Encrypter version or below. |
| Decypher | V1.0-V3.0 | 3,000-8,000c | 2 Gq | Breaks Elliptic-curve Encryption Cyphers. |

### 5.2 File Utilities

| Software | Versions | Cost | Size | Function |
|---|---|---|---|---|
| File Copier | V1.0 | 100c | 1 Gq | Copies files between databanks. Free to all agents. |
| File Deleter | V1.0 | 100c | 1 Gq | Deletes files from databanks. Free to all agents. |
| Defrag | V1.0 | 5,000c | 2 Gq | Consolidates files in memory to free contiguous space. |

### 5.3 Security/Log Tools

| Software | Versions | Cost Range | Function |
|---|---|---|---|
| Log Deleter | V1.0-V4.0 | 500-4,000c | V1: empties log content. V2: deletes log entry (leaves gap). V3: overwrites with legitimate user's log. V4: shifts other logs to cover — undetectable. |
| Log Modifier | V1.0-V2.0 | 4,000-6,000c | Modifies existing log entries. V2 can create new logs in blank spaces. |
| Log UnDeleter | V1.0 | 5,000c | Recovers previously deleted logs. |
| Firewall Disable | V1.0-V5.0 | 2,000-8,000c | Disables firewalls (triggers immediate detection). Handles security levels 1-5. |
| Proxy Disable | V1.0-V5.0 | 3,000-10,000c | Disables proxy servers (triggers detection). |

### 5.4 Bypass Tools (require HUD: Connection Analysis)

| Software | Versions | Cost Range | Function |
|---|---|---|---|
| Firewall Bypass | V1.0-V5.0 | 3,000-10,000c | Silently bypasses firewalls. Handles security levels 1-5. |
| Proxy Bypass | V1.0-V5.0 | 6,000-20,000c | Silently bypasses proxy servers. |
| Monitor Bypass | V1.0-V5.0 | 10,000-25,000c | Silently bypasses security monitors. |

### 5.5 Trace & Reconnaissance Tools

| Software | Versions | Cost Range | Function |
|---|---|---|---|
| Trace Tracker | V1.0-V4.0 | 300-2,500c | V1: trace/no-trace indicator. V2: percentage. V3: time remaining. V4: exact time estimate. |
| IP Lookup | V1.0 | 500c | Converts raw IP to named address and adds to player's links. |
| IP Probe | V1.0-V3.0 | 2,000-5,000c | V1: lists security types. V2: adds version info. V3: adds status info. |
| Voice Analyser | V1.0-V2.0 | 5,000-10,000c | Records/analyses voice patterns. V2 can save/load voice data. |

### 5.6 LAN Tools (require HUD: LAN View)

| Software | Versions | Cost Range | Function |
|---|---|---|---|
| LAN Scan | V1.0-V3.0 | 10,000-25,000c | Scans entire LAN for connected systems. |
| LAN Probe | V1.0-V3.0 | 15,000-30,000c | Probes single LAN system and its connecting links. |
| LAN Spoof | V1.0-V3.0 | 20,000-45,000c | Impersonates a LAN system. V1: level 1 only. V3: all levels. |
| LAN Force | V1.0-V3.0 | 15,000-25,000c | Forces open LAN lock systems (alerts sysadmin). |

### 5.7 HUD Upgrades

| Software | Cost | Size | Function |
|---|---|---|---|
| HUD: Connection Analysis | 20,000c | 3 Gq | Shows security systems on target; required for all Bypass tools. |
| HUD: IRC Client | 4,000c | 2 Gq | Enables Internet Relay Chat with other hackers. |
| HUD: Map Show Trace | 5,000c | 1 Gq | Visualizes trace progress on the world map. Replaces Trace Tracker. |
| HUD: LAN View | 50,000c | 5 Gq | Required for all LAN tools. Enables LAN topology visualization. |

### 5.8 Special Software

| Software | Function |
|---|---|
| Revelation | Self-replicating virus. Doubles in size every 3 minutes. Plot-critical. |
| Revelation Tracker | Monitors which computers are infected with Revelation. |
| Faith | Counter-virus to Revelation. Plot-critical. |

---

## 6. Connection & Routing System

### 6.1 Bounce Chain

Before connecting to a target, the player builds a route through intermediate servers (bounce chain). The connection path is:

**Player Gateway -> Bounce Server 1 -> Bounce Server 2 -> ... -> Target**

Each link in the chain adds time before a trace can reach the player. The player adds/removes bounce servers by clicking locations on the world map.

### 6.2 Trace Mechanics

When a player connects to a computer with active security monitoring, a trace begins. The trace traverses the bounce chain backwards toward the player's gateway.

**Trace speed** depends on the target computer type (seconds per hop):

| Computer Type | Seconds/Hop |
|---|---|
| Public Access Server | Never traces (-1) |
| Central Mainframe | 5 |
| Public Bank Server | 5 |
| Internal Services Machine | 15 |
| Global Criminal Database | 10 |
| International Social Security DB | 15 |
| Stock Market | 20 |
| Central Medical Database | 25 |
| International Academic Database | 35 |

**Access level modifiers** on bounce servers:

| Access Level | Multiplier |
|---|---|
| No account on bounce server | 0.1x (slowest trace) |
| Account on bounce server | 0.7x |
| Admin access on bounce server | 1.0x |
| Central mainframe routing | 1.3x |
| Bank admin routing | 1.6x (fastest trace) |

If a trace completes (reaches the player's gateway), the game triggers consequences based on the target's security posture.

---

## 7. Computer Systems

### 7.1 Computer Types & Hack Difficulties

Difficulty is measured in "ticks per character" for password cracking:

| Type | Difficulty |
|---|---|
| Public Access Server | 6 |
| Uplink Test Machine | 30 |
| Uplink Public Access | 30 |
| Internal Services Machine | 45 |
| LAN Terminal | 75 |
| Central Mainframe | 80 |
| International Academic Database | 90 |
| Public Bank Server | 100 |
| International Social Security DB | 120 |
| Central Medical Database | 120 |
| Stock Market | 120 |
| LAN Authentication Server | 150 |
| Global Criminal Database | 180 |
| LAN Modem | 200 |
| Public Bank Admin Server | 300 |
| LAN Log Server | 300 |
| Uplink Internal Services | 300 |
| Global Intelligence Agency | 450 |
| LAN Main Server | 500 |
| ARC/Arunmor Central Mainframe | 600 |
| ProtoVision | Unhackable (-1) |

### 7.2 Security Systems

Computers can have multiple security layers (each at levels 1-5):

- **Password** — Text password entry. Cracked with Password Breaker or Dictionary Hacker.
- **Firewall** — Blocks unauthorized access. Disabled or bypassed with appropriate tools.
- **Proxy** — Hides real server identity. Disabled or bypassed.
- **Monitor** — Detects intrusions and initiates traces. Bypassed silently or triggers detection.
- **Encryption Cypher** — 30x14 grid puzzle requiring Decypher software.
- **Voice Analysis** — Biometric voice authentication requiring Voice Analyser.
- **High Security Screen** — Multi-layered security cascade requiring all preceding layers bypassed.

### 7.3 Screen Types

When connected to a computer, the player interacts through screens. 37 screen types exist:

**Authentication Screens:**
- Password Screen, UserID Screen, Voice Analysis Screen, Cypher Screen, High Security Screen, Code Card Screen

**Information/Data Screens:**
- File Server Screen, Log Screen, BBS Screen (mission board), Menu Screen, Message Screen, Links Screen, News Screen, Ranking Screen, Company Info Screen

**Database Screens:**
- Record Screen, Criminal Screen, Academic Screen, Social Security Screen

**Financial Screens:**
- Account Screen, Loans Screen, Shares List Screen, Shares View Screen

**Administrative Screens:**
- Console Screen (command-line: DIR, CD, RUN, DELETEALL, SHUTDOWN, DISCONNECT, etc.), Security Screen, Contact Screen

**Commercial Screens:**
- Software Sales Screen, Hardware Sales Screen

**Special Screens:**
- Faith Screen, Voice Phone Screen, Nearest Gateway Screen, Change Gateway Screen, Disconnected Screen, ProtoVision Screen, Nuclear War Screen, Radio Transmitter Screen

---

## 8. Mission System

### 8.1 Standard Missions

Missions appear on BBS boards. Types, minimum difficulties, and base payments:

| Type | Name | Min Difficulty | Base Payment |
|---|---|---|---|
| 1 | Steal File | 2 | 900c |
| 1 | Steal All Files | 5 | 1,500c |
| 2 | Destroy File | 2 | 800c |
| 2 | Destroy All Files | 5 | 1,400c |
| 3 | Find Data | 2 | 1,000c |
| 3 | Find Data (Financial) | 5 | 1,200c |
| 4 | Change Data (Academic) | 3 | 1,000c |
| 4 | Change Data (Social Security) | 4 | 1,200c |
| 4 | Change Data (Criminal) | 5 | 1,500c |
| 5 | Frame User | 9 | 2,200c |
| 6 | Trace User | 7 | 1,800c |
| 7 | Change Account (Bank) | 7 | 1,700c |
| 8 | Remove Computer | 6 | 1,600c |
| 9 | Remove Company | 8 | 2,000c |
| 10 | Remove User | 8 | 1,900c |
| 20 | Pay Fine | N/A | N/A (penalty) |

**Payment formula:** base_payment * difficulty * (1 +/- 30% variance), rounded to nearest 100c. Maximum negotiable: 110% of calculated base.

**Difficulty scaling:** Generated using normal distribution with variance of +/-2 from minimum. Central Mainframe targets add +1 difficulty; LAN targets add +2. Maximum difficulty is 10.

### 8.2 Mission Availability by Player Rating

Mission types unlock as the player's Uplink rating increases:

- **Rating 0-2**: Steal File, Destroy File dominate
- **Rating 3-5**: Change Data missions become common
- **Rating 6**: Remove Computer becomes available
- **Rating 7**: Trace User, Change Account available
- **Rating 8**: Remove User, Remove Company available
- **Rating 9+**: Frame User available
- **Rating 11+**: All types available in balanced distribution

### 8.3 Mission Generation

- New missions generated every 12 hours (game time)
- Demo mode generates missions every 4 hours
- Old missions expire after 30 days
- NPC agents are assigned missions every 8 hours

### 8.4 Payment Methods

- **AFTERCOMPLETION**: Full payment on completion (most common)
- **HALFATSTART**: 50% upfront, 50% on completion
- **ALLATSTART**: Full payment immediately

---

## 9. Plot System (Revelation / Faith)

### 9.1 Overview

The background plot involves a conspiracy between three factions. The player can side with ARC (advancing the virus), Arunmor (stopping it), or remain neutral. The plot unfolds across 6 Acts with ~40 individual scenes, driven by the PlotGenerator system.

### 9.2 Act Structure

**Act 1: The Revelation Begins (8 Scenes)**
- ARC begins work on Revelation
- ARC hires top Uplink agents, creating competitive pressure
- An agent raises suspicions about ARC activity
- ARC publishes a cover story; the journalist is subsequently murdered
- A posthumous warning email is sent to the player
- Uplink Corporation issues a general warning

**Act 2: The Turning Point (3 Scenes)**
- ARC releases the "Maiden Flight" mission — a test of Revelation V1.0
- An NPC agent completes Maiden Flight, proving the virus works
- Arunmor makes contact with the player, offering counter-missions

**Act 3: Revelation Released (4 Scenes)**
- First Revelation attack reported in the news
- Arunmor begins developing Faith (the counter-virus)
- Arunmor announces their counter-strategy publicly
- Federal investigators reveal Andromeda (the AI controlling ARC)

**Act 4: The Arms Race (15 Scenes)**
- Multiple special missions become available from both factions
- Arunmor missions: Tracer, Take Me To Your Leader, ARC Infiltration
- ARC missions: Darwin, Save It For The Jury, Shiny Hammer
- NPC agents attempt faction missions in parallel
- News coverage of each operation

**Act 5: The Endgame (7 Scenes)**
- Arunmor warns of imminent Revelation release
- Final missions become available: Grand Tour (ARC) and CounterAttack (Arunmor)
- Loyalty-based branching: Pro-Arunmor, Pro-ARC, or Neutral paths
- Andromeda launches Revelation at random systems
- ARC can be busted by federal agents
- If Revelation spreads uncontrolled: Game Over (internet destroyed)

**Act 6: Resolution (3 Scenes)**
- Andromeda leader's press statement
- ARC/Arunmor leaders sentenced
- Economic consequences of outcome

### 9.3 Special Plot Missions

**Arunmor-aligned (5 missions):**

| Mission | Payment | Description |
|---|---|---|
| Tracer | 10,000c | Covert installation of a tracer on ARC systems |
| Take Me To Your Leader | 30,000c | Bring CEO of major company into custody |
| ARC Infiltration | 30,000c | Infiltrate ARC's internal network |
| CounterAttack | 50,000c | Launch Faith counter-virus (final mission) |
| Backfire | 15,000c | Counter-intelligence operation |

**ARC-aligned (5 missions):**

| Mission | Payment | Description |
|---|---|---|
| Maiden Flight | 10,000c | Test run of Revelation V1.0 |
| Darwin | 15,000c | Steal research on digital life forms |
| Save It For The Jury | 20,000c | Frame Arunmor's chief tech |
| Shiny Hammer | 30,000c | Destroy all Arunmor research |
| Grand Tour | 50,000c | Release Revelation into the wild (final mission) |

### 9.4 Player Loyalty & Endings

- **playerloyalty = -1**: Sided with ARC. Completing ARC missions moves loyalty negative.
- **playerloyalty = 0**: Neutral. Neither faction's endgame applies directly.
- **playerloyalty = 1**: Sided with Arunmor. Completing Arunmor missions moves loyalty positive.

**Possible endings:**
1. **Arunmor Victory**: Player completes CounterAttack; Faith neutralizes Revelation
2. **ARC Victory**: Revelation spreads uncontrolled; internet destroyed; Game Over
3. **ARC Busted**: Federal agents arrest ARC leadership; Andromeda neutralized
4. **Neutral outcome**: Player didn't commit to either side; Arunmor attempts endgame independently

---

## 10. Consequence System

### 10.1 Security Breach Detection

Security breaches are checked every 8 hours (game time). When a computer's trace catches a hacker:

1. **Criminal record entry**: "Unauthorised systems access" added
2. **Rating penalties**: Uplink and Neuromancer ratings decrease (severity scales with company size)
3. **Trace actions** (bitfield, can combine):
   - DISCONNECT: Immediate forced disconnection
   - WARNINGMAIL: Email warning (no penalty)
   - LEGALACTION: Federal arrest scheduled in 3 hours (2-minute advance warning)
   - TACTICALACTION: Armed response in 5 minutes (1-minute warning)

### 10.2 Legal Consequences Timeline

| Event | Timing | Warning |
|---|---|---|
| Warning email | Immediate | N/A |
| Fine deadline | 7 days | N/A |
| Legal action (arrest) | 3 hours after deadline | 2 minutes |
| Tactical action (raid) | 5 minutes after arrest fails | 1 minute |
| Bank robbery trace | 2 minutes to cover tracks | None |

### 10.3 Game Over Conditions

1. **Federal Arrest** — Caught by tracing
2. **Shot By Feds** — Tactical response to serious crimes
3. **Caught Money Transfer** — Failed to delete logs within 2-minute window
4. **Revelation Uncontrolled** — ARC's virus destroys the internet
5. **Gateway Seizure** — Federal agents confiscate equipment
6. **Demo Rating Exceeded** — Demo mode cap reached (rating 4)
7. **Warez Detection** — Pirated copy detected (rating 5 cap, 60-minute max playtime)

### 10.4 Obituary

When the game ends, the system records:

- Character name, final balance, final ratings
- Special missions completed (bitfield)
- People affected, systems destroyed, high-security hacks completed
- Final score and cause of death/game end
- Winning code (for legitimate completions)

---

## 11. News System

Dynamic news articles are generated in response to game events:

- **Computer Hacked** — Escalating stories for repeat hacks (1st hack, 2nd hack, 3rd+)
- **Computer Destroyed** — System destruction coverage
- **All Files Stolen/Deleted** — Data breach/loss stories
- **Person Arrested** — Federal law enforcement action coverage
- **Plot Events** — Act/Scene progression news (ARC activities, Arunmor announcements, virus outbreaks)

Each story has a headline, 6-part body (intro, frequency context, date, consequences, promised response, miscellaneous), and auto-expires after 30 days.

---

## 12. Scheduled Events System

The EventScheduler maintains timed events that fire at specific game dates:

### 12.1 Recurring Events

| Event | Frequency |
|---|---|
| Generate new missions | Every 12 hours |
| Check security breaches | Every 8 hours |
| Check mission due dates | Every 1 day |
| Give mission to NPC agent | Every 8 hours |
| Expire old news/logs/missions | Every 7 days |
| Add interest on loans | Every 30 days |
| Uplink monthly fee (300c) | Every 30 days |
| Company growth | Annually |

### 12.2 One-Time Events

| Event | Trigger | Effect |
|---|---|---|
| ArrestEvent | Legal action timer | Player/NPC arrested, removed from game |
| ShotByFedsEvent | Tactical action timer | Person killed |
| SeizeGatewayEvent | Serious crime | Gateway confiscated (10-min warning) |
| BankRobberyEvent | Money transfer | 2-minute window to cover tracks |
| InstallHardwareEvent | Hardware purchase | 14 hours delivery (30-min warning) |
| ChangeGatewayEvent | Gateway upgrade | 24 hours to swap |
| RunPlotSceneEvent | Story progression | Triggers next plot Act/Scene |

---

## 13. Local Interface (Player HUD)

The player's gateway interface consists of:

### 13.1 HUD Components

- **World Map** — Interactive map showing all virtual locations. Click to add/remove from bounce chain. Shows trace progress if HUD: Map Show Trace is installed.
- **Connection Bar** — Displays current bounce chain, connect/disconnect buttons, target IP
- **Toolbar** — Quick access buttons for all panels
- **Status Display** — Balance, ratings, game speed, date/time

### 13.2 Panels

| Panel | Function |
|---|---|
| Email | Receive mission offers, warnings, plot messages, and system notifications |
| Finance | View bank accounts, apply for loans, check balance and credit rating |
| Hardware Manager | View and upgrade CPU, modem, memory, security hardware |
| Software Manager | Browse installed software organized by category; launch tools |
| Memory Screen | Manage local file storage; view files, copy/delete, check usage |
| Status Screen | View Uplink rating, Neuromancer rating, credit rating |
| Mission Screen | View accepted missions with objectives, payment, time remaining |
| IRC Client | Chat with other hackers (requires HUD: IRC Client) |
| LAN Interface | View and interact with LAN topologies (requires HUD: LAN View) |
| Gateway Display | Physical gateway status: name, location, hardware installed |

---

## 14. Task Manager (Hacking Tool Execution)

All hacking tools run through the Task Manager. Multiple tools can run simultaneously. Each tool has tick-based progress affected by CPU speed.

### 14.1 Tool Tick Requirements

| Tool | Ticks Required | Notes |
|---|---|---|
| File Copy | 45 per unit size | Scaled by file size |
| File Delete | 9 per unit size | Scaled by file size |
| Decrypt | 90 per character | Scaled by encryption strength |
| Defrag | 3 per memory slot | Consolidates fragmented space |
| Dictionary Hack | 0.2 per word | Tests 10,000 word dictionary |
| Log Delete | 60 per log | Entire log operation |
| Log Modify | 50 per log | Entire log operation |
| Log UnDelete | 60 per log | Entire log operation |
| Analyze Firewall | 40 per firewall | Before disable |
| Disable Firewall | 80 per firewall | After analysis |
| Analyze Proxy | 50 per proxy | Before disable |
| Disable Proxy | 100 per proxy | After analysis |
| Bypass Cypher | 0.1 per element | 30x14 grid = 420 elements |
| LAN Scan (single) | 70 per system | Individual system |
| LAN Scan (full) | 300 total | Entire LAN |
| LAN Link Scan | 100 for all ports | Up to 1024 ports |
| LAN Spoof | 100 per system | Impersonation |
| LAN Force Lock | 100 per lock | Alerts sysadmin |

CPU speed modifier: `base_cpu_speed / player_cpu_speed` (faster CPU = fewer real ticks needed).

---

## 15. Script Library

23 scripted functions handle specific game sequences:

| ID Range | Category | Examples |
|---|---|---|
| 10-13 | Banking | Money transfer, create/close bank account, stock market account |
| 15-17 | Record Access | Search criminal, academic, social security databases |
| 30-43 | Game Start | Opening sequence, registration, gateway connection, OS download, tutorial |
| 45-47 | Patching | Install new patch, show release notes, show recommendations |
| 50-51 | Gateway | Bill player for gateway rental, handle decline |
| 60-63 | Plot Emails | Manage Act 1 warning emails (cancel/view) |
| 70-72 | Agent List | Uplink_Agent_List program, offer money for list, agents killed consequence |
| 80-83 | LAN Controls | Enable/disable LAN locks and isolation bridges |
| 90-93 | Login | New game creation, load game, connection animations |

---

## 16. Cheat Codes (TESTGAME Build Only)

Available when compiled with `TESTGAME` define:

| Cheat | Effect |
|---|---|
| All Links | Access to all IP addresses |
| All Software | Fill memory to 256 Gq, give all software |
| All Hardware | Give all hardware upgrades |
| Lots Of Money | Add 10,000 credits |
| Next Rating | Increment Uplink rating by 1 |
| Max Ratings | Set Uplink rating to TERMINAL (16) |
| Cancel Trace | End current trace immediately |
| End Game | Simulate being shot by feds in 5 seconds |
| Debug Print | Dump all system data to console |
| Event Queue | Open event scheduler view |
| Show LAN | Reveal all LAN systems and links |
| Run Revelation | Spawn Revelation virus at 5 locations |

---

## 17. Build Configurations

| Define | Effect |
|---|---|
| FULLGAME | Complete release version. No restrictions. |
| DEMOGAME | Limited version: max Uplink rating 4, restricted missions, no story completion |
| TESTGAME | All cheats and debug features enabled |
| DEBUGLOG_ENABLED | Logging to debug.log |
| CODECARD_ENABLED | Code card copy protection (currently disabled) |
| CHEATMODES_ENABLED | Enables cheat codes |
| VERIFY_UPLINK_LEGIT | Warez/steam version detection |
| GAME_WINNING_CODE | Shows completion code on game win |

---

## 18. Main Menu Screens

| Screen | Purpose |
|---|---|
| Login | New Game, Load Game, Options, Exit |
| Loading | Save file loading |
| First Load | First-time tutorial/introduction |
| Options | Graphics, Sound, Network, Themes configuration |
| Obituary | Game over stats display |
| Connection Lost | Network disconnect handling |
| Disavowed | Player disavowed by Uplink Corporation |
| The Team | Credits |
| Revelation Won | Victory screen (Arunmor ending) |
| Revelation Lost | Defeat screen (ARC ending) |
| Demo Game Over | Demo version limit reached |
| Warez Game Over | Piracy detection triggered |

### 18.1 Graphics Options

- Screen resolution (default 1024x768), color depth, refresh rate
- Fullscreen toggle
- Button animations toggle with optional faster speed
- Safe mode, software mouse, software rendering
- World map theme selection (default or DEFCON map)
- Custom color themes with per-theme palette overrides

---

## 19. Web Port (Current Implementation)

### 19.1 Technology Stack

- **Backend**: FastAPI, SQLAlchemy (async), SQLite/PostgreSQL, JWT auth, bcrypt
- **Frontend**: Phaser 3.80, TypeScript, Vite
- **Communication**: REST API for CRUD, WebSocket for real-time game loop

### 19.2 Implemented Features (Phases 1-8)

| Feature | Status |
|---|---|
| Core architecture (DB, API, WebSocket) | Complete |
| World generation (companies, computers, locations, NPCs) | Complete |
| Connection/bounce routing system | Complete |
| Screen navigation (password, menu, file server, BBS, log, shops) | Complete |
| 5 hacking tools (Password Breaker, File Copier, File Deleter, Log Deleter, Trace Tracker) | Complete |
| Trace system with bounce chain defense | Complete |
| 4 mission types (steal, destroy, find, change) | Complete |
| Security breach detection and consequences | Complete |
| Hardware/software purchasing | Complete |
| HUD, world map, connection bar, task manager overlay | Complete |
| CRT overlay effect | Complete |
| Email system | Complete |

### 19.3 Not Yet Implemented in Web Port

- Full plot/narrative system (Acts 1-6, special missions)
- Advanced mission types (frame, trace, remove computer/company/user, change account)
- LAN hacking systems
- Bank robbery and money laundering mechanics
- Share/stock trading
- Loan system with interest
- News generation system
- IRC chat
- NPC agent AI and competition
- Voice analysis, cypher, and advanced security screens
- Criminal/academic/social security record screens
- Console screen (command-line interface)
- Multiple gateway locations and upgrades
- Cheat system
- Save/load serialization
- Tutorial system
- ~18 of 37 remote screen types

### 19.4 Web Port Game Loop

Runs at 5 Hz (200ms ticks). Each tick:

1. Advance all running tasks by speed multiplier
2. Advance all active traces
3. Check for completed traces (game over if reached)
4. Every 40 ticks (~8s): check for security breaches, start new traces
5. Process scheduled events (warnings, fines, arrests, mission generation)
6. Increment game time
7. Broadcast updates via WebSocket

### 19.5 WebSocket Protocol

**Client-to-server messages:** heartbeat, bounce_add, bounce_remove, connect, disconnect, screen_action, run_tool, stop_tool, set_speed, accept_mission, complete_mission

**Server-to-client messages:** heartbeat_ack, bounce_chain_updated, connected, disconnected, screen_update, task_update, task_complete, trace_update, trace_complete, balance_changed, rating_changed, message_received, game_over, error
