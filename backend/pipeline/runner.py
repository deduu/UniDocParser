import importlib
import pkgutil
from typing import Dict, Any, List, Type

from backend.config.settings import get_settings
from backend.core.interfaces import PipelineStep

class PipelineRunner:
    """
    Dynamically constructs and executes processing pipelines.
    
    This class reads pipeline definitions from the configuration, discovers all
    available step implementations, and runs the steps for a given pipeline.
    """

    def __init__(self):
        self.settings = get_settings()
        self.pipelines_config: List[Dict[str, Any]] = self.settings.pipelines_config
        self.steps_map: Dict[str, Type[PipelineStep]] = self._discover_steps()

    def _discover_steps(self) -> Dict[str, Type[PipelineStep]]:
        """
        Dynamically imports all PipelineStep classes from the 'steps' module.
        It maps the class name to the class itself.
        """
        steps_map = {}
        steps_module_path = "unidoc_agent.backend.pipeline.steps"
        
        try:
            # Import the top-level 'steps' package
            module = importlib.import_module(steps_module_path)
            # Iterate through all sub-modules in the package
            for _, modname, _ in pkgutil.walk_packages(module.__path__, module.__name__ + '.'):
                sub_module = importlib.import_module(modname)
                # Find classes within the sub-module that are PipelineSteps
                for attribute_name in dir(sub_module):
                    attribute = getattr(sub_module, attribute_name)
                    if isinstance(attribute, type) and issubclass(attribute, PipelineStep) and attribute is not PipelineStep:
                        # Use the class name as the key
                        steps_map[attribute.__name__] = attribute
        except ImportError as e:
            print(f"Could not import steps module: {e}. Please ensure it and its submodules exist.")
        
        return steps_map

    def run(self, pipeline_name: str, initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a named pipeline.

        Args:
            pipeline_name: The name of the pipeline to run (must be in pipelines.yaml).
            initial_context: The starting data for the pipeline.

        Returns:
            The final context after all steps have been executed.
        """
        print(f"INFO: Starting pipeline '{pipeline_name}'...")
        
        pipeline_config = next((p for p in self.pipelines_config if p['name'] == pipeline_name), None)
        
        if not pipeline_config:
            raise ValueError(f"Pipeline '{pipeline_name}' not found in configuration.")

        context = initial_context
        step_names = pipeline_config.get('steps', [])
        
        for step_name in step_names:
            if step_name not in self.steps_map:
                print(f"WARN: Step '{step_name}' not found in discovered steps. Skipping.")
                continue

            step_class = self.steps_map[step_name]
            step_instance = step_class() # Instantiate the step
            
            print(f"INFO: Executing step '{step_name}'...")
            try:
                context = step_instance.execute(context)
                print(f"INFO: Step '{step_name}' completed.")
            except Exception as e:
                print(f"ERROR: Step '{step_name}' failed: {e}")
                raise e # Re-raise the exception to stop the pipeline

        print(f"INFO: Pipeline '{pipeline_name}' finished.")
        return context

# Singleton instance for easy access
pipeline_runner = PipelineRunner()