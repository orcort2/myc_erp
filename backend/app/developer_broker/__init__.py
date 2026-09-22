"""DEV-1A: MYC Developer Broker boundary.

ERP != Broker != shell. This package is the versioned, transport-agnostic
contract between the FastAPI Developer Control Plane (``client``) and the
separate MYC Developer Broker process (``server``), plus the transport port
both sides speak through.

Deliberately framework-free: nothing here imports FastAPI, SQLAlchemy, the
ERP configuration, Mobile auth, the biometric authority or ``app.realtime``.
The Broker authenticates the *calling process* (HMAC over a canonical
envelope + anti-replay); it never authorizes the *user* -- that is the
Developer authority of DEV-0 (``app.core.mobile.developer``), enforced by
FastAPI before a BrokerClient is ever used.

DEV-1A executes nothing: the only operation is ``broker.health``. See
docs/architecture/MOBILE_DEVELOPER_BROKER.md.
"""
