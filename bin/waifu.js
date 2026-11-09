#!/usr/bin/env node
/**
 * Waifu on Telegram - Universal Cross-Platform CLI Launcher
 * Checks runtime environment (Python 3.8+, Node.js, CLI scripts)
 * and executes bin/cli.py without falling into Windows Store python3 alias traps.
 */

const { spawn, spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const PROJECT_ROOT = path.resolve(__dirname, '..');
const CLI_PY = path.join(__dirname, 'cli.py');

// ANSI Colors
const CYAN = '\x1b[96m';
const GREEN = '\x1b[92m';
const YELLOW = '\x1b[93m';
const RED = '\x1b[91m';
const BOLD = '\x1b[1m';
const RESET = '\x1b[0m';

function findWorkingPython() {
  const candidates = [];

  // 1. Virtual Environment
  if (process.env.VIRTUAL_ENV) {
    candidates.push(path.join(process.env.VIRTUAL_ENV, process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python'));
  }
  candidates.push(path.join(PROJECT_ROOT, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python'));
  candidates.push(path.join(PROJECT_ROOT, 'venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python'));

  // 2. Project tools portable python
  candidates.push(path.join(PROJECT_ROOT, 'tools', 'python', 'python.exe'));

  // 3. Platform-specific paths
  if (process.platform === 'win32') {
    candidates.push('python');
    candidates.push('py');
    candidates.push('python3');

    const localAppData = process.env.LOCALAPPDATA || '';
    if (localAppData) {
      candidates.push(path.join(localAppData, 'Programs', 'Python', 'Python313', 'python.exe'));
      candidates.push(path.join(localAppData, 'Programs', 'Python', 'Python312', 'python.exe'));
      candidates.push(path.join(localAppData, 'Programs', 'Python', 'Python311', 'python.exe'));
      candidates.push(path.join(localAppData, 'Programs', 'Python', 'Python310', 'python.exe'));
    }
    const programFiles = process.env.ProgramFiles || 'C:\\Program Files';
    candidates.push(path.join(programFiles, 'Python311', 'python.exe'));
    candidates.push(path.join(programFiles, 'Python312', 'python.exe'));
    candidates.push(path.join(programFiles, 'Python310', 'python.exe'));
  } else {
    candidates.push('python3');
    candidates.push('python');
    candidates.push('/usr/bin/python3');
    candidates.push('/usr/local/bin/python3');
    candidates.push('/opt/homebrew/bin/python3');
  }

  for (const cmd of candidates) {
    if (!cmd) continue;
    try {
      const res = spawnSync(cmd, ['-c', 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")'], {
        encoding: 'utf-8',
        stdio: ['pipe', 'pipe', 'pipe'],
        shell: false,
        timeout: 5000
      });
      if (res.status === 0 && res.stdout) {
        const verStr = res.stdout.trim();
        const parts = verStr.split('.');
        const major = parseInt(parts[0], 10);
        const minor = parseInt(parts[1], 10);
        if (major === 3 && minor >= 8) {
          return { cmd, version: verStr };
        }
      }
    } catch (e) {
      // continue search
    }
  }
  return null;
}

function main() {
  const workingPy = findWorkingPython();

  if (!workingPy) {
    console.error(`\n${RED}${BOLD}====================================================================${RESET}`);
    console.error(`  ${RED}${BOLD}❌ ERROR: Python 3.8+ Belum Terpasang atau Tidak Terdeteksi!${RESET}`);
    console.error(`${RED}${BOLD}====================================================================${RESET}\n`);
    console.error(`Waifu on Telegram membutuhkan ${BOLD}Python 3.8+ (64-bit)${RESET} untuk menjalankan bot & AI engine.\n`);

    if (process.platform === 'win32') {
      console.error(`${YELLOW}${BOLD}💡 Solusi Cepat Windows:${RESET}`);
      console.error(`1. Pasang otomatis via terminal PowerShell:`);
      console.error(`   ${CYAN}winget install Python.Python.3.11 -e${RESET}\n`);
      console.error(`2. Atau unduh installer resmi dari:`);
      console.error(`   ${CYAN}https://www.python.org/downloads/${RESET}`);
      console.error(`   ${BOLD}⚠️ PENTING: Centang kotak "Add python.exe to PATH" sebelum klik Install Now!${RESET}\n`);
      console.error(`3. Jika muncul pesan "Python was not found from Microsoft Store":`);
      console.error(`   Buka: Windows Settings > Apps > Advanced app settings > App execution aliases`);
      console.error(`   Matikan toggle untuk 'python.exe' dan 'python3.exe'.\n`);
    } else {
      console.error(`${YELLOW}${BOLD}💡 Solusi Cepat Linux/macOS:${RESET}`);
      console.error(`- Ubuntu/Debian: ${CYAN}sudo apt update && sudo apt install -y python3 python3-pip python3-venv${RESET}`);
      console.error(`- macOS: ${CYAN}brew install python${RESET}\n`);
    }
    process.exit(1);
  }

  if (!fs.existsSync(CLI_PY)) {
    console.error(`${RED}❌ CLI entrypoint '${CLI_PY}' tidak ditemukan!${RESET}`);
    process.exit(1);
  }

  const child = spawn(workingPy.cmd, [CLI_PY, ...process.argv.slice(2)], {
    stdio: 'inherit',
    cwd: PROJECT_ROOT,
    env: process.env
  });

  process.on('SIGINT', () => {
    // Graceful exit on Ctrl+C without error message
    process.exit(0);
  });

  child.on('close', (code) => {
    process.exit(code || 0);
  });

  child.on('error', (err) => {
    console.error(`${RED}❌ Gagal menjalankan CLI: ${err.message}${RESET}`);
    process.exit(1);
  });
}

main();
