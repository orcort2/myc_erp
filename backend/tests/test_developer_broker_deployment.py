"""DEV-1C: MYCDeveloperBroker Windows service deployment assets.

Cross-platform. Exercises every policy decision of
``deploy/windows/developer-broker/broker_deploy.py`` (ACL plan and ACL
policy, service compatibility, SeServiceLogonRight INF merge, WinSW XML
rendering, managed backend/.env block, secret handling) and statically
checks the PowerShell scripts. It does NOT install a Windows service,
touch ACLs, SCM or secedit: that validation is pending on the real server.
"""

import ast
import importlib.util
import io
import json
import os
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

import pytest

from app.core.config import Settings
from app.developer_broker import host, pipe_name
from app.developer_broker.protocol import OP_BROKER_HEALTH, BrokerSecret
from app.developer_broker.server import BrokerServer


BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
DEPLOY = REPO / "deploy" / "windows" / "developer-broker"
TOOL_PATH = DEPLOY / "broker_deploy.py"
TEMPLATE = DEPLOY / "MYCDeveloperBroker.xml.template"
INSTALL = DEPLOY / "Install-MYCDeveloperBroker.ps1"
UNINSTALL = DEPLOY / "Uninstall-MYCDeveloperBroker.ps1"
VALIDATE = DEPLOY / "Test-MYCDeveloperBroker.ps1"
HARDEN = DEPLOY / "Set-MYCServicesAcl.ps1"
MODULE = DEPLOY / "MYCDeveloperBroker.psm1"
RESTORE = DEPLOY / "Restore-MYCServicesAcl.ps1"
POWERSHELL_FILES = (INSTALL, UNINSTALL, VALIDATE, HARDEN, RESTORE, MODULE)

REPO_ROOT = r"C:\Users\SMM ADMIN\myc_erp"
PYTHON_EXE = REPO_ROOT + r"\venv\Scripts\python.exe"
WORKING_DIR = REPO_ROOT + r"\backend"
SERVICE_DIR = r"C:\MYC\Services\developer-broker"
LOG_DIR = r"C:\MYC\Logs\developer-broker"
# Placeholder with the SHAPE of a virtual account SID (test data only; the
# installer resolves the real one on the host).
SERVICE_SID = "S-1-5-80-1111111111-2222222222-3333333333-4444444444-555555555"
CLIENT_SID = "S-1-5-18"
TRUSTED_INSTALLER = "S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464"


def _load_tool():
    spec = importlib.util.spec_from_file_location("broker_deploy_under_test", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bd = _load_tool()


def _ps(path: Path) -> str:
    return path.read_bytes().decode("utf-8-sig")


def _ps_code(path: Path) -> str:
    """PowerShell source without comment-based help and comment lines."""
    text = re.sub(r"<#.*?#>", "", _ps(path), flags=re.DOTALL)
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def _run(argv, capsys, stdin_text=None, monkeypatch=None):
    if stdin_text is not None:
        monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_text))
    code = bd.main(argv)
    out = capsys.readouterr().out
    return code, out, json.loads(out.strip().splitlines()[-1])


def _render(secret="A" * 64, **overrides):
    environment = bd.broker_environment("MYCDeveloperBroker", secret, CLIENT_SID, SERVICE_SID)
    kwargs = {"python_exe": PYTHON_EXE, "working_dir": WORKING_DIR, "log_dir": LOG_DIR, "environment": environment}
    kwargs.update(overrides)
    return bd.render_service_xml(TEMPLATE.read_text(encoding="utf-8"), **kwargs)


# --- identity / service layout ------------------------------------------------------

def test_service_id_name_account_and_paths():
    assert bd.SERVICE_ID == "MYCDeveloperBroker"
    assert bd.SERVICE_ACCOUNT == "NT SERVICE\\MYCDeveloperBroker"
    assert bd.WRAPPER_NAME == "MYCDeveloperBroker.exe" and bd.CONFIG_NAME == "MYCDeveloperBroker.xml"
    root = ElementTree.fromstring(_render())
    assert root.findtext("id") == "MYCDeveloperBroker"
    assert root.findtext("name") == "MYC Developer Broker"
    assert root.findtext("executable") == PYTHON_EXE
    assert root.findtext("workingdirectory") == WORKING_DIR
    assert root.findtext("logpath") == LOG_DIR


def test_rendered_service_is_automatic_restarting_bounded_and_never_daemonizes():
    root = ElementTree.fromstring(_render())
    assert root.findtext("startmode") == "Automatic"
    assert root.findtext("autoRefresh") == "false"
    assert root.findtext("arguments") == "-B -s -m app.developer_broker.host"
    assert [node.get("action") for node in root.findall("onfailure")] == ["restart"] * 3
    assert root.findtext("resetfailure") == "1 hour"
    stop = re.fullmatch(r"(\d+) sec", root.findtext("stoptimeout"))
    assert stop and 0 < int(stop.group(1)) <= 30
    assert root.find("log").get("mode") == "roll-by-size"
    assert "--daemon" not in _render() and "pythonw" not in _render().lower()


def test_service_identity_is_never_declared_in_xml_and_scm_registration_is_the_virtual_account():
    root = ElementTree.fromstring(_render())
    assert root.find("serviceaccount") is None
    install = _ps(INSTALL)
    create = re.search(r"'create', \$ServiceId, 'binPath=', \$layout\.Wrapper, 'start=', 'demand', 'obj=', \$ServiceAccount", install)
    assert create, "the service must be created directly under the virtual account, on demand start"
    assert "$script:ServiceAccount = 'NT SERVICE\\MYCDeveloperBroker'" in _ps(MODULE)
    for text in (install, _ps(MODULE), _ps(UNINSTALL)):
        assert not re.search(r"obj=',\s*'(LocalSystem|NT AUTHORITY)", text, re.IGNORECASE)
        assert "LocalService" not in text and "NetworkService" not in text
        assert "SMM ADMIN\\\\" not in text.replace("C:\\Users\\SMM ADMIN\\myc_erp", "")
        assert "Add-LocalGroupMember" not in text and "net localgroup" not in text.lower()


@pytest.mark.parametrize("sid", [
    "S-1-5-18", "S-1-5-19", "S-1-5-20", "S-1-5-80-0", TRUSTED_INSTALLER, "S-1-5-32-544",
    "S-1-5-21-1-2-3-1001", "S-1-5-80-1-2-3", "", "NT SERVICE\\MYCDeveloperBroker",
])
def test_broker_identity_is_never_a_shared_broad_or_non_virtual_sid(sid):
    with pytest.raises(bd.PolicyError):
        bd.check_service_sid(sid)


def test_client_sid_is_exactly_localsystem_and_distinct():
    assert bd.check_client_sid("S-1-5-18") == "S-1-5-18"
    for other in ("S-1-5-19", "S-1-5-80-1-2-3-4-5", ""):
        with pytest.raises(bd.PolicyError):
            bd.check_client_sid(other)
    with pytest.raises(bd.PolicyError):
        bd.broker_environment("MYCDeveloperBroker", "A" * 64, SERVICE_SID, SERVICE_SID)


def test_service_sid_is_resolved_on_the_host_never_hard_coded():
    module = _ps(MODULE)
    assert "Translate([Security.Principal.SecurityIdentifier])" in module
    assert "'showsid'" in module and "$viaScm -ne $viaLsa" in module
    virtual_sid = re.compile(r"S-1-5-80-\d+-\d+-\d+-\d+-\d+")
    for path in DEPLOY.iterdir():
        if path.is_file():
            found = set(virtual_sid.findall(path.read_bytes().decode("utf-8-sig")))
            assert found <= {TRUSTED_INSTALLER}, (path.name, found)
    assert '"DEVELOPER_BROKER_SERVICE_SID": check_service_sid(service_sid)' in TOOL_PATH.read_text(encoding="utf-8")


# --- environment names --------------------------------------------------------------

def test_broker_environment_is_exactly_what_the_host_reads():
    root = ElementTree.fromstring(_render())
    assert tuple(node.get("name") for node in root.findall("env")) == host.ENVIRONMENT_KEYS
    assert bd.BROKER_ENVIRONMENT_KEYS is host.ENVIRONMENT_KEYS
    values = {node.get("name"): node.get("value") for node in root.findall("env")}
    assert values["DEVELOPER_BROKER_CLIENT_SID"] == "S-1-5-18"
    assert values["DEVELOPER_BROKER_SERVICE_SID"] == SERVICE_SID
    assert values["DEVELOPER_BROKER_IO_TIMEOUT_SECONDS"] == "5"
    assert values["DEVELOPER_BROKER_MAX_CONNECTIONS"] == "4"
    config = host.BrokerHostConfig.from_environ(values)  # the Broker accepts what is rendered
    assert config.client_sid == "S-1-5-18" and config.max_connections == 4


def test_backend_block_keys_are_exactly_the_settings_fields():
    fields = {name.upper() for name in Settings.model_fields if name.startswith("developer_broker_")}
    assert set(bd.BACKEND_ENVIRONMENT_KEYS) == fields
    values = bd.backend_values("MYCDeveloperBroker", "A" * 64, CLIENT_SID, SERVICE_SID, enabled=True)
    settings = Settings(_env_file=None, **{key.lower(): value for key, value in values.items()})
    assert settings.developer_broker_enabled is True
    assert settings.developer_broker_transport == "named_pipe"
    assert settings.developer_broker_client_sid == "S-1-5-18"
    assert settings.developer_broker_timeout_seconds == 5


def test_pipe_name_validation_is_the_brokers_own():
    assert bd.validate_pipe_name is pipe_name.validate_pipe_name
    assert bd.check_pipe_name("MYCDeveloperBroker") == "MYCDeveloperBroker"
    for bad in ("", "..\\x", "\\\\.\\pipe\\X", "CON", "a b", "my:pipe"):
        with pytest.raises(bd.PolicyError):
            bd.check_pipe_name(bad)


# --- secrets -----------------------------------------------------------------------------

def test_generated_secret_is_strong_unique_and_safe_for_xml_env_and_winsw():
    first, second = bd.generate_secret(), bd.generate_secret()
    assert first != second and len(first) == 64
    assert bd.check_secret(first) == first
    BrokerSecret.from_text(first)


@pytest.mark.parametrize("secret", ["short", "A" * 42, "A" * 60 + "%X%", "A" * 60 + '"<&>', "A" * 60 + " x", "A" * 60 + "#x", "A" * 513])
def test_unsafe_or_short_secrets_are_refused(secret):
    with pytest.raises(bd.PolicyError) as error:
        bd.check_secret(secret)
    assert secret not in str(error.value)


def test_template_and_tracked_deployment_files_hold_no_secret():
    template = TEMPLATE.read_text(encoding="utf-8")
    assert '<env name="DEVELOPER_BROKER_SECRET" value="{{SECRET}}"/>' in template
    assignment = re.compile(r"DEVELOPER_BROKER_SECRET\s*[=:]\s*['\"]?([A-Za-z0-9_\-]{20,})")
    for path in [*DEPLOY.iterdir(), BACKEND / ".env.example", REPO / "docs/architecture/MOBILE_DEVELOPER_BROKER.md"]:
        if path.is_file():
            assert not assignment.search(path.read_bytes().decode("utf-8-sig")), path.name


def test_rendered_xml_is_never_committed():
    ignored = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "deploy/windows/**/*.xml" in ignored
    assert not list(DEPLOY.glob("*.xml"))


def test_secret_is_never_a_command_line_argument_or_echoed():
    parser = bd.build_parser()
    for action in parser._subparsers._group_actions[0].choices.values():
        assert not any("secret" in option and option != "--secret-mode" for arg in action._actions for option in arg.option_strings)
    for path in POWERSHELL_FILES:
        text = _ps(path)
        assert not re.search(r"\[string\]\$\w*Secret\b", text), path.name  # only SecretSource (a mode) exists
        assert "-AsPlainText" not in text
        assert not re.search(r"Write-(Host|Output|Verbose|Warning|Information)[^\n]*\$(plain|secret|secureSecret|first|second)\b", text, re.IGNORECASE)
        assert "Start-Transcript" not in text
        assert not re.search(r"Invoke-MYCNative[^\n]*(secret|Secret)", text)
    assert "[ValidateSet('Generate', 'Prompt', 'Reuse')][string]$SecretSource" in _ps(INSTALL)
    assert "Read-Host -AsSecureString" in _ps(INSTALL)


