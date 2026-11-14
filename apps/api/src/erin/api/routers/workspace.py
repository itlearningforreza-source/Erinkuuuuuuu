from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from decimal import Decimal

from erin.api.core.database import get_sqlite_db, sqlite_transaction
from erin.api.models import NotebookResponse, NotebookBase, NotebookCell, KernelSpec
import json
import secrets
from erin.api.routers.auth import get_current_user
from typing import Optional

router = APIRouter(prefix="/api/v1/workspace", tags=["workspace"])

@router.get("/notebooks", response_model=List[NotebookResponse])
async def get_notebooks(current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM notebooks WHERE user_id = ? ORDER BY updated_at DESC",
            (current_user["id"],)
        )
        notebooks = []
        for row in cursor.fetchall():
            nb = dict(row)
            nb["cells"] = json.loads(nb["cells"])
            nb["kernel_spec"] = json.loads(nb["kernel_spec"])
            nb["metadata"] = json.loads(nb["metadata"]) if nb["metadata"] else {}
            notebooks.append(NotebookResponse(**nb))
        return notebooks

@router.post("/notebooks", response_model=NotebookResponse, status_code=status.HTTP_201_CREATED)
async def create_notebook(notebook: NotebookBase, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        nb_id = secrets.token_urlsafe(16)
        now = datetime.utcnow()
        kernel_spec = KernelSpec(name="python3", display_name="Python 3", language="python")
        conn.execute(
            """INSERT INTO notebooks (id, user_id, title, cells, kernel_spec, metadata, version, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (nb_id, current_user["id"], notebook.title, json.dumps([]),
             json.dumps(kernel_spec.dict()), json.dumps({}), 1, now, now)
        )
        
        cursor = conn.execute("SELECT * FROM notebooks WHERE id = ?", (nb_id,))
        nb = dict(cursor.fetchone())
        nb["cells"] = json.loads(nb["cells"])
        nb["kernel_spec"] = json.loads(nb["kernel_spec"])
        nb["metadata"] = json.loads(nb["metadata"]) if nb["metadata"] else {}
        return NotebookResponse(**nb)

@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def get_notebook(notebook_id: str, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM notebooks WHERE id = ? AND user_id = ?",
            (notebook_id, current_user["id"])
        )
        nb = cursor.fetchone()
        if not nb:
            raise HTTPException(status_code=404, detail="Notebook not found")
        
        nb_dict = dict(nb)
        nb_dict["cells"] = json.loads(nb_dict["cells"])
        nb_dict["kernel_spec"] = json.loads(nb_dict["kernel_spec"])
        nb_dict["metadata"] = json.loads(nb_dict["metadata"]) if nb_dict["metadata"] else {}
        return NotebookResponse(**nb_dict)

@router.put("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def update_notebook(
    notebook_id: str,
    cells: List[NotebookCell],
    version: int,
    current_user = Depends(get_current_user),
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM notebooks WHERE id = ? AND user_id = ? AND version = ?",
            (notebook_id, current_user["id"], version)
        )
        nb = cursor.fetchone()
        if not nb:
            raise HTTPException(status_code=409, detail="Notebook not found or version conflict")
        
        now = datetime.utcnow()
        new_version = version + 1
        conn.execute(
            """UPDATE notebooks SET cells = ?, version = ?, updated_at = ?, last_executed_at = ?
               WHERE id = ?""",
            (json.dumps([c.dict() for c in cells]), new_version, now, now, notebook_id)
        )
        
        cursor = conn.execute("SELECT * FROM notebooks WHERE id = ?", (notebook_id,))
        nb = dict(cursor.fetchone())
        nb["cells"] = json.loads(nb["cells"])
        nb["kernel_spec"] = json.loads(nb["kernel_spec"])
        nb["metadata"] = json.loads(nb["metadata"]) if nb["metadata"] else {}
        return NotebookResponse(**nb)

@router.post("/notebooks/{notebook_id}/execute", response_model=Dict[str, str])
async def execute_notebook_cell(
    notebook_id: str,
    cell_id: str,
    code: str,
    current_user = Depends(get_current_user),
    db = Depends(get_sqlite_db)
):
    # In a real implementation, this would execute the code in a Jupyter kernel
    raise HTTPException(status_code=501, detail="Not implemented")

# Workspaces
class WorkspaceBase(BaseModel):
    name: str
    layout: Dict[str, Any]
    watchlist_ids: List[str] = []
    chart_configs: Dict[str, Any] = {}
    notebook_ids: List[str] = []

class WorkspaceResponse(WorkspaceBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

@router.get("/workspaces", response_model=List[WorkspaceResponse])
async def get_workspaces(current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM workspaces WHERE user_id = ? ORDER BY updated_at DESC",
            (current_user["id"],)
        )
        workspaces = []
        for row in cursor.fetchall():
            ws = dict(row)
            ws["watchlist_ids"] = json.loads(ws["watchlist_ids"]) if ws["watchlist_ids"] else []
            ws["chart_configs"] = json.loads(ws["chart_configs"]) if ws["chart_configs"] else {}
            ws["notebook_ids"] = json.loads(ws["notebook_ids"]) if ws["notebook_ids"] else []
            workspaces.append(WorkspaceResponse(**ws))
        return workspaces

@router.post("/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(workspace: WorkspaceBase, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        ws_id = secrets.token_urlsafe(16)
        now = datetime.utcnow()
        conn.execute(
            """INSERT INTO workspaces (id, user_id, name, layout, watchlist_ids, chart_configs, notebook_ids, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ws_id, current_user["id"], workspace.name, json.dumps(workspace.layout),
             json.dumps(workspace.watchlist_ids), json.dumps(workspace.chart_configs),
             json.dumps(workspace.notebook_ids), now, now)
        )
        
        cursor = conn.execute("SELECT * FROM workspaces WHERE id = ?", (ws_id,))
        ws = dict(cursor.fetchone())
        ws["watchlist_ids"] = json.loads(ws["watchlist_ids"])
        ws["chart_configs"] = json.loads(ws["chart_configs"])
        ws["notebook_ids"] = json.loads(ws["notebook_ids"])
        return WorkspaceResponse(**ws)

@router.get("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(workspace_id: str, current_user = Depends(get_current_user), db = Depends(get_sqlite_db)):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM workspaces WHERE id = ? AND user_id = ?",
            (workspace_id, current_user["id"])
        )
        ws = cursor.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        ws_dict = dict(ws)
        ws_dict["watchlist_ids"] = json.loads(ws_dict["watchlist_ids"])
        ws_dict["chart_configs"] = json.loads(ws_dict["chart_configs"])
        ws_dict["notebook_ids"] = json.loads(ws_dict["notebook_ids"])
        return WorkspaceResponse(**ws_dict)

@router.put("/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    layout: Optional[Dict[str, Any]] = None,
    watchlist_ids: Optional[List[str]] = None,
    chart_configs: Optional[Dict[str, Any]] = None,
    notebook_ids: Optional[List[str]] = None,
    current_user = Depends(get_current_user),
    db = Depends(get_sqlite_db)
):
    with sqlite_transaction() as conn:
        cursor = conn.execute(
            "SELECT * FROM workspaces WHERE id = ? AND user_id = ?",
            (workspace_id, current_user["id"])
        )
        ws = cursor.fetchone()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        
        updates = []
        params = []
        if layout is not None:
            updates.append("layout = ?")
            params.append(json.dumps(layout))
        if watchlist_ids is not None:
            updates.append("watchlist_ids = ?")
            params.append(json.dumps(watchlist_ids))
        if chart_configs is not None:
            updates.append("chart_configs = ?")
            params.append(json.dumps(chart_configs))
        if notebook_ids is not None:
            updates.append("notebook_ids = ?")
            params.append(json.dumps(notebook_ids))
        
        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.utcnow())
            params.append(workspace_id)
            conn.execute(f"UPDATE workspaces SET {', '.join(updates)} WHERE id = ?", params)
        
        cursor = conn.execute("SELECT * FROM workspaces WHERE id = ?", (workspace_id,))
        ws = dict(cursor.fetchone())
        ws["watchlist_ids"] = json.loads(ws["watchlist_ids"])
        ws["chart_configs"] = json.loads(ws["chart_configs"])
        ws["notebook_ids"] = json.loads(ws["notebook_ids"])
        return WorkspaceResponse(**ws)

