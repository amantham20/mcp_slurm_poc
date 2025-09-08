#!/usr/bin/env python3
"""
MCP Server for Slurm Cluster Monitoring
Provides tools to check Slurm system status, nodes, jobs, and queue information.
"""

import asyncio
import json
import subprocess
import sys
from typing import Any, Dict, List, Optional
import paramiko
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Configuration for connecting to Slurm controller
SLURM_HOST = "localhost"
SLURM_PORT = 2222
SLURM_USER = "root"
SLURM_PASSWORD = "slurm123"

class SlurmMCPServer:
    def __init__(self):
        self.ssh_client = None
        
    async def connect_to_slurm(self):
        """Establish SSH connection to Slurm controller"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(
                hostname=SLURM_HOST,
                port=SLURM_PORT,
                username=SLURM_USER,
                password=SLURM_PASSWORD,
                timeout=10
            )
            return True
        except Exception as e:
            print(f"Failed to connect to Slurm controller: {e}")
            return False
    
    async def execute_slurm_command(self, command: str) -> Dict[str, Any]:
        """Execute a command on the Slurm controller"""
        if not self.ssh_client:
            if not await self.connect_to_slurm():
                return {"error": "Cannot connect to Slurm controller"}
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            
            stdout_data = stdout.read().decode('utf-8')
            stderr_data = stderr.read().decode('utf-8')
            
            return {
                "exit_status": exit_status,
                "stdout": stdout_data,
                "stderr": stderr_data,
                "success": exit_status == 0
            }
        except Exception as e:
            return {"error": str(e), "success": False}

# Initialize the MCP server
server = Server("slurm-mcp-server")
slurm_server = SlurmMCPServer()

@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available Slurm monitoring tools"""
    return [
        types.Tool(
            name="check_slurm_status",
            description="Check overall Slurm system status and controller health",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="list_nodes",
            description="List all Slurm compute nodes and their status",
            inputSchema={
                "type": "object",
                "properties": {
                    "detailed": {
                        "type": "boolean",
                        "description": "Include detailed node information",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="list_jobs",
            description="List active jobs in the Slurm queue",
            inputSchema={
                "type": "object",
                "properties": {
                    "user": {
                        "type": "string",
                        "description": "Filter jobs by username"
                    },
                    "state": {
                        "type": "string",
                        "description": "Filter jobs by state (PENDING, RUNNING, COMPLETED, etc.)"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="show_queue",
            description="Show the current job queue status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="node_health_check",
            description="Perform detailed health check on specific node",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_name": {
                        "type": "string",
                        "description": "Name of the node to check (e.g., node1, node2, node3)"
                    }
                },
                "required": ["node_name"]
            }
        ),
        types.Tool(
            name="cluster_utilization",
            description="Get cluster resource utilization statistics",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="submit_test_job",
            description="Submit a test job to verify cluster functionality",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to run in the test job",
                        "default": "hostname && sleep 30"
                    },
                    "partition": {
                        "type": "string",
                        "description": "Partition to submit job to",
                        "default": "debug"
                    }
                },
                "required": []
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls for Slurm operations"""
    
    if name == "check_slurm_status":
        result = await slurm_server.execute_slurm_command("sinfo && scontrol ping")
        if result.get("success"):
            return [types.TextContent(
                type="text",
                text=f"Slurm System Status:\n\n{result['stdout']}\n\nController is responsive and healthy."
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"Slurm System Error:\n{result.get('error', result.get('stderr', 'Unknown error'))}"
            )]
    
    elif name == "list_nodes":
        detailed = arguments.get("detailed", False)
        command = "sinfo -N -l" if detailed else "sinfo -N"
        result = await slurm_server.execute_slurm_command(command)
        
        if result.get("success"):
            return [types.TextContent(
                type="text",
                text=f"Slurm Nodes:\n\n{result['stdout']}"
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"Error listing nodes:\n{result.get('error', result.get('stderr', 'Unknown error'))}"
            )]
    
    elif name == "list_jobs":
        user_filter = arguments.get("user", "")
        state_filter = arguments.get("state", "")
        
        command = "squeue -l"
        if user_filter:
            command += f" -u {user_filter}"
        if state_filter:
            command += f" -t {state_filter}"
            
        result = await slurm_server.execute_slurm_command(command)
        
        if result.get("success"):
            return [types.TextContent(
                type="text",
                text=f"Slurm Jobs:\n\n{result['stdout']}"
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"Error listing jobs:\n{result.get('error', result.get('stderr', 'Unknown error'))}"
            )]
    
    elif name == "show_queue":
        result = await slurm_server.execute_slurm_command("squeue && echo '\n--- Queue Summary ---' && squeue -t PD,R --format='%.8i %.2t %.10u %.20j %.8Q' | tail -n +2 | awk '{pending+=($2==\"PD\"); running+=($2==\"R\")} END {print \"Pending jobs:\", pending+0; print \"Running jobs:\", running+0}'")
        
        if result.get("success"):
            return [types.TextContent(
                type="text",
                text=f"Job Queue Status:\n\n{result['stdout']}"
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"Error showing queue:\n{result.get('error', result.get('stderr', 'Unknown error'))}"
            )]
    
    elif name == "node_health_check":
        node_name = arguments.get("node_name")
        if not node_name:
            return [types.TextContent(
                type="text",
                text="Error: node_name is required"
            )]
        
        command = f"scontrol show node {node_name} && srun -w {node_name} --immediate=60 hostname"
        result = await slurm_server.execute_slurm_command(command)
        
        if result.get("success"):
            return [types.TextContent(
                type="text",
                text=f"Health Check for {node_name}:\n\n{result['stdout']}"
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"Error checking node {node_name}:\n{result.get('error', result.get('stderr', 'Unknown error'))}"
            )]
    
    elif name == "cluster_utilization":
        command = "sinfo -o '%P %.5D %.11T %.4c %.8z %.6m %.8d %.6w %.8f %20E' && echo '\n--- Resource Summary ---' && sinfo -h -o '%D %T' | awk '{total+=$1; if($2==\"idle\") idle+=$1; if($2==\"alloc\") alloc+=$1; if($2==\"down\") down+=$1} END {print \"Total nodes:\", total; print \"Idle nodes:\", idle+0; print \"Allocated nodes:\", alloc+0; print \"Down nodes:\", down+0; if(total>0) print \"Utilization:\", ((alloc+0)/total)*100\"%\";}'"
        result = await slurm_server.execute_slurm_command(command)
        
        if result.get("success"):
            return [types.TextContent(
                type="text",
                text=f"Cluster Utilization:\n\n{result['stdout']}"
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"Error getting utilization:\n{result.get('error', result.get('stderr', 'Unknown error'))}"
            )]
    
    elif name == "submit_test_job":
        command = arguments.get("command", "hostname && sleep 10")
        partition = arguments.get("partition", "debug")
        
        slurm_command = f"sbatch --partition={partition} --job-name=mcp-test --output=/tmp/test-job-%j.out --wrap='{command}'"
        result = await slurm_server.execute_slurm_command(slurm_command)
        
        if result.get("success"):
            return [types.TextContent(
                type="text",
                text=f"Test Job Submitted:\n\n{result['stdout']}\n\nUse 'list_jobs' to monitor the job status."
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"Error submitting test job:\n{result.get('error', result.get('stderr', 'Unknown error'))}"
            )]
    
    elif name == "check_job_history":
        last_n = arguments.get("last_n_jobs", 10)
        
        command = f"tail -n {last_n * 5} /var/log/slurm/job_completions.log 2>/dev/null || echo 'No job completion log found yet'"
        result = await slurm_server.execute_slurm_command(command)
        
        if result.get("success"):
            return [types.TextContent(
                type="text",
                text=f"Recent Job Completions:\n\n{result['stdout']}"
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"Error checking job history:\n{result.get('error', result.get('stderr', 'Unknown error'))}"
            )]
    
    else:
        return [types.TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="slurm-mcp-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())