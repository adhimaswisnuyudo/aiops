# AIOps Agent

AI-powered DevOps / SRE assistant via **SSH + Natural Language**.  
Check server health, Laravel, MySQL, and Nginx — from CLI, REPL, or **Telegram Bot**.

---

## Prerequisites

| Requirement | Minimum |
|---|---|
| Python | 3.11+ |
| Docker (optional) | 24+ |
| SSH key on target servers | ✅ |
| Telegram Bot Token (optional) | from [@BotFather](https://t.me/BotFather) |

---

## Quick Install (any server)

```bash
git clone <your-repo-url> aiops-agent
cd aiops-agent

pip install -e ".[dev]"
```

---

## Configuration

### 1. Edit `config.yaml`

Ganti `YOUR_STAGING_IP_OR_HOSTNAME`, `YOUR_PRODUCTION_IP_OR_HOSTNAME`, dan `YOUR_SSH_USERNAME` dengan nilai asli server kamu:

```yaml
servers:
  - name: staging
    host: 192.168.1.10             # ← GANTI
    port: 22
    username: deploy                # ← GANTI
    environment: staging
    ssh_key_path: ~/.ssh/id_rsa
    tags:
      - web
      - laravel
      - staging

  - name: production
    host: 203.0.113.50              # ← GANTI
    port: 22
    username: deploy                # ← GANTI
    environment: production
    ssh_key_path: ~/.ssh/id_rsa
    tags:
      - web
      - laravel
      - production
```

### 2. Verifikasi instalasi

```bash
aiops "check all" -s staging
```

Output:
```
Connecting to staging (192.168.1.10)...

=== Server Status ===
Uptime: 15 days, 3:22
CPU:  1.2% (load: 0.08 / 0.12 / 0.09)
Memory: 1.8G / 3.8G (47.4%)
Disk:  22G / 78G (28.2%)

=== Laravel Status ===
...
```

---

## CLI Usage

### Single Query
```bash
aiops "check all"                          # semua skill
aiops "check server" -s staging            # server status
aiops "check laravel"                      # Laravel + PHP info
aiops "check database"                     # MySQL
aiops "check nginx"                        # Nginx
```

### Interactive REPL
```bash
aiops repl
```
```
> How is the server?
> Check laravel and database
> /server production     ← switch server
> /quit
```

### List skills / tools
```bash
aiops -l        # list skills
aiops -L        # list tools
aiops -H        # conversation history
```

---

## Docker

```bash
# Build
docker compose build

# REPL
docker compose run --rm aiops-agent repl

# Single query
docker compose run --rm aiops-agent "check all" -s staging

# Run tests
docker compose run --rm aiops-agent test
```

---

## Telegram Bot Integration

### Step-by-step guide — end to end

---

#### Step 1: Buat bot Telegram

1. Buka [@BotFather](https://t.me/BotFather) di Telegram
2. Kirim perintah:

```
/newbot
```

3. Isi nama bot:
```
AIOps Helper
```

4. Isi username bot (harus berakhiran `bot`):
```
aiops_helper_bot
```

5. BotFather akan mengirimkan token. Simpan token ini:
```
123456789:AAHdqTcvCH1gWPA...   ← SIMPAN INI
```

---

#### Step 2: Set environment variable

```bash
export TELEGRAM_BOT_TOKEN="123456789:AAHdqTcvCH1gWPA..."
```

**Opsional — pakai file `.env`:**
```bash
cp .env.example .env
# Edit .env, isi TELEGRAM_BOT_TOKEN
```

---

#### Step 3: Enable Telegram di `config.yaml`

```yaml
telegram:
  enabled: true                      # ← ubah jadi true
  token_env: TELEGRAM_BOT_TOKEN
  allowed_users: []                  # kosong = semua user boleh akses
  webhook: false                     # long polling (paling simpel)
```

**Untuk membatasi user tertentu** (opsional — tambahkan Telegram user ID):
```yaml
  allowed_users:
    - 123456789       # user ID kamu
    - 987654321       # user ID kolega
```

Cara dapat user ID: chat ke [@userinfobot](https://t.me/userinfobot).

---

#### Step 4: Jalankan bot (Long Polling)

```bash
aiops-bot
```

Output:
```
🤖 AIOps Agent Telegram Bot starting...
   Mode: Long Polling
   Servers: staging, production
```

Biarkan terminal ini tetap berjalan. Bot sekarang live.

---

#### Step 5: Interaksi via Telegram

Buka Telegram → cari bot kamu (misal `@aiops_helper_bot`) → `/start`

Kamu akan lihat pesan sambutan. Lalu coba:

```
> check all
> check server
> check laravel and database
> /server production
> /status
> /help
```

Setiap query akan ditampilkan dengan typing indicator `...` lalu hasilnya diformat dengan Markdown.

---

### Webhook Mode (untuk production)

Long polling cocok untuk development. Untuk production, gunakan webhook dengan reverse proxy (nginx/Caddy) + TLS.

**config.yaml:**
```yaml
telegram:
  enabled: true
  token_env: TELEGRAM_BOT_TOKEN
  webhook: true
  webhook_url: "https://your-domain.com/bot"
  webhook_port: 8443
```

**Jalankan:**
```bash
aiops-bot --webhook --webhook-url "https://your-domain.com/bot"
```

Pastikan reverse proxy kamu meneruskan HTTPS ke `localhost:8443`.

---

### Docker dengan Telegram Bot

```bash
# Build image
docker compose build

# Jalankan bot (long polling)
docker compose run --rm aiops-agent aiops-bot

# Dengan env file
docker compose --env-file .env run --rm aiops-agent aiops-bot
```

---

## Available Skills & Natural Language

| Kamu bilang | Skill yang berjalan | Tools |
|---|---|---|
| `check all`, `status` | Semua 4 skill | uptime, cpu, memory, disk, nginx, php, mysql, laravel |
| `check server`, `how is the server`, `cpu` | server_status | uptime, cpu_info, memory, disk_percent, load_average, top_processes |
| `check laravel`, `check app` | laravel_status | laravel_version, laravel_env, php_version, php_modules |
| `check database`, `check db`, `mysql` | database_status | mysql_status, mysql_processes, mysql_slow_queries |
| `check nginx`, `web server` | nginx_status | nginx_status, nginx_config_test, nginx_error_logs |

---

## Telegram Commands

| Command | Fungsi |
|---|---|
| `/start` | Sambutan & quick guide |
| `/help` | Panduan lengkap |
| `/status` | Jalankan `check all` |
| `/servers` | List semua server di config |
| `/server <name>` | Switch ke server lain (contoh: `/server production`) |

---

## Phase 1 — Read-Only Tools (20+)

| Kategori | Tools |
|---|---|
| **System** | uptime, cpu_info, memory, disk_percent, disk_usage, load_average, users, top_processes, os_info, network_info |
| **Nginx** | nginx_status, nginx_config_test, nginx_error_logs, nginx_access_logs |
| **PHP** | php_version, php_modules, php_ini, php_fpm_status |
| **MySQL** | mysql_status, mysql_processes, mysql_slow_queries, mysql_replication |
| **Laravel** | laravel_version, laravel_env, laravel_routes, laravel_cache, laravel_logs, laravel_queues, laravel_scheduler |
| **Docker** | docker_ps, docker_stats, docker_images, docker_version |
| **Git** | git_status, git_log, git_branch, git_remotes |

---

## Project Structure

```
aiops-agent/
├── Dockerfile
├── docker-compose.yaml
├── config.yaml                 # ← server + telegram config
├── pyproject.toml
├── .env.example
├── README.md
├── aiops_agent/
│   ├── agent/planner.py        # NLP parsing & skill orchestration
│   ├── bot/                    # Telegram Bot module
│   │   ├── __init__.py
│   │   └── telegram.py
│   ├── cli/                    # CLI + REPL + bot entry point
│   │   ├── main.py
│   │   └── repl.py
│   ├── config/models.py        # Pydantic models
│   ├── memory/store.py         # SQLite conversation memory
│   ├── skills/                 # 4 skills
│   └── tools/                  # 20+ read-only tools
├── playbooks/
│   ├── server_check.yaml
│   └── laravel_check.yaml
└── tests/
    └── test_agent_planner.py