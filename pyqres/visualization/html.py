"""Self-contained HTML visualizations for pyqres operations.

The Python side exports a structural JSON model.  The browser handles
expand/collapse state and circuit redraws, so generated HTML files are static
and do not need a local server.
"""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any

from pyqres.core.metadata import RegisterMetadata
from pyqres.core.operation import Primitive
from pyqres.core.utils import merge_controllers


def _json_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(val) for key, val in value.items()}
    if hasattr(value, "__name__"):
        return value.__name__
    return repr(value)


def _controller_data(controllers: dict) -> dict:
    return {name: _json_value(items) for name, items in controllers.items() if items}


def _controller_registers(controllers: dict) -> list[str]:
    regs = []
    for items in controllers.values():
        for item in items:
            if isinstance(item, dict):
                regs.extend(str(reg) for reg in item.keys())
            elif isinstance(item, tuple):
                regs.append(str(item[0]))
            else:
                regs.append(str(item))
    return regs


def _node_registers(node) -> list[str]:
    regs = [str(reg) for reg in getattr(node, "reg_list", [])]
    regs.extend(str(reg) for reg, _size in getattr(node, "temp_reg_list", []))
    return regs


def operation_to_tree_data(operation) -> dict:
    """Return a JSON-serializable operation tree model."""
    counter = {"value": 0}
    metadata = RegisterMetadata.get_register_metadata()
    register_size_hints = {str(name): str(size) for name, size in metadata.registers.items()}
    register_type_hints = {
        str(name): metadata.register_types.get(name, "General")
        for name in metadata.registers
    }
    registers = [
        {
            "name": str(name),
            "size": str(size),
            "type": metadata.register_types.get(name, "General"),
        }
        for name, size in metadata.registers.items()
    ]

    def next_id() -> str:
        counter["value"] += 1
        return f"n{counter['value']}"

    def record_register_hints(node) -> None:
        for reg, size in getattr(node, "temp_reg_list", []):
            register_size_hints.setdefault(str(reg), str(size))
            register_type_hints.setdefault(str(reg), "General")

        class_name = node.__class__.__name__
        if class_name == "SplitRegister":
            for reg, size in zip(getattr(node, "reg_list", [])[1:], getattr(node, "param_list", [])):
                register_size_hints[str(reg)] = str(size)
                register_type_hints.setdefault(str(reg), "General")
        elif class_name in ("AddRegister", "AddRegisterWithHadamard") and len(getattr(node, "param_list", [])) >= 3:
            reg, reg_type, size = node.param_list[:3]
            register_size_hints[str(reg)] = str(size)
            register_type_hints[str(reg)] = str(reg_type)

    def build(node, dagger_ctx=False, controllers_ctx=None, depth=0, path="0"):
        controllers_ctx = controllers_ctx or {}
        record_register_hints(node)
        node_id = next_id()
        merged_controllers = merge_controllers(controllers_ctx, getattr(node, "controllers", {}))
        effective_dagger = bool(getattr(node, "dagger_flag", False) ^ dagger_ctx)
        children_dagger = effective_dagger
        if node.is_self_conjugate():
            children_dagger = False

        program_list = list(getattr(node, "program_list", []))
        if isinstance(node, Primitive):
            program_list = []
        elif children_dagger:
            program_list = list(reversed(program_list))

        children = [
            build(child, children_dagger, merged_controllers, depth + 1, f"{path}.{idx}")
            for idx, child in enumerate(program_list)
        ]

        kind = "primitive" if isinstance(node, Primitive) else "composite"
        if node.__class__.__name__ in ("SplitRegister", "CombineRegister", "AddRegister", "RemoveRegister"):
            kind = "register"

        return {
            "id": node_id,
            "path": path,
            "name": node.name,
            "kind": kind,
            "depth": depth,
            "registers": _node_registers(node),
            "registerSizes": {
                reg: register_size_hints.get(reg, "?")
                for reg in _node_registers(node)
            },
            "params": _json_value(getattr(node, "param_list", [])),
            "submodules": _json_value(getattr(node, "submodules", [])),
            "controllers": _controller_data(merged_controllers),
            "controllerRegisters": _controller_registers(merged_controllers),
            "dagger": effective_dagger,
            "children": children,
        }

    tree = build(operation)
    register_names = {reg["name"] for reg in registers}

    def collect_regs(node):
        for reg in node["registers"] + node["controllerRegisters"]:
            if reg not in register_names:
                register_names.add(reg)
                registers.append({
                    "name": reg,
                    "size": register_size_hints.get(reg, "?"),
                    "type": register_type_hints.get(reg, "Unknown"),
                })
        for child in node["children"]:
            collect_regs(child)

    collect_regs(tree)
    return {"root": tree, "registers": registers}


