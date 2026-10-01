"""Single rendering authority: template + context -> subject/text/HTML.

Preview and send must both go through ``render_email`` so that what staff see
is exactly what is delivered. Placeholders are plain ``{name}`` tokens
resolved by regular-expression substitution against a code-side whitelist:
there is no expression evaluation, attribute access or format-spec parsing.
"""

import re
from dataclasses import dataclass
from html import escape
from urllib.parse import urlsplit

from app.services.email.catalog import TemplateDefinition
from app.services.email.errors import EmailTemplateError

PLACEHOLDER = re.compile(r"\{([^{}]*)\}")
VALID_NAME = re.compile(r"[a-z][a-z0-9_]*")
REDACTED = "[enlace protegido]"
MAX_SUBJECT_LENGTH = 300


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    body_text: str
    body_html: str


def placeholders(template: str) -> list[str]:
    return PLACEHOLDER.findall(template)


def validate_template_text(definition: TemplateDefinition, *texts: str) -> None:
    """Reject anything that is not a known ``{variable}`` placeholder."""
    for text in texts:
        stripped = PLACEHOLDER.sub("", text)
        if "{" in stripped or "}" in stripped:
            raise EmailTemplateError("La plantilla contiene llaves sin cerrar o anidadas.")
        for name in placeholders(text):
            if not VALID_NAME.fullmatch(name) or name not in definition.variable_names:
                raise EmailTemplateError(f"Variable no permitida en la plantilla: {name[:40]!r}.")


def _single_line(value: str) -> str:
    return " ".join(value.replace("\r", " ").replace("\n", " ").split())


def _safe_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.netloc or any(c in value for c in "\r\n \t"):
        raise EmailTemplateError("Una variable de enlace no es una URL http(s) válida.")
    return value


def _substitute(text: str, values: dict[str, str]) -> str:
    return PLACEHOLDER.sub(lambda match: values[match.group(1)], text)


def render_email(
    definition: TemplateDefinition,
    *,
    subject_template: str,
    body_template: str,
    context: dict[str, object],
    organization_name: str = "Metrología y Servicios MYC",
    redact_secrets: bool = False,
) -> RenderedEmail:
    validate_template_text(definition, subject_template, body_template)
    unknown = set(context) - definition.variable_names
    if unknown:
        raise EmailTemplateError(f"Variables de contexto no permitidas: {sorted(unknown)}.")
    used = set(placeholders(subject_template)) | set(placeholders(body_template))
    missing = used - set(context)
    if missing:
        raise EmailTemplateError(f"Faltan variables de contexto: {sorted(missing)}.")

    text_values: dict[str, str] = {}
    html_values: dict[str, str] = {}
    for name in used:
        variable = definition.variable(name)
        raw = "" if context[name] is None else str(context[name])
        if variable.secret and redact_secrets:
            text_values[name] = html_values[name] = REDACTED
        elif variable.kind == "url":
            url = _safe_url(raw)
            text_values[name] = url
            html_values[name] = f'<a href="{escape(url, quote=True)}">{escape(url)}</a>'
        else:
            text_values[name] = raw
            html_values[name] = escape(raw)

    subject = _single_line(_substitute(subject_template, {k: _single_line(v) for k, v in text_values.items()}))
    if not subject or len(subject) > MAX_SUBJECT_LENGTH:
        raise EmailTemplateError("El asunto está vacío o excede la longitud permitida.")

    body_text = _substitute(body_template, text_values).replace("\r\n", "\n").strip()
    paragraphs = [
        # Static template text is escaped; variable HTML is injected afterwards.
        "<br>".join(_substitute_escaped(line, html_values) for line in block.split("\n"))
        for block in body_template.replace("\r\n", "\n").strip().split("\n\n")
    ]
    body_html = _wrap_html(organization_name, subject, paragraphs)
    return RenderedEmail(subject=subject, body_text=body_text, body_html=body_html)


def _substitute_escaped(line: str, html_values: dict[str, str]) -> str:
    """Escape literal text between placeholders, keep pre-escaped variable HTML."""
    parts: list[str] = []
    cursor = 0
    for match in PLACEHOLDER.finditer(line):
        parts.append(escape(line[cursor : match.start()]))
        parts.append(html_values[match.group(1)])
        cursor = match.end()
    parts.append(escape(line[cursor:]))
    return "".join(parts)


def _wrap_html(organization_name: str, title: str, paragraphs: list[str]) -> str:
    body = "".join(
        f'<p style="margin:0 0 14px;line-height:1.5;">{paragraph}</p>' for paragraph in paragraphs if paragraph
    )
    return (
        '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
        f"<title>{escape(title)}</title></head>"
        '<body style="margin:0;padding:0;background:#f3f6f7;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:24px 12px;">'
        '<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        'style="max-width:600px;background:#ffffff;font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#1f2d33;">'
        f'<tr><td style="background:#073f48;color:#ffffff;padding:16px 24px;font-size:16px;font-weight:bold;">{escape(organization_name)}</td></tr>'
        f'<tr><td style="padding:24px;">{body}</td></tr>'
        '<tr><td style="padding:12px 24px;font-size:11px;color:#60747b;border-top:1px solid #d2e6e7;">'
        "Mensaje automático del ERP de MYC. No respondas a este correo si no se indica lo contrario.</td></tr>"
        "</table></td></tr></table></body></html>"
    )
