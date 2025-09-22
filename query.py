import argparse
import os, time

from azure.ai.projects import AIProjectClient
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import DeepResearchTool, MessageRole, ThreadMessage
from azure.identity import DefaultAzureCredential

# based on https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-agents/samples/agents_tools/sample_agents_deep_research.py
# (and https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/ai/azure-ai-agents/samples/agents_async/sample_agents_deep_research_async.py)

class DeepResearcher:
    def __init__(self, verbose=False):
        self.verbose = verbose

        self.project_client = AIProjectClient(
            endpoint=os.environ["PROJECT_ENDPOINT"],
            credential=DefaultAzureCredential(),
        )

        self.bing_connection = self.project_client.connections.get(name=os.environ["BING_RESOURCE_NAME"])

        # Initialize a Deep Research tool with Bing Connection ID and Deep Research model deployment name
        self.deep_research_tool = DeepResearchTool(
            bing_grounding_connection_id=self.bing_connection.id,
            deep_research_model=os.environ["DEEP_RESEARCH_MODEL_DEPLOYMENT_NAME"],
        )

    def _vprint(self, *args, **kwargs):
        if self.verbose: print(*args, **kwargs)

    def create_agent(self, prompt):
        self.agent = self.project_client.agents.create_agent(
            model=os.environ["MODEL_DEPLOYMENT_NAME"],
            name="my-agent",
            instructions=prompt,
            tools=self.deep_research_tool.definitions,
        )
        self._vprint(f"Created agent, ID: {self.agent.id}")

        self.thread = self.project_client.agents.threads.create()
        self._vprint(f"Created thread, ID: {self.thread.id}")

    def send_message(self, msg, output_name):
        tmp_name = f"tmp_{output_name}"

        message = self.project_client.agents.messages.create(
            thread_id=self.thread.id,
            role="user",
            content=(msg),
        )
        self._vprint(f"Created message, ID: {message.id}")

        self._vprint(f"Start processing the message... this may take a few minutes to finish. Be patient!")
        run = self.project_client.agents.runs.create(thread_id=self.thread.id, agent_id=self.agent.id)
        last_message_id = None
        while run.status in ("queued", "in_progress"):
            time.sleep(1)
            run = self.project_client.agents.runs.get(thread_id=self.thread.id, run_id=run.id)
            last_message_id = self.fetch_response(last_message_id, tmp_name)
            self._vprint(f"Run status: {run.status}")

        self._vprint(f"Run finished with status: {run.status}, ID: {run.id}")
        if run.status == "failed":
            print(f"Run failed: {run.last_error}")
            return

        # Fetch the final message from the agent in the thread and create a research summary
        final_message = self.project_client.agents.messages.get_last_message_by_role(
            thread_id=self.thread.id,
            role=MessageRole.AGENT
        )
        if final_message:
            self.create_summary(final_message, output_name)
        else:
            print("Could not find final message")

        # Clean-up and delete the agent once the run is finished.
        self.project_client.agents.delete_agent(self.agent.id)
        self._vprint("Deleted agent")

    def fetch_response(self, last_message_id, tmp_name):
        response = self.project_client.agents.messages.get_last_message_by_role(
            thread_id=self.thread.id,
            role=MessageRole.AGENT,
        )

        # No new content, or not a "cot_summary"
        if not response or response.id == last_message_id or not any(t.text.value.startswith("cot_summary:") for t in response.text_messages):
            return last_message_id

        # Write progress to file
        agent_text = "\n".join(t.text.value.replace("cot_summary:", "Reasoning:") for t in response.text_messages)
        with open(tmp_name, "a", encoding="utf-8") as fp:
            fp.write("\nAGENT>\n")
            fp.write(agent_text)
            fp.write("\n")

            for ann in response.url_citation_annotations:
                fp.write(f"Citation: [{ann.url_citation.title}]({ann.url_citation.url})\n")

        return response.id

    def create_summary(self, message, output_name):
        with open(output_name, 'w', encoding="utf-8") as fp:
            text_summary = "\n\n".join([t.text.value.strip() for t in message.text_messages])
            fp.write(text_summary)

            if message.url_citation_annotations:
                fp.write("\n\n## Citations\n")
                seen_urls = set()
                # Dictionary mapping full citation content to ordinal number
                citations_ordinals: Dict[str, int] = {}
                # List of citation URLs indexed by ordinal (0-based)
                text_citation_list: List[str] = []

                for ann in message.url_citation_annotations:
                    url = ann.url_citation.url
                    title = ann.url_citation.title or url

                    if url not in seen_urls:
                        # Use the full annotation text as the key to avoid conflicts
                        citation_key = ann.text if ann.text else f"fallback_{url}"

                        # Only add if this citation content hasn't been seen before
                        if citation_key not in citations_ordinals:
                            # Assign next available ordinal number (1-based for display)
                            ordinal = len(text_citation_list) + 1
                            citations_ordinals[citation_key] = ordinal
                            text_citation_list.append(f"[{title}]({url})")

                        seen_urls.add(url)

                # Write citations in order they were added
                for i, citation_text in enumerate(text_citation_list):
                    fp.write(f"{i + 1}. {citation_text}\n")

def read(filename):
    with open(filename,'r') as file:
        return file.read()

def main(prompt_name, input_name, output_name, verbose=False):
    prompt = read(prompt_name)
    input = read(input_name)

    researcher = DeepResearcher(verbose=verbose)
    researcher.create_agent(prompt)
    researcher.send_message(input, output_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-p", "--prompt", type=str, default="default_prompt.txt", help="prompt to initialize agent")
    parser.add_argument("-i", "--input", type=str, required=True, help="input txt file with query")
    parser.add_argument("-o", "--output", type=str, required=True, help="output txt file for response")
    parser.add_argument("-v", "--verbose", default=False, action="store_true", help="enable verbosity")
    args = parser.parse_args()

    main(args.prompt, args.input, args.output, args.verbose)
