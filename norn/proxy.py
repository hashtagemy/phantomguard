# norn/proxy.py
"""
Norn Proxy - Automatically monitors ALL Strands agents.
Users don't need to modify their code!
"""

import logging
from typing import Any, Optional
from strands import Agent
from strands.models import BedrockModel

from norn.core.interceptor import NornHook
from norn.models.schemas import TaskDefinition

logger = logging.getLogger("norn.proxy")

# Store original Agent class
_OriginalAgent = Agent


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


# Monkey-patch: Replace Strands Agent globally
def enable_global_monitoring(
    mode: str = "monitor",
    auto_task_detection: bool = True,
    norn_url: Optional[str] = None,
):
    """
    Enable Norn for ALL agents in the application.

    Call this once at the start of your application:

    ```python
    from norn.proxy import enable_global_monitoring

    enable_global_monitoring(norn_url="http://localhost:8000")

    # Now ALL Agent() calls are automatically monitored on the dashboard!
    from strands import Agent
    agent = Agent(...)  # ← Automatically monitored!
    ```

    Args:
        mode: "monitor" or "intervene"
        auto_task_detection: Try to detect task from system prompt
        norn_url: Dashboard API URL. If set, steps are streamed to the dashboard.
    """
    import strands

    # Replace Agent class globally
    original_agent_init = strands.Agent.__init__

    def monitored_init(self, *args, **kwargs):
        task = None
        if auto_task_detection and 'system_prompt' in kwargs:
            task = TaskDefinition(description=kwargs['system_prompt'][:200])

        guard = NornHook(
            task=task,
            mode=mode,
            enable_ai_eval=True,
            norn_url=norn_url,
        )

        existing_hooks = kwargs.get('hooks', [])
        kwargs['hooks'] = existing_hooks + [guard]

        self._norn = guard
        original_agent_init(self, *args, **kwargs)

    # Monkey-patch
    strands.Agent.__init__ = monitored_init
    strands.Agent.quality_report = property(
        lambda self: getattr(self, '_norn', None).session_report
        if hasattr(self, '_norn') and self._norn else None
    )

    logger.info("Norn global monitoring enabled - ALL agents will be monitored")
