#!/usr/bin/env bash
set -euo pipefail

APP_NAME="xcelsync"
CONFIG_DIR="${HOME}/.config/xcelsync"
CONFIG_FILE_ENC="${CONFIG_DIR}/xcelsync.conf.enc"
KEY_FILE="${CONFIG_DIR}/key.bin"
LOG_FILE="${PWD}/xcelsync.log"
TMP_DIR="${PWD}/tmp"
REQ_FILE="./requirements.txt"

RED="\033[31m"; GREEN="\033[32m"; YELLOW="\033[33m"; CYAN="\033[36m"; BOLD="\033[1m"; RESET="\033[0m"

now(){ date '+%Y-%m-%d %H:%M:%S'; }
log(){ echo -e "[$(now)] $1" | tee -a "$LOG_FILE"; }

spinner() {
  local pid=$1; local msg="${2:-Working...}"; local delay=0.08; local i=0
  tput civis 2>/dev/null || true
  while kill -0 "$pid" 2>/dev/null; do
    i=$(( (i+1) % 4 ))
    case $i in
      0) printf "\r[ / ] %s" "$msg" ;;
      1) printf "\r[ - ] %s" "$msg" ;;
      2) printf "\r[ \\ ] %s" "$msg" ;;
      3) printf "\r[ | ] %s" "$msg" ;;
    esac
    sleep $delay
  done
  printf "\r\033[K"
  tput cnorm 2>/dev/null || true
}

ensure_dirs() {
  mkdir -p "$TMP_DIR"
  mkdir -p "$CONFIG_DIR"
  chmod 700 "$CONFIG_DIR"
}

banner() {
  clear
  echo "

     < ━━━━━━━━━━━━━ [★] C R E A T E D     B Y    A D I L [★] ━━━━━━━━━━━━━ > 


       ██╗  ██╗ ██████╗███████╗██╗     ███████╗██╗   ██╗███╗   ██╗ ██████╗
       ╚██╗██╔╝██╔════╝██╔════╝██║     ██╔════╝╚██╗ ██╔╝████╗  ██║██╔════╝
        ╚███╔╝ ██║     █████╗  ██║     ███████╗ ╚████╔╝ ██╔██╗ ██║██║     
        ██╔██╗ ██║     ██╔══╝  ██║     ╚════██║  ╚██╔╝  ██║╚██╗██║██║     
       ██╔╝ ██╗╚██████╗███████╗███████╗███████║   ██║   ██║ ╚████║╚██████╗
       ╚═╝  ╚═╝ ╚═════╝╚══════╝╚══════╝╚══════╝   ╚═╝   ╚═╝  ╚═══╝ ╚═════╝
                                                                     v 1.0

    <────────────── [ Coded by =*•.¸♡ MUHAMMED ADIL ♡¸.•* ] ────────────────>            
                                                               " | lolcat || true
  echo
}

ensure_dependencies() {
  log "Checking system / python dependencies..."
  if ! command -v python3 >/dev/null 2>&1; then
    log "${YELLOW}python3 not found. Please install python3 and rerun.${RESET}"; exit 1
  fi
  if ! command -v pip3 >/dev/null 2>&1; then
    log "${YELLOW}pip3 not found. Installing pip3...${RESET}"
    sudo apt-get update -y
    sudo apt-get install -y python3-pip
  fi

  if [[ -f "$REQ_FILE" ]]; then
    log "Installing Python requirements (user install)..."
    pip3 install --user -r "$REQ_FILE" | tee -a "$LOG_FILE" &
    pid=$!; spinner "$pid" "Installing Python packages..."
  else
    log "Warning: $REQ_FILE not found; create requirements.txt with required packages."
  fi

  if ! command -v inotifywait >/dev/null 2>&1; then
    log "Installing inotify-tools..."
    sudo apt-get update -y
    sudo apt-get install -y inotify-tools
  fi

  if ! command -v openssl >/dev/null 2>&1; then
    log "Installing openssl..."
    sudo apt-get update -y
    sudo apt-get install -y openssl
  fi
}

generate_key_if_missing() {
  if [[ ! -f "$KEY_FILE" ]]; then
    log "Generating local AES key..."
    openssl rand -base64 32 > "$KEY_FILE"
    chmod 600 "$KEY_FILE"
    log "Key saved to $KEY_FILE (mode 600)."
  fi
}

