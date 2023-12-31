"""
server.py
Author: Gene Ruebsamen

This file is part of OpenAI-Text-Generation-Inference-Server.

OpenAI-Text-Generation-Inference-Server is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

OpenAI-Text-Generation-Inference-Server is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with OpenAI-Text-Generation-Inference-Server. If not, see <https://www.gnu.org/licenses/>.
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import json
import random
#import openai
import asyncio
import os
import boto3

load_dotenv()

bedrock_control_plane = boto3.client('bedrock', 'us-west-2')
print(bedrock_control_plane.list_foundation_models())

bedrock = boto3.client('bedrock-runtime', 'us-west-2')

model_id = "anthropic.claude-v2"
print(model_id)

accept = "application/json"
content_type = "application/json"

app = FastAPI()

#openai.api_key = os.environ['OPENAI_API_KEY']
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 100

class RequestBody(BaseModel):
    inputs: str
    parameters: Optional[dict]

async def get_bedrock_stream_data(request):
#    events = await openai.ChatCompletion.acreate(
#        model="gpt-3.5-turbo",
#        messages=[{"role": "user", "content": request.inputs}],
#        stream=True,
#        temperature = request.parameters['temperature'] if 'parameters' in request else DEFAULT_TEMPERATURE,
#        max_tokens = request.parameters['max_tokens'] if 'parameters' in request else DEFAULT_MAX_TOKENS,
#        )
    max_tokens = request.parameters['max_tokens'] if 'parameters' in request else DEFAULT_MAX_TOKENS
    temperature = request.parameters['temperature'] if 'parameters' in request else DEFAULT_TEMPERATURE

    body = json.dumps(
      {
        "prompt": request.inputs,
        "max_tokens_to_sample": max_tokens,
        "temperature": temperature
      }
    )

#    try:
    response = bedrock.invoke_model_with_response_stream(
      body=body, 
      modelId=model_id, 
      accept=accept, 
      contentType=content_type
    )
        
    events = response.get('body')
#    output = []

#      for event in events:
#            chunk = event.get('chunk')
#            if chunk:
#                chunk_obj = json.loads(chunk.get('bytes').decode())
#                text = chunk_obj['completion']
#                clear_output(wait=True)
#                output.append(text)
#                display_markdown(Markdown(''.join(output)))
#            
#    except botocore.exceptions.ClientError as error:
#      if error.response['Error']['Code'] == 'AccessDeniedException':
#        print(f"\x1b[41m{error.response['Error']['Message']}\
#                \nTo troubeshoot this issue please refer to the following resources.\
#                 \nhttps://docs.aws.amazon.com/IAM/latest/UserGuide/troubleshoot_access-denied.html\
#                 \nhttps://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html\x1b[0m\n")
#        
#      else:
#        raise error

    gen_text = ""
    end = "\n\n"
    tok_cnt = 0

    #async for event in events:
    for event in events:
        print(event)
        chunk = event.get('chunk')
        try:      
#            content = event['choices'][0]['delta']['content']
            chunk_obj = json.loads(chunk.get('bytes').decode())
            content = chunk_obj['completion']
            finish_reason = chunk_obj['stop_reason']
        except KeyError:
            content = None
#        finish_reason = event['choices'][0]['finish_reason']
        tok_cnt += 1
        if content: # or finish_reason != None:
#            if content:
            gen_text += content
            final_text = None
            details = None
            special = False
            if finish_reason != None and 'null' not in finish_reason:
                final_text = gen_text
                special = True
                details = {"finish_reason":finish_reason,"generated_tokens":tok_cnt-1,"seed":None}
                end = "\n\n\n"
            tok = {
                "token": {
                    "id": random.randrange(0, 2**32),
                    "text": content,
                    "logprob": 0,
                    "special": special,
                },
                "generated_text": final_text,
                "details": details
            }
            json_string = json.dumps(tok,separators=(',', ':'))
            result = f"data:{json_string}"
            print(result)
            yield result + end
            await asyncio.sleep(0)  # Allow other tasks to run

@app.post("/generate_stream")
async def chat_completions(request: RequestBody):
    return StreamingResponse(get_bedrock_stream_data(request), media_type="text/event-stream", headers={"Content-Type": "text/event-stream"})
