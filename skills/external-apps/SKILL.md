---
name: external-apps
description: Use when the user needs to control or automate external GUI/desktop applications. This skill provides a catalog of 69 pre-built CLI harnesses (via CLI-Anything) for software like LibreOffice, Draw.io, Blender, GIMP, OBS Studio, Zoom, Zotero, Ollama, and more. When the user mentions an application, look it up in the catalog below and read apps/<app-name>.md for the specific operation guide. Each sub-skill file contains the CLI commands, element paths, and JSON output formats for that application.
---

# External Application Control

This skill catalogs CLI-Anything harnesses — AI-native command-line interfaces auto-generated from real GUI applications. Each harness calls the application's actual backend API (not GUI simulation), outputs deterministic `--json`, and supports `--help` self-description.

## Important: Installation Required

Harnesses are NOT pre-installed. Before using any app, install it:
```bash
pip install cli-anything-<app-name>
```
Verify with `which cli-anything-<app-name>`. If not installed, tell the user and offer to install it.

## Application Not In Catalog?

If the user mentions an application NOT listed below, respond: "This application does not have a pre-built CLI-Anything harness. You can create one by running `/cli-anything /path/to/app` — this auto-generates a CLI harness from the application's source code." **Never fabricate commands for unlisted apps.**

## How to use

1. Identify the application the user wants to control
2. Find it in the categorized catalog below
3. Read `apps/<app-name>.md` for the complete operation guide
4. Execute CLI commands as documented, always use `--json` for machine-readable output

All harnesses follow the same contract: `cli-anything-<app> <command> --json`.

## Application Catalog

### Office & Documents
| App | File | Description |
|-----|------|-------------|
| LibreOffice | `apps/libreoffice.md` | Word/Excel/PPT creation, editing, PDF export |
| Draw.io | `apps/drawio.md` | Diagram and flowchart creation |
| Mermaid | `apps/mermaid.md` | Text-to-diagram rendering |
| NotebookLM | `apps/notebooklm.md` | AI-powered research notebook |
| Calibre | `apps/calibre.md` | E-book library management |

### Knowledge & Research
| App | File | Description |
|-----|------|-------------|
| Zotero | `apps/zotero.md` | Reference management, paper organization |
| Obsidian | `apps/obsidian.md` | Knowledge base, note-taking with backlinks |
| Joplin | `apps/joplin.md` | Open-source note-taking |
| SiYuan | `apps/siyuan.md` | Local-first knowledge management |

### Terminals & Browsers
| App | File | Description |
|-----|------|-------------|
| iTerm2 | `apps/iterm2.md` | macOS terminal automation |
| Browser | `apps/browser.md` | Generic browser automation |
| Safari | `apps/safari.md` | macOS Safari control |
| iTerm2 CTL | `apps/iterm2-ctl.md` | iTerm2 low-level control |

### Media & Design
| App | File | Description |
|-----|------|-------------|
| Blender | `apps/blender.md` | 3D modeling, rendering, animation |
| GIMP | `apps/gimp.md` | Image editing and manipulation |
| Inkscape | `apps/inkscape.md` | Vector graphics editor |
| Krita | `apps/krita.md` | Digital painting |
| Audacity | `apps/audacity.md` | Audio editing and recording |
| MuseScore | `apps/musescore.md` | Music notation and composition |
| Shotcut | `apps/shotcut.md` | Video editing |
| Kdenlive | `apps/kdenlive.md` | Professional video editing |
| OBS Studio | `apps/obs-studio.md` | Screen recording and live streaming |
| ComfyUI | `apps/comfyui.md` | Stable Diffusion workflow |
| VideoCaptioner | `apps/videocaptioner.md` | Video captioning and subtitles |
| Live2D | `apps/live2d.md` | 2D animation for avatars |

