# HITSZ Network Automation - Project Documentation

## Project Overview
This project extends the existing `hitsz_net.py` script to provide automatic network connectivity detection and authentication for HITSZ campus network.

## Key Documentation

### Requirements
- [requirements.md](./requirements.md) - Comprehensive requirements document

### Research Findings
- [research-findings/codebase-exploration-findings.md](./research-findings/codebase-exploration-findings.md) - Analysis of existing codebase
- [research-findings/network-connectivity-research.md](./research-findings/network-connectivity-research.md) - Research on network detection patterns (in progress)
- [research-findings/daemonization-findings.md](./research-findings/daemonization-findings.md) - Daemonization and service management findings
- [research-findings/selenium-automation-findings.md](./research-findings/selenium-automation-findings.md) - Selenium automation patterns analysis
- [research-findings/librarian-selenium-automation.md](./research-findings/librarian-selenium-automation.md) - External Selenium authentication research
- [selenium-usage-patterns-summary.md](./selenium-usage-patterns-summary.md) - Comprehensive Selenium usage analysis and best practices

### Source Code
- [hitsz_net/hitsz_net.py](./hitsz_net/hitsz_net.py) - Original authentication script
- [hitsz_net/README.md](./hitsz_net/README.md) - Original project README

## Project Structure
```
hitsz-autonet/
├── requirements.md                    # Project requirements
├── CLAUDE.md                         # This documentation index
├── selenium-usage-patterns-summary.md # Selenium analysis and best practices
├── research-findings/                # Research documentation
│   ├── codebase-exploration-findings.md
│   ├── network-connectivity-research.md
│   ├── daemonization-findings.md
│   ├── selenium-automation-findings.md
│   └── librarian-selenium-automation.md
└── hitsz_net/                       # Original project
    ├── hitsz_net.py                  # Main script
    ├── README.md                     # Installation instructions
    ├── LICENSE                       # MIT License
    └── .gitignore                    # Git ignore file
```

## Development Workflow
1. **Requirements Analysis** - Complete (see requirements.md)
2. **Requirements Clarification** - In progress
3. **Implementation Planning** - Pending
4. **Test Strategy Development** - Pending
5. **Implementation** - Pending
6. **Testing** - Pending

## Key Dependencies
- Python 3.8+
- Chrome/Chromium browser
- ChromeDriver
- Selenium, requests, pyyaml, keyring, psutil, webdriver-manager

## Platform Support
- Primary: macOS 10.15+
- Secondary: Linux (Ubuntu 20.04+, CentOS 8+)
