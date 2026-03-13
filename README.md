# OpenClaw 全球分布式部署与无界 AI 安装器

# OpenClaw Installer: Globally Distributed Deployment, Borderless AI for All

**Preserve Native Open Source · Eliminate AI Barriers · Break Regional Restrictions · Make AI Truly Benefit All of Society**

One-click installation of the unmodified, native [OpenClaw](https://github.com/openclaw/openclaw) personal AI assistant, **zero command line, zero technical barriers, no regional access restrictions**

---

## Why We Built This — The Truth and Mission of the AI Era

### 🌍 The Harsh Reality of Global AI Adoption

Of the world's 8.1 billion people, **84% (approximately 6.8 billion people) have never used any AI tool**. They are not uninterested in AI — they are locked out by **CMD/terminal commands, complex configurations, and technical jargon**. This silent majority of 6.8 billion people is the core audience of the OpenClaw Installer, and the population that AI democratization should serve first and foremost.

### 🦞 OpenClaw: A World-Changing Open Source Project

OpenClaw is a groundbreaking **local self-hosted AI agent** that gives everyone a **private, controllable, memory-enabled, executable** personal AI assistant. It supports cross-platform chat interactions, automated workflows, and full-scenario capability expansion, redefining the future of personal AI with a fully open source, privacy-first, vendor-lock-in-free philosophy.

It is a technological treasure for all humanity, a milestone in the democratization, privatization, and popularization of AI, and a digital tool that can truly transform the work and lives of ordinary people.

### ⚠️ The Alarming Status Quo: A Great Project Being White-Labeled for Profit

Today, countless companies **strip, repackage, and rebrand the core code of OpenClaw**, selling it as their own proprietary product for profit. This deprives users of access to **native open source features, community updates, and full customization freedom**, fragments the open source ecosystem, and turns AI benefits that should belong to everyone into a profit-making tool for a handful of enterprises.

### 🌐 An Open Source World Fragmented by Network Barriers

Even more regrettably, more than 60 countries and regions around the world have varying degrees of network access restrictions on GitHub, overseas open source resources, and AI-related services. Countless users who have the ability and willingness to use native OpenClaw cannot connect to the official repository, pull installation packages, or access community updates. They are forced to use crippled, white-labeled versions, or even lose access to this life-changing technology entirely.

OpenClaw natively supports **a globally distributed deployment architecture** — it can be deployed via distributed mirror nodes on local servers in different countries and regions. Without relying on centralized overseas servers, it can provide users in the region with complete, native, and synchronously updated OpenClaw services. This is the core solution to break down regional barriers and achieve borderless AI accessibility for all.

### 🛡️ OpenClaw Installer: Preserve the Native Project, Break Barriers, and Return to the Original Vision

The sole mission of this project is:

**To let ordinary people in every corner of the world use 100% native, unmodified, uncrippled OpenClaw**

- Through globally distributed mirror deployment, we provide localized installation sources for users in different countries and regions, completely bypassing network access restrictions. No special network configuration, no cross-border access required — one-click installation of the native version.

- Full retention of community iteration, memory capabilities, API management, full model support, and open source benefits. No white-labeling, no crippling, no information arbitrage.

- We lower the technical barrier to the minimum, so that even zero-experience users can integrate OpenClaw into their work and life, and change their daily routines with AI.

---

## Project Mission: Simplified Installation + Distributed Deployment = Bringing AI to Every Household

**Simplifying the installation process is the final mile of AI democratization; distributed deployment is the core foundation for borderless AI access.**

OpenClaw Installer takes on this generational mission:

We have encapsulated the cross-network deployment, terminal operations, and environment configuration that only technical experts can handle into an extremely simple process: **Double-click to run → Enter activation code → Enter API Key → Complete**. The entire process **requires no CMD, no command line input, no special network settings**.

Whether you are a student or professional in a region with restricted network access, a small business owner, or an elder with no technical background, you can use our installer to connect to distributed nodes in your region, easily get your own native AI assistant, and seamlessly manage your API keys and OpenClaw memory. Let AI handle your work tasks, manage your daily life, and improve your learning efficiency — truly realizing "AI changes life".

We firmly believe:

**AI should not be a toy for technical elites, nor an exclusive privilege for developed countries — it should be a fundamental tool for the entire society and all humanity.**

The OpenClaw Installer is the bridge connecting 6.8 billion AI-unreachable people to the future world, an open source tool that breaks down technical barriers, regional restrictions, and commercial exploitation.

---

## Core Features: We Handle the Complexity, You Get the Simplicity

- **✅ True One-Click Installation**

Automatically detects/installs Node.js, deploys OpenClaw, configures models, and starts the Gateway, **with full GUI visualization throughout the process, zero terminal operations required**.

- **🌍 Global Distributed Mirror Compatibility**

Supports localized deployment nodes and mirror sources in different countries and regions, bypassing regional network restrictions. No matter where you are, you can install native OpenClaw with one click.

- **✅ Native Open Source Preservation**

Installs the official pure version of OpenClaw, **no white-labeling, no unauthorized modification, full community capability retention**, and synchronizes with the latest official updates.

- **✅ Full Coverage of 20+ Mainstream LLMs**

Supports Anthropic, OpenAI, Zhipu GLM, Kimi (Moonshot), DeepSeek, Tongyi Qianwen (Qwen), Gemini, local Ollama models, and more, adapting to mainstream model services in different regions.

- **✅ Effortless API & Memory Management**

Visual configuration writing, automatic validation of API key validity and quota, so even beginners can manage their AI assets with ease.

- **✅ Secure Activation Code System**

Remote validation, one code per device, machine binding for secure and controllable access, and abuse prevention.

- **✅ In-depth Network Optimization for All Regions**

Multi-region dedicated servers accelerate downloads, bypass GitHub and overseas resource restrictions, adapt to network environments in different regions, and ensure stable, fast, and smooth installation.

- **✅ Ready to Use Right After Installation**

Automatically starts the Gateway and opens the browser, out-of-the-box with no extra setup.

---

## Project Structure

```Plain Text

openclaw-installer/
├── installer/                 # Installer core code
│   ├── main.py               # Main GUI program (tkinter wizard interface)
│   └── core/
│       ├── activator.py      # Activation code validation (online remote verification, distributed node support)
│       ├── api_validator.py  # API Key validation (multi-vendor, multi-region compatibility)
│       ├── fingerprint.py    # Device fingerprint generation
│       ├── node_installer.py # Automatic Node.js installation (multi-region mirror source compatibility)
│       └── openclaw_installer.py  # OpenClaw installation, configuration, startup (distributed node pull support)
├── assets/
│   ├── icon.ico              # Application icon
│   └── icon.png
├── config.example.py         # Configuration example (distributed node configuration support)
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Environment Setup

```Bash

# Python 3.10+ required
pip install -r requirements.txt
```

### 2. Configuration

Copy the configuration example and fill in your server information, with support for multi-region distributed node configuration:

```Bash

cp config.example.py config.py
```

Core Configuration Items:

|File|Variable|Description|
|---|---|---|
|`installer/core/activator.py`|`SERVER_URL`|Your main validation server address, supports multi-region distributed node configuration|
|`installer/core/activator.py`|`SECRET_KEY`|Signature key consistent with the server side|
|`installer/core/openclaw_installer.py`|`OPENCLAW_TGZ_URL`|OpenClaw installation package address, supports multi-region mirror source configuration|
|`installer/main.py`|`TRAY_EXE_URL`|Tray manager download address, supports multi-region mirror source configuration|
### 3. Run in Development Mode

```Bash

python installer/main.py
```

### 4. Package into Executable (exe)

```Bash

# Run on Windows
pip install pyinstaller

pyinstaller --onefile --windowed --name "OpenClaw-Installer" \
  --icon assets/icon.ico \
  --paths installer \
  --hidden-import core.activator \
  --hidden-import core.api_validator \
  --hidden-import core.fingerprint \
  --hidden-import core.node_installer \
  --hidden-import core.openclaw_installer \
  installer/main.py --noconfirm --clean
```

The packaged exe file will be located in the `dist/` directory, ready for direct distribution to users in corresponding regions.

---

## Distributed Node Deployment Guide

This installer natively supports a global distributed deployment architecture. You can set up local mirror nodes in different countries and regions to provide users in the area with unrestricted access to native OpenClaw installation services:

1. Set up a lightweight server in the target region to host the OpenClaw installation package, tray program, and validation service node.

2. Update the installer configuration to use the local mirror address for the region.

3. The packaged installer can directly connect to the local node, allowing users to complete one-click installation without any network configuration.

4. Support node synchronization with the official repository updates, ensuring users always use the latest native OpenClaw version.

We recommend using Python FastAPI + SQLite to build node services, which can run stably with a minimum configuration of 1 core and 1GB of memory, adapting to server environments in different regions.

---

## Validation Server

The installer needs to work with a validation server, which supports distributed node deployment and is responsible for:

- Activation code validation (one code per device, expiration check, regional adaptation)

- Hosting multi-region OpenClaw installation package mirrors to bypass access restrictions

- Hosting multi-region mirrors of the tray manager exe

- Synchronizing official OpenClaw updates to ensure consistent versions across all nodes

The server-side code **is not included in this repository**. You need to build your own service that provides the following APIs:

```Plain Text

POST /api/v1/activate    — Validate activation code, supports multi-region node distribution
GET  /static/*.tgz       — Download OpenClaw installation package, supports multi-region mirrors
GET  /static/*.exe       — Download tray manager, supports multi-region mirrors
```

---

## Supported Large Language Models

|Vendor|Default Model|
|---|---|
|Anthropic (Claude)|claude-sonnet-4-5|
|OpenAI (GPT)|gpt-4o|
|Zhipu (GLM)|glm-4-flash|
|Kimi (Moonshot)|moonshot-v1-8k|
|DeepSeek|deepseek-chat|
|Tongyi Qianwen (Qwen)|qwen-turbo|
|MiniMax|abab6.5s-chat|
|Google (Gemini)|gemini-pro|
|Mistral|mistral-large-latest|
|Groq|llama-3.1-70b-versatile|
|Ollama (Local)|llama3|
|Custom|User-specified|
---

## Technical Details

- **GUI**: customtkinter / tkinter

- **Packaging**: PyInstaller (--onefile)

- **Signature Verification**: HMAC-SHA256 (payload + timestamp + secret)

- **API Validation Policy**: 200/400/403 status codes are considered valid, only 401 is treated as an invalid Key

- **Installation Method**: Download pre-packaged tgz from distributed mirror nodes, extract to the npm global directory

- **Gateway Startup**: PowerShell Start-Process with full path

- **Multi-Region Optimization**: Automatically adapts to mirror sources, npm acceleration sources, and network environments in corresponding regions

---

## Known Issues

- Exe files packaged with PyInstaller may be falsely flagged by antivirus software (we recommend purchasing a code signing certificate)

- Python 3.14 is incompatible with PyInstaller, please use Python 3.12

- The installation package is approximately 480MB, the first download time depends on the network environment of the corresponding regional node

---

## License

MIT

---

## Our Manifesto

**OpenClaw belongs to the world, and AI democratization belongs to everyone.**

No white-labeling, preserve native open source; eliminate barriers, break restrictions; for every country, for every region.

The OpenClaw Installer is more than just an installer.

It is **a social project to bring AI to every household**,

a belief in returning technology to people and open source to its original vision,

and a key for every ordinary person in the world to equally embrace the AI era.
