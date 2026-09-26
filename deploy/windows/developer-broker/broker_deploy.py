"""DEV-1C: deployment policy and secret provisioning for MYCDeveloperBroker.

Invoked ONLY by the Windows deployment scripts (*.ps1) in this directory, on
the Windows host, with the backend venv interpreter:

    python -B -s broker_deploy.py <command> [options]

Split of responsibilities: the .ps1/.psm1 scripts talk to Windows (SCM, ACLs, SIDs,
secedit); this tool holds every decision that can be tested off-Windows --
ACL plan and ACL policy evaluation, directory ownership plan, service
compatibility verdict, SeServiceLogonRight INF merge, WinSW XML rendering,
the managed ``DEVELOPER_BROKER_*`` block of ``backend/.env``, the journaled
two-file provisioning transaction and the install-state ownership ledger.

Secret rules: the HMAC secret is generated here (``--secret-mode
generate``), read from stdin (``stdin``) or reused from the two existing
configuration files (``reuse``). It is NEVER accepted as a command-line
argument, never printed, never logged and never part of an error message.
It is written only to the rendered WinSW XML (protected service directory)
and to the managed block of ``backend/.env``.

Reuses the Broker's own validators (pipe name, minimum secret length) and
``ENVIRONMENT_KEYS`` so the deployment and the Broker cannot drift. Standard
library only; it executes no processes and opens no network connections.

Output: one JSON object on stdout. Exit codes: 0 ok, 3 refused by policy
(fail-closed; ``{"error": "<code>"}``), 2 usage error (argparse).
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from xml.etree import ElementTree
from xml.sax.saxutils import escape


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.developer_broker.host import ENVIRONMENT_KEYS as BROKER_ENVIRONMENT_KEYS  # noqa: E402
from app.developer_broker.pipe_name import validate_pipe_name  # noqa: E402
from app.developer_broker.protocol import BrokerConfigurationError, BrokerSecret  # noqa: E402


SERVICE_ID = "MYCDeveloperBroker"
SERVICE_ACCOUNT = "NT SERVICE\\" + SERVICE_ID
WRAPPER_NAME = SERVICE_ID + ".exe"
CONFIG_NAME = SERVICE_ID + ".xml"
TEMPLATE_PATH = HERE / (CONFIG_NAME + ".template")
EXPECTED_CLIENT_SID = "S-1-5-18"  # MYCBackend runs as LocalSystem (verified by the installer)
DEFAULT_IO_TIMEOUT_SECONDS = "5"
DEFAULT_MAX_CONNECTIONS = "4"
BACKEND_TIMEOUT_SECONDS = "5"

# Generated secrets: 48 random bytes, base64url (64 chars). Operator-supplied
# secrets must use the same alphabet: nothing that XML, WinSW %VAR%
# expansion or the .env parser could reinterpret.
SECRET_PATTERN = re.compile(r"[A-Za-z0-9_-]{43,512}")
# A service virtual account SID: S-1-5-80 + SHA-1 of the service name as
# five sub-authorities. Always resolved on the host, never computed here.
VIRTUAL_ACCOUNT_SID_PATTERN = re.compile(r"S-1-5-80-[0-9]+-[0-9]+-[0-9]+-[0-9]+-[0-9]+")

SYSTEM_SID = "S-1-5-18"
ADMINISTRATORS_SID = "S-1-5-32-544"
USERS_SID = "S-1-5-32-545"
TRUSTED_INSTALLER_SID = "S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464"
ALL_SERVICES_SID = "S-1-5-80-0"
TRUSTED_OWNERS = frozenset({SYSTEM_SID, ADMINISTRATORS_SID, TRUSTED_INSTALLER_SID})
# Never the Broker identity (same policy as windows_pipe.BROAD_SIDS /
# SHARED_SERVICE_SIDS, plus the aggregate service SIDs).
FORBIDDEN_BROKER_SIDS = frozenset({
    "S-1-5-18", "S-1-5-19", "S-1-5-20", ALL_SERVICES_SID, TRUSTED_INSTALLER_SID,
    "S-1-1-0", "S-1-5-11", "S-1-5-32-544", "S-1-5-32-545", "S-1-5-6",
})
# Principals that must never hold write access (and, for secret files,
# read access) on the protected paths.
BROAD_SIDS = frozenset({
    "S-1-1-0",       # Everyone
    "S-1-2-0",       # Local
    "S-1-3-0",       # Creator Owner
    "S-1-5-2",       # Network
    "S-1-5-4",       # Interactive
    "S-1-5-6",       # Service
    "S-1-5-7",       # Anonymous
    "S-1-5-11",      # Authenticated Users
    "S-1-5-32-545",  # Users
    "S-1-5-32-546",  # Guests
    "S-1-5-32-547",  # Power Users
    "S-1-5-113",     # Local account
    ALL_SERVICES_SID,
})

# --- file system rights ------------------------------------------------------
FILE_READ_DATA = 0x0001
FILE_WRITE_DATA = 0x0002
FILE_APPEND_DATA = 0x0004
FILE_READ_EA = 0x0008
FILE_WRITE_EA = 0x0010
FILE_EXECUTE = 0x0020
FILE_DELETE_CHILD = 0x0040
FILE_READ_ATTRIBUTES = 0x0080
FILE_WRITE_ATTRIBUTES = 0x0100
DELETE = 0x00010000
READ_CONTROL = 0x00020000
WRITE_DAC = 0x00040000
WRITE_OWNER = 0x00080000
SYNCHRONIZE = 0x00100000
GENERIC_ALL = 0x10000000
GENERIC_EXECUTE = 0x20000000
GENERIC_WRITE = 0x40000000
GENERIC_READ = 0x80000000

READ_AND_EXECUTE = 0x001200A9
MODIFY = 0x001301BF
FULL_CONTROL = 0x001F01FF
READ_BITS = FILE_READ_DATA | FILE_READ_EA | FILE_READ_ATTRIBUTES
_GENERIC_MAP = {
    GENERIC_READ: 0x00120089,
    GENERIC_WRITE: 0x00120116,
    GENERIC_EXECUTE: 0x001200A0,
    GENERIC_ALL: FULL_CONTROL,
}

# --- managed backend/.env block ------------------------------------------------
BLOCK_BEGIN = "# >>> MYC Developer Broker (managed by deploy/windows/developer-broker; do not edit) >>>"
BLOCK_END = "# <<< MYC Developer Broker <<<"
# Non-secret ownership marker written inside the managed block (a comment:
# the backend's .env parser ignores it, so it changes no configuration).
MARKER_PREFIX = "# dev1c-ownership-marker: "
_MARKER_PATTERN = re.compile(r"[0-9a-f]{32}")
# The fingerprint covers every identity-bearing line of the block (marker,
# transport, pipe, secret, SIDs, timeout). DEVELOPER_BROKER_ENABLED is the
# operational switch DEV-1C itself flips (install/catch/uninstall) and is
# excluded, so toggling it does not change ownership evidence.
FINGERPRINT_EXCLUDED_KEYS = ("DEVELOPER_BROKER_ENABLED",)
FINGERPRINT_ITERATIONS = 200_000
BACKEND_ENVIRONMENT_KEYS = (
    "DEVELOPER_BROKER_ENABLED",
    "DEVELOPER_BROKER_TRANSPORT",
    "DEVELOPER_BROKER_PIPE_NAME",
    "DEVELOPER_BROKER_SECRET",
    "DEVELOPER_BROKER_SERVICE_SID",
    "DEVELOPER_BROKER_CLIENT_SID",
    "DEVELOPER_BROKER_TIMEOUT_SECONDS",
)
_ENV_ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?(DEVELOPER_BROKER_[A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")

MAX_SCANNED_FILE_BYTES = 256 * 1024 * 1024
_SCAN_CHUNK_BYTES = 1024 * 1024


class PolicyError(Exception):
    """A fail-closed refusal. ``code`` is a fixed identifier, never data."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


# --- validation --------------------------------------------------------------

def check_pipe_name(value: str) -> str:
    try:
        return validate_pipe_name(value)
    except BrokerConfigurationError as exc:
        raise PolicyError(exc.reason) from None


def check_secret(value: str) -> str:
    if not SECRET_PATTERN.fullmatch(value or ""):
        raise PolicyError("secret_format_invalid")
    try:
        BrokerSecret.from_text(value)
    except BrokerConfigurationError:
        raise PolicyError("secret_format_invalid") from None
    return value


def check_client_sid(value: str) -> str:
    if value != EXPECTED_CLIENT_SID:
        raise PolicyError("client_sid_unexpected")
    return value


def check_service_sid(value: str) -> str:
    if not VIRTUAL_ACCOUNT_SID_PATTERN.fullmatch(value or "") or value in FORBIDDEN_BROKER_SIDS:
        raise PolicyError("service_sid_invalid")
    return value


def generate_secret() -> str:
    return secrets.token_urlsafe(48)


# --- ACL plan ---------------------------------------------------------------------

def _win(path: str) -> PureWindowsPath:
    text = (path or "").strip()
    candidate = PureWindowsPath(text)
    if not text or not candidate.is_absolute() or ".." in candidate.parts:
        raise PolicyError("path_invalid")
    return candidate


def _is_within(child: PureWindowsPath, parent: PureWindowsPath) -> bool:
    child_parts = [part.lower() for part in child.parts]
    parent_parts = [part.lower() for part in parent.parts]
    return child_parts[: len(parent_parts)] == parent_parts


def acl_plan(repo_root: str, python_home: str, service_dir: str, log_dir: str, service_sid: str) -> list[dict]:
    """Every explicit ACE the Broker identity receives -- nothing else.

    Scopes: ``tree`` = (OI)(CI) folder, subfolders and files;
    ``folder`` = this folder only (list/traverse; NOT its files, so
    ``backend\\.env`` stays unreadable); ``folder_and_files`` = (OI)(NP)
    this folder and the files directly inside it.
    """
    sid = check_service_sid(service_sid)
    repo = _win(repo_root)
    backend = repo / "backend"
    grants = [
        (_win(service_dir), "RX", "tree", "wrapper binary and its XML"),
        (_win(log_dir), "M", "tree", "WinSW log output"),
        (backend, "RX", "folder", "import root (working directory); files such as .env excluded"),
        (backend / "app", "RX", "folder_and_files", "app package __init__.py"),
        (backend / "app" / "developer_broker", "RX", "tree", "Broker code"),
        (repo / "venv", "RX", "tree", "venv interpreter and site-packages (pywin32)"),
    ]
    home = _win(python_home)
    if not _is_within(home, repo / "venv"):
        grants.append((home, "RX", "tree", "base Python runtime of the venv"))
    if _is_within(_win(log_dir), repo) or _is_within(_win(service_dir), repo):
        raise PolicyError("service_paths_inside_repo")
    inheritance = {"tree": "(OI)(CI)", "folder": "", "folder_and_files": "(OI)(NP)"}
    return [
        {
            "path": str(path),
            "sid": sid,
            "rights": rights,
            "scope": scope,
            "reason": reason,
            "icacls_grant": f"*{sid}:{inheritance[scope]}({rights})",
        }
        for path, rights, scope, reason in grants
    ]


# --- directory ownership plan -----------------------------------------------------