encrypt_and_store_config() {
  local tmp_plain
  tmp_plain="$(mktemp)"
  chmod 600 "$tmp_plain"
  cat > "$tmp_plain" <<EOF
DB_HOST="$DB_HOST"
DB_USER="$DB_USER"
DB_PASS_B64="$DB_PASS_B64"
USE_SSL="$USE_SSL"
DB_NAME="$DB_NAME"
EXCEL_PATH="$EXCEL_PATH"
SSL_CA_PATH="${SSL_CA_PATH:-}"
EOF
  openssl enc -aes-256-cbc -pbkdf2 -salt -in "$tmp_plain" -out "$CONFIG_FILE_ENC" -pass file:"$KEY_FILE"
  chmod 600 "$CONFIG_FILE_ENC"
  rm -f "$tmp_plain"
  log "Encrypted config written to $CONFIG_FILE_ENC"
}

decrypt_and_source_config() {
  if [[ ! -f "$CONFIG_FILE_ENC" ]]; then
    log "No encrypted config found at $CONFIG_FILE_ENC"
    return 1
  fi
  local tmp_plain
  tmp_plain="$(mktemp)"
  chmod 600 "$tmp_plain"
  if ! openssl enc -d -aes-256-cbc -pbkdf2 -in "$CONFIG_FILE_ENC" -out "$tmp_plain" -pass file:"$KEY_FILE" 2>/dev/null; then
    rm -f "$tmp_plain"
    log "${RED}Failed to decrypt config (bad key or corrupt file).${RESET}"
    return 2
  fi

  source "$tmp_plain"
  shred -u "$tmp_plain" 2>/dev/null || rm -f "$tmp_plain"
  return 0
}

prompt_config() {
  echo
  echo -e "${BOLD}First-time setup — enter DB details (values saved encrypted at $CONFIG_FILE_ENC)${RESET}"
  read -rp "DB Host (IP or hostname): " DB_HOST
  read -rp "DB Username: " DB_USER
  read -rsp "DB Password (hidden): " DB_PASS
  echo
  read -rp "Use SSL? (on/off/leave blank): " USE_SSL
  read -rp "Database Name: " DB_NAME
  read -rp "Full path to Excel file: " EXCEL_PATH
  read -rp "Optional SSL CA path (leave blank if none): " SSL_CA_PATH

  DB_PASS_B64="$(printf "%s" "$DB_PASS" | base64 | tr -d '\n')"
  encrypt_and_store_config

  unset DB_PASS DB_PASS_B64
}

show_info() {
  if [[ -f "$CONFIG_FILE_ENC" ]]; then
    if decrypt_and_source_config; then
      masked_user="${DB_USER:0:1}**${DB_USER: -1}"
      echo
      echo "Saved (encrypted) Connection Info:"
      echo "  Host: $DB_HOST"
      echo "  User: $masked_user"
      echo "  DB:   $DB_NAME"
      echo "  File: $EXCEL_PATH"
      echo "  SSL:  $USE_SSL"
      echo "  SSL CA path: ${SSL_CA_PATH:-(none)}"
      echo
    else
      echo "Unable to decrypt and show info."
    fi
  else
    echo "No configuration found."
  fi
}

menu() {
  banner
  echo -e "${CYAN}1) Continue (use existing encrypted config)"
  echo -e "2) Start Over (new config and overwrite encrypted file)"
  echo -e "3) Show saved connection info (decrypt & display)"
  echo -e "4) Rotate AES key (re-encrypt existing config with new key)"
  echo -e "5) About"
  echo -e "6) Exit${RESET}"
  read -rp "Select an option [1-6]: " opt
  case "$opt" in
    1) ;;  # continue
    2) prompt_config ;;
    3) show_info; exit 0 ;;
    4) rotate_key ;;
    5) echo 
    banner
    echo "  XcelSync V1.0 - Made By Muhammed Adil" | lolcat 
    echo "  EXCEL(.xlsx) File into Direct SQL Insertation with Python" | lolcat
    echo "  Please Report Any bugs or fix to Instagram - @ Ad1xmohd" | lolcat -a -8 ; exit 0 ;;
    6) exit 0 ;;
    *) echo "Invalid option"; exit 1 ;;
  esac
}