def test_tool_output_and_errors_never_contain_the_secret(tmp_path, capsys, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("DATABASE_URL=postgresql://x\n", encoding="utf-8")
    xml = tmp_path / "MYCDeveloperBroker.xml"
    secret = "S3cr3t-" + "q" * 60
    code, out, _ = _run(_provision_args(tmp_path, "stdin"), capsys, secret + "\r\n", monkeypatch)
    assert code == 0 and secret not in out
    for argv in (
        ["verify", "--xml", str(xml), "--env-file", str(env_file), "--pipe-name", "MYCDeveloperBroker", "--client-sid", CLIENT_SID,
         "--service-sid", SERVICE_SID, "--python-exe", PYTHON_EXE, "--working-dir", WORKING_DIR],
        ["inspect-env", "--env-file", str(env_file)],
        ["scan-for-secret", "--xml", str(xml), "--dir", str(tmp_path)],
    ):
        _code, out, _ = _run(argv, capsys)
        assert secret not in out


# --- provisioning ------------------------------------------------------------------------

def _journal_dir(tmp_path):
    journal = tmp_path / "state"
    journal.mkdir(exist_ok=True)
    return journal


def _ensure_ledger(tmp_path):
    ledger = tmp_path / "state" / "install-state.json"
    if not ledger.exists():
        bd.save_state(ledger, bd.new_state(REPO_ROOT), REPO_ROOT)
    return ledger


def _provision_args(tmp_path, mode):
    _journal_dir(tmp_path)
    ledger = _ensure_ledger(tmp_path)
    return [
        "provision", "--template", str(TEMPLATE), "--xml-out", str(tmp_path / "MYCDeveloperBroker.xml"),
        "--env-file", str(tmp_path / ".env"), "--pipe-name", "MYCDeveloperBroker", "--client-sid", CLIENT_SID,
        "--service-sid", SERVICE_SID, "--python-exe", PYTHON_EXE, "--working-dir", WORKING_DIR,
        "--log-dir", LOG_DIR, "--journal-dir", str(_journal_dir(tmp_path)),
        "--state-file", str(ledger), "--repo-root", REPO_ROOT, "--secret-mode", mode,
    ]


def _secrets(tmp_path):
    xml_secret = bd.xml_environment((tmp_path / "MYCDeveloperBroker.xml").read_text(encoding="utf-8"))["DEVELOPER_BROKER_SECRET"]
    _before, block, _after = bd.split_env_block((tmp_path / ".env").read_text(encoding="utf-8"))
    return xml_secret, block["DEVELOPER_BROKER_SECRET"]


def test_provision_writes_both_sides_with_the_same_secret_and_backend_disabled(tmp_path, capsys):
    original = "DATABASE_URL=postgresql://x\r\nSECRET_KEY=abc\r\n"
    (tmp_path / ".env").write_bytes(original.encode("utf-8"))
    inode = os.stat(tmp_path / ".env").st_ino
    code, _out, result = _run(_provision_args(tmp_path, "generate"), capsys)
    assert code == 0 and result == {"backend_config": "owned", "backend_enabled": False, "recovered": "none", "secret_source": "generate", "status": "provisioned"}
    xml_secret, env_secret = _secrets(tmp_path)
    assert xml_secret == env_secret and bd.check_secret(xml_secret)
    text = (tmp_path / ".env").read_bytes().decode("utf-8")
    assert text.startswith(original) and "\r\n" in text and "\n" not in text.replace("\r\n", "")
    assert "DEVELOPER_BROKER_ENABLED=false" in text and "DEVELOPER_BROKER_CLIENT_SID=S-1-5-18" in text
    assert os.stat(tmp_path / ".env").st_ino == inode  # rewritten in place: keeps its ACL on Windows
    assert not list(tmp_path.glob(".*.new"))
    assert [p.name for p in (tmp_path / "state").iterdir()] == ["install-state.json"]  # journal removed: no lingering copy of the secret


def test_provision_is_idempotent_and_generate_rotates(tmp_path, capsys):
    (tmp_path / ".env").write_text("A=1\n", encoding="utf-8")
    _run(_provision_args(tmp_path, "generate"), capsys)
    first = _secrets(tmp_path)[0]
    _run(_provision_args(tmp_path, "reuse"), capsys)
    assert _secrets(tmp_path) == (first, first)
    assert (tmp_path / ".env").read_text(encoding="utf-8").count(bd.BLOCK_BEGIN) == 1
    _run(_provision_args(tmp_path, "generate"), capsys)
    rotated = _secrets(tmp_path)
    assert rotated[0] == rotated[1] != first


def test_reuse_requires_both_existing_and_equal(tmp_path, capsys):
    (tmp_path / ".env").write_text("A=1\n", encoding="utf-8")
    code, _out, result = _run(_provision_args(tmp_path, "reuse"), capsys)
    assert code == 3 and result == {"error": "secret_reuse_unavailable"}
    _run(_provision_args(tmp_path, "generate"), capsys)
    text = (tmp_path / ".env").read_text(encoding="utf-8")
    xml_secret = _secrets(tmp_path)[0]
    (tmp_path / ".env").write_text(text.replace(xml_secret, "B" * 64), encoding="utf-8")
    code, _out, result = _run(_provision_args(tmp_path, "reuse"), capsys)
    # the edited block no longer matches DEV-1C's evidence: refused before any secret handling
    assert code == 3 and result == {"error": "managed_block_drifted"}


def test_stdin_secret_is_validated(tmp_path, capsys, monkeypatch):
    (tmp_path / ".env").write_text("A=1\n", encoding="utf-8")
    code, _out, result = _run(_provision_args(tmp_path, "stdin"), capsys, "tooshort\n", monkeypatch)
    assert code == 3 and result == {"error": "secret_format_invalid"}
    assert not (tmp_path / "MYCDeveloperBroker.xml").exists()


def test_unmanaged_developer_broker_keys_are_refused_before_anything_is_written(tmp_path, capsys):
    original = "A=1\nexport DEVELOPER_BROKER_SECRET=legacy\n"
    (tmp_path / ".env").write_text(original, encoding="utf-8")
    code, _out, result = _run(_provision_args(tmp_path, "generate"), capsys)
    assert code == 3 and result == {"error": "env_unmanaged_developer_broker_keys"}
    assert (tmp_path / ".env").read_text(encoding="utf-8") == original
    assert not (tmp_path / "MYCDeveloperBroker.xml").exists()


@pytest.mark.parametrize("text", [
    f"{bd.BLOCK_BEGIN}\nDEVELOPER_BROKER_ENABLED=true\n",
    f"{bd.BLOCK_END}\n{bd.BLOCK_BEGIN}\n",
    f"{bd.BLOCK_BEGIN}\n{bd.BLOCK_END}\n{bd.BLOCK_BEGIN}\n{bd.BLOCK_END}\n",
    f"{bd.BLOCK_BEGIN}\nDEVELOPER_BROKER_OTHER=1\n{bd.BLOCK_END}\n",
    f"{bd.BLOCK_BEGIN}\nOTHER=1\n{bd.BLOCK_END}\n",
])
def test_malformed_managed_blocks_are_refused(text):
    with pytest.raises(bd.PolicyError):
        bd.split_env_block(text)


def test_enable_disable_and_remove_block_round_trip(tmp_path, capsys):
    original = "A=1\n# comment\nB=2\n"
    (tmp_path / ".env").write_text(original, encoding="utf-8")
    _run(_provision_args(tmp_path, "generate"), capsys)
    env = str(tmp_path / ".env")
    code, _out, result = _run(["set-backend-enabled", "--env-file", env, "--enabled", "true"], capsys)
    assert code == 0 and result["backend_enabled"] is True
    assert bd.split_env_block((tmp_path / ".env").read_text(encoding="utf-8"))[1]["DEVELOPER_BROKER_ENABLED"] == "true"
    _run(["set-backend-enabled", "--env-file", env, "--enabled", "false"], capsys)
    code, _out, result = _run(["remove-backend-block", "--env-file", env], capsys)
    assert code == 0 and result == {"status": "removed"}
    assert (tmp_path / ".env").read_text(encoding="utf-8") == original
    code, _out, result = _run(["set-backend-enabled", "--env-file", env, "--enabled", "true"], capsys)
    assert code == 3 and result == {"error": "env_block_missing"}


def test_verify_reports_consistency_and_detects_drift(tmp_path, capsys):
    (tmp_path / ".env").write_text("A=1\n", encoding="utf-8")
    _run(_provision_args(tmp_path, "generate"), capsys)
    argv = ["verify", "--xml", str(tmp_path / "MYCDeveloperBroker.xml"), "--env-file", str(tmp_path / ".env"),
            "--pipe-name", "MYCDeveloperBroker", "--client-sid", CLIENT_SID, "--service-sid", SERVICE_SID,
            "--python-exe", PYTHON_EXE, "--working-dir", WORKING_DIR]
    code, _out, result = _run(argv, capsys)
    assert code == 0 and result["ok"] is True and all(result["checks"].values())
    xml_secret = _secrets(tmp_path)[0]
    text = (tmp_path / ".env").read_text(encoding="utf-8")
    (tmp_path / ".env").write_text(text.replace(xml_secret, "C" * 64), encoding="utf-8")
    _code, _out, result = _run(argv, capsys)
    assert result["ok"] is False and result["checks"]["secret_matches"] is False


# --- XML rendering ----------------------------------------------------------------------

def test_paths_with_spaces_and_xml_metacharacters_are_escaped_not_injected():
    xml = _render(working_dir=r"C:\Users\SMM ADMIN\R&D <x>\backend")
    root = ElementTree.fromstring(xml)
    assert root.findtext("workingdirectory") == r"C:\Users\SMM ADMIN\R&D <x>\backend"
    assert len(root.findall("env")) == 6


@pytest.mark.parametrize("override", [
    {"python_exe": r"C:\%PATH%\python.exe"},
    {"python_exe": r"relative\python.exe"},
    {"log_dir": r"C:\MYC\..\Windows"},
])
def test_unsafe_rendering_values_are_refused(override):
    with pytest.raises(bd.PolicyError):
        _render(**override)


def test_unresolved_tokens_or_a_serviceaccount_element_are_refused():
    environment = bd.broker_environment("MYCDeveloperBroker", "A" * 64, CLIENT_SID, SERVICE_SID)
    template = TEMPLATE.read_text(encoding="utf-8")
    kwargs = {"python_exe": PYTHON_EXE, "working_dir": WORKING_DIR, "log_dir": LOG_DIR, "environment": environment}
    with pytest.raises(bd.PolicyError):
        bd.render_service_xml(template.replace("</service>", "<x>{{UNKNOWN}}</x></service>"), **kwargs)
    with pytest.raises(bd.PolicyError):
        bd.render_service_xml(template.replace("</service>", "<serviceaccount><username>LocalSystem</username></serviceaccount></service>"), **kwargs)


# --- secret scan --------------------------------------------------------------------------

def test_scan_for_secret_finds_utf8_utf16_and_chunk_boundaries(tmp_path, capsys, monkeypatch):
    (tmp_path / ".env").write_text("A=1\n", encoding="utf-8")
    _run(_provision_args(tmp_path, "generate"), capsys)
    secret = _secrets(tmp_path)[0]
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "MYCDeveloperBroker.err.log").write_text("Developer Broker escuchando (broker.health)\n", encoding="utf-8")
    argv = ["scan-for-secret", "--xml", str(tmp_path / "MYCDeveloperBroker.xml"), "--dir", str(logs)]
    assert _run(argv, capsys)[2]["secret_found"] is False
    monkeypatch.setattr(bd, "_SCAN_CHUNK_BYTES", 7)
    (logs / "wrapper.log").write_bytes(b"x" * 5 + secret.encode("utf-16-le"))
    assert _run(argv, capsys)[2]["secret_found"] is True
    (logs / "wrapper.log").write_bytes(b"prefix " + secret.encode("utf-8"))
    assert _run(argv, capsys)[2]["secret_found"] is True


# --- SeServiceLogonRight ---------------------------------------------------------------------

def _export(tmp_path, lines):
    text = "[Unicode]\r\nUnicode=yes\r\n[Privilege Rights]\r\n" + "\r\n".join(lines) + "\r\n[Version]\r\nsignature=\"$CHICAGO$\"\r\n"
    path = tmp_path / "export.inf"
    path.write_text(text, encoding="utf-16")
    return path


def test_logon_right_is_not_touched_when_all_services_already_has_it(tmp_path, capsys):
    export = _export(tmp_path, ["SeServiceLogonRight = *S-1-5-80-0,*S-1-5-20"])
    code, _out, result = _run(["logon-right", "--export", str(export), "--sid", SERVICE_SID, "--out", str(tmp_path / "o.inf"), "--action", "grant"], capsys)
    assert code == 0 and result == {"inf_written": False, "status": "granted_via_all_services"}
    assert not (tmp_path / "o.inf").exists()


def test_logon_right_grant_writes_a_single_line_preserving_every_member(tmp_path, capsys):
    export = _export(tmp_path, ["SeNetworkLogonRight = *S-1-1-0", "SeServiceLogonRight = *S-1-5-20,SQLAccount,*S-1-5-19"])
    out = tmp_path / "grant.inf"
    code, _o, result = _run(["logon-right", "--export", str(export), "--sid", SERVICE_SID, "--out", str(out), "--action", "grant"], capsys)
    assert code == 0 and result == {"inf_written": True, "status": "grant_required"}
    text = out.read_text(encoding="utf-16")
    privileges = text.split("[Privilege Rights]")[1].strip().splitlines()
    assert len(privileges) == 1  # exactly ONE privilege line: nothing else of the local policy is written
    assert f"SeServiceLogonRight = *S-1-5-20,SQLAccount,*S-1-5-19,*{SERVICE_SID}" in text
    assert "SeNetworkLogonRight" not in text
    assert bd.logon_right_change(text, SERVICE_SID, "grant")[0] == "already_granted"


def test_logon_right_denied_by_policy_fails_closed(tmp_path):
    for deny in (f"*{SERVICE_SID}", "*S-1-5-80-0"):
        with pytest.raises(bd.PolicyError) as error:
            bd.logon_right_change(f"[Privilege Rights]\nSeDenyServiceLogonRight = {deny}\n", SERVICE_SID, "grant")
        assert error.value.code == "service_logon_denied_by_policy"


def test_logon_right_revoke_removes_only_the_broker(tmp_path):
    text = f"[Privilege Rights]\nSeServiceLogonRight = *S-1-5-20,*{SERVICE_SID}\n"
    status, inf = bd.logon_right_change(text, SERVICE_SID, "revoke")
    assert status == "revoke_required" and "SeServiceLogonRight = *S-1-5-20\r\n" in inf
    assert bd.logon_right_change("[Privilege Rights]\nSeServiceLogonRight = *S-1-5-20\n", SERVICE_SID, "revoke") == ("not_present", None)
    # Broker as the ONLY member (original state: right unassigned): no INF,
    # the caller restores "unassigned" through LsaRemoveAccountRights.
    assert bd.logon_right_change(f"[Privilege Rights]\nSeServiceLogonRight = *{SERVICE_SID}\n", SERVICE_SID, "revoke") == ("revoke_last_member", None)


def test_secedit_is_scoped_to_user_rights_and_ntrights_is_not_used():
    module = _ps(MODULE)
    for call in re.findall(r"secedit[^\n]*|\$secedit -ArgumentList @\([^\n]*", module):
        if "/configure" in call or "/export" in call:
            assert "'/areas', 'USER_RIGHTS'" in call, call
    assert "/overwrite" not in module.lower()
    for path in POWERSHELL_FILES:
        assert not re.search(r"\bntrights(\.exe)?\b", _ps_code(path), re.IGNORECASE)


# --- ACL plan ------------------------------------------------------------------------------------

def _plan(python_home=r"C:\Program Files\Python314"):
    return bd.acl_plan(REPO_ROOT, python_home, SERVICE_DIR, LOG_DIR, SERVICE_SID)


def test_acl_plan_is_minimal_read_execute_plus_own_log_modify():
    plan = {grant["path"]: grant for grant in _plan()}
    assert set(plan) == {
        SERVICE_DIR, LOG_DIR, WORKING_DIR, WORKING_DIR + r"\app", WORKING_DIR + r"\app\developer_broker",
        REPO_ROOT + r"\venv", r"C:\Program Files\Python314",
    }
    assert [path for path, grant in plan.items() if grant["rights"] == "M"] == [LOG_DIR]
    assert all(grant["rights"] in ("RX", "M") for grant in plan.values())
    assert REPO_ROOT not in plan  # no grant on the whole repo
    assert plan[WORKING_DIR]["icacls_grant"] == f"*{SERVICE_SID}:(RX)"  # backend folder only: .env NOT covered
    assert plan[WORKING_DIR + r"\app"]["icacls_grant"] == f"*{SERVICE_SID}:(OI)(NP)(RX)"
    assert plan[WORKING_DIR + r"\app\developer_broker"]["icacls_grant"] == f"*{SERVICE_SID}:(OI)(CI)(RX)"
    assert plan[LOG_DIR]["icacls_grant"] == f"*{SERVICE_SID}:(OI)(CI)(M)"


def test_acl_plan_python_home_inside_venv_needs_no_extra_grant():
    assert len(_plan(REPO_ROOT + r"\venv\base")) == 6


@pytest.mark.parametrize("args", [
    (r"relative\repo", r"C:\Python", SERVICE_DIR, LOG_DIR, SERVICE_SID),
    (REPO_ROOT, r"C:\Python", REPO_ROOT + r"\svc", LOG_DIR, SERVICE_SID),
    (REPO_ROOT, r"C:\Python", SERVICE_DIR, LOG_DIR, "S-1-5-18"),
])
def test_acl_plan_refuses_unsafe_inputs(args):
    with pytest.raises(bd.PolicyError):
        bd.acl_plan(*args)


# --- ACL evaluation -------------------------------------------------------------------------------

def _snapshot(aces, owner="S-1-5-32-544", protected=True):
    return {"owner_sid": owner, "protected": protected, "aces": [
        {"sid": sid, "rights": rights, "type": kind, "inherited": False} for sid, rights, kind in aces
    ]}


FULL, RX, MODIFY = bd.FULL_CONTROL, bd.READ_AND_EXECUTE, bd.MODIFY
PRODUCTION_SERVICES_ACL = _snapshot([
    ("S-1-5-32-544", FULL, "Allow"), ("S-1-5-18", FULL, "Allow"),
    ("S-1-5-32-545", RX, "Allow"), ("S-1-5-11", MODIFY, "Allow"),
], protected=False)
HARDENED_SERVICES_ACL = _snapshot([("S-1-5-18", FULL, "Allow"), ("S-1-5-32-544", FULL, "Allow")])


def test_production_services_acl_is_non_compliant():
    violations = bd.evaluate_acl(PRODUCTION_SERVICES_ACL, "services_root", allow_users_read=True)
    assert "broad_principal:S-1-5-11" in violations
    assert "inheritance_not_disabled" in violations
    assert "broad_principal:S-1-5-32-545" in bd.evaluate_acl(PRODUCTION_SERVICES_ACL, "services_root")


def test_hardened_services_acl_is_compliant_and_users_only_with_read_execute():
    assert bd.evaluate_acl(HARDENED_SERVICES_ACL, "services_root") == []
    with_users = _snapshot([*[(a["sid"], a["rights"], "Allow") for a in HARDENED_SERVICES_ACL["aces"]], ("S-1-5-32-545", RX, "Allow")])
    assert bd.evaluate_acl(with_users, "services_root", allow_users_read=True) == []
    users_write = _snapshot([("S-1-5-18", FULL, "Allow"), ("S-1-5-32-544", FULL, "Allow"), ("S-1-5-32-545", MODIFY, "Allow")])
    assert bd.evaluate_acl(users_write, "services_root", allow_users_read=True) == ["excess_rights:S-1-5-32-545"]


@pytest.mark.parametrize("rights", [bd.GENERIC_ALL, -0x40000000 & 0xFFFFFFFF, bd.GENERIC_WRITE, 0x10000000 - 2**32])
def test_generic_rights_are_normalized(rights):
    snapshot = _snapshot([("S-1-5-18", FULL, "Allow"), ("S-1-5-32-544", FULL, "Allow"), ("S-1-5-11", rights, "Allow")])
    assert "broad_principal:S-1-5-11" in bd.evaluate_acl(snapshot, "services_root")


def test_missing_full_control_untrusted_owner_and_deny_aces():
    snapshot = _snapshot([("S-1-5-32-544", FULL, "Allow"), ("S-1-5-18", RX, "Allow"), ("S-1-5-11", FULL, "Deny")], owner="S-1-5-21-9-9-9-1001")
    violations = bd.evaluate_acl(snapshot, "services_root")
    assert violations == ["untrusted_owner", "unexpected_deny:S-1-5-11", "missing_full_control:S-1-5-18"]


def test_service_and_log_directory_policies():
    base = [("S-1-5-18", FULL, "Allow"), ("S-1-5-32-544", FULL, "Allow")]
    assert bd.evaluate_acl(_snapshot([*base, (SERVICE_SID, RX, "Allow")]), "service_dir", service_sid=SERVICE_SID) == []
    assert bd.evaluate_acl(_snapshot([*base, (SERVICE_SID, MODIFY, "Allow")]), "service_dir", service_sid=SERVICE_SID) == [f"excess_rights:{SERVICE_SID}"]
    assert bd.evaluate_acl(_snapshot([*base, (SERVICE_SID, MODIFY, "Allow")]), "log_dir", service_sid=SERVICE_SID) == []
    assert bd.evaluate_acl(_snapshot([*base, (SERVICE_SID, FULL, "Allow")]), "log_dir", service_sid=SERVICE_SID) == [f"excess_rights:{SERVICE_SID}"]
    assert bd.evaluate_acl(_snapshot([*base, ("S-1-5-32-545", RX, "Allow")]), "service_dir", service_sid=SERVICE_SID) == ["broad_principal:S-1-5-32-545"]
    assert "inheritance_not_disabled" in bd.evaluate_acl(_snapshot(base, protected=False), "log_dir", service_sid=SERVICE_SID)


def test_secret_file_policy_refuses_broad_or_service_readers():
    owner_user = "S-1-5-21-1-2-3-1001"
    assert bd.evaluate_acl(_snapshot([("S-1-5-18", FULL, "Allow"), (owner_user, FULL, "Allow")], owner=owner_user), "secret_file") == []
    assert bd.evaluate_acl(_snapshot([("S-1-5-32-545", RX, "Allow")]), "secret_file") == ["broad_read:S-1-5-32-545"]
    assert bd.evaluate_acl(_snapshot([(SERVICE_SID, RX, "Allow")]), "secret_file") == [f"broad_read:{SERVICE_SID}"]


def test_evaluate_acl_command_accepts_a_list_of_snapshots(tmp_path, capsys):
    path = tmp_path / "acl.json"
    path.write_text(json.dumps([{**PRODUCTION_SERVICES_ACL, "path": r"C:\MYC\Services\backend"}]), encoding="utf-8-sig")
    code, _out, result = _run(["evaluate-acl", "--input", str(path), "--policy", "services_tree"], capsys)
    assert code == 0 and result["compliant"] is False
    assert r"C:\MYC\Services\backend: broad_principal:S-1-5-11" in result["violations"]


def test_hardening_never_grants_broad_principals_and_backs_up_first():
    module = _ps(MODULE)
    body = module[module.index("function Set-MYCServicesAclHardening"):]
    body = body[: body.index("\nfunction ")]
    assert body.index("Backup-MYCAcl") < body.index("Set-MYCProtectedAcl")
    assert "'/inheritance:r'" in module and "'/setowner'" in module
    assert "'/save'" not in _ps_code(MODULE) and "'/T'" not in _ps_code(MODULE)  # no recursive icacls at all
    for path in POWERSHELL_FILES:
        assert not re.search(r"S-1-5-11|S-1-1-0|Authenticated Users|Everyone", _ps_code(path)), path.name
    assert "('*{0}:(OI)(CI)(RX)' -f $script:UsersSid)" in module  # Users: read/execute, only when requested
    assert "[switch]$AllowUsersReadOnServices" in _ps(INSTALL)


