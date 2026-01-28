# HITSZ Network Automation - Requirements Document

## Project Overview

The HITSZ Network Automation project extends the existing `hitsz_net.py` script to provide automatic network connectivity detection and authentication for Harbin Institute of Technology, Shenzhen (HITSZ) campus network. The system will monitor network connectivity, detect captive portal redirects, and automatically authenticate when network access is unavailable, requiring authentication through the campus portal.

### Background
- **Existing Script**: `hitsz_net.py` uses Selenium with headless Chrome to authenticate to the campus portal at `http://10.248.98.2/srun_portal_pc?ac_id=1&theme=basic2`
- **Current Limitations**: Interactive only, no network detection, no automation, Linux-centric implementation
- **Target Platforms**: Primary macOS (darwin), secondary Linux compatibility
- **User Goal**: Automatic detection of network connectivity issues and seamless authentication without manual intervention

## Functional Requirements

### FR-1: Network Connectivity Detection
**Priority**: High

The system must detect network connectivity status through multiple methods:

1. **External Site Accessibility**: Test connectivity to external websites (e.g., www.baidu.com, 8.8.8.8)
2. **HTTP Request Testing**: Perform HTTP GET requests to test endpoints with configurable timeouts
3. **DNS Resolution Testing**: Verify DNS functionality by resolving external domain names
4. **Captive Portal Detection**: Identify when network requests are redirected to campus portal IPs (10.248.98.2) or domain (net.hitsz.edu.cn)
5. **Connection State Classification**: Classify network state as: Connected, Captive Portal, No Connection

### FR-2: Authentication Automation
**Priority**: High

The system must automatically trigger authentication when network connectivity is unavailable:

1. **Automatic Trigger**: Execute authentication script when network detection indicates captive portal or no connectivity
2. **Status Verification**: Verify authentication success by checking JavaScript `window.CONFIG.page` property for "success" value
3. **Post-Authentication Verification**: Re-test network connectivity after authentication to confirm success
4. **Failure Handling**: Handle authentication failures with appropriate retry logic and error reporting

### FR-3: Credential Management
**Priority**: High

The system must securely manage authentication credentials:

1. **Secure Storage Options**: Support multiple secure storage methods:
   - macOS Keychain integration
   - Environment variables (`HITSZ_USERNAME`, `HITSZ_PASSWORD`)
   - Encrypted configuration file
   - Interactive prompt (fallback)
2. **Credential Retrieval**: Retrieve credentials at runtime from configured source
3. **No Hardcoded Credentials**: Prohibit hardcoded credentials in source code
4. **Credential Validation**: Validate credential format and accessibility before authentication attempts

### FR-4: Retry Logic and Error Handling
**Priority**: Medium

The system must implement robust retry mechanisms and error handling:

1. **Configurable Retry Attempts**: Allow configuration of maximum retry attempts for network tests and authentication
2. **Exponential Backoff**: Implement exponential backoff between retry attempts
3. **Error Classification**: Classify errors as transient (retryable) or permanent (require intervention)
4. **Failure Escalation**: Escalate persistent failures through notification mechanisms
5. **Graceful Degradation**: Continue monitoring despite temporary failures in specific components

### FR-5: Scheduling and Daemonization
**Priority**: Medium

The system must run as a background service with appropriate scheduling:

1. **Background Operation**: Run as a daemon/service without requiring user interaction
2. **Platform-Specific Integration**:
   - macOS: LaunchAgent/LaunchDaemon with plist configuration
   - Linux: systemd service unit or cron job
3. **Configurable Check Interval**: Allow configuration of network check frequency (default: 5 minutes)
4. **Service Management**: Provide commands to start, stop, restart, and check service status
5. **Automatic Startup**: Configure service to start automatically on system boot

### FR-6: Logging and Monitoring
**Priority**: Medium

The system must provide comprehensive logging and monitoring:

1. **Structured Logging**: Log all operations with timestamps, severity levels, and context
2. **Log Output Options**: Support console output, file logging, and system logging facilities
3. **Log Rotation**: Implement log rotation to prevent unbounded disk usage
4. **Event Tracking**: Track authentication attempts, successes, failures, and network state changes
5. **Performance Metrics**: Record response times for network tests and authentication operations