DEPLOYMENT_COMPONENT = "developer-broker"


def directory_plan(deployment_root: str, services_root: str, logs_root: str) -> dict:
    r"""Which directories DEV-1C may protect (owner, inheritance, ACEs and
    descendants) and which it may only inspect.

    DEV-1C owns exactly its own ``developer-broker`` children. Their parents
    (``C:\MYC\Deployment``, ``C:\MYC\Logs``) may hold other components and
    are never re-ACLed; ``C:\MYC\Services`` is the one deliberate, global and
    backed-up hardening, kept separate from ownership.
    """
    deployment, services, logs = _win(deployment_root), _win(services_root), _win(logs_root)
    state_dir = deployment / DEPLOYMENT_COMPONENT
    owned = [state_dir, state_dir / "acl-backups", services / DEPLOYMENT_COMPONENT, logs / DEPLOYMENT_COMPONENT]
    return {
        "owned": [str(path) for path in owned],
        "inspect_only": [str(deployment), str(logs)],
        "global_hardening": [str(services)],
    }


def is_owned_directory(path: str, plan: dict) -> bool:
    candidate = str(_win(path)).rstrip("\\").lower()
    return candidate in {entry.rstrip("\\").lower() for entry in plan["owned"]}


# --- ACL evaluation ---------------------------------------------------------------

def normalize_rights(value: int) -> int:
    mask = int(value) & 0xFFFFFFFF
    for generic, specific in _GENERIC_MAP.items():
        if mask & generic:
            mask = (mask & ~generic) | specific
    return mask


def _explicit_deny_sids(snapshot: dict) -> list[str]:
    return [str(ace.get("sid", "")).upper() for ace in snapshot.get("aces", [])
            if str(ace.get("type", "")).lower() == "deny" and not ace.get("inherited", False)]


def _allow_aces(snapshot: dict) -> list[tuple[str, int]]:
    aces = []
    for ace in snapshot.get("aces", []):
        if str(ace.get("type", "")).lower() != "allow":
            continue
        aces.append((str(ace.get("sid", "")).upper(), normalize_rights(ace.get("rights", 0))))
    return aces


ACL_POLICIES = ("services_root", "services_tree", "service_dir", "log_dir", "secret_file", "owned_parent", "owned_dir_base")
# Rights that let a principal delete, rename or re-ACL a CHILD it has no
# access to: whoever holds them on a parent can replace a DEV-1C directory.
CHILD_TAKEOVER_BITS = FILE_DELETE_CHILD | WRITE_DAC | WRITE_OWNER


def evaluate_acl(snapshot: dict, policy: str, *, service_sid: str | None = None, allow_users_read: bool = False) -> list[str]:
    """Violations of ``snapshot`` (owner SID, protection flag, ACEs as SIDs +
    raw rights) against ``policy``. Empty list == compliant."""
    if policy not in ACL_POLICIES:
        raise PolicyError("acl_policy_unknown")
    violations: list[str] = []
    aces = _allow_aces(snapshot)

    if policy == "owned_parent":
        # Inspected, never modified: the parent (e.g. C:\MYC\Deployment) may
        # hold other components. Ordinary Modify is tolerated -- it cannot
        # delete or re-ACL the protected DEV-1C child -- but not the bits
        # that can. CREATOR OWNER is an inherit-only template, not a grant.
        owner = str(snapshot.get("owner_sid", "")).upper()
        if owner not in TRUSTED_OWNERS:
            violations.append("untrusted_owner")
        for sid, rights in aces:
            if sid in (SYSTEM_SID, ADMINISTRATORS_SID, TRUSTED_INSTALLER_SID, "S-1-3-0"):
                continue
            if rights & CHILD_TAKEOVER_BITS:
                violations.append(f"child_takeover_rights:{sid}")
        return violations

    if policy == "secret_file":
        for sid, rights in aces:
            service_identity = sid.startswith("S-1-5-80-") and sid != TRUSTED_INSTALLER_SID
            if rights & READ_BITS and (sid in BROAD_SIDS or service_identity):
                violations.append(f"broad_read:{sid}")
        return violations

    owner = str(snapshot.get("owner_sid", "")).upper()
    if owner not in TRUSTED_OWNERS:
        violations.append("untrusted_owner")
    # DEV-1C-protected trees carry no Deny at all: an explicit Deny could
    # silently lock SYSTEM/Administrators/the Broker out of a "compliant" ACL.
    for sid in _explicit_deny_sids(snapshot):
        violations.append(f"unexpected_deny:{sid}")
    if policy != "services_tree" and not snapshot.get("protected", False):
        violations.append("inheritance_not_disabled")

    extra_allowed: dict[str, int] = {}
    if policy in ("services_root", "services_tree") and allow_users_read:
        extra_allowed[USERS_SID] = READ_AND_EXECUTE
    if policy == "owned_dir_base" and not (owner in (SYSTEM_SID, ADMINISTRATORS_SID)):
        violations.append("owner_not_administrators")
    if policy == "service_dir":
        extra_allowed[check_service_sid(service_sid or "")] = READ_AND_EXECUTE
    if policy == "log_dir":
        extra_allowed[check_service_sid(service_sid or "")] = MODIFY

    held: dict[str, int] = {}
    for sid, rights in aces:
        held[sid] = held.get(sid, 0) | rights
        if sid in (SYSTEM_SID, ADMINISTRATORS_SID, TRUSTED_INSTALLER_SID):
            continue
        if sid in extra_allowed:
            if rights & ~extra_allowed[sid]:
                violations.append(f"excess_rights:{sid}")
            continue
        violations.append(f"broad_principal:{sid}" if sid in BROAD_SIDS else f"unexpected_principal:{sid}")
    if policy != "services_tree":
        for sid in (SYSTEM_SID, ADMINISTRATORS_SID):
            if held.get(sid, 0) & FULL_CONTROL != FULL_CONTROL:
                violations.append(f"missing_full_control:{sid}")
    return violations


# --- service compatibility ---------------------------------------------------

def _unquote(path: str) -> str:
    text = (path or "").strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        text = text[1:-1]
    return text


def service_verdict(info: dict, expected_binary: str) -> dict:
    """``absent`` (install), ``compatible`` (re-run/upgrade) or
    ``incompatible`` (refuse: never adopt or overwrite a foreign service)."""
    if not info.get("exists"):
        return {"verdict": "absent", "reasons": []}
    reasons = []
    if str(info.get("start_name", "")).lower() != SERVICE_ACCOUNT.lower():
        reasons.append("start_name_mismatch")
    if _unquote(str(info.get("path_name", ""))).lower() != str(PureWindowsPath(expected_binary)).lower():
        reasons.append("binary_path_mismatch")
    if str(info.get("service_type", "Own Process")).lower() != "own process":
        reasons.append("service_type_mismatch")
    return {"verdict": "incompatible" if reasons else "compatible", "reasons": reasons}


def service_create_outcome(exit_code: int, verdict_after: str) -> dict:
    """Ledger decision after ``sc.exe create`` given the SCM RE-QUERIED
    afterwards. Ownership ``owned`` only when create succeeded AND the service
    now matches account/binary/type exactly. A create that failed and left
    nothing -> back to ``none``. Anything else (a failed create yet a
    service present, or a service that does not match) stays ``pending`` and
    fails closed for manual inspection."""
    if verdict_after not in ("absent", "compatible", "incompatible"):
        raise PolicyError("verdict_unknown")
    if exit_code == 0 and verdict_after == "compatible":
        return {"service": "owned", "ok": True, "reason": "created"}
    if exit_code != 0 and verdict_after == "absent":
        return {"service": "none", "ok": False, "reason": "create_failed_service_absent"}
    if exit_code == 0 and verdict_after == "absent":
        return {"service": "pending", "ok": False, "reason": "created_but_not_visible"}
    if verdict_after == "incompatible":
        return {"service": "pending", "ok": False, "reason": "service_mismatch_after_create"}
    return {"service": "pending", "ok": False, "reason": "create_failed_but_service_present"}


def service_install_decision(verdict: str, state: dict | None) -> str:
    """What the installer may do with the SCM entry. A compatible service is
    re-configured ONLY when the ledger proves DEV-1C created it (``owned``).
    ``pending`` is a partial install to reconcile with Uninstall first;
    ``none`` or no ledger means the service is not proven to be ours. A
    ledger that claims a service which no longer exists must be reconciled
    by Uninstall too (it sets the record back to ``none``)."""
    ownership = "none" if state is None else state["owned"]["service"]
    if verdict == "incompatible":
        raise PolicyError("service_incompatible")
    if verdict == "absent":
        if ownership == "none":
            return "create"
        raise PolicyError("service_ledger_reconciliation_required")
    if verdict == "compatible":
        if ownership == "owned":
            return "reconfigure"
        if ownership == "pending":
            raise PolicyError("service_partial_install_reconcile_first")
        raise PolicyError("service_not_proven_owned")
    raise PolicyError("verdict_unknown")


def winsw_integrity(actual_sha256: str, expected_sha256: str | None,
                    config_actual_sha256: str | None = None, config_expected_sha256: str | None = None) -> list[str]:
    r"""The WinSW source lived under C:\MYC\Services while Authenticated Users
    had Modify there: its metadata proves nothing. It is used only if its
    SHA-256 equals a hash the operator obtained from a trusted provenance
    (the official WinSW release). The same applies to an accompanying
    .exe.config; an unverified config is never copied."""
    violations = []
    if not expected_sha256:
        violations.append("winsw_expected_sha256_missing")
    elif not _SHA256_PATTERN.fullmatch(expected_sha256):
        violations.append("winsw_expected_sha256_invalid")
    elif not hmac.compare_digest(str(actual_sha256).upper(), expected_sha256.upper()):
        violations.append("winsw_sha256_mismatch")
    if config_actual_sha256:
        if not config_expected_sha256:
            violations.append("winsw_config_unverified")
        elif not _SHA256_PATTERN.fullmatch(config_expected_sha256):
            violations.append("winsw_config_expected_sha256_invalid")
        elif not hmac.compare_digest(config_actual_sha256.upper(), config_expected_sha256.upper()):
            violations.append("winsw_config_sha256_mismatch")
    return violations


# --- SeServiceLogonRight (secedit) -------------------------------------------------

