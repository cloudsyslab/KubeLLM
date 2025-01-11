from pydantic import (
    BaseModel, 
    FilePath, 
    field_validator, 
    AnyUrl, 
    model_validator, 
    PlainSerializer
)
from pydantic.types import StringConstraints
from typing_extensions import Annotated
from typing import List, Any, Optional, TypeAlias

NonEmptyStr: TypeAlias = Annotated[str, StringConstraints(min_length=1)]

class CommandOutput(BaseModel):
    invocation: NonEmptyStr
    stdout: NonEmptyStr = '<|no output|>'
    stderr: NonEmptyStr = '<|no output|>'

    @field_validator('stdout', 'stderr', mode='before')
    @classmethod
    def _empty_to_default(cls, field_value: Any):
        '''If a command had no stdout or no stderr or both,
        then we should tell that to the model. Otherwise,
        the model will believe that we purposely withheld
        the output, or that the RAG tool messed up somewhere.
        '''
        if not field_value or field_value == "":
            return '<|no output|>'
        return field_value

class Model(BaseModel):
    name: NonEmptyStr
    host: Annotated[AnyUrl, PlainSerializer(lambda url: str(url))]
    api_key: Optional[NonEmptyStr] = None

    @model_validator(mode='before')
    def validate_api_key(cls, values: Any):
        if isinstance(values, dict):
            if "gpt" in values["name"] and not "api_key" in values:
                raise ValueError("Model must include 'api_key' if using openai.")
        return values

class Statement(BaseModel):
    problem_description: NonEmptyStr
    goal: NonEmptyStr
    relevant_command_output: List[CommandOutput] = []
    relevant_files: List[FilePath] = []
    use_rag: bool = True
    model: Model