"""Research Notebook Service - Jupyter kernel integration for financial research."""

import asyncio
import logging
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erin.data_infra.storage.sqlite import SQLiteStorage

logger = logging.getLogger(__name__)


class NotebookService:
    """Service for managing research notebooks with Jupyter kernel integration."""

    def __init__(self, storage: 'SQLiteStorage'):
        self.storage = storage
        self._kernels: Dict[str, Any] = {}
        self._kernel_manager = None

    async def initialize_kernel(self):
        """Initialize Jupyter kernel manager."""
        try:
            from jupyter_client import KernelManager
            self._kernel_manager = KernelManager(kernel_name='python3')
            self._kernel_manager.start_kernel()
            logger.info("Jupyter kernel initialized")
        except ImportError:
            logger.warning("jupyter_client not available, notebook execution disabled")
        except Exception as e:
            logger.error(f"Failed to initialize kernel: {e}")

    async def create_notebook(
        self,
        user_id: str,
        title: str,
        kernel_spec: Dict = None
    ) -> str:
        """Create a new research notebook."""
        notebook_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        default_kernel_spec = {
            "name": "python3",
            "display_name": "Python 3",
            "language": "python",
            "argv": ["python", "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "env": {}
        }
        
        notebook_data = {
            "id": notebook_id,
            "user_id": user_id,
            "title": title,
            "cells": [],
            "kernel_spec": kernel_spec or default_kernel_spec,
            "metadata": {},
            "version": 1,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "last_executed_at": None
        }
        
        self.storage.create_notebook(notebook_data)
        return notebook_id

    async def get_notebook(self, notebook_id: str, user_id: str) -> Optional[Dict]:
        """Get notebook by ID."""
        return self.storage.get_notebook(notebook_id, user_id)

    async def get_user_notebooks(self, user_id: str) -> List[Dict]:
        """Get all notebooks for a user."""
        return self.storage.get_notebooks(user_id)

    async def update_notebook(
        self,
        notebook_id: str,
        user_id: str,
        title: str = None,
        cells: List[Dict] = None,
        metadata: Dict = None
    ) -> Optional[Dict]:
        """Update notebook."""
        notebook = await self.get_notebook(notebook_id, user_id)
        if not notebook:
            return None
        
        if title is not None:
            notebook["title"] = title
        if cells is not None:
            notebook["cells"] = cells
            notebook["version"] += 1
        if metadata is not None:
            notebook["metadata"] = metadata
        
        notebook["updated_at"] = datetime.utcnow().isoformat()
        
        self.storage.update_notebook(notebook_id, notebook)
        return notebook

    async def delete_notebook(self, notebook_id: str, user_id: str) -> bool:
        """Delete notebook."""
        return self.storage.delete_notebook(notebook_id, user_id)

    async def add_cell(
        self,
        notebook_id: str,
        user_id: str,
        cell_type: str,  # "code" or "markdown"
        source: str,
        outputs: List[Dict] = None,
        execution_count: int = None
    ) -> Optional[Dict]:
        """Add a cell to notebook."""
        notebook = await self.get_notebook(notebook_id, user_id)
        if not notebook:
            return None
        
        cell = {
            "id": str(uuid.uuid4()),
            "cell_type": cell_type,
            "source": source,
            "outputs": outputs or [],
            "execution_count": execution_count,
            "metadata": {}
        }
        
        notebook["cells"].append(cell)
        notebook["updated_at"] = datetime.utcnow().isoformat()
        
        self.storage.update_notebook(notebook_id, notebook)
        return cell

    async def execute_cell(
        self,
        notebook_id: str,
        user_id: str,
        cell_id: str,
        code: str
    ) -> Dict:
        """Execute a code cell in the Jupyter kernel."""
        if not self._kernel_manager:
            await self.initialize_kernel()
        
        if not self._kernel_manager:
            return {"error": "Kernel not available", "outputs": []}
        
        try:
            # Get kernel client
            kc = self._kernel_manager.client()
            kc.start_channels()
            
            # Execute code
            msg_id = kc.execute(code)
            
            # Wait for results
            outputs = []
            while True:
                msg = kc.get_iopub_msg(timeout=30)
                if msg["parent_header"].get("msg_id") == msg_id:
                    msg_type = msg["msg_type"]
                    content = msg["content"]
                    
                    if msg_type == "stream":
                        outputs.append({
                            "output_type": "stream",
                            "name": content["name"],
                            "text": content["text"]
                        })
                    elif msg_type == "execute_result":
                        outputs.append({
                            "output_type": "execute_result",
                            "data": content["data"],
                            "metadata": content["metadata"],
                            "execution_count": content["execution_count"]
                        })
                    elif msg_type == "error":
                        outputs.append({
                            "output_type": "error",
                            "ename": content["ename"],
                            "evalue": content["evalue"],
                            "traceback": content["traceback"]
                        })
                    elif msg_type == "status" and content["execution_state"] == "idle":
                        break
            
            kc.stop_channels()
            
            return {
                "cell_id": cell_id,
                "outputs": outputs,
                "execution_count": msg.get("content", {}).get("execution_count")
            }
            
        except Exception as e:
            logger.error(f"Cell execution failed: {e}")
            return {"error": str(e), "outputs": []}

    async def execute_notebook(
        self,
        notebook_id: str,
        user_id: str
    ) -> Dict:
        """Execute all code cells in a notebook sequentially."""
        notebook = await self.get_notebook(notebook_id, user_id)
        if not notebook:
            return {"error": "Notebook not found"}
        
        results = []
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                result = await self.execute_cell(notebook_id, user_id, cell["id"], cell["source"])
                cell["outputs"] = result.get("outputs", [])
                cell["execution_count"] = result.get("execution_count")
                results.append({
                    "cell_id": cell["id"],
                    "success": "error" not in result,
                    "outputs": result.get("outputs", [])
                })
        
        notebook["last_executed_at"] = datetime.utcnow().isoformat()
        self.storage.update_notebook(notebook_id, notebook)
        
        return {
            "notebook_id": notebook_id,
            "executed_cells": len(results),
            "results": results
        }

    async def export_notebook(
        self,
        notebook_id: str,
        user_id: str,
        format: str = "ipynb"
    ) -> Optional[str]:
        """Export notebook to various formats."""
        notebook = await self.get_notebook(notebook_id, user_id)
        if not notebook:
            return None
        
        if format == "ipynb":
            # Convert to Jupyter notebook format
            nb = {
                "cells": [],
                "metadata": {
                    "kernelspec": notebook["kernel_spec"],
                    "language_info": {
                        "name": "python",
                        "version": "3.12"
                    }
                },
                "nbformat": 4,
                "nbformat_minor": 5
            }
            
            for cell in notebook["cells"]:
                if cell["cell_type"] == "code":
                    nb["cells"].append({
                        "cell_type": "code",
                        "source": cell["source"].split("\n"),
                        "outputs": cell.get("outputs", []),
                        "execution_count": cell.get("execution_count"),
                        "metadata": cell.get("metadata", {})
                    })
                else:
                    nb["cells"].append({
                        "cell_type": "markdown",
                        "source": cell["source"].split("\n"),
                        "metadata": cell.get("metadata", {})
                    })
            
            return json.dumps(nb, indent=2)
        
        return None

    async def import_notebook(
        self,
        user_id: str,
        content: str,
        format: str = "ipynb"
    ) -> str:
        """Import notebook from various formats."""
        if format == "ipynb":
            nb = json.loads(content)
            
            cells = []
            for cell in nb.get("cells", []):
                source = "\n".join(cell.get("source", []))
                cells.append({
                    "id": str(uuid.uuid4()),
                    "cell_type": cell["cell_type"],
                    "source": source,
                    "outputs": cell.get("outputs", []),
                    "execution_count": cell.get("execution_count"),
                    "metadata": cell.get("metadata", {})
                })
            
            kernel_spec = nb.get("metadata", {}).get("kernelspec", {
                "name": "python3",
                "display_name": "Python 3",
                "language": "python"
            })
            
            return await self.create_notebook(
                user_id=user_id,
                title=nb.get("metadata", {}).get("title", "Imported Notebook"),
                kernel_spec=kernel_spec
            )
        
        return None

    async def install_packages(self, packages: List[str]) -> Dict:
        """Install Python packages in the kernel environment."""
        if not self._kernel_manager:
            await self.initialize_kernel()
        
        if not self._kernel_manager:
            return {"error": "Kernel not available"}
        
        try:
            code = f"import sys; import subprocess; subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + {packages})"
            kc = self._kernel_manager.client()
            kc.start_channels()
            msg_id = kc.execute(code)
            
            while True:
                msg = kc.get_iopub_msg(timeout=120)
                if msg["parent_header"].get("msg_id") == msg_id:
                    if msg["msg_type"] == "status" and msg["content"]["execution_state"] == "idle":
                        break
            
            kc.stop_channels()
            return {"success": True, "installed": packages}
        except Exception as e:
            return {"error": str(e)}

    async def get_kernel_info(self) -> Dict:
        """Get kernel information."""
        if not self._kernel_manager:
            await self.initialize_kernel()
        
        if self._kernel_manager:
            return {
                "kernel_name": self._kernel_manager.kernel_name,
                "has_kernel": True
            }
        return {"has_kernel": False}