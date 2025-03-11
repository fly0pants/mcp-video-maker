# 代理包初始化文件
from agents.base_agent import BaseAgent
from agents.central_agent import CentralAgent
from agents.content_agent import ContentAgent
from agents.visual_agent import VisualAgent
from agents.audio_agent import AudioAgent
from agents.postprod_agent import PostProdAgent
from agents.distribution_agent import DistributionAgent
from agents.storyboard_agent import StoryboardAgent

# MCP 代理
from agents.mcp_base_agent import MCPBaseAgent
from agents.mcp_central_agent import MCPCentralAgent
from agents.mcp_content_agent import MCPContentAgent
from agents.mcp_visual_agent import MCPVisualAgent
from agents.mcp_storyboard_agent import MCPStoryboardAgent

# 弃用警告
import warnings

# 标记旧版代理为弃用
warnings.warn(
    "The old agent classes (BaseAgent, CentralAgent, etc.) are deprecated and will be removed in a future version. "
    "Use the MCP-based agent classes (MCPBaseAgent, MCPCentralAgent, etc.) instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    # 旧版代理 (已弃用)
    'BaseAgent',
    'CentralAgent',
    'ContentAgent',
    'VisualAgent',
    'AudioAgent',
    'PostProdAgent',
    'DistributionAgent',
    'StoryboardAgent',
    
    # MCP 代理
    'MCPBaseAgent',
    'MCPCentralAgent',
    'MCPContentAgent',
    'MCPVisualAgent',
    'MCPStoryboardAgent'
] 