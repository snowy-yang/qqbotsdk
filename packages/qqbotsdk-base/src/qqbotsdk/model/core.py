from pydantic import BaseModel, ConfigDict


class QQBotBaseModel(BaseModel):
    model_config = ConfigDict(
        validate_by_name=True,
        serialize_by_alias=True,
        extra="allow",
    )