### Development & DevOps
| App | File | Description |
|-----|------|-------------|
| Ollama | `apps/ollama.md` | Local LLM management |
| ChromaDB | `apps/chromadb.md` | Vector database |
| PM2 | `apps/pm2.md` | Node.js process manager |
| n8n | `apps/n8n.md` | Workflow automation |
| Dify Workflow | `apps/dify-workflow.md` | AI application workflow |
| WireMock | `apps/wiremock.md` | HTTP mock server |
| RenderDoc | `apps/renderdoc.md` | Graphics debugger |
| LLDB | `apps/lldb.md` | Debugger |
| Nsight Graphics | `apps/nsight-graphics.md` | GPU frame debugger |
| Unreal Insights | `apps/unrealinsights.md` | Game engine profiling |

### 3D & CAD
| App | File | Description |
|-----|------|-------------|
| FreeCAD | `apps/freecad.md` | Parametric 3D CAD |
| Godot | `apps/godot.md` | Game engine |
| s&box | `apps/sbox.md` | Game development platform |
| CloudCompare | `apps/cloudcompare.md` | 3D point cloud processing |
| 3MF | `apps/threemf.md` | 3D manufacturing format |
| EEZ Studio | `apps/eez-studio.md` | Embedded GUI design |

### Communication & Web
| App | File | Description |
|-----|------|-------------|
| Zoom | `apps/zoom.md` | Video conferencing control |
| Mailchimp | `apps/mailchimp.md` | Email marketing |
| Exa | `apps/exa.md` | AI search engine |
| Novita | `apps/novita.md` | AI API platform |
| MiniMax | `apps/minimax.md` | AI model platform |

### System & Utilities
| App | File | Description |
|-----|------|-------------|
| AdGuard Home | `apps/adguardhome.md` | DNS-level ad blocking |
| Jumpserver | `apps/jumpserver.md` | Bastion host / privileged access |
| Firefly III | `apps/firefly-iii.md` | Personal finance manager |
| OpenRefine | `apps/openrefine.md` | Data cleaning and transformation |
| OpenScreen | `apps/openscreen.md` | Screen sharing |
| RMS | `apps/rms.md` | Resource management |
| Sketch | *(unavailable)* | Design tool — harness pending |
| Mubu | `apps/mubu.md` | Mind mapping and outlining |
| UniMol Tools | `apps/unimol-tools.md` | Molecular science tools |
| Web-Yu-Pri | `apps/web-yu-pri.md` | Web printer utility |
| Tigris | `apps/tigris.md` | Serverless data platform |

### CLI-Anything Internal
| App | File | Description |
|-----|------|-------------|
| MacroCLI | `apps/macrocli.md` | Macro recording and playback |
| CLI-Hub Meta | *(meta-skill, no standalone file)* | Self-updating catalog — see source repo |
| CC-Switch | `apps/ccswitch.md` | Claude Code session switcher |
| AnyGen | `apps/anygen.md` | Generic code generator |
| SeaClip | `apps/seaclip.md` | Clipboard manager |
| WaveTone | `apps/wavetone.md` | Audio tone generator |
| QuietShrink | `apps/quietshrink.md` | File compression |
| IntelWatch | `apps/intelwatch.md` | System monitoring |
| NSLogger | `apps/nslogger.md` | Structured logging |
| CloudAnalyzer | `apps/cloudanalyzer.md` | Cloud resource analysis |
| Slay the Spire II | `apps/slay-the-spire-ii.md` | Game modding |
| Rekordbox | `apps/rekordbox.md` | DJ software |
| Eth2 Quickstart | `apps/eth2-quickstart.md` | Ethereum validator setup |
| QGIS | `apps/qgis.md` | Geographic information system |

## Usage Pattern

When the agent reads an application's sub-skill file, it will find:
- The application name and description
- Common operation workflows
- CLI command syntax with `--json` output
- Element paths (e.g., `/slide[1]/shape[2]`)
- Property schemas for each element type

The agent should always prefer `--json` output and use the structured response for subsequent decisions.
