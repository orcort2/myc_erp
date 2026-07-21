from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import Settings
from app.services.office_converter import COMMON_PATHS, diagnose_office_converter, resolve_office_converter


def test_explicit_absolute_path_has_priority(tmp_path):
    executable = tmp_path / "soffice"
    executable.write_text("executable")

    with patch("app.services.office_converter.shutil.which") as which:
        resolved = resolve_office_converter(str(executable))

    assert resolved is not None
    assert resolved.executable == str(executable.resolve())
    assert resolved.source == "configured_path"
    which.assert_not_called()


@pytest.mark.parametrize("variable", ["LIBREOFFICE_EXECUTABLE", "OFFICE_CONVERTER_BINARY"])
def test_canonical_and_legacy_environment_variables_are_accepted(monkeypatch, variable):
    monkeypatch.delenv("LIBREOFFICE_EXECUTABLE", raising=False)
    monkeypatch.delenv("OFFICE_CONVERTER_BINARY", raising=False)
    monkeypatch.setenv(variable, "configured-office")

    assert Settings(_env_file=None).libreoffice_executable == "configured-office"


def test_configured_command_and_path_commands_are_supported():
    def fake_which(command):
        return "/opt/libreoffice/program/soffice" if command == "custom-office" else None

    with patch("app.services.office_converter.shutil.which", side_effect=fake_which):
        resolved = resolve_office_converter("custom-office")

    assert resolved is not None
    assert resolved.executable == "/opt/libreoffice/program/soffice"
    assert resolved.source == "configured_command"


def test_invalid_explicit_value_falls_back_to_soffice_in_path():
    def fake_which(command):
        return "/usr/local/bin/soffice" if command == "soffice" else None

    with patch("app.services.office_converter.shutil.which", side_effect=fake_which):
        resolved = resolve_office_converter("/missing/libreoffice")

    assert resolved is not None
    assert resolved.executable == "/usr/local/bin/soffice"
    assert resolved.source == "path:soffice"


def test_macos_common_application_path_is_checked(tmp_path):
    expected = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    executable = tmp_path / "LibreOffice.app" / "Contents" / "MacOS" / "soffice"
    executable.parent.mkdir(parents=True)
    executable.write_text("executable")
    assert expected in COMMON_PATHS["Darwin"]

    with (
        patch("app.services.office_converter.platform.system", return_value="Darwin"),
        patch("app.services.office_converter.shutil.which", return_value=None),
        patch.dict(COMMON_PATHS, {"Darwin": (str(executable),)}),
    ):
        resolved = resolve_office_converter("")

    assert resolved is not None
    assert resolved.executable == str(executable.resolve())
    assert resolved.source == "system_path"


@pytest.mark.parametrize(
    ("system", "required_paths"),
    [
        ("Darwin", {"/Applications/LibreOffice.app/Contents/MacOS/soffice"}),
        (
            "Windows",
            {
                r"C:\Program Files\LibreOffice\program\soffice.exe",
                r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
            },
        ),
        ("Linux", {"/usr/bin/soffice", "/usr/bin/libreoffice"}),
    ],
)
def test_required_platform_paths_are_declared(system, required_paths):
    assert required_paths.issubset(set(COMMON_PATHS[system]))


def test_diagnostic_reports_resolved_path_and_version():
    completed = MagicMock(returncode=0, stdout="LibreOffice 24.2.0\n", stderr="")
    with (
        patch("app.services.office_converter.resolve_office_converter") as resolver,
        patch("app.services.office_converter.subprocess.run", return_value=completed) as run,
    ):
        resolver.return_value = MagicMock(executable="/usr/bin/soffice", source="path:soffice")
        diagnostic = diagnose_office_converter("")

    assert diagnostic.available is True
    assert diagnostic.executable == "/usr/bin/soffice"
    assert diagnostic.version == "LibreOffice 24.2.0"
    run.assert_called_once_with(
        ["/usr/bin/soffice", "--version"],
        capture_output=True,
        check=False,
        text=True,
        timeout=10,
    )
