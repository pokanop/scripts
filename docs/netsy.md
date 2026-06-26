# 📡 netsy — LAN Discovery Tool · v1.2.1

**Ping-scan the local subnet and list live hosts with hostname, IP, MAC address, and vendor.**

Supports **macOS**, **Linux**, **Windows**, and BSD-style Unix via `ifconfig`.

`netsy` · Python 3 · `nmap` · `rich`

```bash
netsy                                    # Quick scan (auto-detect subnet)
netsy scan --thorough --passes 3 --sudo  # Reliable multi-pass scan
netsy find my-phone --watch --sudo       # Hunt until a device appears
netsy doctor                             # Check prerequisites
```

---

## Quick start

```bash
# Scan the auto-detected local subnet
netsy

# More reliable scan (recommended if results vary)
netsy scan --thorough --passes 3 --sudo

# Hunt for a specific device
netsy find my-phone
netsy find 192.168.1.42 --watch --sudo

# Deep-check one host
netsy probe hostname.local --sudo

# Check prerequisites
netsy doctor
```

---

## Why Results Vary Between Runs

Yes — **different host counts between quick scans is normal**. Common causes:

- **Sleeping devices** — phones, laptops, and IoT gear wake intermittently
- **ICMP filtering** — some hosts block ping but still answer ARP or TCP probes
- **Wi-Fi roaming** — clients move between bands, APs, or VLANs
- **Privilege limits** — without `sudo`/Administrator, macOS/Windows may miss ARP-based discovery

Use `--thorough --passes 3` to run slower probes multiple times and merge the union of results. Use `find --watch` when you're waiting for one device to show up.

---

## How It Works

1. Detects your primary local IP via UDP route probing (`8.8.8.8`, `1.1.1.1`, `208.67.222.222`).
2. Resolves the matching subnet CIDR:
   - **macOS / BSD:** `ifconfig`
   - **Linux:** `ip addr`, falling back to `ifconfig`
   - **Windows:** PowerShell `Get-NetIPAddress`, falling back to `ipconfig`
3. Runs `nmap -sn` (ping scan, no port scan) against that subnet.
4. Optionally repeats the scan and merges results across passes.
5. Parses hostnames, IPs, MAC addresses, and vendors into a sorted table.

**Quick scan:** default `nmap -sn`

**Thorough scan:** adds `-T3`, extra retries, ICMP/TCP/UDP probes — better for stubborn or sleeping hosts.

MAC addresses and vendor strings often require elevated privileges:
- **macOS / Linux:** use `--sudo`
- **Windows:** run from an Administrator shell (`--sudo` is ignored)

---

## Commands

| Command | Description |
|---------|-------------|
| `netsy [subnet]` | Quick scan (auto-detect subnet if omitted) |
| `netsy scan --thorough --passes 3` | Slower, multi-pass scan with merged results |
| `netsy scan --find QUERY` | Filter results to matching hosts |
| `netsy find HOST` | Thorough 3-pass search by IP, name, MAC, or vendor |
| `netsy find HOST --watch` | Keep scanning until the host appears |
| `netsy probe IP` | Deep-check a single host |
| `netsy scan --sudo` | Use sudo for MAC/vendor discovery (macOS/Linux) |
| `netsy scan --json` | JSON output |
| `netsy doctor` | Check nmap and network auto-detection |

---

## Finding a Missing Host

```bash
# Search by hostname fragment
netsy find roku --sudo

# Search by IP
netsy find 192.168.1.55 --sudo

# Wait for a device to wake up and join the network
netsy find my-laptop --watch --interval 15 --sudo

# Probe a host directly (if you know its IP or DNS name)
netsy probe 192.168.1.55 --sudo
netsy probe my-nas.local --sudo
```

If a host still doesn't appear, it may be offline, on another VLAN/subnet, or blocking all discovery probes.

---

## Requirements

- **nmap** — `brew install nmap` (macOS), `apt install nmap` (Linux), or `winget install Insecure.Nmap` (Windows)
- **rich** — installed via `scripts install netsy` (or `pip install -r requirements/netsy.txt`)

---

## Related tools

Built on **[scriptkit](scriptkit.md)** — the shared CLI library (color, messages, progress, tables, config, subprocess). Building or editing a tool? See **[AGENTS.md](../AGENTS.md)**.

Part of the [scripts](../README.md) toolkit — [keyferry](keyferry.md) · [medcat](medcat.md) · [voxtract](voxtract.md) · [pluck](pluck.md) · [aikit](aikit.md)

---

## License

MIT — see [LICENSE](../LICENSE).