# --- service compatibility -------------------------------------------------------------------

WRAPPER = SERVICE_DIR + r"\MYCDeveloperBroker.exe"


@pytest.mark.parametrize("info,verdict", [
    ({"exists": False}, "absent"),
    ({"exists": True, "start_name": "NT SERVICE\\MYCDeveloperBroker", "path_name": f'"{WRAPPER}"', "service_type": "Own Process"}, "compatible"),
    ({"exists": True, "start_name": "nt service\\mycdeveloperbroker", "path_name": WRAPPER.upper(), "service_type": "Own Process"}, "compatible"),
    ({"exists": True, "start_name": "LocalSystem", "path_name": WRAPPER, "service_type": "Own Process"}, "incompatible"),
    ({"exists": True, "start_name": "NT SERVICE\\MYCDeveloperBroker", "path_name": r"C:\evil\x.exe", "service_type": "Own Process"}, "incompatible"),
    ({"exists": True, "start_name": "NT SERVICE\\MYCDeveloperBroker", "path_name": f'"{WRAPPER}" -x', "service_type": "Own Process"}, "incompatible"),
    ({"exists": True, "start_name": "NT SERVICE\\MYCDeveloperBroker", "path_name": WRAPPER, "service_type": "Share Process"}, "incompatible"),
])
def test_service_verdict(info, verdict):
    assert bd.service_verdict(info, WRAPPER)["verdict"] == verdict


def test_install_refuses_incompatible_existing_service_before_any_change():
    install = _ps(INSTALL)
    assert "& $add 'broker_service_state' (& $pf ($verdict.Verdict -ne 'incompatible'))" in install
    uninstall = _ps(UNINSTALL)
    assert "if ($verdict.Verdict -eq 'incompatible')" in uninstall


# --- PowerShell structure ----------------------------------------------------------------------

@pytest.mark.parametrize("path", POWERSHELL_FILES, ids=lambda path: path.name)
def test_powershell_files_are_strict_utf8_bom_and_download_free(path):
    raw = path.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "PowerShell 5.1 needs a BOM to read UTF-8"
    text = _ps(path)
    assert "Set-StrictMode -Version 3.0" in text and "$ErrorActionPreference = 'Stop'" in text
    for forbidden in ("Invoke-WebRequest", "Invoke-RestMethod", "DownloadFile", "Start-BitsTransfer", "Net.WebClient", "curl ", "wget ", "Invoke-Expression", "iex "):
        assert forbidden not in text, forbidden
    for forbidden in ("powershell.exe", "pwsh", "cmd.exe", "Start-Process"):
        assert forbidden not in text, forbidden


@pytest.mark.parametrize("path", POWERSHELL_FILES, ids=lambda path: path.name)
def test_powershell_never_shadows_module_constants_or_automatic_variables(path):
    """PowerShell variable names are case-insensitive: a local ``$systemSid``
    silently IS the exported ``$SystemSid`` constant."""
    exported = re.search(r"Export-ModuleMember -Function \* -Variable ([^\n]+)", _ps(MODULE)).group(1)
    protected = {name.strip().lower() for name in exported.split(",")}
    protected |= {"home", "input", "args", "error", "host", "pid", "pwd", "profile", "event", "sender", "this", "matches", "ofs"}
    for match in re.finditer(r"^\s*\$(\w+)\s*=[^=]", _ps_code(path), re.MULTILINE):
        assert match.group(1).lower() not in protected, (path.name, match.group(0))
    for match in re.finditer(r"foreach \(\$(\w+) in", _ps_code(path)):
        assert match.group(1).lower() not in protected, (path.name, match.group(0))


@pytest.mark.parametrize("path", (INSTALL, UNINSTALL, VALIDATE, HARDEN, RESTORE), ids=lambda path: path.name)
def test_scripts_require_elevation_before_any_change(path):
    text = _ps(path)
    assert "#Requires -RunAsAdministrator" in text
    elevated = text.index("Assert-MYCElevated")
    for mutation in ("'create'", "'delete'", "Copy-Item", "New-MYCProtectedDirectory", "Set-MYC", "Grant-MYC", "Revoke-MYC", "Remove-Item", "Invoke-MYCDeployTool"):
        if mutation in text:
            assert elevated < text.index(mutation), mutation
    assert "[Security.Principal.WindowsBuiltInRole]::Administrator" in _ps(MODULE)


def test_install_runs_the_whole_preflight_before_modifying_windows():
    install = _ps(INSTALL)
    gate = install.index("$failures = @($preflight | Where-Object { $_.Status -eq 'FAIL' })")
    for mutation in ("Start-MYCBrokerState", "Set-MYCServicesAclHardening", "New-MYCOwnedDirectory -Layout", "Copy-Item", "'create', $ServiceId", "Set-MYCServiceLogonRight", "'provision'", "'set-backend-enabled'"):
        assert gate < install.index(mutation), mutation
    assert install.index("exit 1", gate) < install.index("Copy-Item")
    for check in ("'install_state'", "'broker_service_owned'", "'backend_block_owned'", "'parent_acl '", "'elevated'", "'repo_exists'", "'git_checkout'", "'required_files'", "'venv_python'", "'pywin32_imports'",
                  "'winsw_source'", "'backend_service_exists'", "'backend_runs_as_localsystem'", "'backend_process_identity'",
                  "'client_sid_is_localsystem'", "'broker_service_state'", "'service_dir_contents'", "'no_registry_service_environment'",
                  "'backend_env_safe'", "'backend_env_acl'", "'secret_source'", "'broker_import_and_pipe_name'", "'pipe_name_not_squatted'",
                  "'services_acl'", "'wrapper_path_without_spaces'"):
        assert check in install, check


def test_install_enables_the_backend_only_after_the_broker_is_validated():
    install = _ps(INSTALL)
    assert install.index("Test-MYCBrokerRuntime") < install.index("'set-backend-enabled', '--env-file', $layout.EnvFile, '--enabled', 'true'")
    assert install.index("'demand'") < install.index("'start=', 'auto'")
    catch = install[install.index("} catch {\n    $message"):]
    assert "Stop-MYCBrokerService" in catch and "'start=', 'demand'" in catch and "exit 1" in catch
    assert "Restart-Service -Name $BackendServiceName" in install and "if ($RestartBackend)" in install


def test_uninstall_is_explicit_bounded_and_never_touches_other_services():
    uninstall = _ps(UNINSTALL)
    module = _ps(MODULE)
    assert "[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]" in uninstall
    assert uninstall.count("$PSCmdlet.ShouldProcess(") >= 7
    assert "$script:StopTimeoutSeconds = 45" in module and "$script:KillWaitSeconds = 10" in module and "$script:DeleteTimeoutSeconds = 30" in module
    assert re.findall(r"'delete', (\S+)\)", uninstall) == ["$ServiceId"]
    assert "Remove = [bool]$RemoveServiceFiles" in uninstall and "Remove = [bool]$RemoveLogs" in uninstall
    stop = module[module.index("function Stop-MYCBrokerService"):]
    stop = stop[: stop.index("\nfunction ")]
    assert "$sid = Assert-MYCBrokerServiceStillOurs -Layout $Layout" in stop
    assert stop.index("$sid = Assert-MYCBrokerServiceStillOurs") < stop.index("(Get-MYCProcessOwnerSid -ProcessId $processId) -eq $sid") < stop.index("Stop-Process")
    assert "Stop-Service -Name $BackendServiceName" not in uninstall and "'delete', $BackendServiceName" not in uninstall
    assert "if ($actions.revoke_logon_right)" in uninstall  # revoked only if the ledger says DEV-1C added it


def test_installer_supports_the_production_repo_path_with_spaces():
    install = _ps(INSTALL)
    assert "[string]$RepoRoot = 'C:\\Users\\SMM ADMIN\\myc_erp'" in install
    assert "-LiteralPath" in install and "Invoke-Expression" not in install
    assert "& $add 'wrapper_path_without_spaces' (& $pf ($layout.Wrapper -notmatch '[\\s\"]'))" in install


def test_default_pipe_name_is_valid_for_the_broker():
    assert "[string]$PipeName = 'MYCDeveloperBroker'" in _ps(INSTALL)
    assert pipe_name.validate_pipe_name("MYCDeveloperBroker") == "MYCDeveloperBroker"


# --- no process execution / scope ---------------------------------------------------------------

FORBIDDEN_MODULES = {"subprocess", "pty", "multiprocessing", "ctypes", "socket", "asyncio", "pexpect", "http", "urllib"}
FORBIDDEN_OS_CALLS = {"system", "popen", "execv", "execve", "execl", "execlp", "execvp", "spawnl", "spawnv", "startfile", "fork", "posix_spawn"}


def _imports(path: Path) -> set[str]:
    names = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.parametrize("path", [TOOL_PATH, *sorted((BACKEND / "app/developer_broker").glob("*.py"))], ids=lambda path: path.name)
def test_no_process_execution_in_broker_or_deployment_python(path):
    for name in _imports(path):
        assert name.split(".")[0] not in FORBIDDEN_MODULES, f"{path.name} imports {name}"
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "os":
            assert node.attr not in FORBIDDEN_OS_CALLS, f"os.{node.attr} in {path.name}"
        if isinstance(node, ast.keyword):
            assert node.arg != "shell", path.name
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            lowered = node.value.lower()
            for term in ("powershell", "pwsh", "cmd.exe", "conpty", "createpseudoconsole", "psql"):
                assert term not in lowered, (path.name, term)


def test_deployment_tool_imports_only_stdlib_and_the_broker():
    allowed = {"__future__", "argparse", "datetime", "hashlib", "hmac", "json", "os", "re", "secrets", "stat", "sys", "pathlib", "xml.etree", "xml.sax.saxutils",
               "app.developer_broker.host", "app.developer_broker.pipe_name", "app.developer_broker.protocol"}
    assert _imports(TOOL_PATH) <= allowed


def test_broker_health_remains_the_only_operation():
    assert BrokerServer(BrokerSecret.from_text("A" * 64)).operations == (OP_BROKER_HEALTH,)


# =============================================================================================
# Audit fix P0 -- install-state ownership ledger (SeServiceLogonRight and rollback)
# =============================================================================================

def _ledger(tmp_path):
    return tmp_path / "state" / "install-state.json"


def _state_cmd(tmp_path, capsys, command, *extra):
    _journal_dir(tmp_path)
    return _run([command, "--file", str(_ledger(tmp_path)), "--repo-root", REPO_ROOT, *extra], capsys)


def _logon_status(tmp_path, capsys, members):
    """What the installer does: export -> tool decides -> only a written INF
    (grant_required) leads to ownership being recorded."""
    lines = [f"SeServiceLogonRight = {','.join(members)}"] if members else []
    export = _export(tmp_path, lines)
    _code, _out, result = _run(["logon-right", "--export", str(export), "--sid", SERVICE_SID,
                                "--out", str(tmp_path / "grant.inf"), "--action", "grant"], capsys)
    return result


def _install_until_logon_right(tmp_path, capsys, members):
    """Mirror of Install-MYCDeveloperBroker.ps1 steps 0, 5, 6 and 7."""
    _state_cmd(tmp_path, capsys, "state-begin")
    _state_cmd(tmp_path, capsys, "state-update", "--service", "pending")
    # ... sc.exe create + SCM re-query (verdict compatible) ...
    _state_cmd(tmp_path, capsys, "state-update", "--service", "owned")
    _state_cmd(tmp_path, capsys, "state-update", "--service-sid", SERVICE_SID)
    result = _logon_status(tmp_path, capsys, members)
    if result["inf_written"]:
        _state_cmd(tmp_path, capsys, "state-update", "--logon-right", "pending")
        # ... secedit /configure + verified re-export happen here on Windows ...
        _state_cmd(tmp_path, capsys, "state-update", "--logon-right", "added")
    return result["status"]


def test_ledger_exists_before_the_first_mutation_and_holds_no_secret(tmp_path, capsys):
    code, _out, result = _state_cmd(tmp_path, capsys, "state-begin")
    assert code == 0 and result["exists"] and result["owns_nothing"]
    state = json.loads(_ledger(tmp_path).read_text(encoding="utf-8"))
    assert state["schema"] == 6 and state["phase"] == "installing" and state["backend_activation"] == "none"
    assert state["owned"] == {"service": "none", "logon_right": "none", "acl_grants": [], "service_dir": "none", "log_dir": "none",
                              "backend_config": "none",
                              "backend_config_evidence": {"marker": None, "fingerprint": None, "fingerprint_next": None}}
    assert "secret" not in json.dumps(state).lower()
    install = _ps(INSTALL)
    first_mutation = min(install.index(m) for m in ("Set-MYCServicesAclHardening -Layout", "New-MYCOwnedDirectory -Layout", "Copy-Item", "'create', $ServiceId"))
    assert install.index("Start-MYCBrokerState -Layout $layout") < first_mutation


def test_first_install_adds_the_right_then_fails_later_and_rollback_revokes_it(tmp_path, capsys):
    status = _install_until_logon_right(tmp_path, capsys, ["*S-1-5-20"])
    assert status == "grant_required"
    # A later step fails (ACLs, provisioning, runtime): nothing else is written.
    _code, _out, shown = _state_cmd(tmp_path, capsys, "state-show")
    assert shown["state"]["phase"] == "installing"
    assert shown["rollback"] == {"delete_service": True, "service_ownership": "owned", "revoke_logon_right": True, "acl_grants": [],
                                 "service_sid": SERVICE_SID, "service_dir": "none", "log_dir": "none", "backend_config": "none"}


def test_crash_between_secedit_and_the_added_record_is_still_owned(tmp_path, capsys):
    _state_cmd(tmp_path, capsys, "state-begin")
    _state_cmd(tmp_path, capsys, "state-update", "--service-sid", SERVICE_SID)
    assert _logon_status(tmp_path, capsys, ["*S-1-5-20"])["status"] == "grant_required"
    _state_cmd(tmp_path, capsys, "state-update", "--logon-right", "pending")
    # crash: secedit may or may not have applied; "pending" proves the SID was absent before
    _code, _out, shown = _state_cmd(tmp_path, capsys, "state-show")
    assert shown["rollback"]["revoke_logon_right"] is True
    # revoking a right that was never applied is a no-op
    assert bd.logon_right_change("[Privilege Rights]\nSeServiceLogonRight = *S-1-5-20\n", SERVICE_SID, "revoke") == ("not_present", None)


def test_preexisting_direct_right_is_never_owned(tmp_path, capsys):
    status = _install_until_logon_right(tmp_path, capsys, ["*S-1-5-20", f"*{SERVICE_SID}"])
    assert status == "already_granted"
    _code, _out, shown = _state_cmd(tmp_path, capsys, "state-show")
    assert shown["state"]["owned"]["logon_right"] == "none"
    assert shown["rollback"]["revoke_logon_right"] is False


def test_right_effective_through_all_services_is_never_owned(tmp_path, capsys):
    status = _install_until_logon_right(tmp_path, capsys, ["*S-1-5-80-0", "*S-1-5-20"])
    assert status == "granted_via_all_services"
    _code, _out, shown = _state_cmd(tmp_path, capsys, "state-show")
    assert shown["rollback"]["revoke_logon_right"] is False


def test_reinstall_keeps_previous_ownership(tmp_path, capsys):
    assert _install_until_logon_right(tmp_path, capsys, ["*S-1-5-20"]) == "grant_required"
    grant = ["--grant-path", SERVICE_DIR, "--grant-value", f"*{SERVICE_SID}:(OI)(CI)(RX)"]
    _state_cmd(tmp_path, capsys, "state-update", *grant, "--grant-status", "pending")
    _state_cmd(tmp_path, capsys, "state-update", *grant, "--grant-status", "owned")
    _state_cmd(tmp_path, capsys, "state-update", "--phase", "installed")
    # re-run: the ledger is re-opened, the right is now directly present
    code, _out, begun = _state_cmd(tmp_path, capsys, "state-begin")
    assert code == 0 and begun["state"]["phase"] == "installing"
    assert _logon_status(tmp_path, capsys, ["*S-1-5-20", f"*{SERVICE_SID}"])["status"] == "already_granted"
    _state_cmd(tmp_path, capsys, "state-update", *grant, "--grant-status", "owned")  # same plan again: no duplicate
    _code, _out, shown = _state_cmd(tmp_path, capsys, "state-show")
    owned = shown["state"]["owned"]
    assert owned["service"] == "owned" and owned["logon_right"] == "added" and len(owned["acl_grants"]) == 1


def test_uninstall_after_partial_install_removes_only_owned_resources(tmp_path, capsys):
    _install_until_logon_right(tmp_path, capsys, ["*S-1-5-20"])
    _code, _out, shown = _state_cmd(tmp_path, capsys, "state-show")
    assert shown["rollback"]["acl_grants"] == []  # grants never reached: nothing to revoke
    code, _out, refused = _state_cmd(tmp_path, capsys, "state-delete")
    assert code == 3 and refused == {"error": "state_still_owns_resources"}
    _state_cmd(tmp_path, capsys, "state-update", "--phase", "uninstalling")
    _state_cmd(tmp_path, capsys, "state-update", "--service", "none")
    _state_cmd(tmp_path, capsys, "state-update", "--logon-right", "none")  # after the verified secedit revoke
    code, _out, deleted = _state_cmd(tmp_path, capsys, "state-delete")
    assert code == 0 and deleted == {"deleted": True, "retained": False} and not _ledger(tmp_path).exists()


def test_no_ledger_means_nothing_is_owned():
    assert bd.rollback_actions(None) == {"delete_service": False, "service_ownership": "none", "revoke_logon_right": False, "acl_grants": [],
                                         "service_sid": None, "service_dir": "none", "log_dir": "none", "backend_config": "none"}
    uninstall = _ps(UNINSTALL)
    assert "if (-not $stateInfo.exists -and $verdict.Verdict -eq 'compatible')" in uninstall
    for gate in ("if ($actions.delete_service)", "if ($actions.revoke_logon_right)", "foreach ($grant in @($actions.acl_grants))"):
        assert gate in uninstall, gate
    assert "Remove-MYCBrokerState" in uninstall[uninstall.index("if ($actions.revoke_logon_right)"):]