### FR-7: Configuration Management
**Priority**: Medium

The system must be configurable through external configuration:

1. **Configuration File**: Support configuration through YAML/JSON file (e.g., `config.yaml`)
2. **Environment Variables**: Support configuration through environment variables
3. **Default Values**: Provide sensible defaults for all configurable parameters
4. **Configuration Validation**: Validate configuration at startup and provide clear error messages
5. **Configuration Reload**: Support configuration reload without service restart (where applicable)

### FR-8: Notification System
**Priority**: Low

The system may provide notifications for significant events:

1. **Notification Events**: Notify for authentication successes, failures, and persistent network issues
2. **Notification Channels**: Support console notifications, desktop notifications, and optional email/webhook notifications
3. **Configurable Thresholds**: Allow configuration of notification frequency and thresholds
4. **Quiet Periods**: Support configurable quiet periods to prevent notification spam

## Non-Functional Requirements

### NFR-1: Performance
1. **Network Check Latency**: Complete network connectivity check within 10 seconds
2. **Authentication Time**: Complete authentication process within 30 seconds
3. **Resource Usage**: Use minimal CPU and memory resources when idle (< 1% CPU, < 50MB RAM)
4. **Startup Time**: Service should start within 5 seconds

### NFR-2: Security
1. **Credential Protection**: Never log or expose credentials in plaintext
2. **Secure Storage**: Use platform-appropriate secure storage for credentials
3. **Least Privilege**: Operate with minimal necessary permissions
4. **Input Validation**: Validate all inputs to prevent injection attacks
5. **TLS/HTTPS Support**: Support HTTPS for portal access if available

### NFR-3: Usability
1. **Installation Simplicity**: Provide clear installation instructions for both macOS and Linux
2. **Configuration Ease**: Simple configuration through environment variables or config file
3. **Diagnostic Tools**: Provide diagnostic commands to test configuration and connectivity
4. **Clear Error Messages**: Provide actionable error messages for common failure scenarios
5. **Documentation**: Comprehensive documentation covering installation, configuration, and troubleshooting

### NFR-4: Compatibility
1. **Platform Support**: Primary support for macOS 10.15+, secondary support for Linux (Ubuntu 20.04+, CentOS 8+)
2. **Python Version**: Support Python 3.8+
3. **Browser Driver Management**: Automatic ChromeDriver management compatible with installed Chrome versions
4. **Network Environment**: Support both wired and wireless network environments
5. **Proxy Support**: Optional support for HTTP/HTTPS proxies

### NFR-5: Reliability
1. **Service Availability**: Service should maintain 99.9% uptime (excluding planned maintenance)
2. **Fault Tolerance**: Recover from temporary network outages and browser driver failures
3. **Data Persistence**: Maintain state across service restarts
4. **Resource Leak Prevention**: Properly clean up browser processes and temporary files

### NFR-6: Maintainability
1. **Code Organization**: Modular code structure with clear separation of concerns
2. **Testing**: Comprehensive unit and integration test coverage
3. **Logging**: Sufficient logging for debugging and operational monitoring
4. **Configuration Management**: Externalized configuration for easy maintenance
5. **Dependency Management**: Clear dependency specifications with version pinning

## Constraints and Assumptions

### Constraints
1. **Portal URL**: Authentication must work with the existing portal at `http://10.248.98.2/srun_portal_pc?ac_id=1&theme=basic2`
2. **Authentication Method**: Must use existing Selenium-based authentication flow (cannot change portal authentication mechanism)
3. **Browser Requirement**: Requires Chrome/Chromium browser and ChromeDriver
4. **Network Environment**: Designed for HITSZ campus network environment
5. **Legal Compliance**: Must comply with campus network usage policies

### Assumptions
1. **Portal Stability**: Campus portal interface and JavaScript API (`window.CONFIG`) will remain stable
2. **Network Access**: User has valid campus network credentials
3. **System Permissions**: User has necessary permissions to install and run background services
4. **Chrome Availability**: Chrome/Chromium browser is or can be installed on target system
5. **Python Environment**: Python 3.8+ is available on target system

