"""Scaffold orchestration and suborchestration files."""
from __future__ import annotations

from .common import app_root, pascal, write_json, result

_VALID = {"SYNCHRONOUS", "ASYNCHRONOUS", "BUSINESS_PROCESS", "HOME_CARD", "INTEGRATION_SYSTEM"}


def create_orchestration(app: str, name: str, orch_type: str = "SYNCHRONOUS") -> str:
    app_dir = app_root(app)
    orch = app_dir / "orchestration"
    created: list[str] = []
    oid = pascal(name)
    ot = orch_type.upper()
    if ot not in _VALID:
        ot = "SYNCHRONOUS"
    definition = {
        "id": oid,
        "type": ot,
        "startStep": "start",
        "steps": [
            {"id": "start", "name": "Start", "type": "CreateValues",
             "description": "Initialize orchestration inputs."},
            {"id": "process", "name": "Process", "type": "ImplicitGroup",
             "description": "Add data requests / operations here."},
        ],
        "globalErrorHandler": {"strategy": "GlobalErrorHandler",
                               "isContinueAfterError": False, "overrideSeverity": "ERROR"},
    }
    write_json(orch / f"{oid}.orchestration", definition, created)
    notes = [
        f"Orchestration '{oid}' type={ot}.",
        "Build step bodies in Orchestration Builder; never hardcode credentials.",
        "Add local error handlers on Group nodes plus the global handler included.",
        f"Validate:  wdcli app validate {app_dir}",
    ]
    return result(created, notes)


def create_suborchestration(app: str, name: str,
                            input_variables: list[str] | None = None,
                            output_variables: list[str] | None = None,
                            with_error_handling: bool = True) -> str:
    app_dir = app_root(app)
    orch = app_dir / "orchestration"
    created: list[str] = []
    sid = pascal(name)
    inputs = input_variables or ["input1"]
    outputs = output_variables or ["result"]
    steps = [
        {"id": "init", "name": "Init", "type": "CreateValues",
         "description": "Map input variables."},
        {"id": "work", "name": "Work", "type": "ImplicitGroup",
         "description": "Core sub-flow logic."},
    ]
    definition = {
        "id": sid,
        "inputVariables": inputs,
        "outputVariables": outputs,
        "steps": steps,
    }
    if with_error_handling:
        definition["errorHandler"] = {
            "strategy": "ConditionalOutputs",
            "isContinueAfterError": False,
            "overrideSeverity": "ERROR",
            "description": "Local error handler (pattern: OSK141_EH_API_Full).",
        }
    write_json(orch / f"{sid}.suborchestration", definition, created)
    notes = [
        f"Suborchestration '{sid}'  inputs={inputs} outputs={outputs}.",
        "Invoke via a 'Call Subflow' step with subflowId in the parent orchestration.",
        "Reference OSK141 family for full error-handling step bodies.",
    ]
    return result(created, notes)
