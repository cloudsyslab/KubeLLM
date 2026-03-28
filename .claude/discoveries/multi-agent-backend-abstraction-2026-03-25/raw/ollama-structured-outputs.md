[Skip to main content](https://docs.ollama.com/capabilities/structured-outputs#content-area)
[Ollama home page![light logo](https://mintcdn.com/ollama-9269c548/XefrxzvUktkk84RL/images/logo.png?fit=max&auto=format&n=XefrxzvUktkk84RL&q=85&s=03a38b5749aa7f530044e9b251dc10d8)![dark logo](https://mintcdn.com/ollama-9269c548/XefrxzvUktkk84RL/images/logo-dark.png?fit=max&auto=format&n=XefrxzvUktkk84RL&q=85&s=c214b467f5623414c31d4e05c66110fb)](https://ollama.com)
Search...
Ctrl K
##### Get started
  * [Welcome](https://docs.ollama.com/)
  * [Quickstart](https://docs.ollama.com/quickstart)
  * [Cloud](https://docs.ollama.com/cloud)


##### Capabilities
  * [Streaming](https://docs.ollama.com/capabilities/streaming)
  * [Thinking](https://docs.ollama.com/capabilities/thinking)
  * [Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs)
  * [Vision](https://docs.ollama.com/capabilities/vision)
  * [Embeddings](https://docs.ollama.com/capabilities/embeddings)
  * [Tool calling](https://docs.ollama.com/capabilities/tool-calling)
  * [Web search](https://docs.ollama.com/capabilities/web-search)


##### Integrations
  * [Overview](https://docs.ollama.com/integrations)
  * Assistants
    * [OpenClaw](https://docs.ollama.com/integrations/openclaw)
  * Coding
    * [Claude Code](https://docs.ollama.com/integrations/claude-code)
    * [Codex](https://docs.ollama.com/integrations/codex)
    * [OpenCode](https://docs.ollama.com/integrations/opencode)
    * [Droid](https://docs.ollama.com/integrations/droid)
    * [Goose](https://docs.ollama.com/integrations/goose)
    * [Pi](https://docs.ollama.com/integrations/pi)
  * IDEs & Editors
  * Chat & RAG
  * Automation
  * Notebooks


##### More information
  * [CLI Reference](https://docs.ollama.com/cli)
  * Assistant Sandboxing
  * [Modelfile Reference](https://docs.ollama.com/modelfile)
  * [Context length](https://docs.ollama.com/context-length)
  * [Linux](https://docs.ollama.com/linux)
  * [macOS](https://docs.ollama.com/macos)
  * [Windows](https://docs.ollama.com/windows)
  * [Docker](https://docs.ollama.com/docker)
  * [Importing a Model](https://docs.ollama.com/import)
  * [FAQ](https://docs.ollama.com/faq)
  * [Hardware support](https://docs.ollama.com/gpu)
  * [Troubleshooting](https://docs.ollama.com/troubleshooting)


  * [Sign in](https://ollama.com/signin)
  * [Download](https://ollama.com/download)


[Ollama home page![light logo](https://mintcdn.com/ollama-9269c548/XefrxzvUktkk84RL/images/logo.png?fit=max&auto=format&n=XefrxzvUktkk84RL&q=85&s=03a38b5749aa7f530044e9b251dc10d8)![dark logo](https://mintcdn.com/ollama-9269c548/XefrxzvUktkk84RL/images/logo-dark.png?fit=max&auto=format&n=XefrxzvUktkk84RL&q=85&s=c214b467f5623414c31d4e05c66110fb)](https://ollama.com)
Search...
Ctrl K
  * [Sign in](https://ollama.com/signin)
  * [Download](https://ollama.com/download)
  * [Download](https://ollama.com/download)


Search...
Navigation
Capabilities
Structured Outputs
[Documentation](https://docs.ollama.com/)[API Reference](https://docs.ollama.com/api/introduction)
[Documentation](https://docs.ollama.com/)[API Reference](https://docs.ollama.com/api/introduction)
Capabilities
# Structured Outputs
Copy page
Copy page
Structured outputs let you enforce a JSON schema on model responses so you can reliably extract structured data, describe images, or keep every reply consistent.
## 
[?](https://docs.ollama.com/capabilities/structured-outputs#generating-structured-json)
Generating structured JSON
  * cURL
  * Python
  * JavaScript


Copy

```
curl -X POST http://localhost:11434/api/chat -H "Content-Type: application/json" -d '{
  "model": "gpt-oss",
  "messages": [{"role": "user", "content": "Tell me about Canada in one line"}],
  "stream": false,
  "format": "json"
}'

```

Copy

```
from ollama import chat

response = chat(
  model='gpt-oss',
  messages=[{'role': 'user', 'content': 'Tell me about Canada.'}],
  format='json'
)
print(response.message.content)

```

Copy

```
import ollama from 'ollama'

const response = await ollama.chat({
  model: 'gpt-oss',
  messages: [{ role: 'user', content: 'Tell me about Canada.' }],
  format: 'json'
})
console.log(response.message.content)

```

## 
[?](https://docs.ollama.com/capabilities/structured-outputs#generating-structured-json-with-a-schema)
Generating structured JSON with a schema
Provide a JSON schema to the `format` field.
It is ideal to also pass the JSON schema as a string in the prompt to ground the model’s response.
  * cURL
  * Python
  * JavaScript


Copy

```
curl -X POST http://localhost:11434/api/chat -H "Content-Type: application/json" -d '{
  "model": "gpt-oss",
  "messages": [{"role": "user", "content": "Tell me about Canada."}],
  "stream": false,
  "format": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "capital": {"type": "string"},
      "languages": {
        "type": "array",
        "items": {"type": "string"}
      }
    },
    "required": ["name", "capital", "languages"]
  }
}'

```

Use Pydantic models and pass `model_json_schema()` to `format`, then validate the response:
Copy

```
from ollama import chat
from pydantic import BaseModel

class Country(BaseModel):
  name: str
  capital: str
  languages: list[str]

response = chat(
  model='gpt-oss',
  messages=[{'role': 'user', 'content': 'Tell me about Canada.'}],
  format=Country.model_json_schema(),
)

country = Country.model_validate_json(response.message.content)
print(country)

```

Serialize a Zod schema with `zodToJsonSchema()` and parse the structured response:
Copy

```
import ollama from 'ollama'
import { z } from 'zod'
import { zodToJsonSchema } from 'zod-to-json-schema'

const Country = z.object({
  name: z.string(),
  capital: z.string(),
  languages: z.array(z.string()),
})

const response = await ollama.chat({
  model: 'gpt-oss',
  messages: [{ role: 'user', content: 'Tell me about Canada.' }],
  format: zodToJsonSchema(Country),
})

const country = Country.parse(JSON.parse(response.message.content))
console.log(country)

```

## 
[?](https://docs.ollama.com/capabilities/structured-outputs#example-extract-structured-data)
Example: Extract structured data
Define the objects you want returned and let the model populate the fields:
Copy

```
from ollama import chat
from pydantic import BaseModel

class Pet(BaseModel):
  name: str
  animal: str
  age: int
  color: str | None
  favorite_toy: str | None

class PetList(BaseModel):
  pets: list[Pet]

response = chat(
  model='gpt-oss',
  messages=[{'role': 'user', 'content': 'I have two cats named Luna and Loki...'}],
  format=PetList.model_json_schema(),
)

pets = PetList.model_validate_json(response.message.content)
print(pets)

```

## 
[?](https://docs.ollama.com/capabilities/structured-outputs#example-vision-with-structured-outputs)
Example: Vision with structured outputs
Vision models accept the same `format` parameter, enabling deterministic descriptions of images:
Copy

```
from ollama import chat
from pydantic import BaseModel
from typing import Literal, Optional

class Object(BaseModel):
  name: str
  confidence: float
  attributes: str

class ImageDescription(BaseModel):
  summary: str
  objects: list[Object]
  scene: str
  colors: list[str]
  time_of_day: Literal['Morning', 'Afternoon', 'Evening', 'Night']
  setting: Literal['Indoor', 'Outdoor', 'Unknown']
  text_content: Optional[str] = None

response = chat(
  model='gemma3',
  messages=[{
    'role': 'user',
    'content': 'Describe this photo and list the objects you detect.',
    'images': ['path/to/image.jpg'],
  }],
  format=ImageDescription.model_json_schema(),
  options={'temperature': 0},
)

image_description = ImageDescription.model_validate_json(response.message.content)
print(image_description)

```

## 
[?](https://docs.ollama.com/capabilities/structured-outputs#tips-for-reliable-structured-outputs)
Tips for reliable structured outputs
  * Define schemas with Pydantic (Python) or Zod (JavaScript) so they can be reused for validation.
  * Lower the temperature (e.g., set it to `0`) for more deterministic completions.
  * Structured outputs work through the OpenAI-compatible API via `response_format`


[Previous](https://docs.ollama.com/capabilities/thinking)[ Vision Next ](https://docs.ollama.com/capabilities/vision)
Ctrl+I
On this page
  * [Generating structured JSON](https://docs.ollama.com/capabilities/structured-outputs#generating-structured-json)
  * [Generating structured JSON with a schema](https://docs.ollama.com/capabilities/structured-outputs#generating-structured-json-with-a-schema)
  * [Example: Extract structured data](https://docs.ollama.com/capabilities/structured-outputs#example-extract-structured-data)
  * [Example: Vision with structured outputs](https://docs.ollama.com/capabilities/structured-outputs#example-vision-with-structured-outputs)
  * [Tips for reliable structured outputs](https://docs.ollama.com/capabilities/structured-outputs#tips-for-reliable-structured-outputs)