## Dependencies

### Software Dependencies
1. **Python 3.8+**: Core runtime environment
2. **Chrome/Chromium Browser**: Required for Selenium automation
3. **ChromeDriver**: Browser automation driver (version must match Chrome)
4. **Python Packages**:
   - `selenium>=4.0.0`: Browser automation
   - `requests>=2.25.0`: HTTP client for network testing
   - `pyyaml>=6.0`: YAML configuration parsing
   - `keyring>=23.0.0`: Cross-platform keyring access (optional)
   - `psutil>=5.9.0`: Process management for cleanup
   - `webdriver-manager>=3.8.0`: Automatic driver management

### Platform Dependencies
1. **macOS**: Requires proper Chrome installation and LaunchD service framework
2. **Linux**: Requires systemd or cron for service management
3. **Network**: Requires network connectivity for external testing

### External Service Dependencies
1. **Test Endpoints**: External websites (www.baidu.com, 8.8.8.8) for connectivity testing
2. **Campus Portal**: HITSZ campus authentication portal availability
3. **Package Repositories**: PyPI for Python package installation

## Acceptance Criteria

### AC-1: Network Detection
1. **Given** the system is running
   **When** network connectivity is available
   **Then** the system should detect "Connected" state
   **And** not attempt authentication

2. **Given** the system is running
   **When** network requests are redirected to campus portal
   **Then** the system should detect "Captive Portal" state
   **And** trigger authentication process

3. **Given** the system is running
   **When** no network connectivity is available
   **Then** the system should detect "No Connection" state
   **And** log the condition appropriately

### AC-2: Authentication
1. **Given** network detection indicates captive portal
   **When** authentication is triggered
   **Then** the system should successfully authenticate using stored credentials
   **And** verify authentication success via portal status check

2. **Given** authentication fails due to invalid credentials
   **When** retry limit is not exceeded
   **Then** the system should retry according to configured backoff
   **And** log authentication failure

3. **Given** authentication fails due to portal unreachable
   **When** retry limit is exceeded
   **Then** the system should escalate through notification system
   **And** continue monitoring at reduced frequency

### AC-3: Credential Management
1. **Given** credentials are stored in macOS Keychain
   **When** the system starts
   **Then** it should successfully retrieve credentials without user interaction

2. **Given** credentials are provided via environment variables
   **When** the system starts
   **Then** it should use environment variables without prompting

3. **Given** no credentials are available from secure sources
   **When** authentication is required
   **Then** the system should prompt user for credentials interactively
   **And** offer to store them securely for future use

### AC-4: Service Management
1. **Given** the system is installed on macOS
   **When** system boots
   **Then** the service should start automatically via LaunchAgent

2. **Given** the service is running
   **When** network connectivity is lost and regained
   **Then** the service should automatically detect and authenticate without manual intervention

3. **Given** the service encounters a fatal error
   **When** automatic restart is configured
   **Then** the service should restart with exponential backoff

### AC-5: Configuration
1. **Given** a configuration file is provided
   **When** the system starts
   **Then** it should load and validate configuration
   **And** use specified parameters for network checks and authentication

2. **Given** configuration specifies custom test endpoints
   **When** performing network checks
   **Then** the system should use specified endpoints instead of defaults

3. **Given** configuration specifies custom check intervals
   **When** monitoring network connectivity
   **Then** the system should respect specified intervals

### AC-6: Logging and Monitoring
1. **Given** authentication succeeds
   **When** checking logs
   **Then** there should be a timestamped success entry with relevant details

2. **Given** network connectivity changes state
   **When** checking logs
   **Then** there should be a state transition entry with before/after states

3. **Given** a configuration error occurs
   **When** checking logs
   **Then** there should be a clear error message with remediation suggestions

---

## Version History
- **Version 1.0**: Initial requirements document (2026-01-05)
- **Based On**: User requirements, existing hitsz_net.py analysis, and network automation patterns

## Review and Approval
- **Status**: Draft
- **Next Steps**: Requirements clarification, implementation planning, test strategy development