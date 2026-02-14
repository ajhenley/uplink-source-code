# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Uplink is a ~110,000-line C++ hacking simulation game by Introversion Software (started 1999). The source comes from the official Uplink Developer CD. Current version is 10.0 (Release), savefile format SAV62 (minimum supported: SAV56).

A browser-based web port (`web/`) reimplements the game using Phaser 3 (TypeScript frontend) and FastAPI (Python backend).

## Build System

### C++ Game — Linux (Makefile-based)

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

### C++ Game — Windows (Visual Studio 2005)

Open `uplink/src/Uplink.sln`. Build configurations: Debug, Release, DemoDebug, DemoRelease, Unoptimised. The VS solution automatically compiles all internal libraries.

Windows installer uses NSIS (`Installer/` directory). Version numbers must be updated in three places: `globals_defines.h`, `Installer/uplink-version.nsh`, and `Installer/data/readme.txt`.

### Web Port (`web/`)

```bash
cd web

make install          # pip install backend + npm install frontend
make run-backend      # uvicorn on :8000 with hot reload
make run-frontend     # Vite dev server on :5173
make test             # pytest (backend tests)
make migrate          # Alembic auto-generate migration
make migrate-up       # Apply pending migrations
make build-frontend   # Production frontend build → frontend/dist
make clean            # Reset DB and caches
```

Database: SQLite by default (async via `aiosqlite`), PostgreSQL supported via `postgresql+asyncpg://`. Configuration uses environment variables with `UPLINK_` prefix (pydantic-settings).

## Architecture

### Core Object Hierarchy (C++)

The game has a clear top-down ownership structure:

**App** (`app/app.h`) → top-level singleton (`extern App *app`), managing lifecycle, paths, options, network
  - **Game** (`game/game.h`) → master controller owning the three major subsystems:
    - **Interface** (`interface/interface.h`) → all UI (local + remote + task manager)
    - **View** (`view/view.h`) → OpenGL rendering, frame rate
    - **World** (`world/world.h`) → simulation state (locations, companies, computers, people, events, plot)

### Serialization System (C++)

All persistent game objects derive from `UplinkObject` (`app/serialise.h`):

- `virtual bool Load(FILE *file)` / `virtual void Save(FILE *file)` — binary serialization
- `virtual char *GetID()` — string identifier
- `virtual int GetOBJECTID()` — unique integer ID (registered as `OID_*` constants in `serialise.h`)
- `virtual void Print()` — debug output
- `virtual void Update()` — periodic tick (optional)

Key patterns:
- **SaveID/LoadID boundaries**: Each object's Save/Load is bracketed with `SaveID("TAG")` / `LoadID("TAG")` and `SaveID_END("TAG")` / `LoadID_END("TAG")` markers to detect corruption.
- **Generic container serialization**: `SaveDArray()`, `LoadDArray()`, `SaveBTree()`, `LoadBTree()` serialize Tosser containers by writing count, then each item's `OBJECTID` + data. `CreateUplinkObject(OBJECTID)` instantiates the correct type on load.
- **Dynamic strings**: `SaveDynamicString()` / `LoadDynamicString()` with 16384-byte max.

### Eclipse UI Framework (C++)

The `lib/eclipse/` library uses a name-based button/widget system with function pointer callbacks:

```cpp
// Registration
EclRegisterButton(x, y, w, h, caption, name);
EclRegisterButtonCallbacks(name, drawFunc, mouseupFunc, mousedownFunc, mousemoveFunc);

// Lookup and state
EclGetButton(name);
EclIsHighlighted();  EclIsClicked();

// Animation
EclRegisterMovement(name, targetX, targetY, time_ms, callback);
EclRegisterResize(name, targetW, targetH, time_ms, callback);
```

Buttons store: position, size, caption, tooltip, `userinfo` (arbitrary app data), optional images for standard/highlighted/clicked states, and draw/mouse callback pointers. All buttons are identified by unique name strings.

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

### Web Port Architecture (`web/`)

**Backend** (`web/backend/`): FastAPI + SQLAlchemy async ORM.
- `app/models/` — SQLAlchemy models: GameSession, Player, Computer, VLocation, Company, RunningTask, ScheduledEvent, Connection
- `app/game/game_loop.py` — Async game loop at 5 Hz. Per-session speed multiplier (0=paused, 1=normal, 3=fast, 8=megafast). Handles task progress, trace advancement, security breach checks (every 40 ticks), event scheduling.
- `app/ws/protocol.py` — WebSocket message types. Client→Server: `heartbeat`, `connect`, `screen_action`, `run_tool`, `stop_tool`, `set_speed`, `accept_mission`, etc. Server→Client: `connected`, `screen_update`, `task_update`, `trace_update`, `game_over`, etc.
- `app/ws/handler.py` — Connection manager mapping session_id → WebSocket. `SessionState` tracks current computer and sub-page navigation.

**Frontend** (`web/frontend/`): Phaser 3.80 + TypeScript + Vite.
- `src/scenes/` — Phaser scenes: Boot, Preload, Login, MainGame, RemoteScreen, TaskManager, GameOver
- `src/net/WebSocketClient.ts` — Pub/sub message handler with auto-reconnect (3s backoff). Token + sessionId in query params.
- `src/ui/panels/` — Modular HUD panels: Email, Finance, Gateway, Hardware, Mission
- `src/ui/screens/` — Remote computer screens: BBS, FileServer, Password, etc.

**Tests** (`web/backend/tests/`): pytest + pytest-asyncio with in-memory SQLite. Run with `cd web && make test`.

### Key Files for Modding (C++)

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
