"""Code-side authority for institutional email templates.

Defines, per template key, the whitelisted variables and the default content.
Staff may edit the human text stored in ``email_templates`` but can only use
the variables declared here.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TemplateVariable:
    name: str
    kind: str = "text"  # "text" | "url"
    secret: bool = False  # redacted in stored snapshots (one-time credentials)


@dataclass(frozen=True)
class TemplateDefinition:
    key: str
    name: str
    variables: tuple[TemplateVariable, ...]
    subject: str
    body: str

    @property
    def variable_names(self) -> frozenset[str]:
        return frozenset(item.name for item in self.variables)

    @property
    def has_secret(self) -> bool:
        return any(item.secret for item in self.variables)

    def variable(self, name: str) -> TemplateVariable:
        return next(item for item in self.variables if item.name == name)


_SIGNATURE = "Atentamente,\nMetrología y Servicios MYC"

TEMPLATE_DEFINITIONS: dict[str, TemplateDefinition] = {
    definition.key: definition
    for definition in (
        TemplateDefinition(
            key="portal_email_verification",
            name="Portal del Cliente: verificación de correo",
            variables=(
                TemplateVariable("recipient_name"),
                TemplateVariable("verification_url", "url", secret=True),
            ),
            subject="Verifica tu correo del Portal del Cliente MYC",
            body=(
                "Hola {recipient_name},\n\n"
                "Para confirmar tu correo y continuar con tu registro en el Portal del Cliente, abre el siguiente enlace:\n\n"
                "{verification_url}\n\n"
                "Si no solicitaste este registro, ignora este mensaje.\n\n" + _SIGNATURE
            ),
        ),
        TemplateDefinition(
            key="portal_invitation",
            name="Portal del Cliente: invitación",
            variables=(
                TemplateVariable("recipient_name"),
                TemplateVariable("client_name"),
                TemplateVariable("invitation_url", "url", secret=True),
            ),
            subject="Invitación al Portal del Cliente MYC",
            body=(
                "Hola {recipient_name},\n\n"
                "{client_name} te invitó al Portal del Cliente de MYC. Para aceptar la invitación abre el siguiente enlace:\n\n"
                "{invitation_url}\n\n"
                "La invitación tiene vigencia limitada.\n\n" + _SIGNATURE
            ),
        ),
        TemplateDefinition(
            key="password_reset",
            name="Recuperación de contraseña",
            variables=(
                TemplateVariable("recipient_name"),
                TemplateVariable("reset_url", "url", secret=True),
                TemplateVariable("expires_in"),
            ),
            subject="Recuperación de contraseña MYC",
            body=(
                "Hola {recipient_name},\n\n"
                "Recibimos una solicitud para restablecer tu contraseña. El siguiente enlace expira en {expires_in}:\n\n"
                "{reset_url}\n\n"
                "Si no hiciste esta solicitud, ignora este mensaje.\n\n" + _SIGNATURE
            ),
        ),
        TemplateDefinition(
            key="quotation_send",
            name="Envío de cotización",
            variables=tuple(
                TemplateVariable(name)
                for name in (
                    "contact_name",
                    "client_name",
                    "quotation_folio",
                    "advisor_name",
                    "total",
                    "valid_until",
                )
            ),
            subject="Cotización {quotation_folio} - Metrología y Servicios MYC",
            body=(
                "Estimado(a) {contact_name},\n\n"
                "Adjuntamos la cotización {quotation_folio} para {client_name} por un total de {total}, vigente hasta {valid_until}.\n\n"
                "Quedamos atentos a sus comentarios.\n\n{advisor_name}\nMetrología y Servicios MYC"
            ),
        ),
        TemplateDefinition(
            key="invoice_send",
            name="Envío de factura",
            variables=tuple(
                TemplateVariable(name)
                for name in ("contact_name", "client_name", "fiscal_identifier", "cfdi_uuid", "total")
            ),
            subject="Factura {fiscal_identifier} - Metrología y Servicios MYC",
            body=(
                "Estimado(a) {contact_name},\n\n"
                "Adjuntamos la factura {fiscal_identifier} de {client_name} por un total de {total}.\n"
                "Folio fiscal (UUID): {cfdi_uuid}\n\n" + _SIGNATURE
            ),
        ),
    )
}
