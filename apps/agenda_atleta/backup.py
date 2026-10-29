"""Backup SQLite consistente (incluindo registros WAL) para operador local autorizado.

Uso: python -m apps.agenda_atleta.backup --output /local/seguro/backup.sqlite3
Guarde a APP_ENCRYPTION_KEY separadamente. Nunca versionar backups.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sqlite3


def create_backup(source: Path, destination: Path) -> Path:
    source, destination = source.resolve(), destination.absolute()
    if not source.is_file():
        raise FileNotFoundError(f"Banco não encontrado: {source}")
    if source == destination:
        raise ValueError("Backup não pode sobrescrever o banco principal")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation avoids accidental overwrite of a prior backup.
    with destination.open("xb"):
        pass
    try:
        with sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True) as original:
            with sqlite3.connect(destination) as copy:
                original.backup(copy)
                if copy.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise RuntimeError("Backup SQLite falhou na verificação de integridade")
        if os.name == "posix":
            destination.chmod(0o600)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return destination


def main():
    parser = argparse.ArgumentParser(description="Backup seguro do SQLite da Agenda do Atleta")
    parser.add_argument("--db", type=Path, default=Path(os.getenv("APP_DB_PATH", "data/agenda_atleta_secure.sqlite3")))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    saved = create_backup(args.db, args.output)
    print(f"Backup SQLite verificado: {saved}")


if __name__ == "__main__":
    main()