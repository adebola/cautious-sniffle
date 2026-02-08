"""Template Pydantic schemas."""

from pydantic import BaseModel


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: str | None
    icon: str | None
    system_prompt: str
    default_settings: dict
    document_types: list[str]
    output_instructions: str | None
    display_order: int

    model_config = {"from_attributes": True}