def _valid_state():
    state = bd.apply_state_update(bd.new_state(REPO_ROOT), service_sid=SERVICE_SID, service="pending")
    return bd.apply_state_update(state, logon_right="pending")


@pytest.mark.parametrize("mutate,error", [
    (lambda s: "{not json", "state_corrupt"),
    (lambda s: {**s, "schema": 1}, "state_incompatible"),
    (lambda s: {**s, "schema": 2}, "state_incompatible"),  # boolean service ownership (previous draft)
    (lambda s: {**s, "service_id": "OtherService"}, "state_incompatible"),
    (lambda s: {**s, "service_account": "LocalSystem"}, "state_incompatible"),
    (lambda s: {**s, "repo_root": r"C:\other\repo"}, "state_incompatible"),
    (lambda s: {**s, "extra": 1}, "state_corrupt"),
    (lambda s: {**s, "service_sid": "S-1-5-18"}, "state_corrupt"),
    (lambda s: {**s, "service_sid": None}, "state_corrupt"),  # pending logon right without SID
    (lambda s: {**s, "owned": {**s["owned"], "logon_right": "maybe"}}, "state_corrupt"),
    (lambda s: {**s, "owned": {**s["owned"], "service": "yes"}}, "state_corrupt"),
    (lambda s: {**s, "owned": {**s["owned"], "service": True}}, "state_corrupt"),
    (lambda s: {**s, "owned": {**s["owned"], "acl_grants": [{"path": SERVICE_DIR, "grant": "*S-1-5-80-9-9-9-9-9:(RX)"}]}}, "state_corrupt"),
    (lambda s: {**s, "owned": {**s["owned"], "acl_grants": [{"path": SERVICE_DIR, "grant": f"*{SERVICE_SID}:(F)"}]}}, "state_corrupt"),
    (lambda s: [s], "state_corrupt"),
])
def test_corrupt_or_incompatible_state_fails_closed_everywhere(tmp_path, capsys, mutate, error):
    _journal_dir(tmp_path)
    data = mutate(_valid_state())
    _ledger(tmp_path).write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    before = _ledger(tmp_path).read_bytes()
    for command, extra in (("state-show", ()), ("state-begin", ()), ("state-update", ("--service", "pending")), ("state-delete", ())):
        code, _out, result = _state_cmd(tmp_path, capsys, command, *extra)
        assert code == 3 and result == {"error": error}, command
    assert _ledger(tmp_path).read_bytes() == before  # never "repaired" or overwritten


@pytest.mark.parametrize("changes,error", [
    ({"logon_right": "added"}, "state_logon_transition_invalid"),   # none -> added skips the evidence step
    ({"service_sid": "S-1-5-80-9-9-9-9-9"}, "state_sid_mismatch"),
    ({"service": "owned"}, "state_service_transition_invalid"),  # none -> owned skips the SCM re-query
])
def test_invalid_ledger_transitions_are_refused(changes, error):
    state = bd.apply_state_update(bd.new_state(REPO_ROOT), service_sid=SERVICE_SID)
    with pytest.raises(bd.PolicyError) as raised:
        bd.apply_state_update(state, **changes)
    assert raised.value.code == error
    with pytest.raises(bd.PolicyError) as raised:
        bd.apply_state_update(bd.new_state(REPO_ROOT), logon_right="pending")
    assert raised.value.code == "state_sid_missing"