def render_call_tree_html(operation, title: str | None = None) -> str:
    """Render an expandable operation call tree as a standalone HTML page."""
    data = operation_to_tree_data(operation)
    page_title = title or f"{operation.name} call tree"
    return _render_html(page_title, data, mode="tree")


def render_circuit_html(operation, title: str | None = None) -> str:
    """Render an interactive register-level circuit as standalone HTML."""
    data = operation_to_tree_data(operation)
    page_title = title or f"{operation.name} circuit"
    return _render_html(page_title, data, mode="circuit")


def write_call_tree_html(operation, path: str | Path, title: str | None = None) -> Path:
    """Write an expandable operation call tree HTML file."""
    output = Path(path)
    output.write_text(render_call_tree_html(operation, title), encoding="utf-8")
    return output


def write_circuit_html(operation, path: str | Path, title: str | None = None) -> Path:
    """Write an interactive register-level circuit HTML file."""
    output = Path(path)
    output.write_text(render_circuit_html(operation, title), encoding="utf-8")
    return output


def _render_html(title: str, data: dict, mode: str) -> str:
    data_json = json.dumps(data, ensure_ascii=False)
    title_html = escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title_html}</title>
  <style>
    :root {{
      --bg: #f7f8fb;
      --panel: #ffffff;
      --ink: #1f2937;
      --muted: #667085;
      --line: #d8dee9;
      --accent: #2563eb;
      --accent-soft: #dbeafe;
      --gate: #eef4ff;
      --gate-border: #7aa2f7;
      --reg: #f8fafc;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--bg);
    }}
    header {{
      padding: 18px 24px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    h1 {{
      margin: 0;
      font-size: 20px;
      font-weight: 650;
      letter-spacing: 0;
    }}
    main {{
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr);
      min-height: calc(100vh - 62px);
    }}
    aside {{
      border-right: 1px solid var(--line);
      background: var(--panel);
      padding: 16px;
      overflow: auto;
    }}
    section {{
      padding: 18px;
      overflow: auto;
    }}
    .control-group {{
      margin-bottom: 18px;
    }}
    .control-group h2 {{
      margin: 0 0 10px;
      font-size: 13px;
      text-transform: uppercase;
      color: var(--muted);
      letter-spacing: .04em;
    }}
    .module-row {{
      display: grid;
      grid-template-columns: 18px minmax(0, 1fr);
      gap: 8px;
      align-items: start;
      margin: 7px 0;
      font-size: 13px;
    }}
    .module-row span {{
      overflow-wrap: anywhere;
    }}
    .muted {{
      color: var(--muted);
    }}
    input[type="range"] {{
      width: 100%;
    }}
    .tree-root {{
      max-width: 1100px;
    }}
    details {{
      margin: 6px 0 6px 16px;
      border-left: 1px solid var(--line);
      padding-left: 10px;
    }}
    details.root {{
      margin-left: 0;
      border-left: 0;
      padding-left: 0;
    }}
    summary {{
      cursor: pointer;
      list-style: none;
      display: flex;
      align-items: center;
      gap: 8px;
      min-height: 30px;
    }}
    summary::-webkit-details-marker {{
      display: none;
    }}
    .twisty {{
      color: var(--accent);
      width: 14px;
      display: inline-block;
    }}
    details[open] > summary .twisty {{
      transform: rotate(90deg);
    }}
    .node-name {{
      font-weight: 620;
    }}
    .badge {{
      border: 1px solid var(--line);
      color: var(--muted);
      padding: 2px 6px;
      border-radius: 999px;
      font-size: 11px;
      background: #fff;
    }}
    .node-details {{
      margin: 4px 0 10px 22px;
      font-size: 12px;
      color: var(--muted);
      display: grid;
      gap: 3px;
    }}
    .circuit-wrap {{
      min-width: 720px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: auto;
    }}
    .circuit-grid {{
      position: relative;
      display: grid;
      gap: 0;
      padding: 14px 12px;
      min-width: max-content;
    }}
    .reg-label {{
      background: var(--reg);
      border-right: 1px solid var(--line);
      padding: 11px 12px;
      font-size: 13px;
      white-space: nowrap;
      z-index: 2;
    }}
    .wire {{
      align-self: center;
      height: 1px;
      background: var(--line);
      z-index: 1;
    }}
    .gate {{
      align-self: center;
      justify-self: center;
      min-width: 86px;
      max-width: 116px;
      min-height: 30px;
      padding: 6px 8px;
      border: 1px solid var(--gate-border);
      background: var(--gate);
      border-radius: 6px;
      text-align: center;
      font-size: 12px;
      line-height: 1.2;
      z-index: 3;
      box-shadow: 0 1px 3px rgba(31, 41, 55, .08);
      overflow-wrap: anywhere;
    }}
    .gate.composite {{
      border-color: #16a34a;
      background: #ecfdf3;
    }}
    .gate.register {{
      border-color: #d97706;
      background: #fff7ed;
    }}
    .vline {{
      justify-self: center;
      width: 1px;
      background: var(--gate-border);
      z-index: 2;
    }}
    .empty {{
      padding: 20px;
      color: var(--muted);
    }}
  </style>
</head>
<body>
  <header><h1>{title_html}</h1></header>
  <main>
    <aside id="sidebar"></aside>
    <section id="content"></section>
  </main>
  <script>
    window.PYQRES_VIS_MODE = {json.dumps(mode)};
    window.PYQRES_TREE_DATA = {data_json};
  </script>
  <script>
    const data = window.PYQRES_TREE_DATA;
    const mode = window.PYQRES_VIS_MODE;
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('content');

    function formatValue(value) {{
      if (value === null || value === undefined) return '';
      if (typeof value === 'object') return JSON.stringify(value);
      return String(value);
    }}

    function collectCompositeNodes(node, out = []) {{
      if (node.children && node.children.length) out.push(node);
      for (const child of node.children || []) collectCompositeNodes(child, out);
      return out;
    }}

    function allNodes(node, out = []) {{
      out.push(node);
      for (const child of node.children || []) allNodes(child, out);
      return out;
    }}

    function involvedRegisters(node) {{
      const regs = new Set([...(node.registers || []), ...(node.controllerRegisters || [])]);
      for (const child of node.children || []) {{
        for (const reg of involvedRegisters(child)) regs.add(reg);
      }}
      return Array.from(regs);
    }}

    function detailLines(node) {{
      const lines = [];
      if (node.registers?.length) lines.push(['registers', node.registers.join(', ')]);
      if (node.controllerRegisters?.length) lines.push(['controllers', node.controllerRegisters.join(', ')]);
      if (node.params?.length) lines.push(['params', formatValue(node.params)]);
      if (Object.keys(node.controllers || {{}}).length) lines.push(['control detail', formatValue(node.controllers)]);
      if (node.submodules?.length) lines.push(['submodules', formatValue(node.submodules)]);
      return lines;
    }}

    function renderSidebar() {{
      const composites = allNodes(data.root).filter(n => n.kind === 'composite');
      let html = '<div class="control-group"><h2>View</h2>';
      html += `<label class="module-row"><input type="radio" name="mode" value="tree" ${{mode === 'tree' ? 'checked' : ''}}><span>Call tree</span></label>`;
      html += `<label class="module-row"><input type="radio" name="mode" value="circuit" ${{mode === 'circuit' ? 'checked' : ''}}><span>Register circuit</span></label>`;
      html += '</div>';
      html += '<div class="control-group"><h2>Expansion depth</h2><input id="depthSlider" type="range" min="0" max="12" value="1"><div class="muted">Depth: <span id="depthValue">1</span></div><div class="muted">0 keeps the root collapsed; each step expands one more module level.</div></div>';
      html += '<div class="control-group"><h2>Expand modules</h2>';
      if (!composites.length) {{
        html += '<div class="muted">No composite modules with children.</div>';
      }} else {{
        for (const node of composites) {{
          const label = node.id === data.root.id ? `${{node.path}} ${{escapeHtml(node.name)}} (root)` : `${{node.path}} ${{escapeHtml(node.name)}}`;
          html += `<label class="module-row"><input type="checkbox" class="module-toggle" value="${{node.id}}"><span>${{label}}</span></label>`;
        }}
      }}
      html += '</div>';
      sidebar.innerHTML = html;
      sidebar.querySelectorAll('input[name="mode"]').forEach(input => {{
        input.addEventListener('change', () => render(input.value));
      }});
      sidebar.querySelectorAll('input').forEach(input => {{
        if (input.name !== 'mode') input.addEventListener('input', () => render(currentMode()));
      }});
    }}

    function currentMode() {{
      return sidebar.querySelector('input[name="mode"]:checked')?.value || mode;
    }}

    function selectedDepth() {{
      return Number(document.getElementById('depthSlider')?.value || 1);
    }}

    function selectedModules() {{
      return new Set(Array.from(sidebar.querySelectorAll('.module-toggle:checked')).map(input => input.value));
    }}

    function escapeHtml(value) {{
      return String(value).replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
    }}

    function renderTreeNode(node, root = false) {{
      const details = detailLines(node).map(([k, v]) => `<div><strong>${{escapeHtml(k)}}:</strong> ${{escapeHtml(v)}}</div>`).join('');
      const children = (node.children || []).map(child => renderTreeNode(child)).join('');
      return `<details class="${{root ? 'root' : ''}}" open>
        <summary><span class="twisty">&#9654;</span><span class="node-name">${{escapeHtml(node.name)}}${{node.dagger ? '&dagger;' : ''}}</span><span class="badge">${{node.kind}}</span><span class="badge">${{node.path}}</span></summary>
        <div class="node-details">${{details}}</div>
        ${{children}}
      </details>`;
    }}

    function flattenCircuit(node, depth, expandById, maxDepth) {{
      const hasChildren = node.children && node.children.length;
      const canExpand = hasChildren && (expandById.has(node.id) || depth < maxDepth);
      if (canExpand) {{
        return node.children.flatMap(child => flattenCircuit(child, depth + 1, expandById, maxDepth));
      }}
      return [node];
    }}

    function registerOrder(ops) {{
      const known = data.registers.map(reg => reg.name);
      const seen = new Set();
      const ordered = [];
      for (const reg of known) {{
        if (!seen.has(reg)) {{
          seen.add(reg);
          ordered.push(reg);
        }}
      }}
      for (const op of ops) {{
        for (const reg of [...(op.registers || []), ...(op.controllerRegisters || [])]) {{
          if (!seen.has(reg)) {{
            seen.add(reg);
            ordered.push(reg);
          }}
        }}
      }}
      return ordered;
    }}

    function renderCircuit() {{
      const depth = selectedDepth();
      const expanded = selectedModules();
      const ops = flattenCircuit(data.root, 0, expanded, depth);
      const regs = registerOrder(ops);
      document.getElementById('depthValue').textContent = String(depth);
      if (!ops.length || !regs.length) {{
        content.innerHTML = '<div class="empty">No circuit operations to render.</div>';
        return;
      }}
      const rowIndex = new Map(regs.map((reg, idx) => [reg, idx + 1]));
      const colWidth = 124;
      const rowHeight = 44;
      let html = `<div class="circuit-wrap"><div class="circuit-grid" style="grid-template-columns: 170px repeat(${{ops.length}}, ${{colWidth}}px); grid-template-rows: repeat(${{regs.length}}, ${{rowHeight}}px)">`;
      regs.forEach((reg, idx) => {{
        const meta = data.registers.find(item => item.name === reg) || {{}};
        html += `<div class="reg-label" style="grid-column: 1; grid-row: ${{idx + 1}}">${{escapeHtml(reg)}}<span class="muted">[${{escapeHtml(meta.size || '?')}}]</span></div>`;
        html += `<div class="wire" style="grid-column: 2 / ${{ops.length + 2}}; grid-row: ${{idx + 1}}"></div>`;
      }});
      ops.forEach((op, idx) => {{
        const involved = involvedRegisters(op).filter(reg => rowIndex.has(reg));
        if (!involved.length) return;
        const rows = involved.map(reg => rowIndex.get(reg)).sort((a, b) => a - b);
        const start = rows[0];
        const span = rows[rows.length - 1] - rows[0] + 1;
        const col = idx + 2;
        const params = op.params?.length ? `\\nparams: ${{formatValue(op.params)}}` : '';
        const controls = op.controllerRegisters?.length ? `\\ncontrols: ${{op.controllerRegisters.join(', ')}}` : '';
        html += `<div class="vline" style="grid-column: ${{col}}; grid-row: ${{start}} / span ${{span}}"></div>`;
        html += `<div class="gate ${{op.kind}}" title="${{escapeHtml(op.path + params + controls)}}" style="grid-column: ${{col}}; grid-row: ${{start}} / span ${{span}}">${{escapeHtml(op.name)}}${{op.dagger ? '<sup>&dagger;</sup>' : ''}}</div>`;
      }});
      html += '</div></div>';
      content.innerHTML = html;
    }}

    function renderTree() {{
      document.getElementById('depthValue').textContent = String(selectedDepth());
      content.innerHTML = `<div class="tree-root">${{renderTreeNode(data.root, true)}}</div>`;
    }}

    function render(nextMode) {{
      if (nextMode === 'circuit') renderCircuit();
      else renderTree();
    }}

    renderSidebar();
    render(mode);
  </script>
</body>
</html>
"""