def _read_inf(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "[" in text:
            return text
    raise PolicyError("secedit_export_unreadable")


def privilege_members(inf_text: str, privilege: str) -> list[str]:
    in_section = False
    for line in inf_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_section = stripped.lower() == "[privilege rights]"
            continue
        if in_section and "=" in stripped:
            name, _, value = stripped.partition("=")
            if name.strip().lower() == privilege.lower():
                return [member.strip() for member in value.split(",") if member.strip()]
    return []


def logon_right_inf(members: list[str]) -> str:
    return (
        "[Unicode]\r\nUnicode=yes\r\n"
        '[Version]\r\nsignature="$CHICAGO$"\r\nRevision=1\r\n'
        "[Privilege Rights]\r\n"
        f"SeServiceLogonRight = {','.join(members)}\r\n"
    )


def logon_right_change(inf_text: str, sid: str, action: str) -> tuple[str, str | None]:
    """(status, inf_to_apply | None). Only SeServiceLogonRight is ever
    written; every existing member is preserved verbatim."""
    sid = check_service_sid(sid)
    token = "*" + sid
    granted = privilege_members(inf_text, "SeServiceLogonRight")
    upper = [member.upper() for member in granted]
    if action == "grant":
        denied = [member.upper() for member in privilege_members(inf_text, "SeDenyServiceLogonRight")]
        if token.upper() in denied or ("*" + ALL_SERVICES_SID) in denied:
            raise PolicyError("service_logon_denied_by_policy")
        if token.upper() in upper:
            return "already_granted", None
        if ("*" + ALL_SERVICES_SID) in upper:
            return "granted_via_all_services", None
        return "grant_required", logon_right_inf([*granted, token])
    if action == "revoke":
        if token.upper() not in upper:
            return "not_present", None
        remaining = [member for member in granted if member.upper() != token.upper()]
        if not remaining:
            # The Broker is the only member: the original state was "right
            # unassigned". A one-line INF cannot reliably express an empty
            # assignment, so no INF is produced; the caller removes exactly
            # this SID's right through the LSA API (LsaRemoveAccountRights).
            return "revoke_last_member", None
        return "revoke_required", logon_right_inf(remaining)
    raise PolicyError("logon_action_unknown")


# --- WinSW XML ----------------------------------------------------------------------

def broker_environment(pipe_name: str, secret: str, client_sid: str, service_sid: str) -> dict[str, str]:
    environment = {
        "DEVELOPER_BROKER_PIPE_NAME": check_pipe_name(pipe_name),
        "DEVELOPER_BROKER_SECRET": check_secret(secret),
        "DEVELOPER_BROKER_CLIENT_SID": check_client_sid(client_sid),
        "DEVELOPER_BROKER_SERVICE_SID": check_service_sid(service_sid),
        "DEVELOPER_BROKER_IO_TIMEOUT_SECONDS": DEFAULT_IO_TIMEOUT_SECONDS,
        "DEVELOPER_BROKER_MAX_CONNECTIONS": DEFAULT_MAX_CONNECTIONS,
    }
    if tuple(environment) != tuple(BROKER_ENVIRONMENT_KEYS):
        raise PolicyError("broker_environment_drift")
    if client_sid == service_sid:
        raise PolicyError("sids_not_distinct")
    return environment


def render_service_xml(template: str, *, python_exe: str, working_dir: str, log_dir: str, environment: dict[str, str]) -> str:
    tokens = {
        "PYTHON_EXE": str(_win(python_exe)),
        "WORKING_DIR": str(_win(working_dir)),
        "LOG_DIR": str(_win(log_dir)),
        "PIPE_NAME": environment["DEVELOPER_BROKER_PIPE_NAME"],
        "SECRET": environment["DEVELOPER_BROKER_SECRET"],
        "CLIENT_SID": environment["DEVELOPER_BROKER_CLIENT_SID"],
        "SERVICE_SID": environment["DEVELOPER_BROKER_SERVICE_SID"],
        "IO_TIMEOUT_SECONDS": environment["DEVELOPER_BROKER_IO_TIMEOUT_SECONDS"],
        "MAX_CONNECTIONS": environment["DEVELOPER_BROKER_MAX_CONNECTIONS"],
    }
    rendered = template
    for name, value in tokens.items():
        if "%" in value:  # WinSW expands %VAR% in values
            raise PolicyError("value_contains_percent")
        rendered = rendered.replace("{{" + name + "}}", escape(value, {'"': "&quot;"}))
    if "{{" in rendered or "}}" in rendered:
        raise PolicyError("template_token_unresolved")
    root = ElementTree.fromstring(rendered)
    if root.tag != "service" or root.findtext("id") != SERVICE_ID:
        raise PolicyError("template_invalid")
    if root.find("serviceaccount") is not None:
        raise PolicyError("template_invalid")  # identity is owned by the SCM registration
    rendered_env = {node.get("name"): node.get("value") for node in root.findall("env")}
    if rendered_env != environment:
        raise PolicyError("template_invalid")
    return rendered


def xml_environment(xml_text: str) -> dict[str, str]:
    root = ElementTree.fromstring(xml_text)
    return {node.get("name"): node.get("value") for node in root.findall("env")}


# --- managed .env block ----------------------------------------------------------------

def _newline_of(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def split_env_block(text: str) -> tuple[list[str], dict[str, str] | None, list[str]]:
    """(lines before, managed values | None, lines after). Refuses anything
    ambiguous: several blocks, an unterminated block, or DEVELOPER_BROKER_*
    assignments outside the managed block."""
    lines = text.splitlines()
    begins = [index for index, line in enumerate(lines) if line.strip() == BLOCK_BEGIN]
    ends = [index for index, line in enumerate(lines) if line.strip() == BLOCK_END]
    if len(begins) > 1 or len(ends) > 1 or len(begins) != len(ends):
        raise PolicyError("env_block_malformed")
    if begins and ends[0] < begins[0]:
        raise PolicyError("env_block_malformed")
    if begins:
        before, inner, after = lines[: begins[0]], lines[begins[0] + 1 : ends[0]], lines[ends[0] + 1 :]
    else:
        before, inner, after = lines, None, []
    for line in (*before, *after):
        if _ENV_ASSIGNMENT.match(line):
            raise PolicyError("env_unmanaged_developer_broker_keys")
    if inner is None:
        return before, None, after
    values: dict[str, str] = {}
    markers = [line.strip()[len(MARKER_PREFIX):] for line in inner if line.strip().startswith(MARKER_PREFIX)]
    if len(markers) > 1 or (markers and not _MARKER_PATTERN.fullmatch(markers[0])):
        raise PolicyError("env_block_malformed")
    for line in inner:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _ENV_ASSIGNMENT.match(line)
        if not match or match.group(1) not in BACKEND_ENVIRONMENT_KEYS or match.group(1) in values:
            raise PolicyError("env_block_malformed")
        values[match.group(1)] = match.group(2)
    return before, values, after


def block_marker(text: str) -> str | None:
    """The ownership marker of the managed block, if any (validated by
    split_env_block)."""
    lines = text.splitlines()
    begins = [index for index, line in enumerate(lines) if line.strip() == BLOCK_BEGIN]
    if not begins:
        return None
    for line in lines[begins[0] + 1:]:
        if line.strip() == BLOCK_END:
            break
        if line.strip().startswith(MARKER_PREFIX):
            return line.strip()[len(MARKER_PREFIX):]
    return None


def block_fingerprint(values: dict[str, str], marker: str) -> str:
    """Ownership fingerprint of a managed block. Derived with PBKDF2-HMAC-
    SHA256 (salt = the marker, 200k iterations) over a canonical rendering:
    it proves "this exact block" without persisting or exposing the secret,
    and is deliberately slow so even a weak operator-supplied secret cannot
    be recovered from it. Never printed."""
    if not _MARKER_PATTERN.fullmatch(marker or ""):
        raise PolicyError("marker_invalid")
    canonical = "\n".join([f"MARKER={marker}", *[f"{key}={values.get(key, '')}" for key in BACKEND_ENVIRONMENT_KEYS
                                                   if key not in FINGERPRINT_EXCLUDED_KEYS]])
    return hashlib.pbkdf2_hmac("sha256", canonical.encode("utf-8"), bytes.fromhex(marker), FINGERPRINT_ITERATIONS).hex()


def new_marker() -> str:
    return secrets.token_hex(16)


def render_env_file(text: str, values: dict[str, str] | None, marker: str | None = None) -> str:
    """``text`` with the managed block replaced by ``values`` (in the fixed
    key order, with the ownership ``marker`` if given) or removed (``None``).
    Everything else is kept verbatim."""
    newline = _newline_of(text)
    before, existing, after = split_env_block(text)
    if existing is not None or values is not None:
        while before and not before[-1].strip():  # the separator line belongs to the block
            before = before[:-1]
    block: list[str] = []
    if values is not None:
        if set(values) != set(BACKEND_ENVIRONMENT_KEYS):
            raise PolicyError("env_block_keys_invalid")
        marker_lines = [MARKER_PREFIX + marker] if marker else []
        block = [BLOCK_BEGIN, *marker_lines, *[f"{key}={values[key]}" for key in BACKEND_ENVIRONMENT_KEYS], BLOCK_END]
        if before:
            block = ["", *block]
    lines = [*before, *block, *after]
    return newline.join(lines) + (newline if lines else "")


def backend_values(pipe_name: str, secret: str, client_sid: str, service_sid: str, *, enabled: bool) -> dict[str, str]:
    return {
        "DEVELOPER_BROKER_ENABLED": "true" if enabled else "false",
        "DEVELOPER_BROKER_TRANSPORT": "named_pipe",
        "DEVELOPER_BROKER_PIPE_NAME": check_pipe_name(pipe_name),
        "DEVELOPER_BROKER_SECRET": check_secret(secret),
        "DEVELOPER_BROKER_SERVICE_SID": check_service_sid(service_sid),
        "DEVELOPER_BROKER_CLIENT_SID": check_client_sid(client_sid),
        "DEVELOPER_BROKER_TIMEOUT_SECONDS": BACKEND_TIMEOUT_SECONDS,
    }


# --- file I/O -------------------------------------------------------------------------

def _read_text(path: Path) -> str:
    with open(path, "r", encoding="utf-8", newline="") as handle:
        return handle.read()


def _remove_quietly(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _write_private(path: Path, data: bytes) -> None:
    """A NEW file (never an existing one), owner-only mode. On Windows the
    ACL is the one inherited from its (protected) directory."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _replace_file(path: Path, data: bytes) -> None:
    """Atomic single-file switch for files in a protected directory (the
    rendered XML, the install state): staged private sibling + os.replace
    (same directory, so same filesystem)."""
    staged = path.with_name("." + path.name + ".new")
    _remove_quietly(staged)
    _write_private(staged, data)
    try:
        os.replace(staged, path)
    except BaseException:
        _remove_quietly(staged)
        raise


def _rewrite_in_place(path: Path, data: bytes) -> None:
    """For backend/.env: rewritten through the SAME file object so its
    existing ACL is preserved (a replacement file would take the directory's
    inherited ACL instead)."""
    with open(path, "r+b") as handle:
        handle.seek(0)
        handle.write(data)
        handle.truncate()
        handle.flush()
        os.fsync(handle.fileno())


def _existing_secret(xml_path: Path, env_path: Path) -> str:
    """Reuse only a consistent pair: both present and identical. Divergent
    copies are refused, never arbitrated."""
    try:
        from_xml = xml_environment(_read_text(xml_path)).get("DEVELOPER_BROKER_SECRET") or ""
        _before, block, _after = split_env_block(_read_text(env_path))
    except (OSError, ElementTree.ParseError):
        raise PolicyError("secret_reuse_unavailable") from None
    from_env = (block or {}).get("DEVELOPER_BROKER_SECRET") or ""
    if not from_xml or not from_env:
        raise PolicyError("secret_reuse_unavailable")
    if not hmac.compare_digest(from_xml.encode("utf-8"), from_env.encode("utf-8")):
        raise PolicyError("secret_mismatch_between_configs")
    return from_xml


def _obtain_secret(mode: str, xml_path: Path, env_path: Path) -> str:
    if mode == "generate":
        return check_secret(generate_secret())
    if mode == "stdin":
        return check_secret(sys.stdin.readline().rstrip("\r\n"))
    if mode == "reuse":
        return check_secret(_existing_secret(xml_path, env_path))
    raise PolicyError("secret_mode_unknown")


# --- no-follow deletion of a DEV-1C-owned tree ----------------------------------------------
#
# PowerShell 5.1 Remove-Item -Recurse is not trusted near junctions. The
# caller (PowerShell) first proves the directory is owned and protected
# (only SYSTEM/Administrators can write); this walk then deletes bottom-up,
# re-checking EVERY entry with lstat immediately before unlink/rmdir, never
# following a symlink/junction/mount point, and using a non-recursive rmdir
# that fails if anything appeared in a directory after it was scanned.

FILE_ATTRIBUTE_REPARSE_POINT = 0x400


def is_reparse(path: str | os.PathLike) -> bool:
    info = os.lstat(path)
    if getattr(info, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT:
        return True
    return stat.S_ISLNK(info.st_mode)


def _checked_scandir(path: Path) -> list[os.DirEntry]:
    if is_reparse(path):
        raise PolicyError("reparse_point_in_owned_tree")
    with os.scandir(path) as iterator:
        return list(iterator)


def remove_owned_tree(root: Path) -> int:
    """Deletes ``root`` and everything under it without following links.
    Any reparse point, a vanished or newly appeared entry, or any OS error
    aborts with a fixed code and leaves the remaining tree in place."""
    removed = 0
    try:
        if is_reparse(root):
            raise PolicyError("reparse_point_in_owned_tree")
        for entry in _checked_scandir(root):
            child = Path(entry.path)
            if is_reparse(child):
                raise PolicyError("reparse_point_in_owned_tree")
            if child.is_dir():
                removed += remove_owned_tree(child)
            else:
                if is_reparse(child):  # re-check right before the unlink
                    raise PolicyError("reparse_point_in_owned_tree")
                os.unlink(child)
                removed += 1
        if is_reparse(root):
            raise PolicyError("reparse_point_in_owned_tree")
        os.rmdir(root)  # non-recursive: fails if something appeared meanwhile
        return removed + 1
    except PolicyError:
        raise
    except OSError:
        raise PolicyError("owned_tree_changed_during_removal") from None


# --- restore of the C:\\MYC\\Services ACL backup (Restore-MYCServicesAcl.ps1) ---------------------

# SDDL as produced by Get-Acl .Sddl for a file-system object: owner, group,
# DACL flags and ACEs made only of SDDL characters (no conditional ACEs).
_SDDL_PATTERN = re.compile(r"O:[A-Za-z0-9-]+G:[A-Za-z0-9-]+D:[A-Z]*(\([A-Za-z0-9;-]*\))*")


def restore_plan(records: object, services_root: str, excluded: str) -> list[dict]:
    """Strict validation of a Backup-MYCAcl JSON ([{"path", "sddl"}]) and the
    safe restore order. Refuses (nothing is restored) on: a non-list or
    empty backup, extra/missing fields, non-canonical or relative paths,
    ``..``, paths outside the services root, paths inside the Broker's own
    directory (never part of the backup), duplicates (case-insensitive), an
    invalid SDDL, or a backup without the root entry.
    Order: deepest entries first and the root LAST -- a child is restored
    while the current (hardened) ACL of its parents still grants
    Administrators full control, and the root's inheritable ACEs are put
    back at the end."""
    if not isinstance(records, list) or not records:
        raise PolicyError("backup_invalid")
    root, broker = _win(services_root), _win(excluded)
    seen: set[str] = set()
    plan = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {"path", "sddl"}:
            raise PolicyError("backup_entry_invalid")
        path, sddl = record["path"], record["sddl"]
        if not isinstance(path, str) or not isinstance(sddl, str):
            raise PolicyError("backup_entry_invalid")
        candidate = _win(path)
        if str(candidate).lower() != path.lower() or "/" in path:
            raise PolicyError("backup_path_not_canonical")
        if not _is_within(candidate, root):
            raise PolicyError("backup_path_out_of_scope")
        if _is_within(candidate, broker):
            raise PolicyError("backup_path_out_of_scope")
        key = path.lower()
        if key in seen:
            raise PolicyError("backup_entry_duplicate")
        seen.add(key)
        if not _SDDL_PATTERN.fullmatch(sddl):
            raise PolicyError("backup_sddl_invalid")
        plan.append({"path": path, "sddl": sddl, "depth": len(candidate.parts)})
    if str(root).lower() not in seen:
        raise PolicyError("backup_root_missing")
    return sorted(plan, key=lambda entry: (-entry["depth"], entry["path"].lower()))


# --- two-file provisioning transaction -------------------------------------------------
#
# XML and backend/.env must never stay split (new XML + old .env). Before the
# first byte is written, the previous content of BOTH files is saved in a
# private journal inside the protected DEV-1C state directory. Commit 1
# replaces the XML atomically; commit 2 rewrites .env in place. Any failure
# restores both from memory; a crash leaves the journal, and the next
# provisioning run restores it before doing anything else. The journal holds
# secrets only transiently: it is removed on success, on failure after a
# successful restore, and on recovery. A "committed" marker is written after
# both commits so a crash during cleanup never reverts a finished commit.

JOURNAL_NAME = "provision-journal"
_JOURNAL_XML_BEFORE = "xml.before"
_JOURNAL_XML_ABSENT = "xml.absent"
_JOURNAL_ENV_BEFORE = "env.before"
_JOURNAL_TARGETS = "targets.json"
_JOURNAL_COMMITTED = "committed"


def _journal(journal_dir: Path) -> Path:
    return journal_dir / JOURNAL_NAME


def _discard_dir(path: Path) -> None:
    if not path.exists():
        return
    for child in path.iterdir():
        _remove_quietly(child)
    path.rmdir()


def _write_journal(journal_dir: Path, xml_path: Path, env_path: Path, old_xml: bytes | None, old_env: bytes) -> None:
    staging = journal_dir / ("." + JOURNAL_NAME + ".tmp")
    try:
        _discard_dir(staging)
        staging.mkdir(mode=0o700)
        targets = {"xml": str(xml_path.resolve()), "env": str(env_path.resolve())}
        _write_private(staging / _JOURNAL_TARGETS, json.dumps(targets).encode("utf-8"))
        _write_private(staging / _JOURNAL_ENV_BEFORE, old_env)
        if old_xml is None:
            _write_private(staging / _JOURNAL_XML_ABSENT, b"")
        else:
            _write_private(staging / _JOURNAL_XML_BEFORE, old_xml)
        os.rename(staging, _journal(journal_dir))
    except Exception:
        try:
            _discard_dir(staging)
        except OSError:
            pass
        raise PolicyError("provision_journal_failed") from None


def _restore_pair(xml_path: Path, env_path: Path, old_xml: bytes | None, old_env: bytes) -> None:
    _rewrite_in_place(env_path, old_env)
    if old_xml is None:
        _remove_quietly(xml_path)
    else:
        _replace_file(xml_path, old_xml)


def recover_provision(journal_dir: Path, xml_path: Path, env_path: Path) -> str:
    """Finishes an interrupted provisioning: ``none`` (no journal),
    ``committed`` (the commit had finished; journal discarded) or
    ``restored`` (both files back to their previous content)."""
    journal = _journal(journal_dir)
    if not journal.exists():
        return "none"
    try:
        targets = json.loads((journal / _JOURNAL_TARGETS).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise PolicyError("provision_journal_corrupt") from None
    if targets != {"xml": str(xml_path.resolve()), "env": str(env_path.resolve())}:
        raise PolicyError("provision_journal_foreign")
    if (journal / _JOURNAL_COMMITTED).exists():
        _discard_dir(journal)
        return "committed"
    try:
        old_env = (journal / _JOURNAL_ENV_BEFORE).read_bytes()
        old_xml = None if (journal / _JOURNAL_XML_ABSENT).exists() else (journal / _JOURNAL_XML_BEFORE).read_bytes()
        _restore_pair(xml_path, env_path, old_xml, old_env)
    except (OSError, PolicyError):
        raise PolicyError("provision_recovery_failed") from None
    _discard_dir(journal)
    return "restored"


def provision_files(journal_dir: Path, xml_path: Path, env_path: Path, xml_text: str, env_text: str) -> None:
    """Both-or-neither switch of the rendered XML and backend/.env."""
    if not journal_dir.is_dir():
        raise PolicyError("journal_dir_missing")
    old_env = env_path.read_bytes()
    old_xml = xml_path.read_bytes() if xml_path.exists() else None
    _write_journal(journal_dir, xml_path, env_path, old_xml, old_env)
    try:
        _replace_file(xml_path, xml_text.encode("utf-8"))    # commit 1 (atomic)
        _rewrite_in_place(env_path, env_text.encode("utf-8"))  # commit 2
    except Exception:
        try:
            _restore_pair(xml_path, env_path, old_xml, old_env)
        except Exception:
            # Journal kept on purpose: the next run restores from it.
            raise PolicyError("provision_rollback_failed") from None
        _discard_dir(_journal(journal_dir))
        raise PolicyError("provision_commit_failed") from None
    try:
        _write_private(_journal(journal_dir) / _JOURNAL_COMMITTED, b"")
        _discard_dir(_journal(journal_dir))
    except OSError:
        raise PolicyError("provision_journal_cleanup_failed") from None


# --- install state: ownership ledger ----------------------------------------------------
#
# Written BEFORE the first mutation that needs a later rollback and updated
# atomically after each one, so uninstall removes exactly what DEV-1C
# created or added -- never by guessing. No secret is ever stored here.

STATE_SCHEMA = 6
SERVICE_STATES = ("none", "pending", "owned")
# "uninstalled": service/right/ACEs removed but owned directories retained
# (uninstall without -RemoveServiceFiles/-RemoveLogs): the ledger stays as a
# tombstone so a later install recognises them as DEV-1C's.
STATE_PHASES = ("installing", "installed", "uninstalling", "uninstalled")
LOGON_RIGHT_STATES = ("none", "pending", "added")
# Directories and the backend config block follow the same model as the SCM
# entry: "pending" = intent recorded BEFORE the mutation (never authority to
# delete or modify); "owned" only after the result was re-read and proven.
DIRECTORY_STATES = ("none", "pending", "owned")
BACKEND_CONFIG_STATES = ("none", "pending", "owned")
BACKEND_ACTIVATION_STATES = ("none", "pending_restart", "restarted", "restart_failed")
_STATE_KEYS = {"schema", "service_id", "service_account", "repo_root", "service_sid", "phase", "owned",
               "winsw_sha256", "backend_activation", "updated_at_utc"}
_OWNED_KEYS = {"service", "logon_right", "acl_grants", "service_dir", "log_dir", "backend_config", "backend_config_evidence"}
_EVIDENCE_KEYS = {"marker", "fingerprint", "fingerprint_next"}
GRANT_STATES = ("pending", "owned")
_GRANT_PATTERN = re.compile(r"\*(S-1-5-80-[0-9]+-[0-9]+-[0-9]+-[0-9]+-[0-9]+):(\(OI\)\(CI\)|\(OI\)\(NP\))?\((RX|M)\)")
_SHA256_PATTERN = re.compile(r"[0-9A-Fa-f]{64}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_state(repo_root: str) -> dict:
    return {
        "schema": STATE_SCHEMA,
        "service_id": SERVICE_ID,
        "service_account": SERVICE_ACCOUNT,
        "repo_root": str(_win(repo_root)),
        "service_sid": None,
        "phase": "installing",
        "owned": {"service": "none", "logon_right": "none", "acl_grants": [], "service_dir": "none", "log_dir": "none",
                  "backend_config": "none",
                  "backend_config_evidence": {"marker": None, "fingerprint": None, "fingerprint_next": None}},
        "winsw_sha256": None,
        "backend_activation": "none",
        "updated_at_utc": _utc_now(),
    }


def validate_state(data: object, repo_root: str) -> dict:
    """Trusted only if the schema and identity are exactly ours: corrupt ->
    ``state_corrupt``; another schema/service/account/repo -> ``state_incompatible``."""
    if not isinstance(data, dict) or set(data) != _STATE_KEYS:
        raise PolicyError("state_corrupt")
    owned = data["owned"]
    if not isinstance(owned, dict) or set(owned) != _OWNED_KEYS:
        raise PolicyError("state_corrupt")
    if data["schema"] != STATE_SCHEMA or data["service_id"] != SERVICE_ID or data["service_account"] != SERVICE_ACCOUNT:
        raise PolicyError("state_incompatible")
    if not isinstance(data["repo_root"], str) or data["repo_root"].lower() != str(_win(repo_root)).lower():
        raise PolicyError("state_incompatible")
    sid = data["service_sid"]
    if sid is not None and not (isinstance(sid, str) and VIRTUAL_ACCOUNT_SID_PATTERN.fullmatch(sid) and sid not in FORBIDDEN_BROKER_SIDS):
        raise PolicyError("state_corrupt")
    if data["phase"] not in STATE_PHASES or not isinstance(data["updated_at_utc"], str):
        raise PolicyError("state_corrupt")
    if data["winsw_sha256"] is not None and not (isinstance(data["winsw_sha256"], str) and _SHA256_PATTERN.fullmatch(data["winsw_sha256"])):
        raise PolicyError("state_corrupt")
    if owned["service"] not in SERVICE_STATES or owned["logon_right"] not in LOGON_RIGHT_STATES:
        raise PolicyError("state_corrupt")
    if owned["service_dir"] not in DIRECTORY_STATES or owned["log_dir"] not in DIRECTORY_STATES:
        raise PolicyError("state_corrupt")
    if owned["backend_config"] not in BACKEND_CONFIG_STATES:
        raise PolicyError("state_corrupt")
    evidence = owned["backend_config_evidence"]
    if not isinstance(evidence, dict) or set(evidence) != _EVIDENCE_KEYS:
        raise PolicyError("state_corrupt")
    if evidence["marker"] is not None and not (isinstance(evidence["marker"], str) and _MARKER_PATTERN.fullmatch(evidence["marker"])):
        raise PolicyError("state_corrupt")
    for key in ("fingerprint", "fingerprint_next"):
        if evidence[key] is not None and not (isinstance(evidence[key], str) and _SHA256_PATTERN.fullmatch(evidence[key])):
            raise PolicyError("state_corrupt")
    # pending/owned always carry evidence; none never does
    has_evidence = evidence["marker"] is not None and evidence["fingerprint"] is not None
    if (owned["backend_config"] == "none") == has_evidence or (evidence["fingerprint_next"] and not has_evidence):
        raise PolicyError("state_corrupt")
    if data["backend_activation"] not in BACKEND_ACTIVATION_STATES:
        raise PolicyError("state_corrupt")
    grants = owned["acl_grants"]
    if not isinstance(grants, list):
        raise PolicyError("state_corrupt")
    for grant in grants:
        if not isinstance(grant, dict) or set(grant) != {"path", "grant", "status"} or not isinstance(grant["path"], str):
            raise PolicyError("state_corrupt")
        if grant["status"] not in GRANT_STATES:
            raise PolicyError("state_corrupt")
        match = _GRANT_PATTERN.fullmatch(str(grant["grant"]))
        if not match or sid is None or match.group(1) != sid:
            raise PolicyError("state_corrupt")
        _win(grant["path"])
    if len({grant["path"].lower() for grant in grants}) != len(grants):
        raise PolicyError("state_corrupt")
    if owned["logon_right"] != "none" and sid is None:
        raise PolicyError("state_corrupt")
    return data


def load_state(path: Path, repo_root: str) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_bytes().decode("utf-8-sig"))
    except (OSError, ValueError):
        raise PolicyError("state_corrupt") from None
    return validate_state(data, repo_root)


def save_state(path: Path, state: dict, repo_root: str) -> None:
    validate_state(state, repo_root)
    _replace_file(path, (json.dumps(state, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def apply_state_update(
    state: dict,
    *,
    service_sid: str | None = None,
    service: str | None = None,
    logon_right: str | None = None,
    grant_path: str | None = None,
    grant_value: str | None = None,
    grant_status: str | None = None,
    phase: str | None = None,
    winsw_sha256: str | None = None,
    service_dir: str | None = None,
    log_dir: str | None = None,
    backend_config: str | None = None,
    backend_activation: str | None = None,
) -> dict:
    """Pure, monotonic ownership transitions. Ownership is only ever
    recorded by the step that creates/adds the resource and only ever
    cleared by the rollback step that removed it."""
    updated = json.loads(json.dumps(state))
    owned = updated["owned"]
    if service_sid is not None:
        sid = check_service_sid(service_sid)
        if updated["service_sid"] not in (None, sid):
            raise PolicyError("state_sid_mismatch")
        updated["service_sid"] = sid
    if service is not None:
        # none -> pending (intent, BEFORE sc.exe create) -> owned (only after
        # the SCM was re-queried and account/binary/type match exactly).
        # pending -> none when the SCM shows the create did not happen;
        # owned/pending -> none only after uninstall deleted the service.
        allowed = {"none": {"none", "pending"}, "pending": {"pending", "owned", "none"}, "owned": {"owned", "none"}}
        if service not in SERVICE_STATES or service not in allowed[owned["service"]]:
            raise PolicyError("state_service_transition_invalid")
        owned["service"] = service
    if logon_right is not None:
        current = owned["logon_right"]
        allowed = {
            "none": {"none", "pending"},
            "pending": {"pending", "added", "none"},
            "added": {"added", "pending", "none"},
        }[current]
        if logon_right not in LOGON_RIGHT_STATES or logon_right not in allowed:
            raise PolicyError("state_logon_transition_invalid")
        if logon_right != "none" and updated["service_sid"] is None:
            raise PolicyError("state_sid_missing")
        owned["logon_right"] = logon_right
    if grant_status is not None:
        # One grant at a time: absent -> pending (recorded after proving no
        # explicit Broker ACE existed, just BEFORE /grant:r) -> owned (only
        # after the ACL was re-read and matched exactly); "remove" only
        # after uninstall revoked or found it gone. An owned grant never
        # goes back to pending; a path keeps one exact planned grant.
        path = str(_win(grant_path or ""))
        existing = next((entry for entry in owned["acl_grants"] if entry["path"].lower() == path.lower()), None)
        if grant_status == "remove":
            owned["acl_grants"] = [entry for entry in owned["acl_grants"] if entry is not existing]
        elif grant_status in GRANT_STATES:
            match = _GRANT_PATTERN.fullmatch(str(grant_value or ""))
            if not match or updated["service_sid"] is None or match.group(1) != updated["service_sid"]:
                raise PolicyError("state_grant_invalid")
            if existing is not None and existing["grant"] != grant_value:
                raise PolicyError("state_grant_mismatch")
            allowed = {None: {"pending"}, "pending": {"pending", "owned"}, "owned": {"owned"}}
            if grant_status not in allowed[None if existing is None else existing["status"]]:
                raise PolicyError("state_grant_transition_invalid")
            if existing is None:
                owned["acl_grants"].append({"path": path, "grant": grant_value, "status": grant_status})
            else:
                existing["status"] = grant_status
        else:
            raise PolicyError("state_update_invalid")
    # none -> pending (intent) -> owned (proven); pending -> none (it does
    # not exist); owned -> none (removed). owned never goes back to pending
    # and none never jumps to owned.
    three_state = {"none": {"none", "pending"}, "pending": {"pending", "owned", "none"}, "owned": {"owned", "none"}}
    for key, value in (("service_dir", service_dir), ("log_dir", log_dir), ("backend_config", backend_config)):
        if value is not None:
            if value not in three_state or value not in three_state[owned[key]]:
                raise PolicyError("state_transition_invalid")
            owned[key] = value
    if backend_config == "none":
        owned["backend_config_evidence"] = {"marker": None, "fingerprint": None, "fingerprint_next": None}
    if backend_activation is not None:
        if backend_activation not in BACKEND_ACTIVATION_STATES:
            raise PolicyError("state_update_invalid")
        updated["backend_activation"] = backend_activation
    if phase is not None:
        if phase not in STATE_PHASES:
            raise PolicyError("state_update_invalid")
        updated["phase"] = phase
    if winsw_sha256 is not None:
        updated["winsw_sha256"] = winsw_sha256.upper()
    updated["updated_at_utc"] = _utc_now()
    return updated


def rollback_actions(state: dict | None) -> dict:
    """Exactly what uninstall may undo. ``pending`` logon right counts as
    owned: it is recorded only after an export proved the SID was absent and
    just before secedit adds it, so any presence of that SID afterwards
    comes from DEV-1C (revoking an absent SID is a no-op)."""
    if state is None:
        return {"delete_service": False, "service_ownership": "none", "revoke_logon_right": False, "acl_grants": [],
                "service_sid": None, "service_dir": "none", "log_dir": "none", "backend_config": "none"}
    owned = state["owned"]
    return {
        # "pending" may be deleted only after uninstall re-proves, against the
        # SCM, that the existing service matches account, binary and type
        # exactly (service verdict "compatible"); "owned" was proven at install.
        "delete_service": owned["service"] in ("pending", "owned"),
        "service_ownership": owned["service"],
        "revoke_logon_right": owned["logon_right"] in ("pending", "added"),
        # every recorded grant with its exact planned value and status; the
        # uninstall re-reads each ACL and decides per grant (acl-grant-uninstall-action)
        "acl_grants": sorted((dict(grant) for grant in owned["acl_grants"]), key=lambda grant: grant["path"].lower()),
        "service_sid": state["service_sid"],
        "service_dir": owned["service_dir"],
        "log_dir": owned["log_dir"],
        "backend_config": owned["backend_config"],
    }


def external_grant_decision(snapshot: dict, grant: dict, state: dict | None) -> str:
    """For a grant on a path DEV-1C does not own (repo, venv, Python home):
    an EXPLICIT ACE of the Broker SID already there means someone else put
    it; revoking by SID on uninstall would delete it. Allowed only if the
    ledger already records this grant as DEV-1C's (reinstall). Inherited
    ACEs come from DEV-1C's own tree grants and are ignored."""
    match = _GRANT_PATTERN.fullmatch(str(grant.get("icacls_grant") or grant.get("grant") or ""))
    if not match:
        raise PolicyError("grant_invalid")
    sid = match.group(1)
    explicit = [ace for ace in snapshot.get("aces", [])
                if str(ace.get("sid", "")).upper() == sid.upper() and not ace.get("inherited", False)]
    if not explicit:
        return "apply"
    recorded = None if state is None else next(
        (entry for entry in state["owned"]["acl_grants"] if entry["path"].lower() == str(grant["path"]).lower()), None)
    if recorded is None:
        raise PolicyError("preexisting_broker_ace")
    # Ownership alone is not enough: the ACE must still be exactly the one
    # DEV-1C applied (single Allow, same rights, same inheritance and
    # propagation). Anything else -- more rights, a Deny, another scope --
    # is drift that a reinstall must not silently accept.
    if recorded["grant"] != str(grant.get("icacls_grant") or grant.get("grant")) or not grant_matches(snapshot, grant):
        raise PolicyError("broker_ace_drifted" if recorded["status"] == "owned" else "pending_grant_ambiguous")
    # "pending" + EXACT ACE: pending is recorded only after proving that no
    # explicit Broker ACE existed and immediately before /grant:r, so the
    # exact ACE is the result of that /grant:r (crash before "owned").
    return "reapply_owned" if recorded["status"] == "owned" else "reconcile_pending_exact"


def acl_grant_uninstall_action(snapshot: dict, grant: dict) -> str:
    """Per recorded grant, from a FRESH read of the path's ACL: never a
    broad revocation by SID just because the path is in the ledger.
    - no explicit Broker ACE: nothing to revoke -> ``record_none``;
    - exactly the recorded ACE (pending or owned) -> ``revoke``;
    - anything else (more rights, a Deny, other scope, several ACEs)
      -> ``refuse_manual`` and the ACL is not touched."""
    match = _GRANT_PATTERN.fullmatch(str(grant.get("grant") or ""))
    if not match or grant.get("status") not in GRANT_STATES:
        raise PolicyError("grant_invalid")
    sid = match.group(1)
    explicit = [ace for ace in snapshot.get("aces", [])
                if str(ace.get("sid", "")).upper() == sid.upper() and not ace.get("inherited", False)]
    if not explicit:
        return "record_none"
    return "revoke" if grant_matches(snapshot, grant) else "refuse_manual"


def grant_revoked(snapshot: dict, grant: dict) -> bool:
    """After the exact revocation: no explicit ACE of the SID remains."""
    sid = _GRANT_PATTERN.fullmatch(str(grant.get("grant") or "")).group(1)
    return not [ace for ace in snapshot.get("aces", [])
                if str(ace.get("sid", "")).upper() == sid.upper() and not ace.get("inherited", False)]


# icacls scope -> (.NET InheritanceFlags, PropagationFlags):
# ContainerInherit=1, ObjectInherit=2; NoPropagateInherit=1, InheritOnly=2.
_SCOPE_FLAGS = {"(OI)(CI)": (3, 0), "(OI)(NP)": (2, 1), "": (0, 0)}
_RIGHTS_MASKS = {"RX": READ_AND_EXECUTE, "M": MODIFY}


def grant_matches(snapshot: dict, grant: dict) -> bool:
    """The explicit ACEs of the grant's SID are exactly ONE Allow ACE with
    the expected rights mask and the expected inheritance/propagation."""
    match = _GRANT_PATTERN.fullmatch(str(grant.get("icacls_grant") or grant.get("grant") or ""))
    if not match:
        raise PolicyError("grant_invalid")
    sid, scope, rights = match.group(1), match.group(2) or "", match.group(3)
    explicit = [ace for ace in snapshot.get("aces", [])
                if str(ace.get("sid", "")).upper() == sid.upper() and not ace.get("inherited", False)]
    if len(explicit) != 1:
        return False
    ace = explicit[0]
    expected_flags = _SCOPE_FLAGS[scope]
    return (
        str(ace.get("type", "")).lower() == "allow"
        and normalize_rights(ace.get("rights", 0)) == _RIGHTS_MASKS[rights]
        and (int(ace.get("inheritance_flags", -1)), int(ace.get("propagation_flags", -1))) == expected_flags
    )


def scm_guard_decision(verdict: str, lsa_sid: str | None, scm_sid: str | None, state: dict | None) -> str:
    """The ONE gate every mutation of an EXISTING MYCDeveloperBroker service
    passes through, evaluated from a fresh SCM/LSA read taken immediately
    before that mutation (stop, config, sidtype, description, failure,
    failureflag, start, delete -- also inside the installer's catch).
    Returns the verified SID or refuses:
    - the service must still match account/binary/type (``compatible``);
    - LSA and SCM must report the same virtual-account SID;
    - the ledger must record the service as ``pending`` or ``owned``;
    - a SID already in the ledger must be that SID."""
    if verdict != "compatible":
        raise PolicyError("scm_guard_service_changed")
    if not lsa_sid or not scm_sid or lsa_sid != scm_sid:
        raise PolicyError("scm_guard_sid_unverifiable")
    sid = check_service_sid(lsa_sid)
    if state is None or state["owned"]["service"] not in ("pending", "owned"):
        raise PolicyError("scm_guard_not_owned")
    if state["service_sid"] not in (None, sid):
        raise PolicyError("scm_guard_sid_mismatch")
    return sid


def directory_creation_proof(snapshot: dict, entries: list[dict], *, canonical: bool, root_is_reparse: bool) -> list[str]:
    """Proof, read back AFTER creation and protection, that a DEV-1C
    directory is exactly what this run created: canonical, not a reparse
    point, owner Administrators/SYSTEM, protected DACL with only SYSTEM and
    Administrators full control and no Deny, and EMPTY (a directory that
    someone else created or filled in the window cannot pass). Empty list
    == proven."""
    violations = []
    if not canonical:
        violations.append("path_not_canonical")
    if root_is_reparse:
        violations.append("reparse_point")
    if entries:
        violations.append("not_empty")
    violations += evaluate_acl(snapshot, "owned_dir_base")
    return violations


def owned_directory_proof(snapshot: dict, *, kind: str, service_sid: str | None,
                          canonical: bool, root_is_reparse: bool) -> list[str]:
    """Re-proof of an ``owned`` directory before uninstall deletes it: same
    identity checks, and the ACL is either the base protected ACL or the base
    plus exactly the Broker's planned ACE (content is allowed: it is ours)."""
    violations = []
    if not canonical:
        violations.append("path_not_canonical")
    if root_is_reparse:
        violations.append("reparse_point")
    base = evaluate_acl(snapshot, "owned_dir_base")
    if base and service_sid:
        policy = {"service_dir": "service_dir", "log_dir": "log_dir"}[kind]
        with_broker = evaluate_acl(snapshot, policy, service_sid=service_sid)
        violations += with_broker
    else:
        violations += base
    return violations


def directory_uninstall_action(ownership: str, exists: bool, remove_requested: bool, proof_ok: bool) -> str:
    """``pending`` never authorises deletion: absent -> record none;
    present -> keep for manual reconciliation. ``owned`` is deleted only on
    request AND after a fresh proof."""
    if ownership == "none":
        return "untouched"
    if ownership == "pending":
        return "record_none" if not exists else "keep_pending_manual"
    if not exists:
        return "record_none"
    if not remove_requested:
        return "retain"
    return "delete" if proof_ok else "refuse_unproven"


def backend_block_proven(state: dict | None, env_text: str) -> bool:
    """The managed block present in backend\\.env is EXACTLY one DEV-1C
    wrote: its marker equals the ledger's and its fingerprint equals the
    recorded fingerprint (or the one recorded just before an interrupted
    rewrite). Without persisted evidence nothing is proven."""
    if state is None or state["owned"]["backend_config"] == "none":
        return False
    evidence = state["owned"]["backend_config_evidence"]
    _before, values, _after = split_env_block(env_text)
    marker = block_marker(env_text)
    if values is None or marker is None or marker != evidence["marker"]:
        return False
    current = block_fingerprint(values, marker)
    return any(expected and hmac.compare_digest(current, expected)
               for expected in (evidence["fingerprint"], evidence["fingerprint_next"]))


def backend_config_uninstall_action(ownership: str, block_present_after_recovery: bool, proven: bool = False) -> str:
    """backend\\.env is touched only when the ledger records DEV-1C's block
    (``pending``/``owned``) AND the block present is proven DEV-1C's exact
    block (``proven``: marker + fingerprint persisted in the ledger, see
    backend_block_proven). After journal recovery an absent block means
    nothing is left to undo; a present block without proof is never
    modified (manual reconciliation)."""
    if ownership == "none":
        return "untouched"
    if not block_present_after_recovery:
        return "record_none"
    # pending or owned: only a block PROVEN to be DEV-1C's exact block may
    # be disabled/removed; anything else is left for manual reconciliation.
    return "disable_or_remove" if proven else "refuse_manual"


def owns_nothing(state: dict) -> bool:
    """True only when no resource AND no retained artifact is owned: the
    ledger may then be deleted without orphaning DEV-1C directories."""
    actions = rollback_actions(state)
    return not (actions["delete_service"] or actions["revoke_logon_right"] or actions["acl_grants"]
                or actions["service_dir"] != "none" or actions["log_dir"] != "none"
                or actions["backend_config"] != "none")


def owns_only_retained_artifacts(state: dict) -> bool:
    """Service, logon right and ACEs are gone; only retained artifacts remain
    (owned directories, a pending directory awaiting manual reconciliation,
    or the disabled managed block of backend\\.env kept without
    -RemoveBackendConfig): the ledger stays as a tombstone."""
    actions = rollback_actions(state)
    return (not (actions["delete_service"] or actions["revoke_logon_right"] or actions["acl_grants"])
            and (actions["service_dir"] != "none" or actions["log_dir"] != "none"
                 or actions["backend_config"] != "none"))


# --- commands ----------------------------------------------------------------------------

def command_provision(args: argparse.Namespace) -> dict:
    """Journaled XML + backend\\.env provisioning with block ownership:
    - a managed block present before writing must be PROVEN DEV-1C's
      (marker + fingerprint); otherwise nothing is written;
    - the evidence for the NEW block (marker + fingerprint) is persisted in
      the ledger BEFORE the commit (none -> pending; owned keeps owned and
      records ``fingerprint_next``), so a crash after writing but before
      "owned" still leaves verifiable proof;
    - after the commit the block is re-read and must match the evidence
      before the ledger says ``owned``."""
    xml_path, env_path, journal_dir = Path(args.xml_out), Path(args.env_file), Path(args.journal_dir)
    state_path = Path(args.state_file)
    if not env_path.is_file():
        raise PolicyError("env_file_missing")
    if not journal_dir.is_dir():
        raise PolicyError("journal_dir_missing")
    state = load_state(state_path, args.repo_root)
    if state is None:
        raise PolicyError("state_missing")
    recovery = recover_provision(journal_dir, xml_path, env_path)
    # Everything is validated and rendered before anything is written.
    current_text = _read_text(env_path)
    _before, existing_block, _after = split_env_block(current_text)  # refuse unmanaged keys
    ownership = state["owned"]["backend_config"]
    if existing_block is not None:
        if not backend_block_proven(state, current_text):
            raise PolicyError("managed_block_drifted" if ownership == "owned" else "managed_block_not_owned")
        # Proven: the evidence is normalized to the block really present (a
        # crash after a committed write leaves pending, or owned with
        # fingerprint_next); pending is promoted by this proof.
        present = block_fingerprint(existing_block, block_marker(current_text))
        state = apply_state_update(state, backend_config="owned")
        evidence = state["owned"]["backend_config_evidence"]
        evidence["fingerprint"], evidence["fingerprint_next"] = present, None
        save_state(state_path, state, args.repo_root)
        ownership = "owned"
    secret = _obtain_secret(args.secret_mode, xml_path, env_path)
    environment = broker_environment(args.pipe_name, secret, args.client_sid, args.service_sid)
    xml_text = render_service_xml(
        Path(args.template).read_text(encoding="utf-8"),
        python_exe=args.python_exe,
        working_dir=args.working_dir,
        log_dir=args.log_dir,
        environment=environment,
    )
    values = backend_values(args.pipe_name, secret, args.client_sid, args.service_sid, enabled=False)
    evidence = state["owned"]["backend_config_evidence"]
    marker = evidence["marker"] if ownership == "owned" else new_marker()
    env_text = render_env_file(current_text, values, marker)
    fingerprint = block_fingerprint(values, marker)
    # evidence BEFORE the commit
    if ownership == "owned":
        evidence["fingerprint_next"] = fingerprint
    else:
        state = apply_state_update(state, backend_config="pending")
        state["owned"]["backend_config_evidence"] = {"marker": marker, "fingerprint": fingerprint, "fingerprint_next": None}
    save_state(state_path, state, args.repo_root)
    provision_files(journal_dir, xml_path, env_path, xml_text, env_text)
    # re-read and prove, then promote
    written = _read_text(env_path)
    _before, written_block, _after = split_env_block(written)
    if written_block is None or block_marker(written) != marker or not hmac.compare_digest(block_fingerprint(written_block, marker), fingerprint):
        raise PolicyError("managed_block_not_as_written")
    state = apply_state_update(state, backend_config="owned")
    state["owned"]["backend_config_evidence"] = {"marker": marker, "fingerprint": fingerprint, "fingerprint_next": None}
    save_state(state_path, state, args.repo_root)
    return {"status": "provisioned", "secret_source": args.secret_mode, "backend_enabled": False,
            "recovered": recovery, "backend_config": "owned"}


def command_provision_recover(args: argparse.Namespace) -> dict:
    journal_dir = Path(args.journal_dir)
    if not journal_dir.is_dir():
        return {"recovered": "none"}
    return {"recovered": recover_provision(journal_dir, Path(args.xml), Path(args.env_file))}


def _state_path(args: argparse.Namespace) -> Path:
    return Path(args.file)


def _state_result(state: dict | None) -> dict:
    return {"exists": state is not None, "state": state, "rollback": rollback_actions(state),
            "owns_nothing": state is None or owns_nothing(state)}


def command_state_show(args: argparse.Namespace) -> dict:
    return _state_result(load_state(_state_path(args), args.repo_root))


def command_state_begin(args: argparse.Namespace) -> dict:
    path = _state_path(args)
    state = load_state(path, args.repo_root)
    state = new_state(args.repo_root) if state is None else apply_state_update(state, phase="installing")
    save_state(path, state, args.repo_root)
    return _state_result(state)


def command_state_update(args: argparse.Namespace) -> dict:
    path = _state_path(args)
    state = load_state(path, args.repo_root)
    if state is None:
        raise PolicyError("state_missing")
    state = apply_state_update(
        state,
        backend_config=args.backend_config,
        service_dir=args.service_dir,
        log_dir=args.log_dir,
        backend_activation=args.backend_activation,
        service_sid=args.service_sid,
        service=args.service,
        logon_right=args.logon_right,
        grant_path=args.grant_path,
        grant_value=args.grant_value,
        grant_status=args.grant_status,
        phase=args.phase,
        winsw_sha256=args.winsw_sha256,
    )
    save_state(path, state, args.repo_root)
    return _state_result(state)


def command_state_delete(args: argparse.Namespace) -> dict:
    path = _state_path(args)
    state = load_state(path, args.repo_root)
    if state is None:
        return {"deleted": False, "retained": False}
    if not owns_nothing(state):
        if owns_only_retained_artifacts(state):
            # tombstone: keep the ledger while owned directories are retained
            save_state(path, apply_state_update(state, phase="uninstalled"), args.repo_root)
            return {"deleted": False, "retained": True}
        raise PolicyError("state_still_owns_resources")
    path.unlink()
    return {"deleted": True, "retained": False}


def command_restore_plan(args: argparse.Namespace) -> dict:
    try:
        records = json.loads(Path(args.backup).read_bytes().decode("utf-8-sig"))
    except (OSError, ValueError):
        raise PolicyError("backup_invalid") from None
    plan = restore_plan(records, args.services_root, args.exclude)
    return {"entries": plan, "count": len(plan)}


def command_scm_guard(args: argparse.Namespace) -> dict:
    state = load_state(Path(args.file), args.repo_root)
    return {"sid": scm_guard_decision(args.verdict, args.lsa_sid or None, args.scm_sid or None, state)}


def command_directory_proof(args: argparse.Namespace) -> dict:
    data = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    if args.mode == "creation":
        violations = directory_creation_proof(data["snapshot"], data.get("entries", []),
                                              canonical=bool(data["canonical"]), root_is_reparse=bool(data["is_reparse"]))
    else:
        violations = owned_directory_proof(data["snapshot"], kind=args.kind, service_sid=args.service_sid,
                                           canonical=bool(data["canonical"]), root_is_reparse=bool(data["is_reparse"]))
    return {"proven": not violations, "violations": violations}


def command_directory_uninstall_action(args: argparse.Namespace) -> dict:
    return {"action": directory_uninstall_action(args.ownership, args.exists == "true",
                                                 args.remove == "true", args.proof_ok == "true")}


def command_backend_config_action(args: argparse.Namespace) -> dict:
    state = load_state(Path(args.file), args.repo_root)
    ownership = "none" if state is None else state["owned"]["backend_config"]
    text = _read_text(Path(args.env_file))
    _before, block, _after = split_env_block(text)
    proven = backend_block_proven(state, text)
    return {"action": backend_config_uninstall_action(ownership, block is not None, proven),
            "ownership": ownership, "proven": proven}


def command_remove_owned_tree(args: argparse.Namespace) -> dict:
    plan = directory_plan(args.deployment_root, args.services_root, args.logs_root)
    if not is_owned_directory(args.path, plan):
        raise PolicyError("path_not_owned")
    root = Path(args.path)
    if not root.exists() and not os.path.islink(root):
        return {"removed": 0}
    return {"removed": remove_owned_tree(root)}


def command_service_install_decision(args: argparse.Namespace) -> dict:
    return {"action": service_install_decision(args.verdict, load_state(Path(args.file), args.repo_root))}


def command_winsw_integrity(args: argparse.Namespace) -> dict:
    violations = winsw_integrity(args.actual_sha256, args.expected_sha256,
                                 args.config_actual_sha256, args.config_expected_sha256)
    if violations:
        raise PolicyError(violations[0])
    return {"verified": True, "config_verified": bool(args.config_actual_sha256)}


def command_acl_grant_uninstall_action(args: argparse.Namespace) -> dict:
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8-sig"))
    grant = {"path": args.path, "grant": args.grant, "status": args.status}
    if args.after_revoke:
        if not grant_revoked(snapshot, grant):
            raise PolicyError("broker_ace_still_present")
        return {"action": "revoked"}
    return {"action": acl_grant_uninstall_action(snapshot, grant)}


def command_external_grant_verify(args: argparse.Namespace) -> dict:
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8-sig"))
    if not grant_matches(snapshot, {"path": args.path, "grant": args.grant}):
        raise PolicyError("broker_ace_not_normalized")
    return {"matches": True}


def command_service_create_outcome(args: argparse.Namespace) -> dict:
    return service_create_outcome(int(args.exit_code), args.verdict)


def command_external_grant_check(args: argparse.Namespace) -> dict:
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8-sig"))
    grant = {"path": args.path, "grant": args.grant}
    state = load_state(Path(args.file), args.repo_root)
    return {"decision": external_grant_decision(snapshot, grant, state)}


def command_directory_plan(args: argparse.Namespace) -> dict:
    return directory_plan(args.deployment_root, args.services_root, args.logs_root)


def command_set_backend_enabled(args: argparse.Namespace) -> dict:
    env_path = Path(args.env_file)
    text = _read_text(env_path)
    _before, values, _after = split_env_block(text)
    if values is None:
        if args.enabled == "false":
            return {"status": "no_managed_block"}
        raise PolicyError("env_block_missing")
    values = {**values, "DEVELOPER_BROKER_ENABLED": args.enabled}
    _rewrite_in_place(env_path, render_env_file(text, values, block_marker(text)).encode("utf-8"))
    return {"status": "updated", "backend_enabled": args.enabled == "true"}


def command_remove_backend_block(args: argparse.Namespace) -> dict:
    env_path = Path(args.env_file)
    text = _read_text(env_path)
    _before, values, _after = split_env_block(text)
    if values is None:
        return {"status": "no_managed_block"}
    _rewrite_in_place(env_path, render_env_file(text, None).encode("utf-8"))
    return {"status": "removed"}


def command_verify(args: argparse.Namespace) -> dict:
    """Both sides configured consistently. Reports booleans only."""
    checks: dict[str, bool] = {}
    try:
        xml_text = _read_text(Path(args.xml))
        root = ElementTree.fromstring(xml_text)
        broker_env = xml_environment(xml_text)
    except (OSError, ElementTree.ParseError):
        raise PolicyError("service_xml_unreadable") from None
    _before, backend, _after = split_env_block(_read_text(Path(args.env_file)))
    backend = backend or {}
    checks["xml_id"] = root.findtext("id") == SERVICE_ID
    checks["xml_has_no_serviceaccount"] = root.find("serviceaccount") is None
    checks["xml_executable"] = (root.findtext("executable") or "").lower() == args.python_exe.lower()
    checks["xml_working_directory"] = (root.findtext("workingdirectory") or "").lower() == args.working_dir.lower()
    checks["broker_keys_exact"] = tuple(broker_env) == tuple(BROKER_ENVIRONMENT_KEYS)
    checks["backend_keys_exact"] = set(backend) == set(BACKEND_ENVIRONMENT_KEYS)
    for side, values in (("broker", broker_env), ("backend", backend)):
        checks[f"{side}_pipe_name"] = values.get("DEVELOPER_BROKER_PIPE_NAME") == args.pipe_name
        checks[f"{side}_client_sid"] = values.get("DEVELOPER_BROKER_CLIENT_SID") == args.client_sid == EXPECTED_CLIENT_SID
        checks[f"{side}_service_sid"] = values.get("DEVELOPER_BROKER_SERVICE_SID") == args.service_sid
    broker_secret = (broker_env.get("DEVELOPER_BROKER_SECRET") or "").encode("utf-8")
    backend_secret = (backend.get("DEVELOPER_BROKER_SECRET") or "").encode("utf-8")
    checks["secret_valid"] = bool(SECRET_PATTERN.fullmatch(broker_secret.decode("utf-8")))
    checks["secret_matches"] = bool(broker_secret) and hmac.compare_digest(broker_secret, backend_secret)
    checks["backend_transport"] = backend.get("DEVELOPER_BROKER_TRANSPORT") == "named_pipe"
    ok = all(checks.values())
    return {"ok": ok, "checks": checks, "backend_enabled": backend.get("DEVELOPER_BROKER_ENABLED") == "true"}


def _file_contains(path: Path, needles: list[bytes]) -> bool:
    overlap = max(len(needle) for needle in needles) - 1
    tail = b""
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(_SCAN_CHUNK_BYTES)
            if not chunk:
                return False
            window = tail + chunk
            if any(needle in window for needle in needles):
                return True
            tail = window[-overlap:] if overlap > 0 else b""


def command_scan_for_secret(args: argparse.Namespace) -> dict:
    try:
        secret = xml_environment(_read_text(Path(args.xml))).get("DEVELOPER_BROKER_SECRET") or ""
    except (OSError, ElementTree.ParseError):
        raise PolicyError("service_xml_unreadable") from None
    if not secret:
        raise PolicyError("secret_missing")
    needles = [secret.encode("utf-8"), secret.encode("utf-16-le")]
    found, scanned, skipped = False, 0, 0
    for path in sorted(Path(args.dir).rglob("*")):
        if not path.is_file():
            continue
        if path.stat().st_size > MAX_SCANNED_FILE_BYTES:
            skipped += 1
            continue
        scanned += 1
        if _file_contains(path, needles):
            found = True
    return {"secret_found": found, "files_scanned": scanned, "files_skipped": skipped}


def command_logon_right(args: argparse.Namespace) -> dict:
    status, inf = logon_right_change(_read_inf(Path(args.export)), args.sid, args.action)
    if inf is not None:
        Path(args.out).write_text(inf, encoding="utf-16")
    return {"status": status, "inf_written": inf is not None}


def command_acl_plan(args: argparse.Namespace) -> dict:
    return {"grants": acl_plan(args.repo_root, args.python_home, args.service_dir, args.log_dir, args.service_sid)}


def command_evaluate_acl(args: argparse.Namespace) -> dict:
    """Input: one snapshot, or a list of snapshots each carrying ``path``."""
    loaded = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    snapshots = loaded if isinstance(loaded, list) else [loaded]
    violations = []
    for snapshot in snapshots:
        for violation in evaluate_acl(
            snapshot, args.policy, service_sid=args.service_sid, allow_users_read=args.allow_users_read
        ):
            violations.append(f"{snapshot.get('path', '')}: {violation}" if isinstance(loaded, list) else violation)
    return {"compliant": not violations, "violations": violations}


def command_inspect_env(args: argparse.Namespace) -> dict:
    """Read-only preflight of backend/.env: refuses unmanaged
    DEVELOPER_BROKER_* keys; never reports values."""
    env_path = Path(args.env_file)
    if not env_path.is_file():
        raise PolicyError("env_file_missing")
    _before, values, _after = split_env_block(_read_text(env_path))
    return {
        "managed_block": values is not None,
        "backend_enabled": (values or {}).get("DEVELOPER_BROKER_ENABLED") == "true",
        "secret_present": bool((values or {}).get("DEVELOPER_BROKER_SECRET")),
    }


def command_service_verdict(args: argparse.Namespace) -> dict:
    info = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    return service_verdict(info, args.expected_binary)


def command_validate(args: argparse.Namespace) -> dict:
    check_pipe_name(args.pipe_name)
    return {"pipe_name_valid": True, "broker_environment_keys": list(BROKER_ENVIRONMENT_KEYS)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="broker_deploy.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("provision")
    for name in ("--template", "--xml-out", "--env-file", "--pipe-name", "--client-sid",
                 "--service-sid", "--python-exe", "--working-dir", "--log-dir"):
        p.add_argument(name, required=True)
    p.add_argument("--journal-dir", required=True)
    p.add_argument("--state-file", required=True)
    p.add_argument("--repo-root", required=True)
    p.add_argument("--secret-mode", required=True, choices=("generate", "stdin", "reuse"))
    p.set_defaults(handler=command_provision)

    p = sub.add_parser("provision-recover")
    for name in ("--journal-dir", "--xml", "--env-file"):
        p.add_argument(name, required=True)
    p.set_defaults(handler=command_provision_recover)

    for name, handler in (("state-show", command_state_show), ("state-begin", command_state_begin),
                          ("state-delete", command_state_delete)):
        p = sub.add_parser(name)
        p.add_argument("--file", required=True)
        p.add_argument("--repo-root", required=True)
        p.set_defaults(handler=handler)

    p = sub.add_parser("state-update")
    p.add_argument("--file", required=True)
    p.add_argument("--repo-root", required=True)
    p.add_argument("--service-sid")
    p.add_argument("--service", choices=SERVICE_STATES)
    p.add_argument("--service-dir", choices=DIRECTORY_STATES)
    p.add_argument("--log-dir", choices=DIRECTORY_STATES)
    p.add_argument("--backend-config", choices=BACKEND_CONFIG_STATES)
    p.add_argument("--backend-activation", choices=BACKEND_ACTIVATION_STATES)
    p.add_argument("--logon-right", choices=LOGON_RIGHT_STATES)
    p.add_argument("--grant-path")
    p.add_argument("--grant-value")
    p.add_argument("--grant-status", choices=("pending", "owned", "remove"))
    p.add_argument("--phase", choices=STATE_PHASES)
    p.add_argument("--winsw-sha256")
    p.set_defaults(handler=command_state_update)

    p = sub.add_parser("restore-plan")
    for name in ("--backup", "--services-root", "--exclude"):
        p.add_argument(name, required=True)
    p.set_defaults(handler=command_restore_plan)

    p = sub.add_parser("scm-guard")
    for name in ("--verdict", "--file", "--repo-root"):
        p.add_argument(name, required=True)
    p.add_argument("--lsa-sid", default="")
    p.add_argument("--scm-sid", default="")
    p.set_defaults(handler=command_scm_guard)

    p = sub.add_parser("directory-proof")
    p.add_argument("--input", required=True)
    p.add_argument("--mode", required=True, choices=("creation", "owned"))
    p.add_argument("--kind", choices=("service_dir", "log_dir"), default="service_dir")
    p.add_argument("--service-sid")
    p.set_defaults(handler=command_directory_proof)

    p = sub.add_parser("directory-uninstall-action")
    p.add_argument("--ownership", required=True, choices=DIRECTORY_STATES)
    for name in ("--exists", "--remove", "--proof-ok"):
        p.add_argument(name, required=True, choices=("true", "false"))
    p.set_defaults(handler=command_directory_uninstall_action)

    p = sub.add_parser("backend-config-action")
    for name in ("--file", "--repo-root", "--env-file"):
        p.add_argument(name, required=True)
    p.set_defaults(handler=command_backend_config_action)

    p = sub.add_parser("remove-owned-tree")
    for name in ("--path", "--deployment-root", "--services-root", "--logs-root"):
        p.add_argument(name, required=True)
    p.set_defaults(handler=command_remove_owned_tree)

    p = sub.add_parser("service-install-decision")
    for name in ("--verdict", "--file", "--repo-root"):
        p.add_argument(name, required=True)
    p.set_defaults(handler=command_service_install_decision)

    p = sub.add_parser("winsw-integrity")
    p.add_argument("--actual-sha256", required=True)
    p.add_argument("--expected-sha256")
    p.add_argument("--config-actual-sha256")
    p.add_argument("--config-expected-sha256")
    p.set_defaults(handler=command_winsw_integrity)

    p = sub.add_parser("acl-grant-uninstall-action")
    for name in ("--snapshot", "--path", "--grant"):
        p.add_argument(name, required=True)
    p.add_argument("--status", required=True, choices=GRANT_STATES)
    p.add_argument("--after-revoke", action="store_true")
    p.set_defaults(handler=command_acl_grant_uninstall_action)

    p = sub.add_parser("external-grant-verify")
    for name in ("--snapshot", "--path", "--grant"):
        p.add_argument(name, required=True)
    p.set_defaults(handler=command_external_grant_verify)

    p = sub.add_parser("service-create-outcome")
    p.add_argument("--exit-code", required=True)
    p.add_argument("--verdict", required=True)
    p.set_defaults(handler=command_service_create_outcome)

    p = sub.add_parser("external-grant-check")
    for name in ("--snapshot", "--path", "--grant", "--file", "--repo-root"):
        p.add_argument(name, required=True)
    p.set_defaults(handler=command_external_grant_check)

    p = sub.add_parser("directory-plan")
    for name in ("--deployment-root", "--services-root", "--logs-root"):
        p.add_argument(name, required=True)
    p.set_defaults(handler=command_directory_plan)

    p = sub.add_parser("set-backend-enabled")
    p.add_argument("--env-file", required=True)
    p.add_argument("--enabled", required=True, choices=("true", "false"))
    p.set_defaults(handler=command_set_backend_enabled)

    p = sub.add_parser("remove-backend-block")
    p.add_argument("--env-file", required=True)
    p.set_defaults(handler=command_remove_backend_block)

    p = sub.add_parser("verify")
    for name in ("--xml", "--env-file", "--pipe-name", "--client-sid", "--service-sid", "--python-exe", "--working-dir"):
        p.add_argument(name, required=True)
    p.set_defaults(handler=command_verify)

    p = sub.add_parser("scan-for-secret")
    p.add_argument("--xml", required=True)
    p.add_argument("--dir", required=True)
    p.set_defaults(handler=command_scan_for_secret)

    p = sub.add_parser("logon-right")
    p.add_argument("--export", required=True)
    p.add_argument("--sid", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--action", required=True, choices=("grant", "revoke"))
    p.set_defaults(handler=command_logon_right)

    p = sub.add_parser("acl-plan")
    for name in ("--repo-root", "--python-home", "--service-dir", "--log-dir", "--service-sid"):
        p.add_argument(name, required=True)
    p.set_defaults(handler=command_acl_plan)

    p = sub.add_parser("evaluate-acl")
    p.add_argument("--input", required=True)
    p.add_argument("--policy", required=True, choices=ACL_POLICIES)
    p.add_argument("--service-sid")
    p.add_argument("--allow-users-read", action="store_true")
    p.set_defaults(handler=command_evaluate_acl)

    p = sub.add_parser("inspect-env")
    p.add_argument("--env-file", required=True)
    p.set_defaults(handler=command_inspect_env)

    p = sub.add_parser("service-verdict")
    p.add_argument("--input", required=True)
    p.add_argument("--expected-binary", required=True)
    p.set_defaults(handler=command_service_verdict)

    p = sub.add_parser("validate")
    p.add_argument("--pipe-name", required=True)
    p.set_defaults(handler=command_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = args.handler(args)
    except PolicyError as exc:
        print(json.dumps({"error": exc.code}))
        return 3
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