def test_state_write_is_atomic(tmp_path, capsys, monkeypatch):
    _state_cmd(tmp_path, capsys, "state-begin")
    before = _ledger(tmp_path).read_bytes()

    def failing_replace(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(bd.os, "replace", failing_replace)
    with pytest.raises(OSError):
        bd.save_state(_ledger(tmp_path), bd.apply_state_update(json.loads(before), service="pending"), REPO_ROOT)
    assert _ledger(tmp_path).read_bytes() == before
    assert [p.name for p in _ledger(tmp_path).parent.iterdir()] == ["install-state.json"]


def test_logon_right_ownership_is_persisted_around_secedit():
    module = _ps(MODULE)
    body = module[module.index("function Set-MYCServiceLogonRight"):]
    body = body[: body.index("\nfunction ")]
    unchanged = body.index("if (-not $result.inf_written -and -not $lastMember)")
    pending = body.index("'--logon-right', 'pending'")
    configure = body.index("'/configure'")
    verified = body.index("if ($expected -notcontains [string]$check.status)")
    final = body.index("Update-MYCBrokerState -Layout $Layout -Arguments @('--logon-right', $final)")
    assert unchanged < pending < configure < verified < final
    early = body[unchanged: body.index("}", body.index("return [string]$result.status"))]
    assert "'pending'" not in early and "'added'" not in early  # an already-effective right is never recorded as owned
    for path in (*POWERSHELL_FILES, TOOL_PATH):
        assert "logon_right_added" not in path.read_bytes().decode("utf-8-sig")


# =============================================================================================
# Audit fix P1 -- DEV-1C only re-ACLs directories it owns
# =============================================================================================

DEPLOYMENT_ROOT = r"C:\MYC\Deployment"


def test_directory_plan_owns_only_developer_broker_children(tmp_path, capsys):
    plan = bd.directory_plan(DEPLOYMENT_ROOT, r"C:\MYC\Services", r"C:\MYC\Logs")
    assert plan["owned"] == [
        r"C:\MYC\Deployment\developer-broker", r"C:\MYC\Deployment\developer-broker\acl-backups",
        r"C:\MYC\Services\developer-broker", r"C:\MYC\Logs\developer-broker",
    ]
    assert plan["inspect_only"] == [DEPLOYMENT_ROOT, r"C:\MYC\Logs"]
    assert plan["global_hardening"] == [r"C:\MYC\Services"]
    for outside in (DEPLOYMENT_ROOT, DEPLOYMENT_ROOT + "\\", r"C:\MYC\Deployment\another-component",
                    r"C:\MYC\Deployment\another-component\data", r"C:\MYC\Logs", r"C:\MYC\Logs\backend", r"C:\MYC\Services"):
        assert not bd.is_owned_directory(outside, plan), outside
    assert bd.is_owned_directory(r"c:\myc\deployment\DEVELOPER-BROKER\\", plan)
    code, _out, result = _run(["directory-plan", "--deployment-root", DEPLOYMENT_ROOT, "--services-root", r"C:\MYC\Services", "--logs-root", r"C:\MYC\Logs"], capsys)
    assert code == 0 and result == plan


def test_protection_is_refused_outside_the_ownership_plan():
    module = _ps(MODULE)
    body = module[module.index("function New-MYCProtectedDirectory"):]
    body = body[: body.index("\nfunction ")]
    guard = body.index("if ($owned -notcontains $Path.TrimEnd('\\'))")
    assert guard < body.index("New-Item") and guard < body.index("Set-MYCProtectedAcl")
    assert "Get-MYCOwnedDirectories -Layout $Layout" in body


def test_deployment_root_and_siblings_are_never_in_a_mutation_call():
    code = {path.name: _ps_code(path) for path in POWERSHELL_FILES}
    for name, text in code.items():
        for call in re.findall(r"New-MYCProtectedDirectory[^\n]*", text):
            if call.startswith("New-MYCProtectedDirectory {"):
                continue
            target = re.search(r"-Path (\S+)", call).group(1)
            assert target in ("$Layout.StateDir", "$Layout.AclBackupDir", "$layout.ServiceDir", "$layout.LogDir"), (name, call)
        for call in re.findall(r"Set-MYCProtectedAcl -Path (\S+)", text):
            assert call in ("$Path", "$grant.path", "$Layout.ServicesRoot"), (name, call)
        for call in re.findall(r"icacls[^\n]*DeploymentRoot|DeploymentRoot[^\n]*'/(reset|inheritance|setowner|grant)", text):
            raise AssertionError((name, call))
    install_code = code["Install-MYCDeveloperBroker.ps1"]
    assert "if ($isOwnedDir) {" in install_code  # $grant.path is re-protected ONLY when it is one of DEV-1C's own dirs
    assert install_code.index("if ($isOwnedDir) {") < install_code.index("Set-MYCProtectedAcl -Path $grant.path")
    init = code["MYCDeveloperBroker.psm1"]
    init = init[init.index("function Initialize-MYCStateDirectory"):]
    init = init[: init.index("\nfunction ")]
    assert "New-Item -ItemType Directory -Path $Layout.DeploymentRoot" in init  # plain creation only
    assert "Assert-MYCSafeParent -Layout $Layout -Path $Layout.DeploymentRoot" in init
    assert "New-MYCProtectedDirectory -Layout $Layout -Path $Layout.StateDir" in init
    assert "$DeploymentRoot" not in code["Set-MYCServicesAcl.ps1"].split("try {", 1)[1]


def test_owned_parent_policy_inspects_without_requiring_ownership():
    base = [("S-1-5-18", FULL, "Allow"), ("S-1-5-32-544", FULL, "Allow")]
    # the default C:\ inheritance (Authenticated Users Modify, CREATOR OWNER template) cannot take over our child
    ok = _snapshot([*base, ("S-1-5-11", MODIFY, "Allow"), ("S-1-5-32-545", RX, "Allow"), ("S-1-3-0", FULL, "Allow")], protected=False)
    assert bd.evaluate_acl(ok, "owned_parent") == []
    assert bd.evaluate_acl(_snapshot([*base, ("S-1-5-11", FULL, "Allow")], protected=False), "owned_parent") == ["child_takeover_rights:S-1-5-11"]
    assert bd.evaluate_acl(_snapshot([*base, ("S-1-5-32-545", RX | bd.WRITE_DAC, "Allow")]), "owned_parent") == ["child_takeover_rights:S-1-5-32-545"]
    assert bd.evaluate_acl(_snapshot([*base, ("S-1-5-11", bd.GENERIC_ALL, "Allow")]), "owned_parent") == ["child_takeover_rights:S-1-5-11"]
    assert bd.evaluate_acl(_snapshot(base, owner="S-1-5-21-1-2-3-1001"), "owned_parent") == ["untrusted_owner"]


# =============================================================================================
# Audit fix P1 -- XML + backend/.env provisioning is both-or-neither
# =============================================================================================

KNOWN_SECRET = "K" * 30 + "-known-secret-" + "k" * 30


def _seed_pair(tmp_path, capsys, monkeypatch):
    """A previously provisioned, consistent pair (old secret) to protect."""
    (tmp_path / ".env").write_text("DATABASE_URL=postgresql://x\n", encoding="utf-8")
    code, _out, _ = _run(_provision_args(tmp_path, "stdin"), capsys, KNOWN_SECRET + "\n", monkeypatch)
    assert code == 0
    return (tmp_path / "MYCDeveloperBroker.xml").read_bytes(), (tmp_path / ".env").read_bytes()


def _assert_clean(tmp_path, *, journal_expected=False):
    assert not list(tmp_path.glob(".*.new")), "staged XML left behind"
    leftovers = sorted(p.name for p in (tmp_path / "state").iterdir() if p.name != "install-state.json")
    assert leftovers == ([bd.JOURNAL_NAME] if journal_expected else []), leftovers


def _provision_new(tmp_path, capsys, monkeypatch):
    new_secret = "N" * 30 + "-new-secret-" + "n" * 30
    code, out, result = _run(_provision_args(tmp_path, "stdin"), capsys, new_secret + "\n", monkeypatch)
    for secret in (KNOWN_SECRET, new_secret):
        assert secret not in out
    return code, result, new_secret


def test_failure_before_the_first_replace_changes_nothing(tmp_path, capsys, monkeypatch):
    old_xml, old_env = _seed_pair(tmp_path, capsys, monkeypatch)
    real = bd._write_private

    def fail_on_journal(path, data):
        if "provision-journal" in str(path):
            raise OSError("no space")
        return real(path, data)

    monkeypatch.setattr(bd, "_write_private", fail_on_journal)
    code, result, _new = _provision_new(tmp_path, capsys, monkeypatch)
    assert code == 3 and result == {"error": "provision_journal_failed"}
    assert (tmp_path / "MYCDeveloperBroker.xml").read_bytes() == old_xml and (tmp_path / ".env").read_bytes() == old_env
    _assert_clean(tmp_path)


def test_failure_of_the_xml_replace_restores_and_cleans_up(tmp_path, capsys, monkeypatch):
    old_xml, old_env = _seed_pair(tmp_path, capsys, monkeypatch)
    real = os.replace
    calls = {"n": 0}

    def fail_first_replace(src, dst):
        if str(dst).endswith("MYCDeveloperBroker.xml"):
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError("sharing violation")
        return real(src, dst)

    monkeypatch.setattr(bd.os, "replace", fail_first_replace)
    code, result, _new = _provision_new(tmp_path, capsys, monkeypatch)
    assert code == 3 and result == {"error": "provision_commit_failed"}
    assert (tmp_path / "MYCDeveloperBroker.xml").read_bytes() == old_xml and (tmp_path / ".env").read_bytes() == old_env
    _assert_clean(tmp_path)


def test_failure_after_the_xml_before_the_env_restores_the_xml(tmp_path, capsys, monkeypatch):
    old_xml, old_env = _seed_pair(tmp_path, capsys, monkeypatch)
    real = bd._rewrite_in_place
    calls = {"n": 0}

    def fail_first_env_write(path, data):
        calls["n"] += 1
        if calls["n"] == 1:
            raise PermissionError("locked")
        return real(path, data)

    monkeypatch.setattr(bd, "_rewrite_in_place", fail_first_env_write)
    code, result, _new = _provision_new(tmp_path, capsys, monkeypatch)
    assert code == 3 and result == {"error": "provision_commit_failed"}
    assert (tmp_path / "MYCDeveloperBroker.xml").read_bytes() == old_xml  # new XML rolled back
    assert (tmp_path / ".env").read_bytes() == old_env
    _assert_clean(tmp_path)


def test_failure_in_the_middle_of_the_env_write_restores_both(tmp_path, capsys, monkeypatch):
    old_xml, old_env = _seed_pair(tmp_path, capsys, monkeypatch)
    real = bd._rewrite_in_place
    calls = {"n": 0}

    def torn_env_write(path, data):
        calls["n"] += 1
        if calls["n"] == 1:
            with open(path, "r+b") as handle:  # half of the new content, then failure
                handle.write(data[: len(data) // 2])
                handle.truncate()
            raise OSError("I/O error")
        return real(path, data)

    monkeypatch.setattr(bd, "_rewrite_in_place", torn_env_write)
    code, result, _new = _provision_new(tmp_path, capsys, monkeypatch)
    assert code == 3 and result == {"error": "provision_commit_failed"}
    assert (tmp_path / "MYCDeveloperBroker.xml").read_bytes() == old_xml
    assert (tmp_path / ".env").read_bytes() == old_env
    _assert_clean(tmp_path)


def test_failed_restore_fails_closed_keeps_the_journal_and_the_next_run_recovers(tmp_path, capsys, monkeypatch):
    old_xml, old_env = _seed_pair(tmp_path, capsys, monkeypatch)

    def always_fail(path, data):
        raise OSError("device gone")

    with monkeypatch.context() as patch:
        patch.setattr(bd, "_rewrite_in_place", always_fail)
        code, result, new_secret = _provision_new(tmp_path, capsys, monkeypatch)
    assert code == 3 and result == {"error": "provision_rollback_failed"}
    _assert_clean(tmp_path, journal_expected=True)
    assert KNOWN_SECRET not in (tmp_path / "MYCDeveloperBroker.xml").read_text(encoding="utf-8")  # split state on disk ...
    journal = tmp_path / "state" / bd.JOURNAL_NAME
    if os.name == "posix":
        assert all((p.stat().st_mode & 0o077) == 0 for p in journal.iterdir())  # private journal files
    code, _out, recovered = _run(["provision-recover", "--journal-dir", str(tmp_path / "state"),
                                  "--xml", str(tmp_path / "MYCDeveloperBroker.xml"), "--env-file", str(tmp_path / ".env")], capsys)
    assert code == 0 and recovered == {"recovered": "restored"}  # ... repaired by the next run
    assert (tmp_path / "MYCDeveloperBroker.xml").read_bytes() == old_xml and (tmp_path / ".env").read_bytes() == old_env
    _assert_clean(tmp_path)


def test_crash_after_the_xml_commit_is_recovered_before_reuse(tmp_path, capsys, monkeypatch):
    old_xml, old_env = _seed_pair(tmp_path, capsys, monkeypatch)
    xml, env = tmp_path / "MYCDeveloperBroker.xml", tmp_path / ".env"
    # simulated crash: journal written, XML replaced, process killed before .env
    bd._write_journal(tmp_path / "state", xml, env, old_xml, old_env)
    xml.write_bytes(old_xml.replace(KNOWN_SECRET.encode(), b"Z" * 64))
    assert _run(_provision_args(tmp_path, "reuse"), capsys)[2]["recovered"] == "restored"
    assert xml.read_bytes() == old_xml and env.read_bytes() == old_env  # reuse used the restored, consistent pair
    _assert_clean(tmp_path)


def test_crash_during_cleanup_never_reverts_a_finished_commit(tmp_path, capsys, monkeypatch):
    old_xml, old_env = _seed_pair(tmp_path, capsys, monkeypatch)
    xml, env = tmp_path / "MYCDeveloperBroker.xml", tmp_path / ".env"
    bd._write_journal(tmp_path / "state", xml, env, b"<old/>", b"OLD=1\n")
    bd._write_private(tmp_path / "state" / bd.JOURNAL_NAME / "committed", b"")
    assert bd.recover_provision(tmp_path / "state", xml, env) == "committed"
    assert xml.read_bytes() == old_xml and env.read_bytes() == old_env
    _assert_clean(tmp_path)


def test_a_journal_for_other_files_is_refused(tmp_path, capsys, monkeypatch):
    old_xml, old_env = _seed_pair(tmp_path, capsys, monkeypatch)
    bd._write_journal(tmp_path / "state", tmp_path / "other.xml", tmp_path / ".env", old_xml, old_env)
    code, _out, result = _run(_provision_args(tmp_path, "generate"), capsys)
    assert code == 3 and result == {"error": "provision_journal_foreign"}
    assert (tmp_path / "MYCDeveloperBroker.xml").read_bytes() == old_xml


def test_first_provision_failure_removes_the_new_xml(tmp_path, capsys, monkeypatch):
    original = b"A=1\n"
    (tmp_path / ".env").write_bytes(original)
    real = bd._rewrite_in_place
    calls = {"n": 0}

    def fail_first(path, data):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("locked")
        return real(path, data)

    monkeypatch.setattr(bd, "_rewrite_in_place", fail_first)
    code, out, result = _run(_provision_args(tmp_path, "stdin"), capsys, KNOWN_SECRET + "\n", monkeypatch)
    assert code == 3 and result == {"error": "provision_commit_failed"} and KNOWN_SECRET not in out
    assert not (tmp_path / "MYCDeveloperBroker.xml").exists()  # no orphan XML carrying the new secret
    assert (tmp_path / ".env").read_bytes() == original
    _assert_clean(tmp_path)


def test_provision_errors_never_carry_the_secret(tmp_path, capsys, monkeypatch):
    _seed_pair(tmp_path, capsys, monkeypatch)
    monkeypatch.setattr(bd, "_rewrite_in_place", lambda path, data: (_ for _ in ()).throw(OSError(data.decode("utf-8"))))
    with pytest.raises(bd.PolicyError) as raised:
        bd.provision_files(tmp_path / "state", tmp_path / "MYCDeveloperBroker.xml", tmp_path / ".env", "<service/>", "S=" + KNOWN_SECRET)
    assert KNOWN_SECRET not in str(raised.value) and raised.value.__cause__ is None and raised.value.__suppress_context__
    assert "--journal-dir', $layout.StateDir" in _ps(INSTALL)


# =============================================================================================
# Audit v2 -- P1: pre-existing Broker ACEs on paths DEV-1C does not own
# =============================================================================================

EXTERNAL_PATH = REPO_ROOT + r"\venv"
EXTERNAL_GRANT = {"path": EXTERNAL_PATH, "icacls_grant": f"*{SERVICE_SID}:(OI)(CI)(RX)"}


def _acl_with(*aces, rights=RX, flags=(3, 0)):
    return {"owner_sid": "S-1-5-32-544", "protected": False, "aces": [
        {"sid": sid, "rights": rights, "type": kind, "inherited": inherited,
         "inheritance_flags": flags[0], "propagation_flags": flags[1]} for sid, kind, inherited in aces]}


def test_external_grant_without_a_broker_ace_is_applied():
    snapshot = _acl_with(("S-1-5-18", "Allow", False), ("S-1-5-21-1-2-3-1001", "Allow", False))
    assert bd.external_grant_decision(snapshot, EXTERNAL_GRANT, None) == "apply"
    # inherited Broker ACEs only come from DEV-1C's own tree grants
    assert bd.external_grant_decision(_acl_with((SERVICE_SID, "Allow", True)), EXTERNAL_GRANT, None) == "apply"


@pytest.mark.parametrize("kind", ["Allow", "Deny"])
def test_preexisting_explicit_broker_ace_fails_closed_on_first_install(kind):
    snapshot = _acl_with((SERVICE_SID, kind, False))
    for state in (None, bd.apply_state_update(bd.new_state(REPO_ROOT), service_sid=SERVICE_SID)):
        with pytest.raises(bd.PolicyError) as raised:
            bd.external_grant_decision(snapshot, EXTERNAL_GRANT, state)
        assert raised.value.code == "preexisting_broker_ace"


def test_explicit_broker_ace_is_accepted_on_reinstall_only_when_the_ledger_owns_it():
    state = _owned_venv_state()
    snapshot = _acl_with((SERVICE_SID, "Allow", False))
    assert bd.external_grant_decision(snapshot, EXTERNAL_GRANT, state) == "reapply_owned"
    other = {"path": REPO_ROOT + r"\backend", "icacls_grant": f"*{SERVICE_SID}:(RX)"}
    with pytest.raises(bd.PolicyError):
        bd.external_grant_decision(snapshot, other, state)  # ledger owns the venv grant, not this one


def test_external_grant_check_command(tmp_path, capsys):
    _state_cmd(tmp_path, capsys, "state-begin")
    snapshot = tmp_path / "acl.json"
    snapshot.write_text(json.dumps(_acl_with((SERVICE_SID, "Allow", False))), encoding="utf-8")
    argv = ["external-grant-check", "--snapshot", str(snapshot), "--path", EXTERNAL_PATH,
            "--grant", EXTERNAL_GRANT["icacls_grant"], "--file", str(_ledger(tmp_path)), "--repo-root", REPO_ROOT]
    code, _out, result = _run(argv, capsys)
    assert code == 3 and result == {"error": "preexisting_broker_ace"}


# =============================================================================================
# Audit v2 -- P1: the catch never leaves (or hides) DEVELOPER_BROKER_ENABLED=true
# =============================================================================================

def test_catch_reverts_the_backend_it_enabled_before_touching_the_broker():
    install = _ps(INSTALL)
    assert "$backendEnabledByThisRun = $false" in install[: install.index("try {\n    # 0.")]
    enable_call = "Invoke-MYCDeployTool -Layout $layout -Arguments @('set-backend-enabled', '--env-file', $layout.EnvFile, '--enabled', 'true')"
    flag = install.index("$backendEnabledByThisRun = $true")
    assert flag < install.index(enable_call) and install.count("$backendEnabledByThisRun = $true") == 1
    catch = install[install.index("} catch {\n    $message"):]
    catch = catch[: catch.index("\n}\n") + 3]
    revert = catch.index("if ($backendEnabledByThisRun)")
    assert revert < catch.index("Stop-MYCBrokerService")
    assert "'--enabled', 'false'" in catch and "'inspect-env'" in catch  # reverted AND verified
    assert "puede seguir con DEVELOPER_BROKER_ENABLED=true" in catch
    # the reassuring message is only the default when this run never enabled the backend
    default = "$backendNote = 'El backend NO fue habilitado por este intento.'"
    assert catch.count("NO fue habilitado") == 1 and default in catch and catch.index(default) < revert
    assert "Write-MYCFailure (" in catch and "$backendNote" in catch[catch.index("Write-MYCFailure ("):]


def test_enable_then_revert_leaves_the_env_disabled_and_otherwise_identical(tmp_path, capsys, monkeypatch):
    old_xml, _old_env = _seed_pair(tmp_path, capsys, monkeypatch)
    env = str(tmp_path / ".env")
    _run(["set-backend-enabled", "--env-file", env, "--enabled", "true"], capsys)
    before_revert = bd.split_env_block((tmp_path / ".env").read_text(encoding="utf-8"))[1]
    assert _run(["inspect-env", "--env-file", env], capsys)[2]["backend_enabled"] is True
    # ... a later step fails; the catch reverts:
    _run(["set-backend-enabled", "--env-file", env, "--enabled", "false"], capsys)
    code, out, state = _run(["inspect-env", "--env-file", env], capsys)
    assert code == 0 and state == {"backend_enabled": False, "managed_block": True, "secret_present": True}
    after = bd.split_env_block((tmp_path / ".env").read_text(encoding="utf-8"))[1]
    assert {**before_revert, "DEVELOPER_BROKER_ENABLED": "false"} == after
    assert KNOWN_SECRET not in out and (tmp_path / "MYCDeveloperBroker.xml").read_bytes() == old_xml


# =============================================================================================
# Audit v2 -- P1: no reparse point / junction under recursive operations
# =============================================================================================

def _function(name):
    module = _ps(MODULE)
    body = module[module.index(f"function {name} {{"):]
    return body[: body.index("\nfunction ")]


# =============================================================================================
# Audit v2 -- P1: SCM ownership race (none -> pending -> owned)
# =============================================================================================

@pytest.mark.parametrize("exit_code,verdict,expected", [
    (0, "compatible", {"service": "owned", "ok": True, "reason": "created"}),
    (1073, "absent", {"service": "none", "ok": False, "reason": "create_failed_service_absent"}),
    (5, "absent", {"service": "none", "ok": False, "reason": "create_failed_service_absent"}),
    (1073, "compatible", {"service": "pending", "ok": False, "reason": "create_failed_but_service_present"}),
    (0, "incompatible", {"service": "pending", "ok": False, "reason": "service_mismatch_after_create"}),
    (1073, "incompatible", {"service": "pending", "ok": False, "reason": "service_mismatch_after_create"}),
    (0, "absent", {"service": "pending", "ok": False, "reason": "created_but_not_visible"}),
])
def test_service_create_outcome(capsys, exit_code, verdict, expected):
    assert bd.service_create_outcome(exit_code, verdict) == expected
    code, _out, result = _run(["service-create-outcome", "--exit-code", str(exit_code), "--verdict", verdict], capsys)
    assert code == 0 and result == expected


@pytest.mark.parametrize("current,target,allowed", [
    ("none", "pending", True), ("none", "owned", False), ("pending", "owned", True), ("pending", "none", True),
    ("owned", "none", True), ("owned", "pending", False), ("owned", "owned", True),
])
def test_service_ownership_transitions(current, target, allowed):
    state = bd.new_state(REPO_ROOT)
    path = {"none": [], "pending": ["pending"], "owned": ["pending", "owned"]}[current]
    for step in path:
        state = bd.apply_state_update(state, service=step)
    if allowed:
        assert bd.apply_state_update(state, service=target)["owned"]["service"] == target
    else:
        with pytest.raises(bd.PolicyError):
            bd.apply_state_update(state, service=target)


def test_pending_service_is_rolled_back_only_after_an_exact_scm_match():
    pending = bd.apply_state_update(bd.new_state(REPO_ROOT), service="pending")
    assert bd.rollback_actions(pending)["service_ownership"] == "pending"
    install = _ps(INSTALL)
    seq = [install.index(marker) for marker in (
        "@('--service', 'pending')",
        "$create = Invoke-MYCNativeResult -FilePath $sc -ArgumentList @('create'",
        "$afterCreate = Get-MYCBrokerServiceVerdict -Layout $layout",
        "'service-create-outcome'",
        "if ($outcome.service -ne 'pending')",
        "if (-not $outcome.ok)",
    )]
    assert seq == sorted(seq)
    uninstall = _ps(UNINSTALL)
    assert uninstall.index("if ($verdict.Verdict -eq 'incompatible')") < uninstall.index("if ($actions.delete_service)")
    block = uninstall[uninstall.index("if ($actions.delete_service)"):]
    assert block.index("Stop-MYCBrokerService -Layout $layout") < block.index("Invoke-MYCGuardedScm -Layout $layout -Arguments @('delete', $ServiceId)")
    verdict = bd.service_verdict({"exists": True, "start_name": "LocalSystem", "path_name": WRAPPER, "service_type": "Own Process"}, WRAPPER)
    assert verdict["verdict"] == "incompatible"  # a pending record never authorises deleting a mismatching service


# =============================================================================================
# Audit v2 -- P2: explicit exit codes; secedit temporaries always removed
# =============================================================================================

def test_exit_codes_never_come_from_global_state():
    for path in POWERSHELL_FILES:
        code = _ps_code(path)
        for match in re.finditer(r"\$LASTEXITCODE", code):
            owner = code[: match.start()].rsplit("function ", 1)[-1].split(" ", 1)[0]
            assert path == MODULE and owner in ("Invoke-MYCNativeResult", "Invoke-MYCDeployTool"), (path.name, owner)
    assert "$pywin32 = Invoke-MYCNativeResult" in _ps(INSTALL) and "($pywin32.ExitCode -eq 0)" in _ps(INSTALL)
    native = _function("Invoke-MYCNative")
    assert "Invoke-MYCNativeResult -FilePath $FilePath" in native and "$result.ExitCode" in native


def test_secedit_temporaries_are_removed_in_finally():
    body = _function("Set-MYCServiceLogonRight")
    finally_block = body[body.index("} finally {"):]
    assert "foreach ($temporary in @($export, $inf, $db, $log, $verify, $unused))" in finally_block
    assert "Remove-Item -LiteralPath $temporary" in finally_block
    work = body[body.index("    try {"): body.index("} finally {")]
    for call in ("'/export'", "'/configure'", "'logon-right'"):
        assert call in work
    assert "secedit-before" in body and "$verify = Join-Path" in body[: body.index("    try {")]


# =============================================================================================
# Audit v3 -- P1: a compatible service continues as reinstall ONLY if the ledger says "owned"
# =============================================================================================

def _ledger_with_service(ownership):
    state = bd.new_state(REPO_ROOT)
    for step in {"none": [], "pending": ["pending"], "owned": ["pending", "owned"]}[ownership]:
        state = bd.apply_state_update(state, service=step)
    return state


@pytest.mark.parametrize("verdict,ownership,expected", [
    ("absent", None, "create"),
    ("absent", "none", "create"),
    ("absent", "pending", "service_ledger_reconciliation_required"),
    ("absent", "owned", "service_ledger_reconciliation_required"),
    ("compatible", None, "service_not_proven_owned"),
    ("compatible", "none", "service_not_proven_owned"),   # ledger exists, service appeared later: NOT ours
    ("compatible", "pending", "service_partial_install_reconcile_first"),
    ("compatible", "owned", "reconfigure"),
    ("incompatible", "owned", "service_incompatible"),
])
def test_service_install_decision(verdict, ownership, expected):
    state = None if ownership is None else _ledger_with_service(ownership)
    if expected in ("create", "reconfigure"):
        assert bd.service_install_decision(verdict, state) == expected
    else:
        with pytest.raises(bd.PolicyError) as raised:
            bd.service_install_decision(verdict, state)
        assert raised.value.code == expected


def test_ledger_without_service_ownership_never_adopts_a_compatible_service(tmp_path, capsys):
    _state_cmd(tmp_path, capsys, "state-begin")  # install failed before sc.exe create: service "none"
    code, _out, result = _run(["service-install-decision", "--verdict", "compatible",
                               "--file", str(_ledger(tmp_path)), "--repo-root", REPO_ROOT], capsys)
    assert code == 3 and result == {"error": "service_not_proven_owned"}
    install = _ps(INSTALL)
    assert "'broker_service_owned'" in install and "'service-install-decision', '--verdict', $verdict.Verdict" in install
    assert "$owned = ($null -ne $stateInfo) -and $stateInfo.exists" not in install
    body = install[install.index("try {\n    # 0."):]
    decision = body.index("$serviceAction = (Invoke-MYCDeployTool -Layout $layout -Arguments @('service-install-decision'")
    assert decision < body.index("if ($serviceAction -eq 'reconfigure')") < body.index("if ($serviceAction -eq 'create')")
    assert "if ($verdict.Verdict -eq 'absent') {" not in body and "if ($verdict.Verdict -eq 'compatible') {" not in body


# =============================================================================================
# Audit v3 -- P1: SeServiceLogonRight rollback when the Broker is the only member
# =============================================================================================

def test_rollback_restores_an_originally_unassigned_right(tmp_path, capsys):
    # original: right unassigned -> DEV-1C adds the Broker as the only member
    assert _install_until_logon_right(tmp_path, capsys, []) == "grant_required"
    added = f"[Privilege Rights]\nSeServiceLogonRight = *{SERVICE_SID}\n"
    assert bd.logon_right_change(added, SERVICE_SID, "revoke") == ("revoke_last_member", None)
    export = _export(tmp_path, [f"SeServiceLogonRight = *{SERVICE_SID}"])
    code, _out, result = _run(["logon-right", "--export", str(export), "--sid", SERVICE_SID,
                               "--out", str(tmp_path / "r.inf"), "--action", "revoke"], capsys)
    assert code == 0 and result == {"inf_written": False, "status": "revoke_last_member"}
    # after the LSA removal the verified re-export shows the original state
    assert bd.logon_right_change("[Privilege Rights]\n", SERVICE_SID, "revoke") == ("not_present", None)


def test_last_member_revoke_uses_lsa_for_exactly_this_sid_and_is_verified():
    body = _function("Set-MYCServiceLogonRight")
    last = body.index("$lastMember = ($Action -eq 'revoke') -and ([string]$result.status -eq 'revoke_last_member')")
    assert last < body.index("if (-not $result.inf_written -and -not $lastMember)")
    assert body.index("Remove-MYCAccountRightViaLsa -Sid $ServiceSid") < body.index("if ($expected -notcontains [string]$check.status)")
    lsa = _ps(MODULE)
    source = lsa[lsa.index("$script:LsaSource = @'"): lsa.index("'@", lsa.index("$script:LsaSource = @'"))]
    assert "LsaRemoveAccountRights(policy, sidBytes, false, rights, 1)" in source  # allRights=false, one right
    assert "LsaAddAccountRights" not in source and "LsaEnumerate" not in source
    remove = _function("Remove-MYCAccountRightViaLsa")
    assert "RemoveAccountRight($Sid, 'SeServiceLogonRight')" in remove
    assert remove.index("$script:VirtualAccountSidPattern") < remove.index("Add-Type")
    assert "if ($code -ne 0 -and $code -ne 2) { throw" in remove


# =============================================================================================
# Audit v3 -- P1: uninstall never orphans retained DEV-1C directories
# =============================================================================================

# =============================================================================================
# Audit v3 -- P1: reinstall only accepts the EXACT owned ACE and normalizes with /grant:r
# =============================================================================================

def _owned_venv_state(status="owned"):
    state = bd.apply_state_update(bd.new_state(REPO_ROOT), service_sid=SERVICE_SID, grant_path=EXTERNAL_PATH,
                                  grant_value=EXTERNAL_GRANT["icacls_grant"], grant_status="pending")
    return state if status == "pending" else bd.apply_state_update(state, grant_path=EXTERNAL_PATH,
                                                                  grant_value=EXTERNAL_GRANT["icacls_grant"], grant_status="owned")


@pytest.mark.parametrize("snapshot", [
    _acl_with((SERVICE_SID, "Allow", False), rights=FULL),                          # widened to Full Control
    _acl_with((SERVICE_SID, "Allow", False), rights=MODIFY),
    _acl_with((SERVICE_SID, "Allow", False), flags=(0, 0)),                         # scope changed to folder only
    _acl_with((SERVICE_SID, "Allow", False), flags=(3, 2)),                         # inherit-only
    _acl_with((SERVICE_SID, "Allow", False), (SERVICE_SID, "Deny", False)),          # unexpected Deny added
    _acl_with((SERVICE_SID, "Allow", False), (SERVICE_SID, "Allow", False)),         # a second explicit ACE
])
def test_drifted_owned_ace_is_refused_on_reinstall(snapshot):
    with pytest.raises(bd.PolicyError) as raised:
        bd.external_grant_decision(snapshot, EXTERNAL_GRANT, _owned_venv_state())
    assert raised.value.code == "broker_ace_drifted"


def test_exact_owned_ace_is_accepted_and_scopes_map_to_flags():
    assert bd.external_grant_decision(_acl_with((SERVICE_SID, "Allow", False)), EXTERNAL_GRANT, _owned_venv_state()) == "reapply_owned"
    for grant, flags in ((f"*{SERVICE_SID}:(OI)(CI)(RX)", (3, 0)), (f"*{SERVICE_SID}:(OI)(NP)(RX)", (2, 1)), (f"*{SERVICE_SID}:(RX)", (0, 0))):
        assert bd.grant_matches(_acl_with((SERVICE_SID, "Allow", False), flags=flags), {"path": EXTERNAL_PATH, "grant": grant})
        assert not bd.grant_matches(_acl_with((SERVICE_SID, "Allow", False), flags=(1, 0)), {"path": EXTERNAL_PATH, "grant": grant})


def test_grant_is_replaced_and_reverified(tmp_path, capsys):
    snapshot = tmp_path / "acl.json"
    snapshot.write_text(json.dumps(_acl_with((SERVICE_SID, "Allow", False), rights=FULL)), encoding="utf-8")
    code, _out, result = _run(["external-grant-verify", "--snapshot", str(snapshot), "--path", EXTERNAL_PATH,
                               "--grant", EXTERNAL_GRANT["icacls_grant"]], capsys)
    assert code == 3 and result == {"error": "broker_ace_not_normalized"}
    grant = _function("Grant-MYCBrokerAcl")
    assert grant.index("'/grant:r', $Grant.icacls_grant") < grant.index("'external-grant-verify'")
    assert "'/grant', $Grant" not in grant
    snapshot_fn = _function("Get-MYCAclSnapshot")
    assert "inheritance_flags = [int]$rule.InheritanceFlags" in snapshot_fn
    assert "propagation_flags = [int]$rule.PropagationFlags" in snapshot_fn


# =============================================================================================
# Audit v3 -- P1 operational: backend restart is an activation step with a controlled outcome
# =============================================================================================

@pytest.mark.parametrize("path,success_marker", [(INSTALL, "'--backend-activation', 'restarted'"), (UNINSTALL, None)])
def test_backend_restart_is_contained_and_reports_activation(path, success_marker):
    text = _ps(path)
    restart = text[text.index("if ($RestartBackend"):]
    assert restart.index("try {") < restart.index("Restart-Service -Name $BackendServiceName -ErrorAction Stop") < restart.index("} catch {")
    assert "exit 3" in restart and "Wait-MYCServiceState -Name $BackendServiceName -State 'Running'" in restart
    assert text.count("Restart-Service") == 1
    if success_marker:
        assert "'--backend-activation', 'restart_failed'" in restart and success_marker in restart
        assert "INSTALADO y validado. Activación: FALLÓ" in restart
        assert "'--backend-activation', 'pending_restart'" in text[: text.index("if ($RestartBackend")]
    else:
        assert "COMPLETADA. Activación: FALLÓ" in restart


def test_backend_activation_is_part_of_the_validated_ledger():
    state = bd.apply_state_update(bd.new_state(REPO_ROOT), backend_activation="restart_failed")
    assert state["backend_activation"] == "restart_failed"
    with pytest.raises(bd.PolicyError):
        bd.apply_state_update(state, backend_activation="maybe")
    with pytest.raises(bd.PolicyError):
        bd.validate_state({**state, "backend_activation": "unknown"}, REPO_ROOT)


# =============================================================================================
# Audit v3 -- P0 operational: WinSW integrity is proven by a trusted hash, not by metadata
# =============================================================================================

WINSW_HASH = "A" * 64
CONFIG_HASH = "B" * 64


@pytest.mark.parametrize("args,violations", [
    ((WINSW_HASH, WINSW_HASH), []),
    ((WINSW_HASH.lower(), WINSW_HASH), []),
    ((WINSW_HASH, None), ["winsw_expected_sha256_missing"]),
    ((WINSW_HASH, "C" * 64), ["winsw_sha256_mismatch"]),
    ((WINSW_HASH, "xyz"), ["winsw_expected_sha256_invalid"]),
    ((WINSW_HASH, WINSW_HASH, CONFIG_HASH, None), ["winsw_config_unverified"]),
    ((WINSW_HASH, WINSW_HASH, CONFIG_HASH, "D" * 64), ["winsw_config_sha256_mismatch"]),
    ((WINSW_HASH, WINSW_HASH, CONFIG_HASH, CONFIG_HASH), []),
])
def test_winsw_integrity(args, violations):
    assert bd.winsw_integrity(*args) == violations


def test_installer_requires_the_trusted_winsw_hash_before_and_after_copying(capsys):
    code, _out, result = _run(["winsw-integrity", "--actual-sha256", WINSW_HASH], capsys)
    assert code == 3 and result == {"error": "winsw_expected_sha256_missing"}
    install = _ps(INSTALL)
    assert "[string]$WinSWExpectedSha256," in install and "[string]$WinSWConfigExpectedSha256," in install
    assert "& $add 'winsw_integrity' (& $pf $integrityOk)" in install
    body = install[install.index("try {\n    # 0."):]
    before = body.index("Test-MYCWinSWIntegrity -Layout $layout -Source $WinSWSource")
    copy = body.index("Copy-Item -LiteralPath $WinSWSource -Destination $layout.Wrapper")
    after = body.index("Test-MYCWinSWIntegrity -Layout $layout -Source $layout.Wrapper")
    assert before < copy < after < body.index("'create', $ServiceId")
    assert not re.search(r"[0-9A-Fa-f]{64}", _ps_code(INSTALL))  # no hash baked in: it comes from the operator
    integrity = _function("Test-MYCWinSWIntegrity")
    assert "--config-actual-sha256" in integrity and '"$Source.config"' in integrity


# =============================================================================================
# Audit v3 -- P2: no junction-following walks; Deny is a policy violation; accurate secret wording
# =============================================================================================

def test_no_recursive_get_childitem_anywhere():
    for path in POWERSHELL_FILES:
        assert not re.search(r"Get-ChildItem[^\n]*-Recurse", _ps_code(path)), path.name
    tree = _function("Get-MYCServicesTreePaths")
    assert "Get-MYCTreeEntries -Path $Layout.ServicesRoot -Exclude $Layout.ServiceDir" in tree
    services = _function("Test-MYCServicesAcl")
    assert "reparse_point" in services


@pytest.mark.parametrize("policy,sid", [("services_root", None), ("service_dir", SERVICE_SID), ("log_dir", SERVICE_SID)])
def test_explicit_deny_is_a_violation_on_protected_trees(policy, sid):
    base = [("S-1-5-18", FULL, "Allow"), ("S-1-5-32-544", FULL, "Allow")]
    if sid:
        base.append((sid, RX if policy == "service_dir" else MODIFY, "Allow"))
    assert bd.evaluate_acl(_snapshot(base), policy, service_sid=sid) == []
    denied = _snapshot([*base, ("S-1-5-18", bd.DELETE, "Deny")])
    assert "unexpected_deny:S-1-5-18" in bd.evaluate_acl(denied, policy, service_sid=sid)
    inherited = _snapshot(base)
    inherited["aces"].append({"sid": "S-1-5-11", "rights": FULL, "type": "Deny", "inherited": True})
    assert bd.evaluate_acl(inherited, policy, service_sid=sid) == []  # only explicit Deny ACEs are flagged
    # a Deny can only restrict a secret file: not a violation there
    assert bd.evaluate_acl(_snapshot([("S-1-5-32-545", RX, "Deny")]), "secret_file") == []


def test_secret_handling_is_documented_accurately():
    module = _ps(MODULE)
    assert "PowerShell only ever holds it as a SecureString" not in module
    assert "It is NOT only ever a SecureString" in module and "plain .NET string" in module
    assert "transiently as a plain .NET string" in _ps(INSTALL)
    doc = (REPO / "docs/architecture/MOBILE_DEVELOPER_BROKER.md").read_text(encoding="utf-8")
    assert "texto plano transitorio" in doc


# =============================================================================================
# Audit v4 -- P1: fresh SCM query + ledger SID immediately before any service mutation
# =============================================================================================

# =============================================================================================
# Audit v4 -- P1: uninstall without a ledger modifies nothing (not even backend\.env)
# =============================================================================================

def test_uninstall_without_ledger_is_a_noop_before_touching_backend_env():
    uninstall = _ps(UNINSTALL)
    noop = uninstall.index("if (-not $stateInfo.exists) {")
    exit_ = uninstall.index("exit 0", noop)
    for mutation in ("'provision-recover'", "'remove-backend-block'", "'set-backend-enabled'", "Update-MYCBrokerState",
                     "Stop-MYCBrokerService", "Remove-MYCBrokerGrantExact", "Set-MYCServiceLogonRight", "Remove-MYCOwnedTree"):
        assert exit_ < uninstall.index(mutation), mutation
    # compatible/incompatible services without a ledger were already refused before
    assert uninstall.index("if (-not $stateInfo.exists -and $verdict.Verdict -eq 'compatible')") < noop
    after = uninstall[exit_:]
    assert "if ($actions.backend_config -ne 'none' -and (Test-Path -LiteralPath $layout.EnvFile" in after  # ledger-gated below


# =============================================================================================
# Audit v4 -- P2: normalization removes explicit Deny ACEs; LSA handle always closed; docs
# =============================================================================================

def test_normalization_removes_explicit_deny_and_unexpected_allow():
    body = _function("Remove-MYCUnexpectedExplicitAces")
    assert "$_.type -eq 'Deny'" in body and "'/remove:d'" in body
    assert "$_.type -eq 'Allow' -and $KeepSids -notcontains $_.sid" in body and "'/remove:g'" in body
    assert "-not $_.inherited" in body
    protected = _function("Set-MYCProtectedAcl")
    assert protected.index("'/inheritance:r'") < protected.index("Remove-MYCUnexpectedExplicitAces")


def test_lsa_policy_handle_is_closed_even_if_allocation_fails():
    module = _ps(MODULE)
    source = module[module.index("$script:LsaSource = @'"): module.index("'@", module.index("$script:LsaSource = @'"))]
    body = source[source.index("public static int RemoveAccountRight"):]
    open_ = body.index("LsaOpenPolicy(")
    try_ = body.index("try", open_)
    alloc = body.index("buffer = Marshal.StringToHGlobalUni(right);")
    assert open_ < try_ < alloc
    assert "IntPtr buffer = Marshal.StringToHGlobalUni" not in body
    assert "if (buffer != IntPtr.Zero) { Marshal.FreeHGlobal(buffer); }" in body
    assert "if (policy != IntPtr.Zero) { LsaClose(policy); }" in body


def test_help_examples_and_docs_match_the_current_contract():
    install = _ps(INSTALL)
    examples = re.findall(r"\.EXAMPLE\n\s+(.+)", install)
    assert examples and all("-WinSWExpectedSha256" in example for example in examples)
    doc = (REPO / "docs/architecture/MOBILE_DEVELOPER_BROKER.md").read_text(encoding="utf-8")
    assert "idempotente con\n`icacls /grant`" not in doc and "`icacls /grant:r`" in doc
    assert "Sin ledger, el uninstall no\nmodifica nada" in doc


def test_stale_destination_config_is_never_kept_unverified():
    install = _ps(INSTALL)
    body = install[install.index("try {\n    # 0."):]
    removal = body.index("Remove-Item -LiteralPath $layout.WrapperConfig -Force")
    assert body.index("Copy-Item -LiteralPath $WinSWSource -Destination $layout.Wrapper") < removal
    assert removal < body.index("Test-MYCWinSWIntegrity -Layout $layout -Source $layout.Wrapper")


# =============================================================================================
# Audit v5 -- one SCM gate before EVERY mutation of the existing service (races reproduced)
# =============================================================================================

OTHER_SID = "S-1-5-80-9999999999-8888888888-7777777777-6666666666-555555555"


def _owned_service_state(ownership="owned", sid=SERVICE_SID):
    state = _ledger_with_service(ownership)
    return bd.apply_state_update(state, service_sid=sid) if sid else state


@pytest.mark.parametrize("verdict,lsa,scm,state,expected", [
    ("compatible", SERVICE_SID, SERVICE_SID, "owned", SERVICE_SID),
    ("compatible", SERVICE_SID, SERVICE_SID, "pending_no_sid", SERVICE_SID),     # catch before the SID was recorded
    ("incompatible", SERVICE_SID, SERVICE_SID, "owned", "scm_guard_service_changed"),
    ("absent", None, None, "owned", "scm_guard_service_changed"),
    ("compatible", SERVICE_SID, OTHER_SID, "owned", "scm_guard_sid_unverifiable"),
    ("compatible", None, SERVICE_SID, "owned", "scm_guard_sid_unverifiable"),
    ("compatible", SERVICE_SID, SERVICE_SID, "none", "scm_guard_not_owned"),
    ("compatible", SERVICE_SID, SERVICE_SID, None, "scm_guard_not_owned"),
    ("compatible", OTHER_SID, OTHER_SID, "owned", "scm_guard_sid_mismatch"),
])
def test_scm_guard_decision(verdict, lsa, scm, state, expected):
    ledger = {"owned": _owned_service_state("owned"), "pending_no_sid": _owned_service_state("pending", sid=None),
              "none": bd.new_state(REPO_ROOT), None: None}[state]
    if expected.startswith("scm_guard"):
        with pytest.raises(bd.PolicyError) as raised:
            bd.scm_guard_decision(verdict, lsa, scm, ledger)
        assert raised.value.code == expected
    else:
        assert bd.scm_guard_decision(verdict, lsa, scm, ledger) == expected


class FakeScm:
    """The SCM as the PowerShell guard sees it: each read is fresh."""

    def __init__(self):
        self.verdict, self.lsa, self.scm = "compatible", SERVICE_SID, SERVICE_SID
        self.applied = []

    def read(self):
        return self.verdict, self.lsa, self.scm


def _run_guarded(ops, scm, state, *, between=None):
    """Mirror of Invoke-MYCGuardedScm: for each op, a fresh read + the guard,
    immediately followed by that single op. ``between`` mutates the SCM after
    a given op (the concurrent administrator)."""
    for index, op in enumerate(ops):
        bd.scm_guard_decision(*scm.read(), state)
        scm.applied.append(op)
        if between and index in between:
            between[index](scm)


INSTALL_SCM_SEQUENCE = ["stop", "config demand", "sidtype", "description", "failure", "failureflag", "config auto", "start"]


def test_service_replaced_between_stop_and_config_is_never_reconfigured():
    scm = FakeScm()

    def replaced(fake):
        fake.verdict = "incompatible"  # someone repoints binPath/account after our stop

    with pytest.raises(bd.PolicyError) as raised:
        _run_guarded(INSTALL_SCM_SEQUENCE, scm, _owned_service_state(), between={0: replaced})
    assert raised.value.code == "scm_guard_service_changed"
    assert scm.applied == ["stop"]  # no config/sidtype/.../start reached the replaced service


def test_service_replaced_before_auto_start_is_never_started():
    scm = FakeScm()

    def swapped(fake):
        fake.lsa = fake.scm = OTHER_SID  # recreated under another name-identical account

    with pytest.raises(bd.PolicyError) as raised:
        _run_guarded(INSTALL_SCM_SEQUENCE, scm, _owned_service_state(), between={5: swapped})
    assert raised.value.code == "scm_guard_sid_mismatch"
    assert "config auto" not in scm.applied and "start" not in scm.applied


def test_catch_without_a_known_sid_touches_the_scm_only_with_proof():
    # ledger pending, SID never recorded ($serviceSid = $null in the catch)
    scm = FakeScm()
    _run_guarded(["stop", "config demand"], scm, _owned_service_state("pending", sid=None))
    assert scm.applied == ["stop", "config demand"]
    # same, but the ledger never claimed the service: nothing is touched
    scm = FakeScm()
    with pytest.raises(bd.PolicyError):
        _run_guarded(["stop", "config demand"], scm, bd.new_state(REPO_ROOT))
    assert scm.applied == []


def test_scm_guard_command_reads_the_ledger(tmp_path, capsys):
    _state_cmd(tmp_path, capsys, "state-begin")
    argv = ["scm-guard", "--verdict", "compatible", "--lsa-sid", SERVICE_SID, "--scm-sid", SERVICE_SID,
            "--file", str(_ledger(tmp_path)), "--repo-root", REPO_ROOT]
    code, _out, result = _run(argv, capsys)
    assert code == 3 and result == {"error": "scm_guard_not_owned"}
    _state_cmd(tmp_path, capsys, "state-update", "--service", "pending")
    code, _out, result = _run(argv, capsys)
    assert code == 0 and result == {"sid": SERVICE_SID}


def test_every_sc_mutation_goes_through_the_single_guard():
    guard = _function("Invoke-MYCGuardedScm")
    lines = [line.strip() for line in guard.splitlines() if line.strip() and not line.strip().startswith(("<#", "#"))]
    body = [line for line in lines if not line.startswith(("param(", "function", "}", "description", "family", "service", "here:"))]
    assert_at = next(i for i, line in enumerate(body) if line.startswith("$sid = Assert-MYCBrokerServiceStillOurs"))
    assert body[assert_at + 1].startswith("Invoke-MYCNative -FilePath (Get-MYCSystemTool 'sc.exe') -ArgumentList $Arguments")
    assert "scm-guard" in _function("Assert-MYCBrokerServiceStillOurs")
    # the ONLY direct sc.exe invocations: showsid reads, the guarded call and sc.exe create (a service that does not exist yet)
    for path in POWERSHELL_FILES:
        code = _ps_code(path)
        for match in re.finditer(r"Invoke-MYCNative(Result)? -FilePath (\$sc|\(Get-MYCSystemTool 'sc\.exe'\)) -ArgumentList (\S+)", code):
            target = match.group(3)
            assert target in ("@('showsid',", "$Arguments", "@('create',"), (path.name, match.group(0))
    stop = _function("Stop-MYCBrokerService")
    assert "Invoke-MYCGuardedScm -Layout $Layout -Arguments @('stop', $script:ServiceId)" in stop
    install = _ps(INSTALL)
    for op in ("'sidtype'", "'description'", "'failure'", "'failureflag'", "'start=', 'auto'", "@('start', $ServiceId)", "'start=', 'demand'"):
        for line in [l for l in install.splitlines() if op in l and "Invoke-" in l and "@('create'" not in l]:
            assert "Invoke-MYCGuardedScm" in line, line
    catch = install[install.index("} catch {\n    $message"):]
    assert "if ($serviceSid) {" not in catch and "Stop-MYCBrokerService -Layout $layout" in catch


# =============================================================================================
# Audit v5 -- directories: none -> pending -> owned; pending never authorises deletion
# =============================================================================================

BASE_ACL = [("S-1-5-18", FULL, "Allow"), ("S-1-5-32-544", FULL, "Allow")]


@pytest.mark.parametrize("snapshot,entries,canonical,reparse,expected", [
    (_snapshot(BASE_ACL), [], True, False, []),
    (_snapshot(BASE_ACL), [{"path": "x", "is_reparse": False}], True, False, ["not_empty"]),   # filled in the window
    (_snapshot([*BASE_ACL, ("S-1-5-11", MODIFY, "Allow")]), [], True, False, ["broad_principal:S-1-5-11"]),
    (_snapshot(BASE_ACL, owner="S-1-5-21-1-2-3-1001"), [], True, False, ["untrusted_owner", "owner_not_administrators"]),
    (_snapshot(BASE_ACL, protected=False), [], True, False, ["inheritance_not_disabled"]),
    (_snapshot([*BASE_ACL, ("S-1-5-18", bd.DELETE, "Deny")]), [], True, False, ["unexpected_deny:S-1-5-18"]),
    (_snapshot(BASE_ACL), [], False, True, ["path_not_canonical", "reparse_point"]),
])
def test_directory_creation_proof(snapshot, entries, canonical, reparse, expected):
    assert bd.directory_creation_proof(snapshot, entries, canonical=canonical, root_is_reparse=reparse) == expected


def test_directory_created_by_someone_else_between_pending_and_create_stays_pending(tmp_path, capsys):
    _state_cmd(tmp_path, capsys, "state-begin")
    _state_cmd(tmp_path, capsys, "state-update", "--service-dir", "pending")   # intent recorded
    # ... the other identity creates the directory now; New-Item fails, nothing is promoted ...
    _code, _out, shown = _state_cmd(tmp_path, capsys, "state-show")
    assert shown["state"]["owned"]["service_dir"] == "pending"
    # uninstall must NOT delete it, even with -RemoveServiceFiles
    assert bd.directory_uninstall_action("pending", exists=True, remove_requested=True, proof_ok=True) == "keep_pending_manual"
    # if it disappears, the intent is simply cleared
    assert bd.directory_uninstall_action("pending", exists=False, remove_requested=True, proof_ok=False) == "record_none"
    code, _out, refused = _state_cmd(tmp_path, capsys, "state-update", "--service-dir", "owned")
    assert code == 0  # promotion itself is allowed from pending ...
    with pytest.raises(bd.PolicyError):  # ... but never skipping pending
        bd.apply_state_update(bd.new_state(REPO_ROOT), service_dir="owned")
    with pytest.raises(bd.PolicyError):
        bd.apply_state_update(bd.apply_state_update(bd.apply_state_update(bd.new_state(REPO_ROOT), log_dir="pending"), log_dir="owned"), log_dir="pending")


@pytest.mark.parametrize("ownership,exists,remove,proof,expected", [
    ("none", True, True, True, "untouched"),
    ("owned", True, False, True, "retain"),
    ("owned", True, True, True, "delete"),
    ("owned", True, True, False, "refuse_unproven"),
    ("owned", False, True, False, "record_none"),
])
def test_directory_uninstall_action(ownership, exists, remove, proof, expected):
    assert bd.directory_uninstall_action(ownership, exists, remove, proof) == expected


def test_owned_directory_proof_accepts_base_or_exact_broker_ace_only():
    broker_rx = _snapshot([*BASE_ACL, (SERVICE_SID, RX, "Allow")])
    assert bd.owned_directory_proof(_snapshot(BASE_ACL), kind="service_dir", service_sid=SERVICE_SID, canonical=True, root_is_reparse=False) == []
    assert bd.owned_directory_proof(broker_rx, kind="service_dir", service_sid=SERVICE_SID, canonical=True, root_is_reparse=False) == []
    widened = _snapshot([*BASE_ACL, (SERVICE_SID, FULL, "Allow")])
    assert bd.owned_directory_proof(widened, kind="service_dir", service_sid=SERVICE_SID, canonical=True, root_is_reparse=False)
    foreign = _snapshot([*BASE_ACL, ("S-1-5-21-1-2-3-1001", RX, "Allow")])
    assert bd.owned_directory_proof(foreign, kind="log_dir", service_sid=SERVICE_SID, canonical=True, root_is_reparse=False)


def test_owned_directory_transaction_order():
    body = _function("New-MYCOwnedDirectory")
    existing = body[body.index("if (Test-Path -LiteralPath $Path)"): body.index("Update-MYCBrokerState -Layout $Layout -Arguments @($flag, 'pending')")]
    assert "if ($ownership -ne 'owned') { throw" in existing and "-Mode owned" in existing
    fresh = body[body.index("@($flag, 'pending')"):]
    order = [fresh.index(marker) for marker in ("New-Item -ItemType Directory", "Set-MYCProtectedAcl -Path $Path",
                                                "Test-MYCDirectoryProof -Layout $Layout -Path $Path -Mode creation",
                                                "if (-not $proof.proven) { throw", "@($flag, 'owned')")]
    assert order == sorted(order)
    assert "@('--service-dir', 'owned', '--log-dir', 'owned')" not in _ps(INSTALL)


def test_retained_artifacts_keep_a_tombstone_and_allow_reinstall(tmp_path, capsys):
    _install_until_logon_right(tmp_path, capsys, ["*S-1-5-20"])
    for flag in ("--service-dir", "--log-dir", "--backend-config"):
        _state_cmd(tmp_path, capsys, "state-update", flag, "pending")
        _state_cmd(tmp_path, capsys, "state-update", flag, "owned")
    _state_cmd(tmp_path, capsys, "state-update", "--service", "none")
    _state_cmd(tmp_path, capsys, "state-update", "--logon-right", "none")
    code, _out, closed = _state_cmd(tmp_path, capsys, "state-delete")  # directories and disabled block retained
    assert code == 0 and closed == {"deleted": False, "retained": True}
    assert bd.load_state(_ledger(tmp_path), REPO_ROOT)["phase"] == "uninstalled"
    _state_cmd(tmp_path, capsys, "state-begin")
    assert bd.service_install_decision("absent", bd.load_state(_ledger(tmp_path), REPO_ROOT)) == "create"
    for flag in ("--service-dir", "--log-dir", "--backend-config"):
        _state_cmd(tmp_path, capsys, "state-update", flag, "none")
    code, _out, closed = _state_cmd(tmp_path, capsys, "state-delete")
    assert code == 0 and closed == {"deleted": True, "retained": False}


# =============================================================================================
# Audit v5 -- backend\.env block is touched only when the ledger owns it
# =============================================================================================

def _env_with_block(tmp_path, capsys, monkeypatch):
    return _seed_pair(tmp_path, capsys, monkeypatch)


# =============================================================================================
# Audit v5 -- reparse points: no /T, lock-then-enumerate, no-follow deletion (real filesystem)
# =============================================================================================

def _tree(root):
    (root / "a" / "b").mkdir(parents=True)
    (root / "a" / "b" / "f.txt").write_text("x")
    (root / "top.txt").write_text("y")
    return root


def test_remove_owned_tree_deletes_everything_without_following(tmp_path):
    root = _tree(tmp_path / "owned")
    assert bd.remove_owned_tree(root) == 5 and not root.exists()


def test_symlink_inside_the_owned_tree_aborts_and_the_target_survives(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "precious.txt").write_text("keep")
    root = _tree(tmp_path / "owned")
    os.symlink(outside, root / "a" / "link", target_is_directory=True)
    with pytest.raises(bd.PolicyError) as raised:
        bd.remove_owned_tree(root)
    assert raised.value.code == "reparse_point_in_owned_tree"
    assert (outside / "precious.txt").read_text() == "keep"


def test_reparse_point_introduced_after_the_walk_started_aborts(tmp_path, monkeypatch):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "precious.txt").write_text("keep")
    root = _tree(tmp_path / "owned")
    real_unlink = os.unlink
    armed = {"done": False}

    def racing_unlink(path, *args, **kwargs):
        real_unlink(path, *args, **kwargs)
        if not armed["done"]:
            armed["done"] = True
            # the concurrent actor swaps a not-yet-visited subdirectory for a link
            victim = root / "a"
            if victim.exists():
                for child in sorted(victim.rglob("*"), reverse=True):
                    child.unlink() if child.is_file() else child.rmdir()
                victim.rmdir()
            os.symlink(outside, victim, target_is_directory=True)

    monkeypatch.setattr(bd.os, "unlink", racing_unlink)
    with pytest.raises(bd.PolicyError) as raised:
        bd.remove_owned_tree(root)
    assert raised.value.code in ("reparse_point_in_owned_tree", "owned_tree_changed_during_removal")
    assert (outside / "precious.txt").read_text() == "keep"


def test_entry_appearing_in_a_scanned_directory_aborts_instead_of_recursing_blindly(tmp_path, monkeypatch):
    root = _tree(tmp_path / "owned")
    real_unlink = os.unlink
    state = {"n": 0}

    def appearing(path, *args, **kwargs):
        real_unlink(path, *args, **kwargs)
        state["n"] += 1
        if state["n"] == 1:
            (root / "late.txt").write_text("appeared after the scan")

    monkeypatch.setattr(bd.os, "unlink", appearing)
    with pytest.raises(bd.PolicyError) as raised:
        bd.remove_owned_tree(root)
    assert raised.value.code == "owned_tree_changed_during_removal"
    assert (root / "late.txt").exists()  # nothing unexpected was deleted


def test_symlinked_root_and_non_owned_paths_are_refused(tmp_path, capsys):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    os.symlink(target, link, target_is_directory=True)
    with pytest.raises(bd.PolicyError):
        bd.remove_owned_tree(link)
    assert target.exists()
    code, _out, result = _run(["remove-owned-tree", "--path", r"C:\MYC\Deployment\another-component",
                               "--deployment-root", DEPLOYMENT_ROOT, "--services-root", r"C:\MYC\Services", "--logs-root", r"C:\MYC\Logs"], capsys)
    assert code == 3 and result == {"error": "path_not_owned"}


def test_hardening_closes_the_root_first_then_locks_before_enumerating():
    body = _function("Set-MYCProtectedAcl")
    root_owner = body.index("@($Path, '/setowner'")
    root_dacl = body.index("(@($Path, '/inheritance:r') + $grantArgs)")
    loop = body.index("while ($pending.Count -gt 0)")
    assert root_owner < root_dacl < loop
    walk = body[loop:]
    reparse = walk.index("[IO.FileAttributes]::ReparsePoint) { throw")
    reset = walk.index("@($entry.FullName, '/reset', '/C', '/Q')")
    recheck = walk.index("if (Test-MYCIsReparsePoint -Path $entry.FullName) { throw")
    push = walk.index("$pending.Push($entry.FullName)")
    assert reparse < reset < recheck < push  # a directory is enumerated only after it was locked
    for path in POWERSHELL_FILES:
        code = _ps_code(path)
        assert "'/T'" not in code and "'/save'" not in code, path.name
        assert not re.search(r"Remove-Item[^\n]*-Recurse", code), path.name
    remove = _function("Remove-MYCOwnedTree")
    assert remove.index("-Mode owned") < remove.index("'remove-owned-tree'")
    backup = _function("Backup-MYCAcl")
    assert backup.index("Where-Object { $_.IsReparse }") < backup.index("Get-Acl -LiteralPath $entry.Path")


# =============================================================================================
# DEV-1C close-out 1 -- backend\.env block ownership needs persisted, verifiable evidence
# =============================================================================================

def _action(tmp_path, capsys):
    return _run(["backend-config-action", "--file", str(_ledger(tmp_path)), "--repo-root", REPO_ROOT,
                 "--env-file", str(tmp_path / ".env")], capsys)[2]


def _backend_state(tmp_path):
    return bd.load_state(_ledger(tmp_path), REPO_ROOT)["owned"]


@pytest.mark.parametrize("ownership,block,proven,expected", [
    ("none", True, False, "untouched"), ("none", True, True, "untouched"), ("none", False, False, "untouched"),
    ("pending", False, False, "record_none"),
    ("pending", True, False, "refuse_manual"),       # block present WITHOUT DEV-1C proof: never touched
    ("pending", True, True, "disable_or_remove"),    # block present WITH proof: rollback allowed
    ("owned", True, False, "refuse_manual"),         # owned but drifted
    ("owned", True, True, "disable_or_remove"),
    ("owned", False, False, "record_none"),
])
def test_backend_config_uninstall_action(ownership, block, proven, expected):
    assert bd.backend_config_uninstall_action(ownership, block, proven) == expected


def test_crash_before_provision_leaves_nothing_to_touch(tmp_path, capsys, monkeypatch):
    (tmp_path / ".env").write_text("A=1\n", encoding="utf-8")
    monkeypatch.setattr(bd, "_write_journal", lambda *a, **k: (_ for _ in ()).throw(bd.PolicyError("provision_journal_failed")))
    code, _out, result = _run(_provision_args(tmp_path, "generate"), capsys)
    assert code == 3 and result == {"error": "provision_journal_failed"}
    owned = _backend_state(tmp_path)
    assert owned["backend_config"] == "pending" and owned["backend_config_evidence"]["fingerprint"]  # evidence first
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "A=1\n"
    assert _action(tmp_path, capsys) == {"action": "record_none", "ownership": "pending", "proven": False}


def test_crash_after_write_before_owned_is_proven_by_the_persisted_evidence(tmp_path, capsys, monkeypatch):
    (tmp_path / ".env").write_text("A=1\n", encoding="utf-8")
    real = bd.save_state

    def crash_on_promotion(path, state, repo_root):
        if state["owned"]["backend_config"] == "owned":
            raise OSError("power loss")
        return real(path, state, repo_root)

    with monkeypatch.context() as patch:
        patch.setattr(bd, "save_state", crash_on_promotion)
        with pytest.raises(OSError):
            bd.main(_provision_args(tmp_path, "generate"))
    capsys.readouterr()
    assert _backend_state(tmp_path)["backend_config"] == "pending"
    assert bd.split_env_block((tmp_path / ".env").read_text(encoding="utf-8"))[1] is not None  # the block was written
    assert _action(tmp_path, capsys) == {"action": "disable_or_remove", "ownership": "pending", "proven": True}
    # a re-run proves and promotes it instead of refusing it
    code, _out, result = _run(_provision_args(tmp_path, "reuse"), capsys)
    assert code == 0 and result["backend_config"] == "owned" and _backend_state(tmp_path)["backend_config"] == "owned"


@pytest.mark.parametrize("forge", ["no_marker", "copied_marker"])
def test_foreign_block_appearing_during_pending_is_never_touched(tmp_path, capsys, monkeypatch, forge):
    (tmp_path / ".env").write_text("A=1\n", encoding="utf-8")
    monkeypatch.setattr(bd, "_write_journal", lambda *a, **k: (_ for _ in ()).throw(bd.PolicyError("provision_journal_failed")))
    _run(_provision_args(tmp_path, "generate"), capsys)            # crash: ledger pending, nothing written
    monkeypatch.undo()
    marker = _backend_state(tmp_path)["backend_config_evidence"]["marker"]
    values = bd.backend_values("MYCDeveloperBroker", "F" * 64, CLIENT_SID, SERVICE_SID, enabled=True)
    foreign = bd.render_env_file("A=1\n", values, marker if forge == "copied_marker" else None)
    (tmp_path / ".env").write_text(foreign, encoding="utf-8")       # the third party
    assert _action(tmp_path, capsys) == {"action": "refuse_manual", "ownership": "pending", "proven": False}
    code, _out, result = _run(_provision_args(tmp_path, "generate"), capsys)
    assert code == 3 and result == {"error": "managed_block_not_owned"}
    assert (tmp_path / ".env").read_text(encoding="utf-8") == foreign and not (tmp_path / "MYCDeveloperBroker.xml").exists()


def test_owned_block_drift_is_refused_but_the_enable_switch_is_not_drift(tmp_path, capsys):
    (tmp_path / ".env").write_text("A=1\n", encoding="utf-8")
    _run(_provision_args(tmp_path, "generate"), capsys)
    env = str(tmp_path / ".env")
    _run(["set-backend-enabled", "--env-file", env, "--enabled", "true"], capsys)   # DEV-1C's own switch
    assert _action(tmp_path, capsys)["proven"] is True
    text = (tmp_path / ".env").read_text(encoding="utf-8")
    drifted = text.replace("DEVELOPER_BROKER_PIPE_NAME=MYCDeveloperBroker", "DEVELOPER_BROKER_PIPE_NAME=OtherPipe")
    (tmp_path / ".env").write_text(drifted, encoding="utf-8")
    assert _action(tmp_path, capsys) == {"action": "refuse_manual", "ownership": "owned", "proven": False}
    code, _out, result = _run(_provision_args(tmp_path, "generate"), capsys)
    assert code == 3 and result == {"error": "managed_block_drifted"}
    assert (tmp_path / ".env").read_text(encoding="utf-8") == drifted


def test_normal_install_and_uninstall_of_the_block(tmp_path, capsys):
    original = "A=1\nB=2\n"
    (tmp_path / ".env").write_text(original, encoding="utf-8")
    code, _out, result = _run(_provision_args(tmp_path, "generate"), capsys)
    assert code == 0 and result["backend_config"] == "owned"
    owned = _backend_state(tmp_path)
    secret = _secrets(tmp_path)[0]
    ledger_bytes = _ledger(tmp_path).read_bytes()
    assert secret.encode() not in ledger_bytes                      # neither the secret ...
    assert owned["backend_config_evidence"]["fingerprint"] != __import__("hashlib").sha256(secret.encode()).hexdigest()
    assert bd.block_marker((tmp_path / ".env").read_text(encoding="utf-8")) == owned["backend_config_evidence"]["marker"]
    assert _action(tmp_path, capsys)["action"] == "disable_or_remove"
    _run(["set-backend-enabled", "--env-file", str(tmp_path / ".env"), "--enabled", "false"], capsys)
    _run(["remove-backend-block", "--env-file", str(tmp_path / ".env")], capsys)
    _state_cmd(tmp_path, capsys, "state-update", "--backend-config", "none")
    assert (tmp_path / ".env").read_text(encoding="utf-8") == original
    assert _backend_state(tmp_path)["backend_config_evidence"] == {"marker": None, "fingerprint": None, "fingerprint_next": None}
    # reinstall (owned) keeps the marker and moves the fingerprint through fingerprint_next
    _run(_provision_args(tmp_path, "generate"), capsys)
    first = _backend_state(tmp_path)["backend_config_evidence"]
    _run(_provision_args(tmp_path, "generate"), capsys)
    second = _backend_state(tmp_path)["backend_config_evidence"]
    assert second["marker"] == first["marker"] and second["fingerprint"] != first["fingerprint"] and second["fingerprint_next"] is None


def test_uninstall_and_preflight_rely_on_proof_not_on_the_recorded_state():
    uninstall = _ps(UNINSTALL)
    assert "} elseif ($envAction -eq 'refuse_manual') {" in uninstall
    refuse = uninstall.index("} elseif ($envAction -eq 'refuse_manual') {")
    assert refuse < uninstall.index("'remove-backend-block'") and refuse < uninstall.index("'set-backend-enabled', '--env-file', $layout.EnvFile, '--enabled', 'false'")
    assert "@('--backend-config', 'owned')" not in uninstall  # uninstall never promotes
    install = _ps(INSTALL)
    assert "'--state-file', $layout.StateFile, '--repo-root', $layout.RepoRoot" in install
    assert "--require-no-managed-block" not in install and "@('--backend-config', 'pending')" not in install
    assert ").proven" in install[install.index("'backend_block_owned'") - 900: install.index("'backend_block_owned'")]


# =============================================================================================
# DEV-1C close-out 2 -- external ACL grants: pending -> owned, per grant, exact
# =============================================================================================

def _grant_state(status):
    return _owned_venv_state(status)


@pytest.mark.parametrize("status,snapshot,install_expected,uninstall_expected", [
    # pending before /grant:r: no explicit Broker ACE yet
    ("pending", _acl_with(("S-1-5-18", "Allow", False)), "apply", "record_none"),
    # pending after /grant:r, crash before owned: exact ACE
    ("pending", _acl_with((SERVICE_SID, "Allow", False)), "reconcile_pending_exact", "revoke"),
    # foreign ACE that appeared during pending
    ("pending", _acl_with((SERVICE_SID, "Allow", False), rights=FULL), "pending_grant_ambiguous", "refuse_manual"),
    ("owned", _acl_with((SERVICE_SID, "Allow", False)), "reapply_owned", "revoke"),               # owned exact
    ("owned", _acl_with((SERVICE_SID, "Allow", False), flags=(0, 0)), "broker_ace_drifted", "refuse_manual"),  # owned drifted
    ("owned", _acl_with((SERVICE_SID, "Allow", False), (SERVICE_SID, "Deny", False)), "broker_ace_drifted", "refuse_manual"),
    ("owned", _acl_with(("S-1-5-18", "Allow", False)), "apply", "record_none"),                  # removed by someone: nothing to revoke
])
def test_grant_lifecycle_decisions(status, snapshot, install_expected, uninstall_expected):
    state = _grant_state(status)
    if install_expected in ("apply", "reapply_owned", "reconcile_pending_exact"):
        assert bd.external_grant_decision(snapshot, EXTERNAL_GRANT, state) == install_expected
    else:
        with pytest.raises(bd.PolicyError) as raised:
            bd.external_grant_decision(snapshot, EXTERNAL_GRANT, state)
        assert raised.value.code == install_expected
    grant = next(entry for entry in state["owned"]["acl_grants"] if entry["path"] == EXTERNAL_PATH)
    assert bd.acl_grant_uninstall_action(snapshot, grant) == uninstall_expected


def test_revocation_is_verified_after_the_fact(tmp_path, capsys):
    still = tmp_path / "after.json"
    still.write_text(json.dumps(_acl_with((SERVICE_SID, "Allow", False))), encoding="utf-8")
    argv = ["acl-grant-uninstall-action", "--snapshot", str(still), "--path", EXTERNAL_PATH,
            "--grant", EXTERNAL_GRANT["icacls_grant"], "--status", "owned", "--after-revoke"]
    code, _out, result = _run(argv, capsys)
    assert code == 3 and result == {"error": "broker_ace_still_present"}
    still.write_text(json.dumps(_acl_with(("S-1-5-18", "Allow", False))), encoding="utf-8")
    assert _run(argv, capsys)[2] == {"action": "revoked"}


def test_grant_ledger_transitions_never_record_ownership_by_intent():
    state = bd.apply_state_update(bd.new_state(REPO_ROOT), service_sid=SERVICE_SID)
    value = EXTERNAL_GRANT["icacls_grant"]
    with pytest.raises(bd.PolicyError):   # absent -> owned skips pending (no evidence)
        bd.apply_state_update(state, grant_path=EXTERNAL_PATH, grant_value=value, grant_status="owned")
    pending = bd.apply_state_update(state, grant_path=EXTERNAL_PATH, grant_value=value, grant_status="pending")
    owned = bd.apply_state_update(pending, grant_path=EXTERNAL_PATH, grant_value=value, grant_status="owned")
    with pytest.raises(bd.PolicyError):   # owned never goes back to pending
        bd.apply_state_update(owned, grant_path=EXTERNAL_PATH, grant_value=value, grant_status="pending")
    with pytest.raises(bd.PolicyError):   # one exact planned grant per path
        bd.apply_state_update(owned, grant_path=EXTERNAL_PATH, grant_value=f"*{SERVICE_SID}:(OI)(CI)(M)", grant_status="owned")
    with pytest.raises(bd.PolicyError):   # the grant's SID must be the ledger's
        bd.apply_state_update(state, grant_path=EXTERNAL_PATH, grant_value=f"*{OTHER_SID}:(RX)", grant_status="pending")
    removed = bd.apply_state_update(owned, grant_path=EXTERNAL_PATH, grant_status="remove")
    assert removed["owned"]["acl_grants"] == []
    assert owned["owned"]["acl_grants"] == [{"path": EXTERNAL_PATH, "grant": value, "status": "owned"}]


def test_installer_and_uninstall_handle_grants_one_at_a_time_and_exactly():
    install = _ps(INSTALL)
    loop = install[install.index("foreach ($grant in $plan) {"): install.index("# 9. Secret + configuration")]
    external = loop[loop.index("} else {"):]  # the branch for paths DEV-1C does not own
    order = [external.index(marker) for marker in (
        "$decision = Get-MYCExternalGrantDecision -Layout $layout -Grant $grant",
        "-Status pending",
        "Grant-MYCBrokerAcl -Layout $layout -Grant $grant",
        "Test-MYCGrantExact -Layout $layout -Grant $grant",
        "-Status owned",
    )]
    assert order == sorted(order)
    assert "Add-MYCBrokerStateAclGrants" not in _ps_code(MODULE) + _ps_code(INSTALL)
    grant = _function("Grant-MYCBrokerAcl")
    assert "'/grant:r'" in grant and "'external-grant-verify'" in grant
    remove = _function("Remove-MYCBrokerGrantExact")
    decision = remove.index("'acl-grant-uninstall-action'")
    revoke = remove.index("'/remove:g'")
    verify = remove.index("'--after-revoke'")
    assert decision < remove.index("if ($decision -ne 'revoke') { return $decision }") < revoke < verify
    uninstall = _ps(UNINSTALL)
    assert "Remove-MYCBrokerGrantExact -Layout $layout -Grant $grant" in uninstall
    assert "if ($grantAction -eq 'refuse_manual')" in uninstall
    assert "Revoke-MYCSidFromPath" not in _ps_code(MODULE) + _ps_code(UNINSTALL)


def test_schema_5_ledgers_are_refused():
    legacy = {**bd.new_state(REPO_ROOT), "schema": 5}
    with pytest.raises(bd.PolicyError) as raised:
        bd.validate_state(legacy, REPO_ROOT)
    assert raised.value.code == "state_incompatible"
    old_grant = bd.new_state(REPO_ROOT)
    old_grant["service_sid"] = SERVICE_SID
    old_grant["owned"]["acl_grants"] = [{"path": EXTERNAL_PATH, "grant": EXTERNAL_GRANT["icacls_grant"]}]  # schema-5 shape
    with pytest.raises(bd.PolicyError):
        bd.validate_state(old_grant, REPO_ROOT)


# =============================================================================================
# DEV-1C close-out 3 -- reinstall never degrades the ACL of an owned ServiceDir/LogDir
# =============================================================================================

def test_existing_owned_directory_is_proven_and_left_untouched():
    body = _function("New-MYCOwnedDirectory")
    existing = body[body.index("if (Test-Path -LiteralPath $Path) {"): body.index("Update-MYCBrokerState -Layout $Layout -Arguments @($flag, 'pending')")]
    assert "Test-MYCDirectoryProof -Layout $Layout -Path $Path -Mode owned" in existing
    assert "return" in existing
    code_only = "\n".join(line for line in existing.splitlines() if not line.strip().startswith("#"))
    assert "Set-MYCProtectedAcl" not in code_only and "icacls" not in code_only
    fresh = body[body.index("@($flag, 'pending')"):]
    assert "Set-MYCProtectedAcl -Path $Path" in fresh  # a NEW directory still gets the base ACL before its proof


# =============================================================================================
# DEV-1C close-out 4 -- ACL backup restore (Restore-MYCServicesAcl.ps1)
# =============================================================================================

SERVICES = r"C:\MYC\Services"
BROKER_DIR = SERVICES + r"\developer-broker"
ROOT_SDDL = "O:BAG:SYD:PAI(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;0x1301bf;;;AU)"
CHILD_SDDL = "O:BAG:SYD:AI(A;ID;FA;;;SY)(A;ID;FA;;;BA)(A;ID;0x1301bf;;;AU)"


def _backup(*extra, root=True):
    records = [{"path": SERVICES, "sddl": ROOT_SDDL}] if root else []
    return records + list(extra)


def test_restore_plan_orders_deepest_first_and_root_last():
    records = _backup({"path": SERVICES + r"\backend", "sddl": CHILD_SDDL},
                      {"path": SERVICES + r"\backend\MYCBackend.exe", "sddl": CHILD_SDDL},
                      {"path": SERVICES + r"\frontend", "sddl": CHILD_SDDL})
    plan = bd.restore_plan(records, SERVICES, BROKER_DIR)
    assert [entry["path"] for entry in plan] == [
        SERVICES + r"\backend\MYCBackend.exe", SERVICES + r"\backend", SERVICES + r"\frontend", SERVICES]
    assert plan[-1]["sddl"] == ROOT_SDDL


@pytest.mark.parametrize("records,error", [
    ([], "backup_invalid"),
    ({"path": SERVICES, "sddl": ROOT_SDDL}, "backup_invalid"),
    (_backup({"path": SERVICES + r"\x", "sddl": CHILD_SDDL, "extra": 1}), "backup_entry_invalid"),
    (_backup({"path": SERVICES + r"\x"}), "backup_entry_invalid"),
    (_backup({"path": 7, "sddl": CHILD_SDDL}), "backup_entry_invalid"),
    (_backup({"path": r"MYC\Services\x", "sddl": CHILD_SDDL}), "path_invalid"),
    (_backup({"path": SERVICES + r"\..\Windows", "sddl": CHILD_SDDL}), "path_invalid"),
    (_backup({"path": "C:/MYC/Services/x", "sddl": CHILD_SDDL}), "backup_path_not_canonical"),
    (_backup({"path": SERVICES + r"\\x", "sddl": CHILD_SDDL}), "backup_path_not_canonical"),
    (_backup({"path": r"C:\MYC\ServicesEvil\x", "sddl": CHILD_SDDL}), "backup_path_out_of_scope"),
    (_backup({"path": r"C:\Windows\System32", "sddl": CHILD_SDDL}), "backup_path_out_of_scope"),
    (_backup({"path": BROKER_DIR + r"\MYCDeveloperBroker.xml", "sddl": CHILD_SDDL}), "backup_path_out_of_scope"),
    (_backup({"path": SERVICES + r"\a", "sddl": CHILD_SDDL}, {"path": SERVICES + r"\A", "sddl": CHILD_SDDL}), "backup_entry_duplicate"),
    (_backup({"path": SERVICES + r"\a", "sddl": "not an sddl"}), "backup_sddl_invalid"),
    (_backup({"path": SERVICES + r"\a", "sddl": 'O:BAG:SYD:(XA;;FA;;;WD;(@User.x=="y"))'}), "backup_sddl_invalid"),
    (_backup({"path": SERVICES + r"\a", "sddl": CHILD_SDDL}, root=False), "backup_root_missing"),
])
def test_restore_plan_refuses_invalid_backups(records, error):
    with pytest.raises(bd.PolicyError) as raised:
        bd.restore_plan(records, SERVICES, BROKER_DIR)
    assert raised.value.code == error


def test_restore_plan_command(tmp_path, capsys):
    backup = tmp_path / "services.acl.json"
    backup.write_text(json.dumps(_backup({"path": SERVICES + r"\backend", "sddl": CHILD_SDDL})), encoding="utf-8-sig")
    code, _out, result = _run(["restore-plan", "--backup", str(backup), "--services-root", SERVICES, "--exclude", BROKER_DIR], capsys)
    assert code == 0 and result["count"] == 2 and result["entries"][-1]["path"] == SERVICES
    backup.write_text("{broken", encoding="utf-8")
    code, _out, result = _run(["restore-plan", "--backup", str(backup), "--services-root", SERVICES, "--exclude", BROKER_DIR], capsys)
    assert code == 3 and result == {"error": "backup_invalid"}


def test_restore_script_validates_everything_before_the_first_change():
    text = _ps(RESTORE)
    code = _ps_code(RESTORE)
    assert "#Requires -RunAsAdministrator" in text and "SupportsShouldProcess = $true, ConfirmImpact = 'High'" in text
    plan = code.index("'restore-plan', '--backup', $BackupFile")
    precheck = code.index("foreach ($entry in $entries) {\n        if (-not (Test-Path -LiteralPath $entry.path))")
    first_change = code.index("Set-Acl -LiteralPath $entry.path -AclObject $acl")
    assert plan < precheck < first_change
    loop = code[code.index("$restored = 0"):]
    order = [loop.index(marker) for marker in (
        "$PSCmdlet.ShouldProcess($entry.path",
        "Assert-MYCNoRedirectedPath -Path $entry.path",
        "$acl.SetSecurityDescriptorSddlForm([string]$entry.sddl)",
        "Set-Acl -LiteralPath $entry.path -AclObject $acl",
        "$effective = (Get-Acl -LiteralPath $entry.path).Sddl",
        "if ($effective -cne [string]$entry.sddl) { throw",
    )]
    assert order == sorted(order)
    assert "# Final pass" in text and "-cne [string]$_.sddl" in code
    assert "icacls" not in code.lower() and "/restore" not in code
    assert "'--exclude', $layout.ServiceDir" in code
    assert "Test-MYCIsReparsePoint -Path $BackupFile" in code and ".acl.json" in code
    # never run automatically
    for path in (INSTALL, UNINSTALL, HARDEN, MODULE):
        assert "Restore-MYCServicesAcl.ps1 -" not in _ps_code(path) and "& (Join-Path $PSScriptRoot 'Restore" not in _ps_code(path)
    backup = _function("Backup-MYCAcl")
    assert "Get-MYCTreeEntries -Path $Path -Exclude $Layout.ServiceDir" in backup


def test_no_document_or_script_suggests_icacls_restore_for_these_backups():
    paths = [*DEPLOY.iterdir(), *(REPO / "docs").rglob("*.md")]
    for path in paths:
        if path.is_file() and path.suffix in (".md", ".ps1", ".psm1", ".py"):
            text = path.read_bytes().decode("utf-8-sig")
            assert "icacls C:\\MYC /restore" not in text and "/restore <" not in text, path
    doc = (REPO / "docs/architecture/MOBILE_DEVELOPER_BROKER.md").read_text(encoding="utf-8")
    assert "Restore-MYCServicesAcl.ps1" in doc and "SDDL" in doc


def test_docs_and_code_describe_the_current_backup_and_block_ownership_api():
    texts = {path: path.read_bytes().decode("utf-8-sig") for path in [*DEPLOY.iterdir(), *(REPO / "docs").rglob("*.md")]
             if path.is_file() and path.suffix in (".md", ".ps1", ".psm1", ".py")}
    for path, text in texts.items():
        assert "require-no-managed-block" not in text and "require_no_managed_block" not in text, path
        assert "respaldo `icacls /save`" not in text, path
    registry = (REPO / "docs/PROJECT_FILE_REGISTRY.md").read_text(encoding="utf-8")
    for name in ("MYCDeveloperBroker.psm1", "Set-MYCServicesAcl.ps1"):
        row = next(line for line in registry.splitlines() if line.startswith(f"| deploy/windows/developer-broker/{name} |"))
        assert "Backup-MYCAcl" in row and "Restore-MYCServicesAcl.ps1" in row, name
    doc = (REPO / "docs/architecture/MOBILE_DEVELOPER_BROKER.md").read_text(encoding="utf-8")
    assert "marker +\n   fingerprint persistidos en el ledger" in doc
