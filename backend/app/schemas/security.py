from pydantic import BaseModel, Field, model_validator


class DestructiveSecurityRead(BaseModel):
    require_password_for_sale_delete: bool
    require_password_for_purchase_delete: bool
    configured: bool


class DestructiveSecurityUpdate(BaseModel):
    current_credential: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)
    confirm_password: str = Field(min_length=8, max_length=256)

    @model_validator(mode="after")
    def passwords_match(self) -> "DestructiveSecurityUpdate":
        if self.new_password != self.confirm_password:
            raise ValueError("New deletion passwords do not match")
        return self
