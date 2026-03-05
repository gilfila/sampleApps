"""In-process agent for Get-Help channel and Cursor CLI.

Returns placeholder or future LLM/tool-calling responses. Used when messages
are sent to #Get-Help (wire) and by the agent chat API.
"""

import logging

logger = logging.getLogger(__name__)


def get_agent_reply(message_text: str, user_id=None, context=None) -> str:
    """
    Generate an agent reply for a user message (e.g. from #Get-Help).

    MVP: returns a helpful placeholder. Later: call LLM with tool-use for
    tickets, worker lookup, etc.
    """
    if not (message_text or "").strip():
        return "Please send a message and I'll help you."
    # Placeholder response; can be extended with real LLM + tools
    return (
        "Thanks for your message. I'm the hackathon assistant. "
        "You can create a ticket from the Tickets page, or ask here for help. "
        "Experts may follow up in this channel."
    )
