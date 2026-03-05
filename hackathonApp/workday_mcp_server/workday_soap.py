"""
Workday SOAP client for the Staffing/Human_Resources Get_Workers operation.

Uses the staffing WSDL to derive the SOAP endpoint base; calls Human_Resources
Get_Workers with a SOAP envelope to fetch worker data by ID.
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

# Namespaces used in Workday SOAP
NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
NS_WD = "urn:com.workday/bsvc"


def _find_wsdl_path() -> Path:
    """Resolve path to staffingwsdl.xml (default: parent dir of this package)."""
    env_path = os.environ.get("WORKDAY_WSDL_PATH", "").strip()
    if env_path and os.path.isfile(env_path):
        return Path(env_path)
    this_dir = Path(__file__).resolve().parent
    # Default: hackathonApp/staffingwsdl.xml relative to workday_mcp_server
    default = this_dir.parent / "staffingwsdl.xml"
    if default.is_file():
        return default
    return this_dir.parent / "staffingwsdl.xml"


def get_soap_endpoint_base_from_wsdl(wsdl_path: Path | None = None) -> str:
    """
    Read the staffing WSDL and return the SOAP endpoint base URL.

    The WSDL address is like:
      https://wcpdev-services1.wd101.myworkday.com/ccx/service/hack116_wcpdev1/Scheduling/v46.0
    We strip the service and version to get the base:
      https://wcpdev-services1.wd101.myworkday.com/ccx/service/hack116_wcpdev1
    """
    path = wsdl_path or _find_wsdl_path()
    if not path.is_file():
        raise FileNotFoundError(f"WSDL file not found: {path}")
    content = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r'address\s+location="([^"]+)"', content)
    if not match:
        raise ValueError("Could not find address location in WSDL")
    full_url = match.group(1).strip()
    # Remove trailing /Scheduling/v46.0 (or similar) to get base
    base = re.sub(r"/[^/]+/v[\d.]+$", "", full_url.rstrip("/"))
    return base


def get_workers_soap_url(wsdl_path: Path | None = None, version: str = "v42.0") -> str:
    """Return the Human_Resources Get_Workers SOAP endpoint URL."""
    base = get_soap_endpoint_base_from_wsdl(wsdl_path)
    return f"{base}/Human_Resources/{version}"


def _build_get_workers_envelope(worker_id: str, id_type: str = "WID") -> str:
    """
    Build SOAP 1.1 envelope for Get_Workers_Request.

    worker_id: The worker identifier (WID, employee ID, or contingent worker ID).
    id_type: One of WID, Employee_ID, Contingent_Worker_ID.
    """
    # Escape for XML
    def esc(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    wid = esc(worker_id)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:wd="urn:com.workday/bsvc">
  <soapenv:Header/>
  <soapenv:Body>
    <wd:Get_Workers_Request>
      <wd:Request_References>
        <wd:Worker_Reference>
          <wd:ID wd:type="{esc(id_type)}">{wid}</wd:ID>
        </wd:Worker_Reference>
      </wd:Request_References>
    </wd:Get_Workers_Request>
  </soapenv:Body>
</soapenv:Envelope>"""


def _parse_get_workers_response(xml_body: str) -> dict:
    """Parse Get_Workers_Response SOAP body into a dict for JSON-friendly output."""
    root = ET.fromstring(xml_body)
    # Strip namespaces for easier traversal
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
        for k, v in list(el.attrib.items()):
            if "}" in k:
                new_k = k.split("}", 1)[1]
                del el.attrib[k]
                el.attrib[new_k] = v

    def elem_to_dict(el: ET.Element) -> dict | list | str | None:
        if el.text and el.text.strip() and len(el) == 0:
            return el.text.strip()
        if len(el) == 0 and (el.text or "").strip():
            return (el.text or "").strip()
        children = list(el)
        if not children:
            return (el.text or "").strip() or None
        out: dict = {}
        for child in children:
            key = child.tag
            val = elem_to_dict(child)
            if key in out:
                if not isinstance(out[key], list):
                    out[key] = [out[key]]
                out[key].append(val)
            else:
                out[key] = val
        return out

    body = root.find(f".//{{{NS_SOAP}}}Body") or root.find("Body")
    if body is None:
        return {"_raw": xml_body[:2000]}

    # Get_Workers_Response may be in wd namespace
    resp = body.find(f".//{{{NS_WD}}}Get_Workers_Response") or body.find("Get_Workers_Response")
    if resp is not None:
        return elem_to_dict(resp) or {}
    fault = body.find(f".//{{{NS_SOAP}}}Fault") or body.find("Fault")
    if fault is not None:
        return {"Fault": elem_to_dict(fault)}
    return {"_raw": ET.tostring(body, encoding="unicode", method="xml")[:2000]}


def get_worker_via_soap(
    worker_id: str,
    access_token: str,
    id_type: str = "WID",
    wsdl_path: Path | None = None,
    hr_version: str = "v42.0",
) -> dict:
    """
    Call Workday Human_Resources Get_Workers via SOAP and return the response as a dict.

    worker_id: Worker WID, Employee_ID, or Contingent_Worker_ID.
    access_token: Bearer token from workday_auth.
    id_type: WID, Employee_ID, or Contingent_Worker_ID.
    """
    url = get_workers_soap_url(wsdl_path=wsdl_path, version=hr_version)
    envelope = _build_get_workers_envelope(worker_id, id_type=id_type)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": "Get_Workers",
    }
    response = requests.post(url, data=envelope.encode("utf-8"), headers=headers, timeout=60)
    if not response.ok:
        raise ValueError(
            f"Workday SOAP error: {response.status_code} {response.reason}. "
            f"Details: {response.text[:1000]}"
        )
    return _parse_get_workers_response(response.text)
