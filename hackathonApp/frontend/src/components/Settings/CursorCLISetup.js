/**
 * Cursor CLI setup instructions and config for connecting Cursor to the Workday MCP server.
 * Shown in the Settings tab so developers can connect Cursor to the agent/MCP tools.
 */
import React, { useState } from 'react';

const MCP_CONFIG_SNIPPET = `{
  "mcpServers": {
    "workday": {
      "command": "python",
      "args": ["workday_mcp_server/server.py"]
    }
  }
}`;

const MCP_CONFIG_GLOBAL_SNIPPET = `{
  "mcpServers": {
    "workday": {
      "command": "python",
      "args": ["/absolute/path/to/hackathonApp/workday_mcp_server/server.py"]
    }
  }
}`;

function CursorCLISetup() {
  const [copied, setCopied] = useState(false);
  const [copiedGlobal, setCopiedGlobal] = useState(false);

  const copySnippet = (text, setter) => {
    navigator.clipboard.writeText(text).then(() => {
      setter(true);
      setTimeout(() => setter(false), 2000);
    });
  };

  return (
    <div className="card" style={{ marginTop: '24px' }}>
      <h3>Cursor CLI / Workday MCP</h3>
      <p style={{ color: '#666', marginBottom: '16px' }}>
        Connect Cursor to the Workday MCP server to use Workday tools (e.g. <code>get_worker_profile</code>) from Cursor. The agent backend is tied to this MCP server.
      </p>

      <h4 style={{ marginTop: '16px', marginBottom: '8px' }}>1. Prerequisites</h4>
      <ul style={{ color: '#444', marginBottom: '16px', paddingLeft: '20px' }}>
        <li>Clone this repo and open it as the project root in Cursor.</li>
        <li>Configure <code>workday_mcp_server/.env</code> with your Workday credentials (see SETUP.md).</li>
        <li>Install Python dependencies in <code>workday_mcp_server</code> (e.g. <code>pip install -r requirements.txt</code>).</li>
      </ul>

      <h4 style={{ marginTop: '16px', marginBottom: '8px' }}>2. Add the MCP server to Cursor</h4>
      <p style={{ color: '#444', marginBottom: '8px' }}>
        Create or edit <code>.cursor/mcp.json</code> in your <strong>project root</strong> (this repo):
      </p>
      <div style={{ position: 'relative' }}>
        <pre style={{
          background: '#f5f5f5',
          border: '1px solid #ddd',
          borderRadius: '6px',
          padding: '12px',
          paddingTop: '36px',
          overflow: 'auto',
          fontSize: '13px',
        }}>
          <code>{MCP_CONFIG_SNIPPET}</code>
        </pre>
        <button
          type="button"
          className="btn btn-secondary"
          style={{ position: 'absolute', top: '8px', right: '8px', fontSize: '12px' }}
          onClick={() => copySnippet(MCP_CONFIG_SNIPPET, setCopied)}
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <p style={{ fontSize: '13px', color: '#666', marginTop: '8px' }}>
        This runs the server from the project root so <code>workday_mcp_server/.env</code> is loaded correctly.
      </p>

      <p style={{ color: '#444', marginTop: '16px', marginBottom: '8px' }}>
        Or use a <strong>global</strong> config at <code>~/.cursor/mcp.json</code> with the full path to <code>server.py</code>:
      </p>
      <div style={{ position: 'relative' }}>
        <pre style={{
          background: '#f5f5f5',
          border: '1px solid #ddd',
          borderRadius: '6px',
          padding: '12px',
          paddingTop: '36px',
          overflow: 'auto',
          fontSize: '13px',
        }}>
          <code>{MCP_CONFIG_GLOBAL_SNIPPET}</code>
        </pre>
        <button
          type="button"
          className="btn btn-secondary"
          style={{ position: 'absolute', top: '8px', right: '8px', fontSize: '12px' }}
          onClick={() => copySnippet(MCP_CONFIG_GLOBAL_SNIPPET, setCopiedGlobal)}
        >
          {copiedGlobal ? 'Copied!' : 'Copy'}
        </button>
      </div>

      <h4 style={{ marginTop: '16px', marginBottom: '8px' }}>3. Restart Cursor</h4>
      <p style={{ color: '#444', marginBottom: '8px' }}>
        Restart Cursor completely after editing <code>mcp.json</code> for the new server to appear. You can then use the Workday tools (e.g. get_worker_profile) from Cursor.
      </p>
    </div>
  );
}

export default CursorCLISetup;
