"""Scaffolding generators for Workday Extend artifacts."""
from .extend_app import create_extend_app
from .pmd_page import add_pmd_page
from .business_object import create_business_object
from .orchestration import create_orchestration, create_suborchestration
from .agent import create_agent

__all__ = [
    "create_extend_app", "add_pmd_page", "create_business_object",
    "create_orchestration", "create_suborchestration", "create_agent",
]
