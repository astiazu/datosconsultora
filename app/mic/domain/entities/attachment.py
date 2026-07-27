from dataclasses import dataclass


@dataclass(slots=True)
class Attachment:
    """
    Archivo adjunto asociado a un mensaje.
    """

    attachment_id: str

    type: str

    url: str

    size: int | None = None