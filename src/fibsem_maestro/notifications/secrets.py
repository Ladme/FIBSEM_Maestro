# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass

import keyring


class SecretsError(Exception):
    """Raised when a required secret cannot be retrieved or managed."""

    pass


@dataclass(frozen=True)
class SecretRef:
    """
    Reference to a secret stored in the system keychain.

    A `SecretRef` uniquely identifies a secret using a logical service name
    and a key within that service namespace. It contains no secret material
    itself and is safe to store in configuration files.

    Attributes:
        service (str):
            Logical service name under which the secret is stored
            (e.g., "fibsem-maestro").
        key (str):
            Identifier of the secret within the service namespace
            (e.g., "smtp.muni.cz/123456@IS.MUNI.CZ").
    """

    service: str
    key: str


class SecretStore:
    """
    Keyring-backed secret storage.

    This class provides a minimal abstraction over the system keychain,
    allowing secrets to be retrieved, stored, and deleted using `SecretRef`
    objects.
    """

    def get(self, ref: SecretRef) -> str:
        """
        Retrieve a secret from the keychain.

        Args:
            ref (SecretRef):
                Reference identifying the secret to retrieve.

        Returns:
            str:
                The secret value associated with the given reference.

        Raises:
            SecretsError:
                If the secret does not exist in the keychain.
        """
        value = keyring.get_password(ref.service, ref.key)
        if value is None:
            raise SecretsError(
                f"Missing secret in keyring: service={ref.service!r}, key={ref.key!r}.\n"
                f"Run `uv run src/maestro_secrets.py set {ref.service} {ref.key}` to store it."
            )

        return value

    def set(self, ref: SecretRef, value: str) -> None:
        """
        Store or update a secret in the keychain.

        Args:
            ref (SecretRef):
                Reference identifying where the secret should be stored.
            value (str):
                Secret value to store.
        """
        keyring.set_password(ref.service, ref.key, value)

    def delete(self, ref: SecretRef) -> None:
        """
        Delete a secret from the keychain.

        Args:
            ref (SecretRef):
                Reference identifying the secret to delete.
        """
        keyring.delete_password(ref.service, ref.key)
