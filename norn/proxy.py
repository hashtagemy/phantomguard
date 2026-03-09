# norn/proxy.py
"""
Norn Proxy — MonitoredAgent wrapper for Strands agents.
"""

import logging
from typing import Optional
from strands import Agent

from norn.core.interceptor import NornHook
from norn.models.schemas import TaskDefinition

logger = logging.getLogger("norn.proxy")


class MonitoredAgent(Agent):
    """
    Drop-in replacement for Strands Agent that automatically includes Norn.
    
    Usage:
        # Instead of:
        from strands import Agent
        
        # Use:
        from norn.proxy import Agent
        
        # Everything else stays the same!
        agent = Agent(model=..., tools=...)
    """
    
    def __init__(
        self,
        *args,
        norn_enabled: bool = True,
        norn_mode: str = "monitor",
        norn_task: Optional[str] = None,
        **kwargs
    ):
        """
        Create agent with automatic Norn monitoring.
        
        Args:
            norn_enabled: Enable/disable monitoring
            norn_mode: "monitor" or "intervene"
            norn_task: Task description for quality evaluation
            *args, **kwargs: Standard Agent parameters
        """
        # Add Norn hook automatically
        if norn_enabled:
            task = TaskDefinition(description=norn_task) if norn_task else None
            guard = NornHook(
                task=task,
                mode=norn_mode,
                enable_ai_eval=True,
                enable_shadow_browser=False,  # Can be enabled via env var
            )
            
            # Add to hooks
            existing_hooks = kwargs.get('hooks', [])
            kwargs['hooks'] = existing_hooks + [guard]
            
            # Store guard reference for later access
            self._norn = guard
            
            logger.info("Norn monitoring enabled for agent")
        else:
            self._norn = None
        
        # Initialize parent Agent
        super().__init__(*args, **kwargs)
    
    @property
    def quality_report(self):
        """Get Norn quality report."""
        if self._norn:
            return self._norn.session_report
        return None
    
    @property
    def security_score(self):
        """Get security score."""
        if self._norn and self._norn.session_report:
            return self._norn.session_report.security_score
        return None
