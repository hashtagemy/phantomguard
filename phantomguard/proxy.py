# phantomguard/proxy.py
"""
PhantomGuard Proxy - Automatically monitors ALL Strands agents.
Users don't need to modify their code!
"""

import logging
from typing import Any, Optional
from strands import Agent
from strands.models import BedrockModel

from phantomguard.core.interceptor import PhantomGuardHook
from phantomguard.models.schemas import TaskDefinition

logger = logging.getLogger("phantomguard.proxy")

# Store original Agent class
_OriginalAgent = Agent


class MonitoredAgent(Agent):
    """
    Drop-in replacement for Strands Agent that automatically includes PhantomGuard.
    
    Usage:
        # Instead of:
        from strands import Agent
        
        # Use:
        from phantomguard.proxy import Agent
        
        # Everything else stays the same!
        agent = Agent(model=..., tools=...)
    """
    
    def __init__(
        self,
        *args,
        phantomguard_enabled: bool = True,
        phantomguard_mode: str = "monitor",
        phantomguard_task: Optional[str] = None,
        **kwargs
    ):
        """
        Create agent with automatic PhantomGuard monitoring.
        
        Args:
            phantomguard_enabled: Enable/disable monitoring
            phantomguard_mode: "monitor" or "intervene"
            phantomguard_task: Task description for quality evaluation
            *args, **kwargs: Standard Agent parameters
        """
        # Add PhantomGuard hook automatically
        if phantomguard_enabled:
            task = TaskDefinition(description=phantomguard_task) if phantomguard_task else None
            guard = PhantomGuardHook(
                task=task,
                mode=phantomguard_mode,
                enable_ai_eval=True,
                enable_shadow_browser=False,  # Can be enabled via env var
            )
            
            # Add to hooks
            existing_hooks = kwargs.get('hooks', [])
            kwargs['hooks'] = existing_hooks + [guard]
            
            # Store guard reference for later access
            self._phantomguard = guard
            
            logger.info("PhantomGuard monitoring enabled for agent")
        else:
            self._phantomguard = None
        
        # Initialize parent Agent
        super().__init__(*args, **kwargs)
    
    @property
    def quality_report(self):
        """Get PhantomGuard quality report."""
        if self._phantomguard:
            return self._phantomguard.session_report
        return None
    
    @property
    def security_score(self):
        """Get security score."""
        if self._phantomguard and self._phantomguard.session_report:
            return self._phantomguard.session_report.security_score
        return None


# Monkey-patch: Replace Strands Agent globally
def enable_global_monitoring(
    mode: str = "monitor",
    auto_task_detection: bool = True
):
    """
    Enable PhantomGuard for ALL agents in the application.
    
    Call this once at the start of your application:
    
    ```python
    from phantomguard.proxy import enable_global_monitoring
    
    # Enable monitoring for all agents
    enable_global_monitoring()
    
    # Now ALL Agent() calls are automatically monitored!
    from strands import Agent
    agent = Agent(...)  # ← Automatically monitored!
    ```
    
    Args:
        mode: "monitor" or "intervene"
        auto_task_detection: Try to detect task from system prompt
    """
    import strands
    
    # Replace Agent class globally
    original_agent_init = strands.Agent.__init__
    
    def monitored_init(self, *args, **kwargs):
        # Add PhantomGuard automatically
        task = None
        if auto_task_detection and 'system_prompt' in kwargs:
            # Try to extract task from system prompt
            task = TaskDefinition(description=kwargs['system_prompt'][:200])
        
        guard = PhantomGuardHook(
            task=task,
            mode=mode,
            enable_ai_eval=True,
        )
        
        existing_hooks = kwargs.get('hooks', [])
        kwargs['hooks'] = existing_hooks + [guard]
        
        # Store guard reference
        self._phantomguard = guard
        
        # Call original init
        original_agent_init(self, *args, **kwargs)
    
    # Monkey-patch
    strands.Agent.__init__ = monitored_init
    strands.Agent.quality_report = property(lambda self: getattr(self, '_phantomguard', None).session_report if hasattr(self, '_phantomguard') and self._phantomguard else None)
    
    logger.info("PhantomGuard global monitoring enabled - ALL agents will be monitored")


# Environment variable support
import os
if os.getenv("PHANTOMGUARD_AUTO_ENABLE", "").lower() == "true":
    enable_global_monitoring(
        mode=os.getenv("PHANTOMGUARD_MODE", "monitor")
    )
    logger.info("PhantomGuard auto-enabled via environment variable")