rotate_key() {
  log "Rotating AES key..."
  if [[ ! -f "$CONFIG_FILE_ENC" ]]; then
    log "No encrypted config to rotate."
    return 1
  fi
  local tmp_plain
  tmp_plain="$(mktemp)"; chmod 600 "$tmp_plain"
  if ! openssl enc -d -aes-256-cbc -pbkdf2 -in "$CONFIG_FILE_ENC" -out "$tmp_plain" -pass file:"$KEY_FILE" 2>/dev/null; then
    rm -f "$tmp_plain"
    log "${RED}Failed to decrypt current config; aborting key rotation.${RESET}"
    return 2
  fi

  local newkey
  newkey="$(mktemp)"
  openssl rand -base64 32 > "$newkey"
  chmod 600 "$newkey"

  cp "$KEY_FILE" "${KEY_FILE}.bak.$(date +%s)"
  mv "$newkey" "$KEY_FILE"
  chmod 600 "$KEY_FILE"

  openssl enc -aes-256-cbc -pbkdf2 -salt -in "$tmp_plain" -out "$CONFIG_FILE_ENC" -pass file:"$KEY_FILE"
  rm -f "$tmp_plain"
  log "Key rotated and config re-encrypted. Old key backed up to ${KEY_FILE}.bak.*"
}

ensure_ping() {
  while true; do
    log "Pinging ${DB_HOST}..."
    if ping -c 1 -W 2 "$DB_HOST" >/dev/null 2>&1; then
      log "${GREEN}Host ${DB_HOST} reachable${RESET}"; break
    else
      log "${YELLOW}Host ${DB_HOST} unreachable. Enter DB host again or Ctrl+C to abort.${RESET}"
      read -rp "DB Host: " DB_HOST
      DB_PASS_B64="${DB_PASS_B64:-}"
      encrypt_and_store_config
    fi
  done
}

decrypt_and_export_env() {
  if ! decrypt_and_source_config; then
    return 1
  fi
  export XCELSYNC_PASS_B64="${DB_PASS_B64:-}"
  if [[ -n "${SSL_CA_PATH:-}" ]]; then
    export XCELSYNC_SSL_CA="${SSL_CA_PATH}"
  fi
  unset DB_PASS_B64
  return 0
}

mysql_probe() {
  log "Probing MySQL auth with Python backend..."
  if ! decrypt_and_export_env; then
    log "Failed to load config for probe."
    return 1
  fi
  python3 main.py test "$DB_HOST" "$DB_USER" "$DB_NAME" "$USE_SSL" "$EXCEL_PATH" "$TMP_DIR"
}

run_import() {
  log "Launching backend import..."
  if ! decrypt_and_export_env; then
    log "Failed to decrypt config; aborting import."
    return 1
  fi
  python3 main.py import "$DB_HOST" "$DB_USER" "$DB_NAME" "$USE_SSL" "$EXCEL_PATH" "$TMP_DIR" 2>&1 | tee -a "$LOG_FILE" &
  pid=$!; spinner "$pid" "Import in progress..."
  wait "$pid"; rc=$?
  if [[ $rc -ne 0 ]]; then
    log "${RED}Import failed (exit $rc). See $LOG_FILE${RESET}"; return $rc
  fi
  log "${GREEN}Import completed successfully.${RESET}"
  return 0
}

watch_loop() {
  log "Watching file for changes: $EXCEL_PATH"
  while true; do
    inotifywait -e close_write "$EXCEL_PATH" >/dev/null 2>&1
    log "Change detected. Re-importing..."
    run_import || log "Re-import ended with errors."
    log "Waiting for next change..."
  done
}

ensure_dirs
ensure_dependencies
generate_key_if_missing
menu

if [[ ! -f "$CONFIG_FILE_ENC" ]]; then
  log "No encrypted config found; starting interactive setup..."
  prompt_config
fi

if ! decrypt_and_source_config; then
  log "${RED}Cannot decrypt config. Exiting.${RESET}"
  exit 1
fi

if [[ -z "${DB_HOST:-}" || -z "${DB_USER:-}" || -z "${DB_NAME:-}" || -z "${EXCEL_PATH:-}" ]]; then
  echo "Configuration incomplete. Re-run and choose option 2 to configure."
  exit 1
fi

ensure_ping

until mysql_probe; do
  log "Authentication probe failed — reconfigure credentials."
  prompt_config
done

run_import
watch_loop
