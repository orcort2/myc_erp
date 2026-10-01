class EmailError(Exception):
    """Base of controlled email-infrastructure failures (safe to show)."""

    code = "email_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EmailTemplateError(EmailError):
    code = "email_template_invalid"


class EmailAddressError(EmailError):
    code = "email_address_invalid"


class EmailTransportError(EmailError):
    code = "email_transport_failed"
