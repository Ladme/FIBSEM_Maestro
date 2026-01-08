# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

"""
maestro_secrets
===============

Command-line utility for storing and managing secrets in the system keychain
using `SecretStore`.

This tool is intended for one-time or occasional setup on a lab or instrument
machine. Secrets are stored securely via the OS keychain backend (through
`keyring`) and are later accessed by application components using `SecretRef`.
Secrets are never stored in source code or configuration files.

Usage:
    uv run src/maestro_secrets.py set <service> <key>
    uv run src/maestro_secrets.py delete <service> <key>

Commands:
    set:
        Stores a secret value in the keychain. The value is requested
        interactively and is not echoed to the terminal.

    delete:
        Removes a previously stored secret from the keychain.

Examples:
    Store an MU SMTP secondary password for email notifications::

        maestro-secrets set fibsem-maestro smtp.muni.cz/123456@IS.MUNI.CZ

    Reference the stored secret in configuration using:

        service: fibsem-maestro
        key: smtp.muni.cz/123456@IS.MUNI.CZ

Notes:
    - Secrets are stored per OS user account.
    - This command must be run as the same OS user that runs the application.
    - If a required secret is missing at runtime, the application will raise
      an error instructing the user to run this tool.
"""

from __future__ import annotations

import argparse
import getpass

from fibsem_maestro.notifications.secrets import SecretRef, SecretStore


def main() -> None:
    parser = argparse.ArgumentParser(prog="maestro-secrets")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_set = sub.add_parser("set")
    p_set.add_argument("service")
    p_set.add_argument("key")

    p_del = sub.add_parser("delete")
    p_del.add_argument("service")
    p_del.add_argument("key")

    args = parser.parse_args()
    store = SecretStore()

    ref = SecretRef(service=args.service, key=args.key)

    if args.cmd == "set":
        value = getpass.getpass("Secret value (hidden): ")
        store.set(ref, value)
        print("Saved.")
    elif args.cmd == "delete":
        store.delete(ref)
        print("Deleted.")


if __name__ == "__main__":
    main()
