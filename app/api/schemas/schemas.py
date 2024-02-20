from pydantic import BaseModel


class GroupBase(BaseModel):
    group_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "group_id": "test-group-1",
            }
        }


class CreateGroup(GroupBase):
    pass


class DeleteGroup(GroupBase):
    pass
