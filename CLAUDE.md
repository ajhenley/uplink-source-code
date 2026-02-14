# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Uplink is a ~110,000-line C++ hacking simulation game by Introversion Software (started 1999). The source comes from the official Uplink Developer CD. Current version is 10.0 (Release), savefile format SAV62 (minimum supported: SAV56).

## Build System

### Linux (Makefile-based)

Set environment first: `export UPLINKROOT=$(pwd)`

Build order matters — dependencies must be compiled first:

```bash
# 1. External dependencies
cd $UPLINKROOT/contrib && make

# 2. Internal libraries
cd $UPLINKROOT/lib && make

# 3. Game executable
cd $UPLINKROOT/uplink/src && make          # produces uplink.full
```

Distribution targets (from `uplink/src/`):
- `make dist-full` — redistributable full game (output: `dist/full/uplink/lib/uplink.bin.x86`)
- `make dist-demo` — demo distribution
- `make dist-patch` — patch distribution

Compiler: apg++ (autopackage GCC wrapper). Flags defined in `standard.mk`.

### Windows (Visual Studio 2005)

Open `uplink/src/Uplink.sln`. Build configurations: Debug, Release, DemoDebug, DemoRelease, Unoptimised. The VS solution automatically compiles all internal libraries.

Windows installer uses NSIS (`Installer/` directory). Version numbers must be updated in three places: `globals_defines.h`, `Installer/uplink-version.nsh`, and `Installer/data/readme.txt`.

## Architecture

### Core Object Hierarchy

The game has a clear top-down ownership structure:

**App** (`app/app.h`) → top-level singleton managing lifecycle, paths, options, network
  - **Game** (`game/game.h`) → master controller owning the three major subsystems:
    - **Interface** (`interface/interface.h`) → all UI (local + remote + task manager)
    - **View** (`view/view.h`) → OpenGL rendering, frame rate
    - **World** (`world/world.h`) → simulation state (locations, companies, computers, people, events, plot)

### Source Tree (`uplink/src/`)

| Directory | Purpose |
|-----------|---------|
| `app/` | Application core: initialization, OpenGL setup, serialization, globals |
| `game/` | Game controller, obituary system, script library, balancing data |
| `interface/localinterface/` | Player's own HUD: email, world map, IRC, hardware/software managers |
| `interface/remoteinterface/` | 40+ screen types for connected computers (BBS, bank, console, security, etc.) |
| `interface/taskmanager/` | 27+ hacking tools (decrypter, firewall disabler, password breaker, etc.) |
| `world/` | Game entities: VLocation, Company, Computer, Person, Agent, Mission |
| `world/generator/` | Procedural generation: missions, plot, world, news, names |
| `world/scheduler/` | Timed events: arrests, missions, bank robberies, plot progression |
| `world/computer/` | Computer simulation: security, data screens, bank systems, LAN |
| `mainmenu/` | Login, loading, options, theme, obituary screens |
| `network/` | Multi-monitor support, client/server networking |
| `options/` | Game options management |
| `view/` | 3D view rendering |

### Internal Libraries (`lib/`)

| Library | Purpose |
|---------|---------|
| **eclipse** | UI framework — buttons, text fields, icons, animations, panels |
| **gucci** | Graphics layer — image loading (TIFF), font rendering, screen management |
| **soundgarden** | Audio — sound effects and MOD music playback |
| **bungle** | Data file access — reads ZIP-format `.dat` archives |
| **redshirt** | Security/encryption — save games, data file integrity |
| **tosser** | Template data structures — DArray, LList, BTree, hash tables |
| **vanbakel** | Task manager implementation |
| **mmgr** | Memory management and leak detection |
| **common** | Shared utilities and debug infrastructure |

### Key Files for Modding

- **`app/globals_defines.h`** — Build type (`FULLGAME`/`DEMOGAME`/`TESTGAME`), version numbers, cheat flags, debug toggles
- **`game/data/data.h` / `data.cpp`** — All game balance constants: starting money, hardware/software specs, tick rates for every tool, trace speeds, mission probabilities. Changing these requires a full recompile and new profile.
- **`app/opengl_interface.cpp`** — Default rendering for windows, buttons, icons. Start here for graphics changes.
- **`world/generator/missiongenerator.cpp`** — All BBS mission generation and completion checking. Missions follow a standard format.
- **`world/generator/plotgenerator.cpp`** — Background plot script (Acts and Scenes). Reference `other/revelation.doc` for plot breakdown.
- **`world/generator/worldgenerator.cpp`** — Initial world setup. Changes only visible with a new user profile.

### Data Files (`uplink/bin/`)

Binary ZIP archives: `data.dat`, `fonts.dat`, `graphics.dat`, `loading.dat`, `music.dat`, `sounds.dat`, `world.dat`, plus sequential patches (`patch.dat`, `patch2.dat`, `patch3.dat`). Read via the bungle library.

### External Dependencies (`contrib/`)

SDL 1.2.11 (windowing/input), SDL_mixer 1.2.7 (MOD music), OpenGL (rendering), FreeType (fonts), FTGL/GLTT (font rendering), libtiff, libjpeg, zlib, tcp4u 3.31 (networking), irclib (IRC), unrar (SHA1 verification).

## Build Configuration Defines

Key preprocessor defines in `globals_defines.h`:
- `FULLGAME` / `DEMOGAME` / `TESTGAME` — mutually exclusive build types
- `DEBUGLOG_ENABLED` — enables logging to debug.log
- `CODECARD_ENABLED` — code card copy protection (currently disabled)
- `CHEATMODES_ENABLED` — enables cheat codes
- `TESTGAME` — enables all cheats and debug features
